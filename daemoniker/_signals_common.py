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
from .utils import default_to

from .exceptions import DaemonikerSignal


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
    

IGNORE_SIGNAL = 1793
    
    
def _noop(*args, **kwargs):
    ''' Used for ignoring signals.
    '''
    pass
                
                
def send(pid_file, signal):
    ''' Sends the signal in signum to the pid_file. Num can be either
    int or one of the exceptions.
    '''
    if isinstance(signal, DaemonikerSignal):
        signum = signal.SIGNUM
    elif isinstance(signal, type) and issubclass(signal, DaemonikerSignal):
        signum = signal.SIGNUM
    else:
        signum = int(signal)
    
    with open(pid_file, 'r') as f:
        pid = int(f.read())
        
    os.kill(pid, signum)
    
    
def ping(pid_file):
    ''' Returns True if the process in pid_file is available, and False
    otherwise. Note that availability does not imply the process is
    running, just that it recently has been. For example, recently-
    exited processes will still return True.
    
    Uhhh shit, this isn't going to work well, windows converts signal 0
    into an interrupt. Okay, punt for now.
    '''
    try:
        send(pid_file, 0)
    except OSError:
        return False
    else:
        return True


def _normalize_handler(handler, default_handler):
    ''' Normalizes a signal handler. Converts None to the default, and
    IGNORE_SIGNAL to noop.
    '''
    # None -> _default_handler
    handler = default_to(handler, default_handler)
    # IGNORE_SIGNAL -> _noop
    handler = default_to(handler, _noop, comparator=IGNORE_SIGNAL)
    
    return handler
        
        
class _SighandlerCore:
    ''' Core, platform-independent functionality for signal handlers.
    '''
    @property
    def sigint(self):
        ''' Gets sigint.
        '''
        return self._sigint
        
    @sigint.setter
    def sigint(self, handler):
        ''' Normalizes and sets sigint.
        '''
        self._sigint = _normalize_handler(handler, self._default_handler)
        
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
        self._sigterm = _normalize_handler(handler, self._default_handler)
        
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
        self._sigabrt = _normalize_handler(handler, self._default_handler)
        
    @sigabrt.deleter
    def sigabrt(self):
        ''' Returns the sigabrt handler to the default.
        '''
        self.sigabrt = None
