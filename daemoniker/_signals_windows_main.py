""" 

This file is separate from _signals_windows to avoid a RuntimeWarning caused by 
_signals_windows being both runned by python and imported by __init__

"""
from ._signals_windows import signals_main

if __name__ == '__main__':
    signals_main()