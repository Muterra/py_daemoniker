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

import unittest
import collections
import threading
import logging
import tempfile
import sys
import os
import time
import shutil
import pickle
import subprocess
import signal
import random

from daemoniker._signals_windows import _SUPPORTED_PLATFORM

from daemoniker._signals_common import IGNORE_SIGNAL
from daemoniker._signals_common import send
from daemoniker._signals_common import ping
from daemoniker._signals_common import _noop
from daemoniker._signals_common import _normalize_handler

from daemoniker.exceptions import SignalError
from daemoniker.exceptions import ReceivedSignal
from daemoniker.exceptions import SIGINT
from daemoniker.exceptions import SIGTERM
from daemoniker.exceptions import SIGABRT

if _SUPPORTED_PLATFORM:
    import psutil


# ###############################################
# "Paragon of adequacy" test fixtures
# ###############################################


import _fixtures


class ProcFixture:
    def __init__(self, returncode):
        self.returncode = returncode
        
    def wait(self):
        pass


# ###############################################
# Testing
# ###############################################
        
        
class Signals_test(unittest.TestCase):
    def setUp(self):
        ''' Add a check that a test has not called for an exit, keeping
        forks from doing a bunch of nonsense.
        '''
        if _fixtures.__SKIP_ALL_REMAINING__:
            raise unittest.SkipTest('Internal call to skip remaining.')
        
    def test_noop(self):
        ''' Hey, it's a gimme.
        '''
        _noop(signal.SIGINT)
        _noop(signal.SIGTERM)
        _noop(signal.SIGABRT)
        
    def test_handler_normalization(self):
        ''' Convert defaults and constants to their intended targets.
        '''
        handler = lambda x: x
        default_handler = lambda y: y
        
        self.assertEqual(
            _normalize_handler(handler, default_handler), 
            handler
        )
        self.assertEqual(
            _normalize_handler(None, default_handler), 
            default_handler
        )
        self.assertEqual(
            _normalize_handler(IGNORE_SIGNAL, default_handler), 
            _noop
        )
        

if __name__ == "__main__":
    unittest.main()