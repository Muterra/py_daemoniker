Daemoniker: cross-platform Python daemonization tools
===============================================================================

What is Daemoniker?
-------------------------------------------------------------------------------

Daemoniker provides a cross-platform Python API for running Python code as
a daemon. On Unix, it uses a standard double-fork procedure; on Windows, it
creates an independent subprocess for ``pythonw.exe`` that exists independently
of the initiating process.

Daemoniker also provides several utility tools for the resulting daemons. In
particular, it includes cross-platform signaling capability for the created
daemons.

Example usage
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    
Insert sample usage here, because that's sorta the whole point of this section:

.. code-block:: python

    >>> obj += ' Welcome to Hypergolix.'
    >>> obj.hgx_push_threadsafe()
    >>> obj
    <JsonProxy to 'Hello world! Welcome to Hypergolix.' at Ghid('AdGI5by1-Ppf0ymF26R37waIZnYADnPht5rZqLSDAmD0kV1ax94Yan_9mdd93-8i89QjDeIjBZOQhZxeG5O3HO8=')>

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
