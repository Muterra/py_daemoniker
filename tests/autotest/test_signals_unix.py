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

from daemoniker._signals_unix import _SUPPORTED_PLATFORM

from daemoniker._signals_common import IGNORE_SIGNAL
from daemoniker._signals_common import send
from daemoniker._signals_common import ping

from daemoniker._signals_unix import SignalHandler1
from daemoniker._signals_unix import _restore_any_previous_handler

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
        
        
@unittest.skipIf(not _SUPPORTED_PLATFORM, 'Unsupported platform.')
class Signals_test(unittest.TestCase):
    def setUp(self):
        ''' Add a check that a test has not called for an exit, keeping
        forks from doing a bunch of nonsense.
        '''
        if _fixtures.__SKIP_ALL_REMAINING__:
            raise unittest.SkipTest('Internal call to skip remaining.')
    
    def test_default_handler(self):
        ''' Test the default signal handler.
        '''
        with self.assertRaises(SignalError):
            worker = threading.Thread(
                target = SignalHandler1._default_handler,
                args = (-42,),
                daemon = True
            )
            worker.start()
            time.sleep(.1)
            
        with self.assertRaises(SIGABRT):
            worker = threading.Thread(
                target = SignalHandler1._default_handler,
                args = (signal.SIGABRT,),
                daemon = True
            )
            worker.start()
            time.sleep(.1)
            
        with self.assertRaises(SIGINT):
            worker = threading.Thread(
                target = SignalHandler1._default_handler,
                args = (signal.SIGINT,),
                daemon = True
            )
            worker.start()
            time.sleep(.1)
            
        with self.assertRaises(SIGTERM):
            worker = threading.Thread(
                target = SignalHandler1._default_handler,
                args = (signal.SIGTERM,),
                daemon = True
            )
            worker.start()
            time.sleep(.1)
        
    def test_send(self):
        ''' Test sending signals.
        '''
        with tempfile.TemporaryDirectory() as dirpath:
            pidfile = dirpath + '/pid.pid'
            with open(pidfile, 'w') as f:
                f.write(str(os.getpid()) + '\n')
            
            for sig in [2, signal.SIGINT, SIGINT]:
                with self.subTest(sig):
                    with self.assertRaises(KeyboardInterrupt):
                        send(pidfile, sig)
                        time.sleep(.1)
        
    def test_receive(self):
        ''' Test receiving signals.
        '''
        timeout = 1
        pause = .1
        
        my_pid = os.getpid()
        
        events = {
            signal.SIGINT: threading.Event(),
            signal.SIGTERM: threading.Event(),
            signal.SIGABRT: threading.Event()
        }
        
        def handler(signum):
            events[signum].set()
        
        try:
            pidfile = dirpath + '/pid.pid'
            
            sighandler = SignalHandler1(
                pidfile, 
                sigint = handler, 
                sigterm = handler, 
                sigabrt = handler
            )
            sighandler.start()
            
            for signum in [signal.SIGINT, signal.SIGTERM, signal.SIGABRT]:
                with self.subTest(signum):
                    os.kill(my_pid, signum)
                    time.sleep(pause)
                    check_flag = events[signum]
                    self.assertTrue(check_flag.wait(timeout))
                    
        finally:
            sighandler.stop()
        

if __name__ == "__main__":
    unittest.main()