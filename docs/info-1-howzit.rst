How it works
===============================================================================

Daemonization is a little tricky to get right (and very difficult to test).
Cross-platform "daemonization" is even less straightforward.

Daemonization: Unix
-------------------------------------------------------------------------------

On Unix, daemonization with Daemoniker performs the following steps:

1.  Create a PID file, failing if it already exists
2.  Register cleanup of the PID file for program exit
3.  Double-fork, dissociating itself from the original process group and any
    possible control terminal
4.  Reset ``umask`` and change current working directory
5.  Write its PID to the PID file
6.  Close file descriptors
7.  Redirect ``stdin``, ``stdout``, and ``stderr``.

.. note::

    To be considered a "well-behaved daemon", applications should also, at the
    least, handle termination through a ``SIGTERM`` handler (see 
    :doc:`api-2-signals` for using Daemoniker for this purpose).

Daemonization: Windows
-------------------------------------------------------------------------------

On Windows, "daemonization" with Daemoniker performs the following steps:

1.  Find the currently-running Python interpreter and file.
2.  Search for a copy of ``pythonw.exe`` within the same directory.
3.  Create a PID file, failing if it already exists.
4.  Save the current namespace and re-launch the script using ``pythonw.exe``.
5.  Bypass any already-completed code using an environment variable "switch".
6.  Change current working directory.
7.  Write its process handle to the PID file and register the file's cleanup
    for program exit.
8.  Extract the old namespace.
9.  Return the old namespace into the resumed "daemonized" process and allow
    the original process to exit.
    
.. warning::
    
    Due to the implementation of signals on Windows (as well as their use
    within the CPython interpreter), any signals sent to this daughter process
    will result in its **immediate termination, without any cleanup.** That
    means no ``atexit`` calls, no ``finally:`` blocks, etc. See 
    :ref:`howzit-win-signals` below for more information, or see
    :doc:`api-2-signals` for using Daemoniker as a workaround.

Signals: Unix
-------------------------------------------------------------------------------

Signal handling on Unix is very straightforward. The signal handler provided
by ``SigHandler1`` provides a thin wrapper around the built-in 
``signal.signal`` functionality. To maintain uniform cross-platform behavior,
the ``frame`` argument typically passed to ``signal.signal`` callbacks is
removed, but otherwise, Daemoniker is simply a convenience wrapper around
``signal.signal`` that includes several default signal handlers.

.. _howzit-win-signals:

Signals: Windows
-------------------------------------------------------------------------------

Signals on Windows are not natively supported by the operating system. They are
included in the C runtime environment provided by Windows, but their role is
substantially different than that in Unix systems. Furthermore, these signals
are largely limited to transmission between parent/child processes, and because
the "daemonization" process creates a fully-independent process group, every
available signal (including the Windows-specific ``CTRL_C_EVENT`` and
``CTRL_BREAK_EVENT``) result in immediate termination of the daughter process
without cleanup.

To avoid this thoroughly undesirable behavior, Daemoniker uses the following
workaround:

1.  From the main thread of the (daemonized) Python script, launch a daughter
    **thread** devoted to signal handling.
2.  From that daughter thread, launch a sleep-loop-forever daughter
    **process**.
3.  Overwrite the PID file with the PID of the daughter process.
4.  Wait for the daughter process to complete. If it was killed by a signal,
    its return code equals the number of the signal. Handle it accordingly.
5.  For every signal received, create a new daughter process.

Additionally, to mimic the behavior of ``signal.signal`` and replicate Unix
behavior, the default Daemoniker signal handlers call a ``ctypes`` API to raise
an exception **in the main thread** of the parent script.