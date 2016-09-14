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
import logging
import tempfile
import sys
import os
import time
import shutil
import random
import subprocess
import traceback

from daemoniker.utils import platform_specificker

from daemoniker._daemonize_common import _make_range_tuples
from daemoniker._daemonize_common import _flush_stds
from daemoniker._daemonize_common import _redirect_stds
from daemoniker._daemonize_common import _write_pid
from daemoniker._daemonize_common import _acquire_pidfile


# ###############################################
# "Paragon of adequacy" test fixtures
# ###############################################


import _fixtures


# ###############################################
# Testing
# ###############################################
        
        
class Deamonizing_test(unittest.TestCase):
    def setUp(self):
        ''' Add a check that a test has not called for an exit, keeping
        forks from doing a bunch of nonsense.
        '''
        if _fixtures.__SKIP_ALL_REMAINING__:
            raise unittest.SkipTest('Internal call to skip remaining.')
    
    def test_make_ranges(self):
        ''' Test making appropriate ranges for file auto-closure. 
        Platform-independent.
        '''
        # This would be better done with hypothesis, but that can come later.
        argsets = []
        expected_results = []
        
        argsets.append(
            (0, 5, [])
        )
        expected_results.append(
            [
                (0, 5),
            ]
        )
        
        argsets.append(
            (3, 10, [1, 2])
        )
        expected_results.append(
            [
                (3, 10),
            ]
        )
        
        argsets.append(
            (3, 7, [4,])
        )
        expected_results.append(
            [
                (3, 4),
                (5, 7),
            ]
        )
        
        argsets.append(
            (3, 14, [4, 5, 10])
        )
        expected_results.append(
            [
                (3, 4),
                (6, 10),
                (11, 14),
            ]
        )
        
        argsets.append(
            (1, 3, [1, 2, 3])
        )
        expected_results.append(
            [
            ]
        )
        
        for argset, expected_result in zip(argsets, expected_results):
            with self.subTest(argset):
                actual_result = _make_range_tuples(*argset)
                self.assertEqual(actual_result, expected_result)
        
    def test_flush_stds(self):
        ''' Test flushing stds. Platform-independent.
        '''
        # Should this do any kind of verification or summat?
        _flush_stds()
        
    def test_redirect_stds(self):
        ''' Test redirecting stds. Platform-independent.
        '''
        stdin = sys.stdin
        stdout = sys.stdout
        stderr = sys.stderr
                
        # Cache all of the stds
        stdin_fd = os.dup(0)
        stdout_fd = os.dup(1)
        stderr_fd = os.dup(2)
        
        # Perform the actual tests
        with tempfile.TemporaryDirectory() as dirname:
            try:
                with self.subTest('Separate streams'):
                    _redirect_stds(
                        dirname + '/stdin.txt',
                        dirname + '/stdout.txt',
                        dirname + '/stderr.txt'
                    )
                
                with self.subTest('Shared streams'):
                    _redirect_stds(
                        dirname + '/stdin2.txt',
                        dirname + '/stdshr.txt',
                        dirname + '/stdshr.txt'
                    )
                
                with self.subTest('Combined streams'):
                    _redirect_stds(
                        dirname + '/stdcomb.txt',
                        dirname + '/stdcomb.txt',
                        dirname + '/stdcomb.txt'
                    )
        
            # Restore our original stdin, stdout, stderr. Do this before dir
            # cleanup or we'll get cleanup errors.
            finally:
                os.dup2(stdin_fd, 0)
                os.dup2(stdout_fd, 1)
                os.dup2(stderr_fd, 2)
        
    def test_write_pid(self):
        ''' Test that writing the pid to the pidfile worked. Platform-
        specific.
        '''
        pid = str(os.getpid())
        # Test new file
        with tempfile.TemporaryFile('w+') as fp:
            _write_pid(fp)
            fp.seek(0)
            self.assertEqual(fp.read(), pid + '\n')
            
        # Test existing file
        with tempfile.TemporaryFile('w+') as fp:
            fp.write('hello world, overwrite me!')
            _write_pid(fp)
            fp.seek(0)
            self.assertEqual(fp.read(), pid + '\n')
            
    def test_acquire_pidfile(self):
        ''' Test that acquiring/"locking" the pidfile worked.
        Platform-independent.
        '''
        with tempfile.TemporaryDirectory() as dirname:
            fpath = dirname + '/testpid.txt'
                
            self.assertFalse(os.path.exists(fpath))
            try:
                pidfile = _acquire_pidfile(fpath)
                self.assertTrue(os.path.exists(fpath))
                with self.assertRaises(SystemExit):
                    pidfile = _acquire_pidfile(fpath, silence_logger=True)
            finally:
                pidfile.close()
        

if __name__ == "__main__":
    unittest.main()