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


# ###############################################
# Boilerplate
# ###############################################


# Logging shenanigans
import logging
# Py2.7+, but this is Py3.5.1+
from logging import NullHandler
logging.getLogger(__name__).addHandler(NullHandler())

# Control * imports.
__all__ = [
    'Daemonizer',
    'daemonize',
    'SignalHandler1',
    'IGNORE_SIGNAL',
    'send',
    'SIGINT',
    'SIGTERM',
    'SIGABRT',
]


# ###############################################
# Library
# ###############################################

# Submodules
from . import exceptions
from . import utils

from ._signals_common import IGNORE_SIGNAL
from ._signals_common import send

from .exceptions import SIGINT
from .exceptions import SIGTERM
from .exceptions import SIGABRT

# Add in toplevel stuff
from .utils import platform_specificker
platform_switch = platform_specificker(
    linux_choice = 'unix',
    win_choice = 'windows',
    # Dunno if this is a good idea but might as well try
    cygwin_choice = None,
    osx_choice = 'unix',
    other_choice = 'unix'
)

if platform_switch == 'unix':
    from ._daemonize_unix import Daemonizer
    from ._daemonize_unix import daemonize
    
    from ._signals_unix import SignalHandler1
    
elif platform_switch == 'windows':
    from ._daemonize_windows import Daemonizer
    from ._daemonize_windows import daemonize
    
    from ._signals_windows import SignalHandler1
    
else:
    raise RuntimeError(
        'Your runtime environment is unsupported by daemoniker.'
    )