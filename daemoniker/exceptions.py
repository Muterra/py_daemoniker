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

import signal

# Control * imports.
__all__ = [
    # Base class for all of the above
    'DaemonikerException',
    # These are daemonization/sighandling errors and exceptions
    'SignalError',
    # These are actual signals
    'DaemonikerSignal',
    'SIGABRT',
    'SIGINT',
    'SIGTERM',
]


class DaemonikerException(Exception):
    ''' This is suclassed for all exceptions and warnings, so that code
    using daemoniker as an import can successfully catch all daemoniker
    exceptions with a single except.
    '''
    pass


# ###############################################
# Signal handling errors and exceptions
# ###############################################


class SignalError(DaemonikerException, RuntimeError):
    ''' This exception (or a subclass thereof) is raised for all issues
    related to signal handling.
    '''
    pass


# ###############################################
# Signals themselves
# ###############################################
    
    
class _SignalMeta(type):
    def __int__(self):
        return self.SIGNUM


class DaemonikerSignal(BaseException, metaclass=_SignalMeta):
    ''' Subclasses of this exception are raised by all of the default
    signal handlers defined using SignalHandlers.
    
    This subclasses BaseException because, when unhandled, it should
    always be a system-exiting exception. That being said, it should not
    subclass SystemExit, because that's a whole different can of worms.
    '''
    SIGNUM = -1
    
    def __int__(self):
        return self.SIGNUM
        
        
ReceivedSignal = DaemonikerSignal


class SIGABRT(DaemonikerSignal):
    ''' Raised upon receipt of SIGABRT.
    '''
    SIGNUM = int(signal.SIGABRT)


class SIGINT(DaemonikerSignal):
    ''' Raised upon receipt of SIGINT, CTRL_C_EVENT, CTRL_BREAK_EVENT.
    '''
    SIGNUM = int(signal.SIGINT)


class SIGTERM(DaemonikerSignal):
    ''' Raised upon receipt of SIGTERM.
    '''
    SIGNUM = int(signal.SIGTERM)
