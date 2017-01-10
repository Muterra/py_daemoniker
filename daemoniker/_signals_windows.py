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
import os
import sys
import time
import signal
import subprocess
import atexit
import ctypes
import threading

# Intra-package dependencies
from .utils import platform_specificker

from ._daemonize_windows import _get_clean_env
from ._signals_common import _SighandlerCore

from .exceptions import DaemonikerSignal
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


logger = logging.getLogger(__name__)

# Control * imports.
__all__ = [
    # 'Inquisitor',
]


# ###############################################
# Library
# ###############################################
    
    
def _sketch_raise_in_main(exc):
    ''' Sketchy way to raise an exception in the main thread.
    '''
    if isinstance(exc, BaseException):
        exc = type(exc)
    elif issubclass(exc, BaseException):
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
        ctypes.pythonapi.PyThreadState_SetAsyncExc(main_id, 0)
        raise SystemError('Failed to raise in main thread.')
    
    
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
    
    
class SignalHandler1(_SighandlerCore):
    ''' Signal handling system using a daughter thread and a disposable
    daughter process.
    '''
    
    def __init__(self, pid_file, sigint=None, sigterm=None, sigabrt=None):
        ''' Creates a signal handler, using the passed callables. None
        will assign the default handler (raise in main). passing
        IGNORE_SIGNAL constant will result in the signal being noop'd.
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
        try:
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
        
        except:
            self._stop_nowait()
            raise
        
    def stop(self):
        ''' Hold the phone! Idempotent.
        '''
        self._stop_nowait()
        self._stopped.wait()
        
    def _stop_nowait(self):
        ''' Stops the listener without waiting for the _stopped flag.
        Only called directly if there's an error while starting.
        '''
        with self._opslock:
            self._running = False
            
            # If we were running, kill the process so that the loop breaks free
            if self._worker is not None and self._worker.returncode is None:
                self._worker.terminate()
                
        atexit.unregister(self.stop)
        
    def _listen_loop(self):
        ''' Manages all signals.
        '''
        python_path = sys.executable
        python_path = os.path.abspath(python_path)
        worker_cmd = ('"' + python_path + '" -m ' +
                      'daemoniker._signals_windows')
        worker_env = {'__CREATE_SIGHANDLER__': 'True'}
        worker_env.update(_get_clean_env())
        
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
                        handler = self._default_handler
                        
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
        self._stop_nowait()
    
    @staticmethod
    def _default_handler(signum, *args):
        ''' The default signal handler. Don't register with built-in
        signal.signal! This needs to be used on the subprocess await
        death workaround.
        '''
        # All valid cpython windows signals
        sigs = {
            signal.SIGABRT: SIGABRT,
            # signal.SIGFPE: 'fpe', # Don't catch this
            # signal.SIGSEGV: 'segv', # Don't catch this
            # signal.SIGILL: 'illegal', # Don't catch this
            signal.SIGINT: SIGINT,
            signal.SIGTERM: SIGTERM,
            # Note that signal.CTRL_C_EVENT and signal.CTRL_BREAK_EVENT are
            # converted to SIGINT in _await_signal
        }
        
        try:
            exc = sigs[signum]
        except KeyError:
            exc = DaemonikerSignal
            
        _sketch_raise_in_main(exc)
    
    
if __name__ == '__main__':
    ''' Do this so we can support process-based workers using Popen
    instead of multiprocessing, which would impose extra requirements
    on whatever code used Windows daemonization to avoid infinite
    looping.
    '''
    if '__CREATE_SIGHANDLER__' in os.environ:
        # Use this to create a signal handler.
        _infinite_noop()
