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
import time
import signal
import pickle
import base64
import subprocess
import multiprocessing
import shlex
import tempfile
import atexit
import ctypes
import threading

# Intra-package dependencies
from .utils import platform_specificker
from .utils import default_to

from ._daemonize_common import _redirect_stds
from ._daemonize_common import _write_pid
from ._daemonize_common import _acquire_pidfile

from ._daemonize_unix import send
from ._daemonize_unix import ping

from .exceptions import SignalError
from .exceptions import ReceivedSignal
from .exceptions import SIGABRT
from .exceptions import SIGINT
from .exceptions import SIGTERM

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


import logging
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
        if '__INVOKE_DAEMON__' in os.environ:
            self._parent = False
        else:
            self._parent = True
        
    def __enter__(self):
        # This the parent / setup pass
        if self._parent:
            return self._parent, _daemonize1
        
        # This the child / daemon pass
        else:
            return self._parent, _daemonize2
        
    def __exit__(self, exc_type, exc_value, exc_tb):
        ''' Exit doesn't really need to do any cleanup. But, it's needed
        for context managing.
        '''
        pass
            
            
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
            with open(self.name, 'wb') as f:
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
                 stdin_goto, stdout_goto, stderr_goto, args):
    ''' Opens a fork worker, shielding the parent from cancellation via
    signal sending. Basically, thanks Windows for being a dick about 
    signals.
    '''
    # Find out our PID so the daughter can tell us to exit
    my_pid = os.getpid()
    # Pack up all of the args that the child will need to use.
    # Prepend it to *args
    payload = (my_pid, pid_file, chdir, stdin_goto, stdout_goto, 
               stderr_goto) + args
    
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
                strip_cmd_args=False):
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
                child_env = {**_get_clean_env(), '__INVOKE_DAEMON__': fpath}
                    
                # We need to shield ourselves from signals, or we'll be terminated
                # by python before running cleanup. So use a spawned worker to
                # handle the actual daemon creation.
                
                with _NamespacePasser() as worker_argpath:
                    # Write an argvector for the worker to the namespace passer
                    worker_argv = (
                        fpath, # namespace_path
                        child_env,
                        pid_file,
                        invocation,
                        chdir,
                        stdin_goto,
                        stdout_goto,
                        stderr_goto,
                        args
                    )
                    with open(worker_argpath, 'wb') as f:
                        # Use the highest available protocol
                        pickle.dump(worker_argv, f, protocol=-1)
                        
                    # Create an env for the worker to let it know what to do
                    worker_env = {**_get_clean_env(), '__CREATE_DAEMON__': 'True'}
                    # Figure out the path to the current file
                    worker_target = os.path.abspath(__file__)
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
                
        # Success. Exit the interpreter.
        os._exit(0)
    
    
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
    parent, pid_file, chdir, stdin_goto, stdout_goto, stderr_goto, *args = pkg
    
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
        except:
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
    
    return args


if '__INVOKE_DAEMON__' in os.environ:
    daemonize = _daemonize2
else:
    daemonize = _daemonize1
    
    
def _get_clean_env():
    ''' Gets a clean copy of our environment, with any flags stripped.
    '''
    env2 = {**os.environ}
    flags = {
        '__INVOKE_DAEMON__', 
        '__CREATE_DAEMON__', 
        '__CREATE_SIGHANDLER__'
    }
    
    for key in flags:
        if key in env2:
            del env2[key]
            
    return env2
    
    
def _sketch_raise_in_main(exc):
    ''' Sketchy way to raise an exception in the main thread.
    '''
    if isinstance(exc, Exception):
        exc = type(exc)
    elif issubclass(exc, Exception):
        pass
    else:
        raise TypeError('Must raise an exception.')
    
    # Figure out the id of the main thread
    main_id = threading.main_thread().ident
    thread_ref = ctypes.c_long(main_id)
    exc = ctypes.py_object(exc)
    
    result = ctypes.pythonapi.PyThreadState_SetAsyncExc(
        thread_ref,
        exc
    )
    
    # 0 Is failed.
    if result == 0:
        raise SystemError('Main thread had invalid ID?')
    # 1 succeeded
    # > 1 failed
    elif result > 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(target_tid, 0)
        raise SystemError('Failed to raise in main thread.')
    
    
def _default_handler(signum, *args):
    ''' The default signal handler. Don't register with signal.signal!
    This needs to be used on the subprocess await death workaround.
    '''
    # All valid cpython windows signals
    sigs = {
        signal.SIGABRT: SIGABRT,
        # signal.SIGFPE: 'fpe', # Don't catch this
        # signal.SIGSEGV: 'segv', # Don't catch this
        # signal.SIGILL: 'illegal', # Don't catch this
        signal.SIGINT: SIGINT,
        signal.SIGTERM: SIGTERM,
        # signal.CTRL_C_EVENT: SIGINT, # Convert to SIGINT in _await_signal
        # signal.CTRL_BREAK_EVENT: SIGINT # Convert to SIGINT in _await_signal
    }
    
    try:
        exc = sigs[signum]
    except KeyError:
        exc = SignalError
        
    _sketch_raise_in_main(exc)
    
    
def _noop(*args, **kwargs):
    ''' Used for ignoring signals.
    '''
    pass
    
    
def _infinite_noop():
    ''' Give a process something to do while it waits for a signal.
    '''
    while True:
        time.sleep(9999)
        
        
def _await_signal(process):
    ''' Waits for the process to die, and then returns the exit code for
    the process, converting CTRL_C_EVENT and CTRL_BREAK_EVENT into
    SIGINT.
    '''
    # Note that this is implemented with a busy wait
    process.wait()
    code = process.returncode
    
    if code == signal.CTRL_C_EVENT:
        code = signal.SIGINT
    elif code == signal.CTRL_BREAK_EVENT:
        code = signal.SIGINT
    
    return code
    

IGNORE = 1793


def _normalize_handler(handler):
    ''' Normalizes a signal handler. Converts None to the default, and
    IGNORE to noop.
    '''
    # None -> _default_handler
    handler = default_to(handler, _default_handler)
    # IGNORE -> _noop
    handler = default_to(handler, _noop, comparator=IGNORE)
    
    return handler
    
    
class SignalHandler1:
    ''' Signal handling system using a daughter thread.
    '''
    def __init__(self, pid_file, sigint=None, sigterm=None, sigabrt=None):
        ''' Creates a signal handler, using the passed callables. None
        will assign the default handler (raise in main). passing IGNORE
        constant will result in the signal being noop'd.
        '''
        self.sigint = sigint
        self.sigterm = sigterm
        self.sigabrt = sigabrt
        
        self._pidfile = pid_file
        self._running = None
        self._worker = None
        self._thread = None
        self._watcher = None
        
        self._opslock = threading.Lock()
        self._stopped = threading.Event()
        self._started = threading.Event()
        
    def start(self):
        with self._opslock:
            if self._running:
                raise RuntimeError('SignalHandler is already running.')
                
            self._stopped.clear()
            self._running = True
            self._thread = threading.Thread(
                target = self._listen_loop,
                # We need to always reset the PID file.
                daemon = False
            )
            self._thread.start()
            
        atexit.register(self.stop)
        
        # Only set up a watcher once, and then let it run forever.
        if self._watcher is None:
            self._watcher = threading.Thread(
                target = self._watch_for_exit,
                # Who watches the watchman?
                # Daemon threading this is important to protect us against
                # issues during closure.
                daemon = True
            )
            self._watcher.start()
            
        self._started.wait()
        
    def stop(self):
        ''' Hold the phone! Idempotent.
        '''
        with self._opslock:
            self._running = False
            
            # If we were running, kill the process so that the loop breaks free
            if self._worker is not None and self._worker.returncode is None:
                self._worker.terminate()
                
        atexit.unregister(self.stop)
        
        self._stopped.wait()
        
    @property
    def sigint(self):
        ''' Gets sigint.
        '''
        return self._sigint
        
    @sigint.setter
    def sigint(self, handler):
        ''' Normalizes and sets sigint.
        '''
        self._sigint = _normalize_handler(handler)
        
    @sigint.deleter
    def sigint(self):
        ''' Returns the sigint handler to the default.
        '''
        self.sigint = None
        
    @property
    def sigterm(self):
        ''' Gets sigterm.
        '''
        return self._sigterm
        
    @sigterm.setter
    def sigterm(self, handler):
        ''' Normalizes and sets sigterm.
        '''
        self._sigterm = _normalize_handler(handler)
        
    @sigterm.deleter
    def sigterm(self):
        ''' Returns the sigterm handler to the default.
        '''
        self.sigterm = None
        
    @property
    def sigabrt(self):
        ''' Gets sigabrt.
        '''
        return self._sigabrt
        
    @sigabrt.setter
    def sigabrt(self, handler):
        ''' Normalizes and sets sigabrt.
        '''
        self._sigabrt = _normalize_handler(handler)
        
    @sigabrt.deleter
    def sigabrt(self):
        ''' Returns the sigabrt handler to the default.
        '''
        self.sigabrt = None
        
    def _listen_loop(self):
        ''' Manages all signals.
        '''
        python_path = sys.executable
        python_path = os.path.abspath(python_path)
        worker_cmd = ('"' + python_path + '" -m ' + 
                      'daemoniker._daemonize_windows')
        worker_env = {**_get_clean_env(), '__CREATE_SIGHANDLER__': 'True'}
        
        # Iterate until we're reaped by the main thread exiting.
        try:
            while self._running:
                try:
                    # Create a process. Depend upon it being reaped if the
                    # parent quits
                    self._worker = subprocess.Popen(
                        worker_cmd,
                        env = worker_env,
                    )
                    worker_pid = self._worker.pid
                    
                    # Record the PID of the worker in the pidfile, overwriting
                    # its contents.
                    with open(self._pidfile, 'w+') as f:
                        f.write(str(worker_pid) + '\n')
                    
                finally:
                    # Now let the start() call know we are CTR, even if we
                    # raised, so it can proceed. I might consider adding an
                    # error signal so that the start call will raise if it
                    # didn't work.
                    self._started.set()
                
                # Wait for the worker to generate a signal. Calling stop()
                # will break out of this.
                signum = _await_signal(self._worker)
                
                # If the worker was terminated by stopping the
                # SignalHandler, then discard errything.
                if self._running:
                    # Handle the signal, catching unknown ones with the
                    # default handler. Do this each time so that the
                    # SigHandler can be updated while running.
                    signums = {
                        signal.SIGABRT: self.sigabrt, 
                        signal.SIGINT: self.sigint, 
                        signal.SIGTERM: self.sigterm
                    }
                    try:
                        handler = signums[signum]
                    except KeyError:
                        handler = _default_handler
                        
                    handler(signum)
        
        # If we exit, be sure to reset self._running and stop the running
        # worker, if there is one (note terinate is idempotent)
        finally:
            try:
                self._running = False
                self._worker.terminate()
                self._worker = None
                # Restore our actual PID to the pidfile, overwriting its
                # contents.
                with open(self._pidfile, 'w+') as f:
                    f.write(str(os.getpid()) + '\n')
            finally:
                self._stopped.set()
                self._started.clear()
    
    def _watch_for_exit(self):
        ''' Automatically watches for termination of the main thread and
        then closes self gracefully.
        '''
        main = threading.main_thread()
        main.join()
        self.stop()
    
    
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
        
    elif '__CREATE_SIGHANDLER__' in os.environ:
        # Use this to create a signal handler.
        _infinite_noop()