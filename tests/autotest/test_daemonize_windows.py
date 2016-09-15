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
import pickle
import subprocess
import multiprocessing

from daemoniker._daemonize_windows import _SUPPORTED_PLATFORM

from daemoniker._daemonize_windows import Daemonizer
from daemoniker._daemonize_windows import daemonize
from daemoniker._daemonize_windows import _daemonize1
from daemoniker._daemonize_windows import _daemonize2
from daemoniker._daemonize_windows import _capability_check
from daemoniker._daemonize_windows import _filial_usurpation
from daemoniker._daemonize_windows import _clean_file
from daemoniker._daemonize_windows import _NamespacePasser
from daemoniker._daemonize_windows import _fork_worker


# ###############################################
# "Paragon of adequacy" test fixtures
# ###############################################


import _fixtures


def childproc_daemonizer(pid_file, token, res_path, check_path, check_seed,
                         parent_pid_file):
    try:
        with Daemonizer() as (is_setup, daemonize):
            if is_setup:
                # It should only exist if we run is_setup twice.
                if os.path.exists(check_path):
                    check_seed = 9999
                
                with open(check_path, 'w') as f:
                    f.write(str(check_seed) + '\n')
                    
            is_parent, token, res_path = daemonize(pid_file, token, res_path)
            
            if is_parent:
                with open(parent_pid_file, 'w') as f:
                    f.write(str(os.getpid()) + '\n')
                
            else:
                with open(res_path, 'w') as f:
                    f.write(str(token) + '\n')
                    
                # Wait a moment so that the grandparent can check our PID file
                time.sleep(1)
                
    except:
        logging.error(
            'Failure writing token w/ traceback: \n' + 
            ''.join(traceback.format_exc())
        )
        raise


def childproc_daemon(pid_file, token, res_path):
    ''' The test daemon quite simply daemonizes itself, does some stuff 
    to confirm its existence, waits for a signal to die, and then dies.
    '''
    # Daemonize ourselves
    token, res_path = daemonize(pid_file, token, res_path)
    
    # Unfortunately we don't have an easy way to deal with logging right now
    # from hypergolix import logutils
    # logname = logutils.autoconfig(suffix='daemon')
    
    # Write the token to the response path
    try:
        with open(res_path, 'w') as f:
            f.write(str(token) + '\n')
            
        # Wait 1 second so that the parent can make sure our PID file exists
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
        
        
@unittest.skipIf(not _SUPPORTED_PLATFORM, 'Unsupported platform.')
class Deamonizing_test(unittest.TestCase):
    def setUp(self):
        ''' Add a check that a test has not called for an exit, keeping
        forks from doing a bunch of nonsense.
        '''
        if _fixtures.__SKIP_ALL_REMAINING__:
            raise unittest.SkipTest('Internal call to skip remaining.')
        
    def test_filial_usurp(self):
        ''' Test decoupling child from parent environment. Platform-
        specific.
        '''
        cwd = os.getcwd()
        
        with tempfile.TemporaryDirectory() as dirname:
            chdir = os.path.abspath(dirname)
            
            _filial_usurpation(dirname)
            self.assertEqual(os.getcwd(), dirname)
            
            os.chdir(cwd)
        
    def test_clean_file(self):
        ''' Test closing files. Platform-specific.
        '''
        # Ensure this does not raise
        _clean_file('/this/path/does/not/exist')
        with tempfile.TemporaryDirectory() as dirname:
            path = dirname + '/test.txt'
            with open(path, 'w') as f:
                pass
            self.assertTrue(os.path.exists(path))
            _clean_file(path)
            self.assertFalse(os.path.exists(path))
        
    def test_namespace_passer(self):
        ''' Test the namespace passing thingajobber.
        '''
        with _NamespacePasser() as temppath:
            self.assertTrue(os.path.exists(temppath))
            
            # Make sure we can also open and write
            with open(temppath, 'w') as f:
                f.write('hello world')
                
            tempdir = os.path.dirname(temppath)
            
        # Ensure everything was cleaned up
        self.assertFalse(os.path.exists(temppath))
        self.assertFalse(os.path.exists(tempdir))
        
    def test_fork_worker(self):
        ''' Test the worker meant to start the new process. Platform-
        specific.
        '''
        with tempfile.TemporaryDirectory() as dirname:
            ns_path = dirname + '/test'
            child_env = os.environ
            pid_file = dirname + '/pid.pid'
            invocation = '"' + sys.executable + '" -c return'
            chdir = '/'
            stdin_goto = None
            stdout_goto = None
            stderr_goto = None
            _exit_caller = True
            args = ('hello world', 'I am tired', 'hello Tired, I am Dad.')
            
            _fork_worker(
                ns_path, 
                child_env, 
                pid_file, 
                invocation, 
                chdir,
                stdin_goto,
                stdout_goto,
                stderr_goto,
                _exit_caller,
                args
            )
            
            with open(ns_path, 'rb') as f:
                payload = pickle.load(f)
                
            self.assertEqual(payload[0], os.getpid())
            self.assertEqual(payload[1], pid_file)
            self.assertEqual(payload[2], chdir)
            self.assertEqual(payload[3], stdin_goto)
            self.assertEqual(payload[4], stdout_goto)
            self.assertEqual(payload[5], stderr_goto)
            self.assertEqual(payload[6], _exit_caller)
            self.assertEqual(payload[7:], args)
        
    def test_daemonize2(self):
        ''' Test respawning. Platform-specific.
        '''
        # Cache all of the stds
        stdin_fd = os.dup(0)
        stdout_fd = os.dup(1)
        stderr_fd = os.dup(2)
        
        cwd = os.getcwd()
        
        invocation = '"' + sys.executable + \
                     '" -c "import time; time.sleep(60)"'
        worker = None
        
        try:
            with _NamespacePasser() as ns_path:
                dirname = os.path.dirname(ns_path)
        
                worker = subprocess.Popen(invocation)
        
                parent = worker.pid
                pid_file = dirname + '/pid.pid'
                chdir = '/'
                stdin_goto = os.devnull
                stdout_goto = os.devnull
                stderr_goto = os.devnull
                _exit_caller = True
                args = ('hello world', 'I am tired', 'hello Tired, I am Dad.')
                
                pkg = (parent, pid_file, chdir, stdin_goto, stdout_goto, 
                       stderr_goto, _exit_caller) + args
                
                with open(ns_path, 'wb') as f:
                    pickle.dump(pkg, f, protocol=-1)
                    
                os.environ['__INVOKE_DAEMON__'] = ns_path
                
                result = _daemonize2()
                
                self.assertEqual(list(result), list(args))
                
        # Restore our original stdin, stdout, stderr. Do this before dir
        # cleanup or we'll get cleanup errors.
        finally:
            os.dup2(stdin_fd, 0)
            os.dup2(stdout_fd, 1)
            os.dup2(stderr_fd, 2)
            os.chdir(cwd)
            
            if worker is not None and worker.returncode is None:
                worker.terminate()
        
    def test_daemonization(self):
        ''' Test whole daemonization chain. Platform-specific.
        '''
        with tempfile.TemporaryDirectory() as dirname:
            
            pid_file = dirname + '/testpid.pid'
            token = 2718282
            res_path = dirname + '/response.txt'
            
            worker_env = {
                **os.environ,
                '__TESTWORKER__': 'True',
                '__WORKER_PIDFILE__': pid_file,
                '__WORKER_TOKEN__': str(token),
                '__WORKER_RESPATH__': res_path,
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
                self.assertTrue(response.startswith(str(token)))
                # Make sure the pid file exists
                self.assertTrue(os.path.exists(pid_file))
                    
                # Now hold off just a moment and then make sure the pid is 
                # cleaned up successfully. Note that this timing is dependent
                # upon the child process.
                time.sleep(5)
                self.assertFalse(os.path.exists(pid_file))
                
                
            # Terminate the worker if it remains.
            finally:
                if worker is not None and worker.returncode is None:
                    worker.terminate()
                
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
            parent_pid_file = dirname + '/parentpid.pid'
            
            worker_env = {
                **os.environ,
                '__CONTEXTWORKER__': 'True',
                '__WORKER_PIDFILE__': pid_file,
                '__WORKER_TOKEN__': str(token),
                '__WORKER_RESPATH__': res_path,
                '__WORKER_CHECKPATH__': check_path,
                '__WORKER_CHECKSEED__': str(check_seed),
                '__WORKER_PARENTPID__': parent_pid_file,
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
                time.sleep(.75)
                
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
                
                # Now make sure the parent pid file exists, and that it reads
                # the grandparent pid, and then remove it.
                self.assertTrue(os.path.exists(parent_pid_file))
                with open(parent_pid_file, 'r') as f:
                    grandparent_pid = int(f.read())
                self.assertEqual(grandparent_pid, worker.pid)
                # Don't need to cleanup because it's in a tempdir
                    
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
        pid_file = os.environ['__WORKER_PIDFILE__']
        token = int(os.environ['__WORKER_TOKEN__'])
        res_path = os.environ['__WORKER_RESPATH__']
        childproc_daemon(pid_file, token, res_path)
        
    elif '__CONTEXTWORKER__' in os.environ:
        try:
            pid_file = os.environ['__WORKER_PIDFILE__']
            token = int(os.environ['__WORKER_TOKEN__'])
            res_path = os.environ['__WORKER_RESPATH__']
            check_path = os.environ['__WORKER_CHECKPATH__']
            check_seed = int(os.environ['__WORKER_CHECKSEED__'])
            parent_pid_file = os.environ['__WORKER_PARENTPID__']
            childproc_daemonizer(
                pid_file, 
                token, 
                res_path, 
                check_path, 
                check_seed,
                parent_pid_file
            )
        except:
            with open(res_path,'w') as f:
                f.write(''.join(traceback.format_exc()))
            raise
        
    else:
        unittest.main()