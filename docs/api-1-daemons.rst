Daemonization API
===============================================================================

General Daemoniker usage should follow the following pattern:

.. code-block:: python

    from daemoniker import Daemonizer
    
    with Daemonizer() as (is_setup, daemonize):
        if is_setup:
            # This code is run before daemonization.
            do_things_here()
            
        # We need to explicitly pass resources to the daemon; other variables
        # may not be correct    
        my_arg1, my_arg2 = daemonize(
            'path/to/pid/file.pid', 
            my_arg1, 
            my_arg2,
            ...,
            **daemonize_kwargs
        )
    
    # We are now daemonized.
    code_continues_here()
    
When used in this manner, the ``Daemonizer`` context manager will return a
boolean ``is_setup`` and the :func:`daemonize` function.
    
.. note::
    
    Do not include an ``else`` clause after ``is_setup``. It will not be run
    on Unix:

    .. code-block:: python

        from daemoniker import Daemonizer
        
        with Daemonizer() as (is_setup, daemonize):
            if is_setup:
                # This code is run before daemonization.
                do_things_here()
            else:
                # This code will not run on Unix systems.
                do_no_things_here()
                
.. function:: daemonize(pid_file, *args, chdir=None, stdin_goto=None, \
                        stdout_goto=None, stderr_goto=None, umask=0o027, \
                        shielded_fds=None, fd_fallback_limit=1024, \
                        success_timeout=30, strip_cmd_args=False)
                    
    .. versionadded:: 0.1
    
    The function used to actually perform daemonization. It may be called
    directly, but is intended to be used within the ``Daemonizer`` context
    manager, as detailed above.
    
    .. warning::
    
        When used directly, all code prior to ``daemonize()`` will be repeated
        by the daemonized process. It is best to limit all pre-``daemonize``
        code to import statements. If you want to run setup code, use the
        context manager.
    
    .. note::
        
        All ``*args`` must be pickleable on Windows systems.
    
    :param str pid_file: The path to use for the PID file.
    :param ``*args``: All variables to preserve across the daemonization
        boundary. On Windows, only these values (which will be returned by
        ``daemonize``) are guaranteed to be persistent.
    :param str chdir: The path to use for the working directory after
        daemonizing. Defaults to the current directory, which can
        result in "directory busy" errors on both Unix and Windows systems.
        **This argument is keyword-only.**
    :param str stdin_goto: A filepath to redirect ``stdin`` into. A value of
        ``None`` defaults to ``os.devnull``. **This argument is keyword-only.**
    :param str stdout_goto: A filepath to redirect ``stdout`` into. A value of
        ``None`` defaults to ``os.devnull``. **This argument is keyword-only.**
    :param str stderr_goto: A filepath to redirect ``stderr`` into. A value of
        ``None`` defaults to ``os.devnull``. **This argument is keyword-only.**
    :param int umask: The file creation mask to apply to the daemonized
        process. Unused on Windows. **This argument is keyword-only.**
    :param shielded_fds: An iterable of integer file descriptors to shield from
        closure. Unused on Windows. **This argument is keyword-only.**
    :param int fd_ballback_limit: If the file descriptor ``resource`` hard
        limit and soft limit are both infinite, this fallback integer will be
        one greater than the highest file descriptor closed. Unused on Windows.
        **This argument is keyword-only.**
    :param success_timeout: A numeric limit, in seconds, for how long the
        parent process should wait for acknowledgment of successful startup by
        the daughter process. Unused on Unix. **This argument is
        keyword-only.**
    :param bool strip_cmd_args: If the current script was started from a prompt
        using arguments, as in ``python script.py --arg1 --arg2``, this value
        determines whether or not those arguments should be stripped when
        re-invoking the script. In this example, calling ``daemonize`` with
        ``strip_cmd_args=True`` would be re-invoke the script as
        ``python script.py``. Unused on Unix. **This argument is
        keyword-only.**
    :returns: ``*args``

    .. code-block:: python

        >>> from daemoniker import daemonize
        >>> daemonize('pid.pid')