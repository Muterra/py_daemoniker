'''
Testing boilerplate.

LICENSING
-------------------------------------------------

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
import argparse
import logging
import unittest
import sys

# From within the test folder
import logutils

# ###############################################
# Testing
# ###############################################
                
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Daemoniker test suite.')
    parser.add_argument(
        '--logdir', 
        action = 'store',
        type = str,
        default = None,
        help = 'Stores the log to a file in dir.'
    )
    parser.add_argument(
        '--verbosity', 
        action = 'store',
        default = 'warning', 
        type = str,
        help = 'Specify the logging level. '
                '"debug" -> most verbose, '
                '"info" -> somewhat verbose, '
                '"warning" -> default python verbosity, '
                '"error" -> quiet.',
    )
    parser.add_argument('unittest_args', nargs='*')

    args, unittest_args = parser.parse_known_args()
    
    if args.logdir is not None:
        logutils.autoconfig(
            tofile = True,
            logdirname = args.logdir,
            loglevel = args.verbosity
        )
    else:
        logutils.autoconfig(
            loglevel = args.verbosity
        )
    
    from autotest import *
    unittest.main(argv=sys.argv[:1] + unittest_args)