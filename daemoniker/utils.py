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

import sys

# Control * imports.
__all__ = [
]


# ###############################################
# Logging boilerplate
# ###############################################


import logging
logger = logging.getLogger(__name__)


# ###############################################
# Lib
# ###############################################
        
        
def platform_specificker(linux_choice, win_choice, cygwin_choice, osx_choice, 
                        other_choice):
    ''' For the three choices, returns whichever is appropriate for this
    platform.
    
    "Other" means a non-linux Unix system, see python.sys docs: 
        
        For Unix systems, except on Linux, this is the lowercased OS 
        name as returned by uname -s with the first part of the version 
        as returned by uname -r appended, e.g. 'sunos5' or 'freebsd8', 
        at the time when Python was built.
    '''
    platform = sys.platform
    if platform.startswith('linux'):
        return linux_choice
    elif platform.startswith('win32'):
        return win_choice
    elif platform.startswith('cygwin'):
        return cygwin_choice
    elif platform.startswith('darwin'):
        return osx_choice
    else:
        return other_choice


def default_to(check, default, comparator=None):
    ''' If check is None, apply default; else, return check.
    '''
    if comparator is None:
        if check is None:
            return default
        else:
            return check
    else:
        if check == comparator:
            return default
        else:
            return check