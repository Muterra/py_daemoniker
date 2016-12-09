'''
LICENSING
-------------------------------------------------

daemoniker: Cross-platform daemonization tools.
    Copyright (C) 2016 Muterra, Inc.
    
    Contributors
    ------------
    Nick Badger
        badg@muterra.io | badg@nickbadger.com | nickbadger.com

    This library is free software; you can redistribute it and/or
    modify it under the terms of the GNU Lesser General Public
    License as published by the Free Software Foundation; either
    version 2.1 of the License, or (at your option) any later version.

    This library is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
    Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with this library; if not, write to the
    Free Software Foundation, Inc.,
    51 Franklin Street,
    Fifth Floor,
    Boston, MA  02110-1301 USA

------------------------------------------------------
'''

# Global dependencies
import logging
import traceback
import os
import sys
import signal
import pickle
import base64
import subprocess
import shlex
import tempfile
import atexit

# Intra-package dependencies
from .utils import platform_specificker
from .utils import default_to

from ._daemonize_common import _redirect_stds
from ._daemonize_common import _write_pid
from ._daemonize_common import _acquire_pidfile

_SUPPORTED_PLATFORM = platform_specificker(
    linux_choice = False,
    win_choice = True,
    # Dunno if this is a good idea but might as well try
    cygwin_choice = True,
    osx_choice = False,
    other_choice = False
)

# ###############################################
# Boilerplate
# ###############################################


logger = logging.getLogger(__name__)

# Control * imports.
__all__ = [
    # 'Inquisitor',
]


# ###############################################
# Library
# ###############################################


class Daemonizer:
    ''' Emulates Unix daemonization and registers all appropriate
    cleanup functions.
    
    with Daemonizer() as (is_setup, daemonize):
        if is_setup:
            setup_code_here()
        else:
            this_will_not_be_run_on_unix()
            
        *args = daemonize(*daemonizer_args, *args)
    '''
    
    def __init__(self):
        ''' Inspect the environment and determine if we're the parent
        or the child.
        '''
        self._is_parent = None
        self._daemonize_called = None
        
    def _daemonize(self, *args, **kwargs):
        ''' Very simple pass-through that does not exit the caller.
        '''
        self._daemonize_called = True
        
        if self._is_parent:
            return _daemonize1(*args, _exit_caller=False, **kwargs)
        
        else:
            return _daemonize2(*args, **kwargs)
        
    def __enter__(self):
        self._daemonize_called = False
        
        if '__INVOKE_DAEMON__' in os.environ:
            self._is_parent = False
            
        else:
            self._is_parent = True
            
        # In both cases, just return _is_parent and _daemonize
        return self._is_parent, self._daemonize
        
    def __exit__(self, exc_type, exc_value, exc_tb):
        ''' Exit doesn't really need to do any cleanup. But, it's needed
        for context managing.
        '''
        # This should only happen if __exit__ was called directly, without
        # first calling __enter__
        if self._daemonize_called is None:
            self._is_parent = None
            raise RuntimeError('Context manager was inappropriately exited.')
            
        # This will happen if we used the context manager, but never actually
        # called to daemonize.
        elif not self._daemonize_called:
            self._daemonize_called = None
            self._is_parent = None
            logger.warning('Daemonizer exited without calling daemonize.')
            # Note that any encountered error will be raise once the context is
            # departed, so there's no reason to handle or log errors here.
            return
            
        # We called to daemonize, and this is the parent.
        elif self._is_parent:
            # If there was an exception, give some information before the
            # summary self-execution that is os._exit
            if exc_type is not None:
                logger.error(
                    'Exception in parent:\n' +
                    ''.join(traceback.format_tb(exc_tb)) + '\n' +
                    repr(exc_value)
                )
                print(
                    'Exception in parent:\n' +
                    ''.join(traceback.format_tb(exc_tb)) + '\n' +
                    repr(exc_value),
                    file=sys.stderr
                )
                os._exit(2)
                
            else:
                os._exit(0)
            
        # We called to daemonize, and this is the child.
        else:
            return
            
            
def _capability_check(pythonw_path, script_path):
    ''' Does a compatibility and capability check.
    '''
    if not _SUPPORTED_PLATFORM:
        raise OSError(
            'The Windows Daemonizer cannot be used on the current '
            'platform.'
        )
        
    if not os.path.exists(pythonw_path):
        raise SystemExit(
            'pythonw.exe must be available in the same directory as the '
            'current Python interpreter to support Windows daemonization.'
        )
        
    if not os.path.exists(script_path):
        raise SystemExit(
            'Daemonizer cannot locate the script to daemonize (it seems '
            'to have lost itself).'
        )
    
    
def _filial_usurpation(chdir):
    ''' Changes our working directory, helping decouple the child
    process from the parent. Not necessary on windows, but could help
    standardize stuff for cross-platform apps.
    '''
    # Well this is certainly a stub.
    os.chdir(chdir)
        
        
def _clean_file(path):
    ''' Remove the file at path, if it exists, suppressing any errors.
    '''
    # Clean up the PID file.
    try:
        # This will raise if the child process had a chance to register
        # and complete its exit handler.
        os.remove(path)
        
    # So catch that error if it happens.
    except OSError:
        pass
        
        
class _NamespacePasser:
    ''' Creates a path in a secure temporary directory, such that the
    path can be used to write in a reentrant manner. Upon context exit,
    the file will be overwritten with zeros, removed, and then the temp
    directory cleaned up.
    
    We can't use the normal tempfile stuff because:
    1. it doesn't zero the file
    2. it prevents reentrant opening
    
    Using this in a context manager will return the path to the file as
    the "as" target, ie, "with _ReentrantSecureTempfile() as path:".
    '''
    
    def __init__(self):
        ''' Store args and kwargs to pass into enter and exit.
        '''
        seed = os.urandom(16)
        self._stem = base64.urlsafe_b64encode(seed).decode()
        self._tempdir = None
        self.name = None
    
    def __enter__(self):
        try:
            # Create a resident tempdir
            self._tempdir = tempfile.TemporaryDirectory()
            # Calculate the final path
            self.name = self._tempdir.name + '/' + self._stem
            # Ensure the file exists, so future cleaning calls won't error
            with open(self.name, 'wb'):
                pass
            
        except:
            if self._tempdir is not None:
                self._tempdir.cleanup()
                
            raise
            
        else:
            return self.name
        
    def __exit__(self, exc_type, exc_value, exc_tb):
        ''' Zeroes the file, removes it, and cleans up the temporary
        directory.
        '''
        try:
            # Open the existing file and overwrite it with zeros.
            with open(self.name, 'r+b') as f:
                to_erase = f.read()
                eraser = bytes(len(to_erase))
                f.seek(0)
                f.write(eraser)
                
            # Remove the file. We just accessed it, so it's guaranteed to exist
            os.remove(self.name)
            
        # Warn of any errors in the above, and then re-raise.
        except:
            logger.error(
                'Error while shredding secure temp file.\n' +
                ''.join(traceback.format_exc())
            )
            raise
            
        finally:
            self._tempdir.cleanup()
            
            
def _fork_worker(namespace_path, child_env, pid_file, invocation, chdir,
                 stdin_goto, stdout_goto, stderr_goto, _exit_caller, args):
    ''' Opens a fork worker, shielding the parent from cancellation via
    signal sending. Basically, thanks Windows for being a dick about
    signals.
    '''
    # Find out our PID so the daughter can tell us to exit
    my_pid = os.getpid()
    # Pack up all of the args that the child will need to use.
    # Prepend it to *args
    payload = (my_pid, pid_file, chdir, stdin_goto, stdout_goto,
               stderr_goto, _exit_caller) + args
    
    # Pack it up. We're shielded from pickling errors already because pickle is
    # needed to start the worker.
    # Write the payload to the namespace passer using the highest available
    # protocol
    with open(namespace_path, 'wb') as f:
        pickle.dump(payload, f, protocol=-1)
    
    # Invoke the invocation!
    daemon = subprocess.Popen(
        invocation,
        # This is important, because the parent _forkish is telling the child
        # to run as a daemon via env. Also note that we need to calculate this
        # in the root _daemonize1, or else we'll have a polluted environment
        # due to the '__CREATE_DAEMON__' key.
        env = child_env,
        # This is vital; without it, our process will be reaped at parent
        # exit.
        creationflags = subprocess.CREATE_NEW_CONSOLE,
    )
    # Busy wait until either the daemon exits, or it sends a signal to kill us.
    daemon.wait()
            
            
def _daemonize1(pid_file, *args, chdir=None, stdin_goto=None, stdout_goto=None,
                stderr_goto=None, umask=0o027, shielded_fds=None,
                fd_fallback_limit=1024, success_timeout=30,
                strip_cmd_args=False, _exit_caller=True):
    ''' Create an independent process for invocation, telling it to
    store its "pid" in the pid_file (actually, the pid of its signal
    listener). Payload is an iterable of variables to pass the invoked
    command for returning from _respawnish.
    
    Note that a bare call to this function will result in all code
    before the daemonize() call to be run twice.
    
    The daemon's pid will be recorded in pid_file, but creating a
        SignalHandler will overwrite it with the signaling subprocess
        PID, which will change after every received signal.
    *args will be passed to child. Waiting for success signal will
        timeout after success_timeout seconds.
    strip_cmd_args will ignore all additional command-line args in the
        second run.
    all other args identical to unix version of daemonize.
    
    umask, shielded_fds, fd_fallback_limit are unused for this
    Windows version.
    
    success_timeout is the wait for a signal. If nothing happens
    after timeout, we will raise a ChildProcessError.
    
    _exit_caller=True makes the parent (grandparent) process immediately
    exit. If set to False, THE GRANDPARENT MUST CALL os._exit(0) UPON
    ITS FINISHING. This is a really sticky situation, and should be
    avoided outside of the shipped context manager.
    '''
    ####################################################################
    # Error trap and calculate invocation
    ####################################################################
    
    # Convert any unset std streams to go to dev null
    stdin_goto = default_to(stdin_goto, os.devnull)
    stdin_goto = os.path.abspath(stdin_goto)
    stdout_goto = default_to(stdout_goto, os.devnull)
    stdout_goto = os.path.abspath(stdout_goto)
    stderr_goto = default_to(stderr_goto, os.devnull)
    stderr_goto = os.path.abspath(stderr_goto)
    
    # Convert chdir to go to current dir, and also to an abs path.
    chdir = default_to(chdir, '.')
    chdir = os.path.abspath(chdir)
        
    # First make sure we can actually do this.
    # We need to check the path to pythonw.exe
    python_path = sys.executable
    python_path = os.path.abspath(python_path)
    python_dir = os.path.dirname(python_path)
    pythonw_path = python_dir + '/pythonw.exe'
    # We also need to check our script is known and available
    script_path = sys.argv[0]
    script_path = os.path.abspath(script_path)
    _capability_check(pythonw_path, script_path)
    
    invocation = '"' + pythonw_path + '" "' + script_path + '"'
    # Note that we don't need to worry about being too short like this; python
    # doesn't care with slicing. But, don't forget to escape the invocation.
    if not strip_cmd_args:
        for cmd_arg in sys.argv[1:]:
            invocation += ' ' + shlex.quote(cmd_arg)
    
    ####################################################################
    # Begin actual forking
    ####################################################################
            
    # Convert the pid_file to an abs path
    pid_file = os.path.abspath(pid_file)
    # Get a "lock" on the PIDfile before forking anything by opening it
    # without silencing anything. Unless we error out while birthing, it
    # will be our daughter's job to clean up this file.
    open_pidfile = _acquire_pidfile(pid_file)
    open_pidfile.close()
        
    try:
        # Now open up a secure way to pass a namespace to the daughter process.
        with _NamespacePasser() as fpath:
            # Determine the child env
            child_env = {'__INVOKE_DAEMON__': fpath}
            child_env.update(_get_clean_env())
                
            # We need to shield ourselves from signals, or we'll be terminated
            # by python before running cleanup. So use a spawned worker to
            # handle the actual daemon creation.
            
            with _NamespacePasser() as worker_argpath:
                # Write an argvector for the worker to the namespace passer
                worker_argv = (
                    fpath,  # namespace_path
                    child_env,
                    pid_file,
                    invocation,
                    chdir,
                    stdin_goto,
                    stdout_goto,
                    stderr_goto,
                    _exit_caller,
                    args
                )
                with open(worker_argpath, 'wb') as f:
                    # Use the highest available protocol
                    pickle.dump(worker_argv, f, protocol=-1)
                    
                # Create an env for the worker to let it know what to do
                worker_env = {'__CREATE_DAEMON__': 'True'}
                worker_env.update(_get_clean_env())
                # Figure out the path to the current file
                # worker_target = os.path.abspath(__file__)
                worker_cmd = ('"' + python_path + '" -m ' +
                              'daemoniker._daemonize_windows ' +
                              '"' + worker_argpath + '"')
                
                try:
                    # This will wait for the worker to finish, or cancel it at
                    # the timeout.
                    worker = subprocess.run(
                        worker_cmd,
                        env = worker_env,
                        timeout = success_timeout
                    )
                    
                    # Make sure it actually terminated via the success signal
                    if worker.returncode != signal.SIGINT:
                        raise RuntimeError(
                            'Daemon creation worker exited prematurely.'
                        )
                    
                except subprocess.TimeoutExpired as exc:
                    raise ChildProcessError(
                        'Timeout while waiting for daemon init.'
                    ) from exc
                
    # If anything goes wrong in there, we need to clean up the pidfile.
    except:
        _clean_file(pid_file)
        raise
    
    # Success.
    # _exit_caller = True. Exit the interpreter.
    if _exit_caller:
        os._exit(0)
        
    # Don't _exit_caller. Return is_parent=True, and change all of the args to
    # None to prevent accidental modification attempts in the parent.
    else:
        # Reset args to be an equivalent expansion of *[None]s
        args = [None] * len(args)
        # is_parent, *args
        return [True] + list(args)
    
    
def _daemonize2(*_daemonize1_args, **_daemonize1_kwargs):
    ''' Unpacks the daemonization. Modifies the new environment as per
    the parent's forkish() call. Registers appropriate cleanup methods
    for the pid_file. Signals successful daemonization. Returns the
    *args passed to parent forkish() call.
    '''
    ####################################################################
    # Unpack and prep the arguments
    ####################################################################
    
    # Unpack the namespace.
    ns_passer_path = os.environ['__INVOKE_DAEMON__']
    with open(ns_passer_path, 'rb') as f:
        pkg = pickle.load(f)
    (
        parent,
        pid_file,
        chdir,
        stdin_goto,
        stdout_goto,
        stderr_goto,
        _exit_caller,
        *args
    ) = pkg
    
    ####################################################################
    # Resume actual daemonization
    ####################################################################
    
    # Do some important housekeeping
    _redirect_stds(stdin_goto, stdout_goto, stderr_goto)
    _filial_usurpation(chdir)
        
    # Get the "locked" PIDfile, bypassing _acquire entirely.
    with open(pid_file, 'w+') as open_pidfile:
        _write_pid(open_pidfile)
        
    # Define a memoized cleanup function.
    def cleanup(pid_path=pid_file):
        try:
            os.remove(pid_path)
        except Exception:
            if os.path.exists(pid_path):
                logger.error(
                    'Failed to clean up pidfile w/ traceback: \n' +
                    ''.join(traceback.format_exc())
                )
            else:
                logger.info('Pidfile was removed prior to atexit cleanup.')
    
    # Register this as soon as possible in case something goes wrong.
    atexit.register(cleanup)
    
    # "Notify" parent of success
    os.kill(parent, signal.SIGINT)
    
    # If our parent exited, we are being called directly and don't need to
    # worry about any of this silliness.
    if _exit_caller:
        return args
    
    # Our parent did not exit, so we're within a context manager, and our
    # application expects a return value for is_parent
    else:
        # is_parent, *args
        return [False] + list(args)


if '__INVOKE_DAEMON__' in os.environ:
    daemonize = _daemonize2
else:
    daemonize = _daemonize1
    
    
def _get_clean_env():
    ''' Gets a clean copy of our environment, with any flags stripped.
    '''
    env2 = dict(os.environ)
    flags = {
        '__INVOKE_DAEMON__',
        '__CREATE_DAEMON__',
        '__CREATE_SIGHANDLER__'
    }
    
    for key in flags:
        if key in env2:
            del env2[key]
            
    return env2
    
    
if __name__ == '__main__':
    ''' Do this so we can support process-based workers using Popen
    instead of multiprocessing, which would impose extra requirements
    on whatever code used Windows daemonization to avoid infinite
    looping.
    '''
    if '__CREATE_DAEMON__' in os.environ:
        # Use this to create a daemon worker, similar to a signal handler.
        argpath = sys.argv[1]
        with open(argpath, 'rb') as f:
            args = pickle.load(f)
        _fork_worker(*args)
