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

from ._signals_common import _SighandlerCore

from .exceptions import DaemonikerSignal
from .exceptions import SignalError
from .exceptions import SIGINT
from .exceptions import SIGTERM
from .exceptions import SIGABRT

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
        
        
def _restore_any_previous_handler(signum, maybe_handler, force_clear=False):
    ''' Makes sure that a previous handler was actually set, and then
    restores it.
    
    maybe_handler is the cached potential handler. If it's the constant
    (ZeroDivisionError) we've been using to denote nothingness, then
    maybe_handler will either:
    
    1. do nothing, if force_clear == False
    2. restore signal.SIG_DEFL, if force_clear == True
    '''
    # Nope, wasn't previously set
    if maybe_handler == ZeroDivisionError:
        # Restore the default if we're forcing it
        if force_clear:
            signal.signal(signum, signal.SIG_DFL)
        # (Do nothing otherwise)
        
    # It was previously set, so re-set it.
    else:
        signal.signal(signum, maybe_handler)
    

class SignalHandler1(_SighandlerCore):
    ''' Signal handling system using lightweight wrapper around built-in
    signal.signal handling.
    '''
    def __init__(self, pid_file, sigint=None, sigterm=None, sigabrt=None):
        ''' Creates a signal handler, using the passed callables. None
        will assign the default handler (raise in main). passing
        IGNORE_SIGNAL constant will result in the signal being noop'd.
        '''
        self.sigint = sigint
        self.sigterm = sigterm
        self.sigabrt = sigabrt
        
        # Yeah, except this isn't used at all (just here for cross-platform
        # consistency)
        self._pidfile = pid_file
        
        # Assign these to impossible values so we can compare against them
        # later, when deciding whether or not to restore a previous handler.
        # Don't use None, in case it gets used to denote a default somewhere.
        # This is deliberately unconventional.
        self._old_sigint = ZeroDivisionError
        self._old_sigterm = ZeroDivisionError
        self._old_sigabrt = ZeroDivisionError
        
        self._running = False
        
    def start(self):
        ''' Starts signal handling.
        '''
        if self._running:
            raise RuntimeError('SignalHandler is already running.')
            
        # Initialize stuff to values that are impossible for signal.signal.
        # Don't use None, in case it gets used to denote a default somewhere.
        # This is deliberately unconventional.
        old_sigint = ZeroDivisionError
        old_sigterm = ZeroDivisionError
        old_sigabrt = ZeroDivisionError
        
        try:
            # First we need to make closures around all of our attributes, so
            # they can be updated after we start listening to signals
            def sigint_closure(signum, frame):
                return self.sigint(signum)
            def sigterm_closure(signum, frame):
                return self.sigterm(signum)
            def sigabrt_closure(signum, frame):
                return self.sigabrt(signum)
                
            # Now simply register those with signal.signal
            old_sigint = signal.signal(signal.SIGINT, sigint_closure)
            old_sigterm = signal.signal(signal.SIGTERM, sigterm_closure)
            old_sigabrt = signal.signal(signal.SIGABRT, sigabrt_closure)
            
        # If that fails, restore previous state and reraise
        except:
            _restore_any_previous_handler(signal.SIGINT, old_sigint)
            _restore_any_previous_handler(signal.SIGTERM, old_sigterm)
            _restore_any_previous_handler(signal.SIGABRT, old_sigabrt)
            raise
            
        # If that succeeds, set self._running and cache old handlers
        else:
            self._old_sigint = old_sigint
            self._old_sigterm = old_sigterm
            self._old_sigabrt = old_sigabrt
            self._running = True
        
    def stop(self):
        ''' Stops signal handling, returning all signal handlers to
        their previous handlers, or restoring their defaults if
        something went fishy.
        '''
        try:
            _restore_any_previous_handler(
                signal.SIGINT,
                self._old_sigint,
                force_clear = True
            )
            _restore_any_previous_handler(
                signal.SIGTERM,
                self._old_sigterm,
                force_clear = True
            )
            _restore_any_previous_handler(
                signal.SIGABRT,
                self._old_sigabrt,
                force_clear = True
            )
            
        # If we get an exception there, just force restoring all defaults and
        # reraise
        except:
            signal.signal(signal.SIGINT, signal.SIG_DFL)
            signal.signal(signal.SIGTERM, signal.SIG_DFL)
            signal.signal(signal.SIGABRT, signal.SIG_DFL)
            raise
            
        finally:
            # See notes above re: using ZeroDivisionError instead of None
            self._old_sigint = ZeroDivisionError
            self._old_sigterm = ZeroDivisionError
            self._old_sigabrt = ZeroDivisionError
            self._running = False
        
    @staticmethod
    def _default_handler(signum, *args):
        ''' The default signal handler for Unix.
        '''
        # Just parallel the sighandlers that are available in Windows, because
        # it is definitely the limiting factor here
        sigs = {
            signal.SIGABRT: SIGABRT,
            signal.SIGINT: SIGINT,
            signal.SIGTERM: SIGTERM,
        }
        
        try:
            exc = sigs[signum]
        except KeyError:
            exc = DaemonikerSignal
            
        raise exc()
