Exception API
===============================================================================

.. exception:: DaemonikerException

    All of the custom exceptions in ``Daemoniker`` subclass this exception. As
    such, an application can catch any ``Daemoniker`` exception via:
    
    .. code-block:: python
    
        try:
            code_goes_here()
            
        except DaemonikerException:
            handle_error_here()

.. exception:: SignalError
    
    These errors are only raised if something goes wrong internally while
    handling signals.
    
.. exception:: ReceivedSignal

    Subclasses of ``ReceivedSignal`` exceptions are raised by the default
    signal handlers. A ``ReceivedSignal`` will only be raise directly:
    
    1.  if the actual signal number passed to the callback does not match its
        expected value.
    2.  if, on Windows, the signal handling daughter process terminates
        abnormally.
        
    .. note::
    
        Calling ``int()`` on a ``ReceivedSignal`` class or instance, or a
        class or instance of any of its subclasses, will return the signal
        number associated with the signal.
        
.. exception:: SIGINT

    Raised for incoming ``SIGINT`` signals. May also be used to :func:`send`
    signals to other processes.
    
    :attr SIGNUM: The signal number associated with the signal.
        
.. exception:: SIGTERM

    Raised for incoming ``SIGTERM`` signals. May also be used to :func:`send`
    signals to other processes.
    
    :attr SIGNUM: The signal number associated with the signal.
        
.. exception:: SIGABRT

    Raised for incoming ``SIGABRT`` signals. May also be used to :func:`send`
    signals to other processes.
    
    :attr SIGNUM: The signal number associated with the signal.
    
    
Exception hierarchy
-------------------------------------------------------------------------------

The ``Daemoniker`` exceptions have the following inheritance::

    DaemonikerException
        SignalError
        ReceivedSignal
            SIGINT
            SIGTERM
            SIGABRT
