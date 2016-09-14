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

from daemoniker import Daemonizer

from daemoniker._daemonize_common import _make_range_tuples
from daemoniker._daemonize_common import _flush_stds
from daemoniker._daemonize_common import _redirect_stds
from daemoniker._daemonize_common import _write_pid
from daemoniker._daemonize_common import _acquire_pidfile


# ###############################################
# "Paragon of adequacy" test fixtures
# ###############################################


import _fixtures


def childproc_daemonizer(pid_file, token, res_path, check_path, check_seed):
    try:
        with Daemonizer() as (is_setup, daemonize):
            if is_setup:
                # It should only exist if we run is_setup twice.
                if os.path.exists(check_path):
                    check_seed = 9999
                
                with open(check_path, 'w') as f:
                    f.write(str(check_seed) + '\n')
                    
            token, res_path = daemonize(pid_file, token, res_path)
            
            with open(res_path, 'w') as f:
                f.write(str(token) + '\n')
                
            # Wait a moment so that the parent can check our PID file
            time.sleep(1)
    except:
        logging.error(
            'Failure writing token w/ traceback: \n' + 
            ''.join(traceback.format_exc())
        )
        raise
        


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
                
    def test_context_manager(self):
        ''' Test the context manager. Should produce same results on
        Windows and Unix, but still needs to be run on both.
        '''
        with tempfile.TemporaryDirectory() as dirname:
            pid_file = dirname + '/testpid.pid'
            token = 2718282
            check_seed = 3179
            res_path = dirname + '/response.txt'
            # Check path is there to ensure that setup code only runs once
            check_path = dirname + '/check.txt'
            
            worker_env = {
                **os.environ,
                '__TESTWORKER__': 'True',
                '__WORKER_PIDFILE__': pid_file,
                '__WORKER_TOKEN__': str(token),
                '__WORKER_RESPATH__': res_path,
                '__WORKER_CHECKPATH__': check_path,
                '__WORKER_CHECKSEED__': str(check_seed),
            }
            
            # Create another instance of this same file in a daughter process
            # to shield us from the os._exit at the end of the daemonization
            # process
            invocation = '"' + sys.executable + '" ' + \
                         '"' + os.path.abspath(__file__) + '"'
            worker = None
            
            try:
                # Create the actual worker
                worker = subprocess.Popen(
                    invocation,
                    # We're passing args via environment vars.
                    env = worker_env,
                )
                
                # Wait a moment for the daemon to show up
                time.sleep(.5)
                
                # Now read the res_path if it's available
                try:
                    with open(res_path, 'r') as res:
                        response = res.read()
                
                except (IOError, OSError) as exc:
                    raise AssertionError from exc
                    
                # Make sure the token matches
                try:
                    self.assertEqual(int(response), token)
                except:
                    print(response)
                    raise
                    
                # Make sure the pid file exists
                self.assertTrue(os.path.exists(pid_file))
                
                # Now read the check_path if it's available
                try:
                    with open(check_path, 'r') as f:
                        check = f.read()
                
                except (IOError, OSError) as exc:
                    raise AssertionError from exc
                self.assertEqual(int(check), check_seed)
                    
                # Now hold off just a moment and then make sure the pid is 
                # cleaned up successfully. Note that this timing is dependent
                # upon the child process.
                time.sleep(5)
                self.assertFalse(os.path.exists(pid_file))
                
                # And verify the check file was not overwritten either
                try:
                    with open(check_path, 'r') as f:
                        check = f.read()
                
                except (IOError, OSError) as exc:
                    raise AssertionError from exc
                self.assertEqual(int(check), check_seed)
                
                
            # Terminate the worker if it remains.
            finally:
                if worker is not None and worker.returncode is None:
                    worker.terminate()
        

if __name__ == "__main__":
    if '__TESTWORKER__' in os.environ:
        try:
            pid_file = os.environ['__WORKER_PIDFILE__']
            token = int(os.environ['__WORKER_TOKEN__'])
            res_path = os.environ['__WORKER_RESPATH__']
            check_path = os.environ['__WORKER_CHECKPATH__']
            check_seed = int(os.environ['__WORKER_CHECKSEED__'])
            childproc_daemonizer(
                pid_file, 
                token, 
                res_path, 
                check_path, 
                check_seed
            )
        except:
            with open(res_path,'w') as f:
                f.write(''.join(traceback.format_exc()))
            raise
            
    else:
        unittest.main()