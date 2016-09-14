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

This was written with heavy consultation of the following resources:
    Chad J. Schroeder, Creating a daemon the Python way (Python recipe) 
        http://code.activestate.com/recipes/
        278731-creating-a-daemon-the-python-way/
    Ilya Otyutskiy, Daemonize
        https://github.com/thesharp/daemonize
    David Mytton, unknown, et al: A simple daemon in Python
        http://www.jejik.com/articles/2007/02/
        a_simple_unix_linux_daemon_in_python/www.boxedice.com
    
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

        
def _setuser(user):
    ''' Normalizes user to a uid and sets the current uid, or does 
    nothing if user is None.
    '''
    if user is None:
        return
        
    # Normalize group to gid
    elif isinstance(user, str):
        uid = pwd.getpwnam(user).pw_uid
    # The group is already a gid.
    else:
        uid = user
        
    try:
        os.setuid(uid)
    except OSError:
        self.logger.error('Unable to change user.')
        sys.exit(1)
    
    
def _setgroup(group):
    ''' Normalizes group to a gid and sets the current gid, or does 
    nothing if group is None.
    '''
    if group is None:
        return
        
    # Normalize group to gid
    elif isinstance(group, str):
        gid = grp.getgrnam(group).gr_gid
    # The group is already a gid.
    else:
        gid = group
        
    try:
        os.setgid(gid)
    except OSError:
        self.logger.error('Unable to change group.')
        sys.exit(1)


def daemote(pid_file, user, group):
    ''' Change gid and uid, dropping privileges.
    
    Either user or group may explicitly pass None to keep it the same.
    
    The pid_file will be chown'ed so it can still be cleaned up.
    '''
    if not _SUPPORTED_PLATFORM:
        raise OSError('Daemotion is unsupported on your platform.')
    
    # No need to do anything special, just chown the pidfile
    # This will also catch any bad group, user names
    shutil.chown(pid_file, user, group)
    
    # Now update group and then user
    _setgroup(group)
    _setuser(user)
