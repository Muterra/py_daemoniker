""" 

This file is separate from _daemonize_windows to avoid a RuntimeWarning caused by 
_daemonize_windows being both runned by python and imported by __init__

"""

from ._daemonize_windows import daemonize_main

if __name__ == '__main__':
    daemonize_main()