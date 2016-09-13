'''
Boilerplate for automatic test detection.

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

__all__ = []

import pkgutil
import inspect

# Man, I'm really not sure how I feel about manipulating globals like this; I'd
# much rather hook into importlib or something. Well, one of these days, TODO.

# We want to load everything, but we want to do it in a way that doesn't cause
# name conflicts if the tests accidentally reuse test case names.
for loader, mod_name, is_pkg in pkgutil.walk_packages(__path__):
    module = loader.find_module(mod_name).load_module(mod_name)

    # So let's go ahead and forcibly name mangle everything.
    for member_name, member in inspect.getmembers(module):
        # Just for good measure, we want to skip everything that uses a single
        # underscore. Note that double underscores will be caught by this 
        # anyways, and aren't hugely useful because even non-self.__<something>
        # references will get name mangled within classes.
        if member_name.startswith('_'):
            continue
        
        # Mangle the name. This doesn't match up with "stock" name mangling, 
        # instead it's just <module name>_<member name>
        mangled_name = mod_name + '_' + member_name

        globals()[mangled_name] = member
        __all__.append(mangled_name)