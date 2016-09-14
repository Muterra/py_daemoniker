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

from daemoniker._signals_windows import SignalHandler1
from daemoniker._signals_windows import _sketch_raise_in_main
from daemoniker._signals_windows import _default_handler
from daemoniker._signals_windows import _noop
# No good way to test this, but it's super simple so whatever
# from daemoniker._signals_windows import _infinite_noop
from daemoniker._signals_windows import _await_signal
from daemoniker._signals_windows import _normalize_handler

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
    
    def test_raise_in_main(self):
        ''' Punch holes in the interpreter for fun and profit!
        '''
        with self.assertRaises(SignalError):
            worker = threading.Thread(
                target = _sketch_raise_in_main,
                args = (SignalError,),
                daemon = True
            )
            worker.start()
            time.sleep(.1)
    
    def test_default_handler(self):
        ''' Test the default signal handler.
        '''
        with self.assertRaises(SignalError):
            worker = threading.Thread(
                target = _default_handler,
                args = (-42,),
                daemon = True
            )
            worker.start()
            time.sleep(.1)
            
        with self.assertRaises(SIGABRT):
            worker = threading.Thread(
                target = _default_handler,
                args = (signal.SIGABRT,),
                daemon = True
            )
            worker.start()
            time.sleep(.1)
            
        with self.assertRaises(SIGINT):
            worker = threading.Thread(
                target = _default_handler,
                args = (signal.SIGINT,),
                daemon = True
            )
            worker.start()
            time.sleep(.1)
            
        with self.assertRaises(SIGTERM):
            worker = threading.Thread(
                target = _default_handler,
                args = (signal.SIGTERM,),
                daemon = True
            )
            worker.start()
            time.sleep(.1)
        
    def test_noop(self):
        ''' Hey, it's a gimme.
        '''
        _noop(signal.SIGINT)
        _noop(signal.SIGTERM)
        _noop(signal.SIGABRT)
        
    def test_signal_waiting(self):
        ''' Fixture thine self.
        '''
        proc1 = ProcFixture(signal.SIGINT)
        proc2 = ProcFixture(signal.SIGTERM)
        proc3 = ProcFixture(signal.SIGABRT)
        proc4 = ProcFixture(signal.CTRL_C_EVENT)
        proc5 = ProcFixture(signal.CTRL_BREAK_EVENT)
        
        self.assertEqual(_await_signal(proc1), signal.SIGINT)
        self.assertEqual(_await_signal(proc2), signal.SIGTERM)
        self.assertEqual(_await_signal(proc3), signal.SIGABRT)
        self.assertEqual(_await_signal(proc4), signal.SIGINT)
        self.assertEqual(_await_signal(proc5), signal.SIGINT)
        
    def test_handler_normalization(self):
        ''' Convert defaults and constants to their intended targets.
        '''
        handler = lambda x: x
        
        self.assertEqual(_normalize_handler(handler), handler)
        self.assertEqual(_normalize_handler(None), _default_handler)
        self.assertEqual(_normalize_handler(IGNORE_SIGNAL), _noop)
        
    def test_send(self):
        ''' Test sending signals.
        '''
        python_path = sys.executable
        python_path = os.path.abspath(python_path)
        worker_cmd = ('"' + python_path + '" -c ' + 
                      '"import time; time.sleep(60)"')
        
        with tempfile.TemporaryDirectory() as dirpath:
            pidfile = dirpath + '/pid.pid'
            
            for sig in [2, signal.SIGTERM, SIGABRT]:
                with self.subTest(sig):
                    worker = subprocess.Popen(
                        worker_cmd
                    )
                    worker_pid = worker.pid
                    
                    with open(pidfile, 'w') as f:
                        f.write(str(worker_pid) + '\n')
                        
                    send(pidfile, sig)
                    worker.wait()
                    self.assertEqual(worker.returncode, int(sig))
        
                    # Get a false PID so we can test against it as well
                    # Note the mild race condition here
                    bad_pid = os.getpid()
                    while psutil.pid_exists(bad_pid):
                        bad_pid = random.randint(1000, 99999)
                    
                    with open(pidfile, 'w') as f:
                        f.write(str(bad_pid) + '\n')
                        
                    with self.assertRaises(OSError):
                        send(pidfile, sig)
        
    def test_receive(self):
        ''' Test receiving signals.
        '''
        timeout = 1
        pause = .1
        
        events = {
            signal.SIGINT: threading.Event(),
            signal.SIGTERM: threading.Event(),
            signal.SIGABRT: threading.Event()
        }
        
        def handler(signum):
            events[signum].set()
        
        with tempfile.TemporaryDirectory() as dirpath:
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
                    with open(pidfile, 'r') as f:
                        pid = int(f.read())
                        
                    os.kill(pid, signum)
                    check_flag = events[signum]
                    self.assertTrue(check_flag.wait(timeout))
                    time.sleep(pause)
                    
            sighandler.stop()
        

if __name__ == "__main__":
    unittest.main()