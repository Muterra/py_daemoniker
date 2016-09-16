Daemoniker: cross-platform Python daemonization tools
===============================================================================

What is Daemoniker?
-------------------------------------------------------------------------------

Daemoniker provides a cross-platform Python API for running and signaling
daemonized Python code. On Unix, it uses a standard double-fork procedure; on
Windows, it creates an separate subprocess for ``pythonw.exe`` that exists
independently of the initiating process.

Daemoniker also provides several utility tools for the resulting daemons. In
particular, it includes cross-platform signaling capability for the created
daemons.

Installing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Daemoniker requires **Python 3.5** or higher.

.. code-block:: console

    pip install daemoniker

Example usage
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    
At the beginning of your script, invoke daemonization through the
``daemoniker.Daemonizer`` context manager:

.. code-block:: python

    from daemoniker import Daemonizer
    
    with Daemonizer() as (is_setup, daemonizer):
        if is_setup:
            # This code is run before daemonization.
            do_things_here()
            
        # We need to explicitly pass resources to the daemon; other variables
        # may not be correct    
        is_parent, my_arg1, my_arg2 = daemonizer(
            path_to_pid_file, 
            my_arg1, 
            my_arg2
        )
        
        if is_parent:
            # Run code in the parent after daemonization
            parent_only_code()
    
    # We are now daemonized, and the parent just exited.
    code_continues_here()
    
Signal handling works through the same ``path_to_pid_file``:

.. code-block:: python

    from daemoniker import SignalHandler1
    
    # Create a signal handler that uses the daemoniker default handlers for
    # ``SIGINT``, ``SIGTERM``, and ``SIGABRT``
    sighandler = SignalHandler1(path_to_pid_file)
    sighandler.start()
    
    # Or, define your own handlers, even after starting signal handling
    def handle_sigint(signum):
        print('SIGINT received.')
    sighandler.sigint = handle_sigint
    
These processes can then be sent signals from other processes:

.. code-block:: python

    from daemoniker import send
    from daemoniker import SIGINT
    
    # Send a SIGINT to a process denoted by a PID file
    send(path_to_pid_file, SIGINT)

Comparison to ``multiprocessing``, ``subprocess``, etc
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The modules included in the standard library for creating new processes from
the current Python interpreter are intended for dependent subprocesses only.
They will not continue to run if the current Python session is terminated, and
when called from a Unix terminal in the background using ``&``, etc, they will
still result in the process being reaped upon terminal exit (this includes SSH
session termination).

Daemonziation using daemoniker creates fully-independent, well-behaved
processes that place no requirements on the launching terminal.

Comparison to ``signal.signal``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For Unix systems, Daemoniker provides a lightweight wrapper around
``signal.signal`` and the poorly-named ``os.kill`` for the three signals
(``SIGINT``, ``SIGTERM``, and ``SIGABRT``) that are both available on
Windows and meaningful within the Python interpreter. On Unix systems,
Daemoniker signal handling gives you little more than convenience.

On Windows systems, signal handling is poorly-supported at best. Furthermore,
when sending signals to the independent processes created through Daemoniker,
*all* signals sent to the process through ``os.kill`` will result in the
target (daemon) process immediately exiting **without cleanup** (bypassing
``try:``/``finally:`` blocks, ``atexit`` calls, etc). On Windows systems,
Daemoniker substantially expands this behavior, allowing Python processes to
safely handle signals.

For more information on standard Windows signal handling, see:

1. `Sending ^C to Python subprocess objects on Windows <http://stackoverflow.com/questions/7085604/sending-c-to-python-subprocess-objects-on-windows>`_
2. `Python send SIGINT to subprocess using os.kill as if pressing Ctrl+C <http://stackoverflow.com/questions/26578799/python-send-sigint-to-subprocess-using-os-kill-as-if-pressing-ctrlc>`_
3. `How to handle the signal in python on windows machine <http://stackoverflow.com/questions/35772001/how-to-handle-the-signal-in-python-on-windows-machine>`_


ToC
-------------------------------------------------------------------------------

.. toctree::
    :maxdepth: 2

    info-1-howzit
    api-1-daemons
    api-2-signals
    api-3-exceptions

..
    Comment all of this stuff out until it's deemed useful
    
    Indices and tables
    -------------------------------------------------------------------------------

    * :ref:`genindex`
    * :ref:`modindex`
    * :ref:`search`
