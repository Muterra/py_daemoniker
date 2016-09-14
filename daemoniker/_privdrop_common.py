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
# import logging
# import traceback
# import os
# import sys
# import time
# import signal
# import pickle
# import base64
# import subprocess
# import multiprocessing
# import shlex
# import tempfile
# import atexit
# import ctypes
# import threading

# Intra-package dependencies
# from .utils import default_to

# from ._daemonize import _redirect_stds
# from ._daemonize import _write_pid
# from ._daemonize import send
# from ._daemonize import ping

# from .exceptions import SignalError
# from .exceptions import ReceivedSignal
# from .exceptions import SIGABRT
# from .exceptions import SIGINT
# from .exceptions import SIGTERM


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
