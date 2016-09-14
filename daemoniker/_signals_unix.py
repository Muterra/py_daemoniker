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
    

class SignalHandler1:
    ''' Sets up an automatic signal handling system.
    '''
    def __init__(self, sigterm):
        def handle_sigterm(signum, frame, action=sigterm):
            ''' Call sys.exit when a sigterm is received. Or don't! Who 
            knows!
            '''
            logger.warning('Caught signal. Exiting.')
            
            if action is not None:
                action()
            
            raise SystemExit()
            
        # Should this be advanced to just after forking?
        signal.signal(signal.SIGTERM, self._handle_sigterm)
