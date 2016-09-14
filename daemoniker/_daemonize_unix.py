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

This was written with heavy consultation of the following resources:
    Chad J. Schroeder, Creating a daemon the Python way (Python recipe) 
        http://code.activestate.com/recipes/
        278731-creating-a-daemon-the-python-way/
    Ilya Otyutskiy, Daemonize
        https://github.com/thesharp/daemonize
    David Mytton, unknown, et al: A simple daemon in Python
        http://www.jejik.com/articles/2007/02/
        a_simple_unix_linux_daemon_in_python/www.boxedice.com
    
'''

# Global dependencies
import os
import sys
import signal
import logging
import atexit
import traceback
import shutil

# Intra-package dependencies
from .utils import platform_specificker
from .utils import default_to

from ._daemonize_common import _make_range_tuples
from ._daemonize_common import _flush_stds
from ._daemonize_common import _redirect_stds
from ._daemonize_common import _write_pid
from ._daemonize_common import _acquire_pidfile

from .exceptions import ReceivedSignal

_SUPPORTED_PLATFORM = platform_specificker(
    linux_choice = True,
    win_choice = False,
    cygwin_choice = False,
    osx_choice = True,
    # Dunno if this is a good idea but might as well try
    other_choice = True
)

if _SUPPORTED_PLATFORM:
    import fcntl
    import pwd
    import grp
    import resource


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
        
# Daemonization and helpers


class Daemonizer:
    ''' This is really very boring on the Unix side of things.
    
    with Daemonizer() as (is_setup, daemonize):
        if is_setup:
            setup_code_here()
        else:
            this_will_not_be_run_on_unix()
            
        *args = daemonize(*daemonizer_args, *args)
    ''' 
    def __enter__(self):
        # This will always only be entered by the parent.
        # This will always only be exited by the child.
        return True, daemonize
        
    def __exit__(self, exc_type, exc_value, exc_tb):
        ''' Exit doesn't really need to do any cleanup. But, it's needed
        for context managing.
        '''
        # This will always only be entered by the parent.
        # This will always only be exited by the child.
        pass

            
def _fratricidal_fork():
    ''' Fork the current process, and immediately exit the parent.
    
    OKAY TECHNICALLY THIS WOULD BE PARRICIDE but it just doesn't 
    have the same ring to it.
    '''
    try:
        # This will create a clone of our process. The clone will get zero
        # for the PID, and the parent will get an actual PID.
        pid = os.fork()
            
    except OSError as exc:
        logger.critical(
            'Fork failed with traceback: \n' + 
            ''.join(traceback.format_exc())
        )
        raise SystemExit('Failed to fork.') from exc
    
    # If PID != 0, this is the parent process, and we should IMMEDIATELY 
    # die.
    if pid != 0:
        # Exit parent without cleanup.
        os._exit(0)
    else:
        logger.info('Fork successful.')

        
def _filial_usurpation(chdir, umask):
    ''' Decouple the child process from the parent environment.
    '''
    # This prevents "directory busy" errors when attempting to remove 
    # subdirectories.
    os.chdir(chdir)
    
    # Get new PID.
    # Stop listening to parent signals.
    # Put process in new parent group
    # Detatch controlling terminal.
    new_sid = os.setsid()
    if new_sid == -1:
        # A new pid of -1 is bad news bears
        logger.critical('Failed setsid call.')
        raise SystemExit('Failed setsid call.')
        
    # Set the permissions mask
    os.umask(umask)

        
def _autoclose_files(shielded=None, fallback_limit=1024):
    ''' Automatically close any open file descriptors.
    
    shielded is iterable of file descriptors.
    '''
    # Process shielded.
    shielded = default_to(shielded, [])
    
    # Figure out the maximum number of files to try to close.
    # This returns a tuple of softlimit, hardlimit; the hardlimit is always
    # greater.
    softlimit, hardlimit = resource.getrlimit(resource.RLIMIT_NOFILE)
    
    # If the hard limit is infinity, we can't iterate to it.
    if hardlimit == resource.RLIM_INFINITY:
        # Check the soft limit. If it's also infinity, fallback to guess.
        if softlimit == resource.RLIM_INFINITY:
            fdlimit = fallback_limit
            
        # The soft limit is finite, so fallback to that.
        else:
            fdlimit = softlimit
            
    # The hard limit is not infinity, so prefer it.
    else:
        fdlimit = hardlimit
    
    # Skip fd 0, 1, 2, which are used by stdin, stdout, and stderr 
    # (respectively)
    ranges_to_close = _make_range_tuples(
        start = 3,
        stop = fdlimit,
        exclude = shielded
    )
    for start, stop in ranges_to_close:
        # How nice of os to include this for us!
        os.closerange(start, stop)

        
def daemonize(pid_file, *args, chdir=None, stdin_goto=None, stdout_goto=None, 
              stderr_goto=None, umask=0o027, shielded_fds=None, 
              fd_fallback_limit=1024, success_timeout=30, 
              strip_cmd_args=False):
    ''' Performs a classic unix double-fork daemonization. Registers all
    appropriate cleanup functions.
    
    fd_check_limit is a fallback value for file descriptor searching 
    while closing descriptors.
    
    umask is the eponymous unix umask. The default value:
        1. will allow owner to have any permissions.
        2. will prevent group from having write permission
        3. will prevent other from having any permission
    See https://en.wikipedia.org/wiki/Umask
    '''
    if not _SUPPORTED_PLATFORM:
        raise OSError(
            'The Unix daemonization function cannot be used on the current '
            'platform.'
        )
    
    ####################################################################
    # Prep the arguments
    ####################################################################
    
    # Convert the pid_file to an abs path
    pid_file = os.path.abspath(pid_file)
    
    # Get the noop stream, in case Python is using something other than 
    # /dev/null
    if hasattr(os, "devnull"):
        devnull = os.devnull
    else:
        devnull = "/dev/null"
        
    # Convert any unset std streams to go to dev null
    stdin_goto = default_to(stdin_goto, devnull)
    stdout_goto = default_to(stdout_goto, devnull)
    stderr_goto = default_to(stderr_goto, devnull)
    
    # Convert chdir to go to current dir, and also to an abs path.
    chdir = default_to(chdir, '.')
    chdir = os.path.abspath(chdir)
    
    # And convert shield_fds to a set
    shielded_fds = default_to(shielded_fds, set())
    shielded_fds = set(shielded_fds)
    
    ####################################################################
    # Begin actual daemonization
    ####################################################################
    
    # Get a lock on the PIDfile before forking anything.
    locked_pidfile = _acquire_pidfile(pid_file)
    # Make sure we don't accidentally autoclose it though.
    shielded_fds.add(locked_pidfile.fileno())
    
    # Define a memoized cleanup function.
    def cleanup(pid_path=pid_file, pid_lock=locked_pidfile):
        try:
            pid_lock.close()
            os.remove(pid_path)
        except:
            logger.error(
                'Failed to clean up pidfile w/ traceback: \n' + 
                ''.join(traceback.format_exc())
            )
            raise
    
    # Register this as soon as possible in case something goes wrong.
    atexit.register(cleanup)
    # Note that because fratricidal fork is calling os._exit(), our parents
    # will never call cleanup.
    
    # Now fork the toplevel parent, killing it.
    _fratricidal_fork()
    # We're now running from within the child. We need to detach ourself 
    # from the parent environment.
    _filial_usurpation(chdir, umask)
    # Okay, re-fork (no zombies!) and continue business as usual
    _fratricidal_fork()
    
    # Do some important housekeeping
    _write_pid(locked_pidfile)
    _autoclose_files(shielded_fds, fd_fallback_limit)
    _redirect_stds(stdin_goto, stdout_goto, stderr_goto)
    
    return args