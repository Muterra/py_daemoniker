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

# Global dependencies
import os
import sys
import signal
import logging
import atexit
import traceback
import shutil

# Intra-package dependencies
from .utils import default_to


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

    
def _make_range_tuples(start, stop, exclude):
    ''' Creates a list of tuples for all ranges needed to close all 
    files between start and stop, except exclude. Ex:
    start=3, stop=7, exclude={4,}:
        (3, 4),
        (5, 7)
    '''
    # Make a list copy of exclude, discarding anything less than stop
    exclude = [ii for ii in exclude if ii >= start]
    # Sort ascending
    exclude.sort()
    
    ranges = []
    seeker = start
    for ii in exclude:
        # Only add actual slices (it wouldn't matter if we added empty ones, 
        # but there's also no reason to).
        if seeker != ii:
            this_range = (seeker, ii)
            ranges.append(this_range)
            
        # But always do this.
        seeker = ii + 1
        
    # Don't forget to add the final range!
    if seeker < stop:
        final_range = (seeker, stop)
        ranges.append(final_range)
        
    return ranges

        
def _flush_stds():
    ''' Flush stdout and stderr.
    
    Note special casing needed for pythonw.exe, which has no stdout or 
    stderr.
    '''
    try:
        sys.stdout.flush()
    except BlockingIOError:
        logger.error(
            'Failed to flush stdout w/ traceback: \n' + 
            ''.join(traceback.format_exc())
        )
        # Honestly not sure if we should exit here.

    try:
        sys.stderr.flush()
    except BlockingIOError:
        logger.error(
            'Failed to flush stderr w/ traceback: \n' + 
            ''.join(traceback.format_exc())
        )
        # Honestly not sure if we should exit here.

        
def _redirect_stds(stdin_goto, stdout_goto, stderr_goto):
    ''' Set stdin, stdout, sterr. If any of the paths don't exist, 
    create them first.
    '''
    # The general strategy here is to:
    # 1. figure out which unique paths we need to open for the redirects
    # 2. figure out the minimum access we need to open them with
    # 3. open the files to get them a file descriptor
    # 4. copy those file descriptors into the FD's used for stdio, etc
    # 5. close the original file descriptors
    
    # Remove repeated values through a set.
    streams = {stdin_goto, stdout_goto, stderr_goto}
    # Transform that into a dictionary of {location: 0, location: 0...}
    # Basically, start from zero permissions
    streams = {stream: 0 for stream in streams}
    # And now create a bitmask for each of reading and writing
    read_mask = 0b01
    write_mask = 0b10
    rw_mask = 0b11
    # Update the streams dict depending on what access each stream requires
    streams[stdin_goto] |= read_mask
    streams[stdout_goto] |= write_mask
    streams[stderr_goto] |= write_mask
    # Now create a lookup to transform our masks into file access levels
    access_lookup = {
        read_mask: os.O_RDONLY,
        write_mask: os.O_WRONLY,
        rw_mask: os.O_RDWR
    }
    access_lookup_2 = {
        read_mask: 'r',
        write_mask: 'w',
        rw_mask: 'w+'
    }
    access_mode = {}
    
    # Now, use our mask lookup to translate into actual file descriptors
    for stream in streams:
        # First create the file if its missing.
        if not os.path.exists(stream):
            with open(stream, 'w'):
                pass
        
        # Transform the mask into the actual access level.
        access = access_lookup[streams[stream]]
        # Open the file with that level of access.
        stream_fd = os.open(stream, access)
        # Also alias the mode in case of pythonw.exe
        access_mode[stream] = access_lookup_2[streams[stream]]
        # And update streams to be that, instead of the access mask.
        streams[stream] = stream_fd
        # We cannot immediately close the stream, because we'll get an 
        # error about a bad file descriptor.
    
    # Okay, duplicate our streams into the FDs for stdin, stdout, stderr.
    stdin_fd = streams[stdin_goto]
    stdout_fd = streams[stdout_goto]
    stderr_fd = streams[stderr_goto]
    
    # Note that we need special casing for pythonw.exe, which has no stds
    if sys.stdout is None:
        open_streams = {}
        for stream in streams:
            open_streams[stream] = os.fdopen(
                fd = streams[stream], 
                mode = access_mode[stream]
            )
            
        sys.stdin = open_streams[stdin_goto]
        sys.stdout = open_streams[stdout_goto]
        sys.stderr = open_streams[stderr_goto]
        
    else:
        # Flush before transitioning
        _flush_stds()
        # Do iiiitttttt
        os.dup2(stdin_fd, 0)
        os.dup2(stdout_fd, 1)
        os.dup2(stderr_fd, 2)

        # Finally, close the extra fds.
        for duped_fd in streams.values():
            os.close(duped_fd)

        
def _write_pid(locked_pidfile):
    ''' Write our PID to the (already "locked" (by us)) PIDfile.
    '''
    locked_pidfile.seek(0)
    locked_pidfile.truncate(0)
    pid = str(os.getpid())
    locked_pidfile.write(pid + '\n')
    locked_pidfile.flush()
        
        
def _acquire_pidfile(pid_file, ignore_lock=False, silence_logger=False):
    ''' Opens the pid_file, but unfortunately, as this is Windows, we 
    cannot really lock it. Assume existence is equivalent to locking,
    unless autoclean=True.
    '''
    try:
        if os.path.isfile(pid_file):
            if ignore_lock:
                if not silence_logger:
                    logger.warning(
                        'PID file already exists. It will be overwritten with '
                        'the new PID upon successful daemonization.'
                    )
                open_pid = open(pid_file, 'r+')
                
            else:
                if not silence_logger:
                    logger.critical(
                        'PID file already exists. Acquire with autoclean=True '
                        'to force cleanup of existing PID file. Traceback:\n' + 
                        ''.join(traceback.format_exc())
                    )
                raise SystemExit('Unable to acquire PID file.')
                
        else:
            open_pid = open(pid_file, 'w+')
            
    except (IOError, OSError) as exc:
        logger.critical(
            'Unable to create/open the PID file w/ traceback: \n' + 
            ''.join(traceback.format_exc())
        )
        raise SystemExit('Unable to create/open PID file.') from exc
        
    return open_pid
