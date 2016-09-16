Daemonization API
===============================================================================

Simple daemonization may be performed by directly calling the :func:`daemonize`
funtion. In general, it should be the first thing called by your code (except
perhaps ``import`` statements, global declarations, and so forth). If you need
to do anything more complicated, use the :class:`Daemonizer` context manager.
                
.. function:: daemonize(pid_file, *args, chdir=None, stdin_goto=None, \
                        stdout_goto=None, stderr_goto=None, umask=0o027, \
                        shielded_fds=None, fd_fallback_limit=1024, \
                        success_timeout=30, strip_cmd_args=False)
                    
    .. versionadded:: 0.1
    
    The function used to actually perform daemonization. It may be called
    directly, but is intended to be used within the :class:`Daemonizer` context
    manager.
    
    .. warning::
    
        When used directly, all code prior to ``daemonize()`` will be repeated
        by the daemonized process on Windows systems. It is best to limit all
        pre-``daemonize`` code to import statements, global declarations, etc.
        If you want to run specialized setup code, use the :class:`Daemonizer`
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
        
.. class:: Daemonizer()

    .. versionadded:: 0.1
    
    A context manager for more advanced daemonization. Entering the context
    assigns a tuple of (boolean ``is_setup``, callable ``daemonizer``) to the
    ``with Daemonizer() as target:`` target.

    .. code-block:: python

        from daemoniker import Daemonizer
        
        with Daemonizer() as (is_setup, daemonizer):
            if is_setup:
                # This code is run before daemonization.
                do_things_here()
                
            # We need to explicitly pass resources to the daemon; other variables
            # may not be correct    
            is_parent, my_arg1, my_arg2 = daemonizer(
                'path/to/pid/file.pid', 
                my_arg1, 
                my_arg2,
                ...,
                **daemonize_kwargs
            )
            
            # This allows us to run parent-only post-daemonization code
            if is_parent:
                run_some_parent_code_here()
        
        # We are now daemonized and the parent has exited.
        code_continues_here(my_arg1, my_arg2)
        
    When used in this manner, the :class:`Daemonizer` context manager will
    return a boolean ``is_setup`` and a wrapped :func:`daemonize` function.
        
    .. note::
        
        Do not include an ``else`` clause after ``is_setup``. It will not be
        run on Unix:

        .. code-block:: python

            from daemoniker import Daemonizer
            
            with Daemonizer() as (is_setup, daemonizer):
                if is_setup:
                    # This code is run before daemonization.
                    do_things_here()
                else:
                    # This code will never run on Unix systems.
                    do_no_things_here()
                    
                ...
                    
    .. note::
    
        To prevent resource contention with the daemonized child, the parent
        process must be terminated via ``os._exit`` when exiting the context.
        You must perform any cleanup inside the ``if is_parent:`` block.
        
    .. method:: __enter__()
    
        Entering the context will return a tuple of:
        
        .. code-block:: python
        
            with Daemonizer() as (is_setup, daemonizer):
            
        ``is_setup`` is a ``bool`` that will be True when code is running in
        the parent (pre-daemonization) process.
        
        ``daemonizer`` wraps :func:`daemonize`, prepending a bool ``is_parent``
        to its return value. To prevent accidental manipulation of
        already-passed variables from the parent process, it also replaces
        them with ``None`` in the parent caller. It is otherwise identical to
        :func:`daemonize`. For example:
        
        .. code-block:: python

            from daemoniker import Daemonizer
            
            with Daemonizer() as (is_setup, daemonizer):
                if is_setup:
                    my_arg1 = 'foo'
                    my_arg2 = 'bar'
        
                is_parent, my_arg1, my_arg2 = daemonizer(
                    'path/to/pid/file.pid',
                    my_arg1,
                    my_arg2
                )
                
                # This code will only be run in the parent process
                if is_parent:
                    # These will return True
                    my_arg1 == None
                    my_arg2 == None
                    
                # This code will only be run in the daemonized child process
                else:
                    # These will return True
                    my_arg1 == 'foo'
                    my_arg2 == 'bar'
                    
            # The parent has now exited. All following code will only be run in
            # the daemonized child process.
            program_continues_here(my_arg1, my_arg2)
                    
    .. method:: __exit__()
    
        Exiting the context will do nothing in the child. In the parent,
        leaving the context will initiate a forced termination via ``os._exit``
        to prevent resource contention with the daemonized child.