Signal handling API
===============================================================================

.. class:: SignalHandler1(pid_file, sigint=None, sigterm=None, sigabrt=None)

    .. versionadded:: 0.1
    
    Handles signals for the daemonized process.
    
    :param str pid_file: The path to the PID file.
    :param sigint: A callable handler for the ``SIGINT`` signal. May also be
        ``daemoniker.IGNORE_SIGNAL`` to explicitly ignore the signal. Passing
        the default value of ``None`` will assign the default ``SIGINT``
        handler, which will simply ``raise daemoniker.SIGINT`` **within the
        main thread.**
    :param sigterm: A callable handler for the ``SIGTERM`` signal. May also be
        ``daemoniker.IGNORE_SIGNAL`` to explicitly ignore the signal. Passing
        the default value of ``None`` will assign the default ``SIGTERM``
        handler, which will simply ``raise daemoniker.SIGTERM`` **within the
        main thread.**
    :param sigabrt: A callable handler for the ``SIGABRT`` signal. May also be
        ``daemoniker.IGNORE_SIGNAL`` to explicitly ignore the signal. Passing
        the default value of ``None`` will assign the default ``SIGABRT``
        handler, which will simply ``raise daemoniker.SIGABRT`` **within the
        main thread.**
        
    .. warning::
    
        There is a slight difference in handler calling between Windows and
        Unix systems. In every case, the default handler will always ``raise``
        from within **the main thread.** However, if you define a custom signal
        handler, on Windows systems it will be called from within a daughter
        thread devoted to signal handling. This has two consequences:
        
        1.  All signal handlers must be threadsafe
        2.  On Windows, future signals will be silently dropped until the
            callback completes
            
        On Unix systems, the handler will be called from within the main
        thread.
        
    .. note::
    
        On Windows, ``CTRL_C_EVENT`` and ``CTRL_BREAK_EVENT`` signals are both
        converted to ``SIGINT`` signals internally. This also applies to
        custom signal handlers.
            
    .. code-block:: python
    
        >>> from daemoniker import SignalHandler1
        >>> sighandler = SignalHandler1('pid.pid')

    .. attribute:: sigint

        The current handler for ``SIGINT`` signals. This must be a callable.
        It will be invoked with a single argument: the signal number. It may
        be re-assigned, even after calling :meth:`start`. Deleting it will
        restore the default ``Daemoniker`` signal handler; **to ignore it,
        instead assign** ``daemoniker.IGNORE_SIGNAL`` **as the handler.**

    .. attribute:: sigterm

        The current handler for ``SIGTERM`` signals. This must be a callable.
        It will be invoked with a single argument: the signal number. It may
        be re-assigned, even after calling :meth:`start`. Deleting it will
        restore the default ``Daemoniker`` signal handler; **to ignore it,
        instead assign** ``daemoniker.IGNORE_SIGNAL`` **as the handler.**

    .. attribute:: sigabrt

        The current handler for ``SIGABRT`` signals. This must be a callable.
        It will be invoked with a single argument: the signal number. It may
        be re-assigned, even after calling :meth:`start`. Deleting it will
        restore the default ``Daemoniker`` signal handler; **to ignore it,
        instead assign** ``daemoniker.IGNORE_SIGNAL`` **as the handler.**

    .. method:: start()
    
        Starts signal handling. Must be called to receive signals with the
        ``SignalHandler``.

    .. method:: stop()
    
        Stops signal handling. Must be called to stop receive signals. ``stop``
        will be automatically called:
        
        1.  at the interpreter exit, and
        2.  when the main thread exits.
        
        ``stop`` is idempotent. On Unix systems, it will also restore the
        previous signal handlers.

.. data:: IGNORE_SIGNAL

    A constant used to explicitly declare that a :class:`SignalHandler1` should
    ignore a particular signal.

.. function:: send(pid_file, signal)

    .. versionadded:: 0.1
    
    Send a ``signal`` to the process at ``pid_file``.
    
    :param str pid_file: The path to the PID file.
    :param signal: The signal to send. This may be either:
    
        1.  an *instance* of one of the :exc:`ReceivedSignal` exceptions, for
            example: ``daemoniker.SIGINT()`` (see :exc:`SIGINT`)
        2.  the *class* for one of the :exc:`ReceivedSignal` exceptions, for
            example: ``daemoniker.SIGINT`` (see :exc:`SIGINT`)
        3.  an integer-like value, corresponding to the signal number, for
            example: ``signal.SIGINT``

    .. code-block:: python

        >>> from daemoniker import send
        >>> from daemoniker import SIGINT
        >>> send('pid.pid', SIGINT)
