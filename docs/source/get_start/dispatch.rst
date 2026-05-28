Dispatch usage
====================

An alternative to ``argparse`` subcommands, :class:`~argclz.dispatch.core.Dispatch`
provides a way to call distinct functions
by the given command name. Unlike ``argparse`` subcommands, the user has more freedom to decide when
and how to use it, and it does not restrict the command-line parsing control flow.

With :class:`~argclz.dispatch.core.Dispatch`, it packs logic control flow, help document and source code together,
which makes codebase maintainability easier.

.. seealso ::

    see dispatch usage in :mod:`argclz.dispatch`

Normal use case with commandline
--------------------------------

.. code-block:: python

    from argclz import *
    from argclz.dispatch import Dispatch, dispatch

    class Main(AbstractParser, Dispatch): # [1]

        command:str = pos_argument('CMD') # [2]
        command_args:list[str] = var_argument('ARGS') # [2]

        def run(self):
            self.invoke_command(self.command, *self.command_args) # [3]

        @dispatch('A') # [4]
        def run_a(self):
            ...

        @dispatch('B') # [4]
        def run_b(self):
            ...

    Main().main()

1. inherit ``Dispatch`` to gain related methods, such as ``invoke_command``.
2. we use ``command`` argument to decide which dispatch function need to be run.
3. run dispatch function according to ``command`` argument. User has more control on when to call.
4. methods labeled as dispatch functions.

Other use case
--------------

Beside using dispatch as sub commands, it can be used as a restricted set (or an enum) with individual,
specific behavior. They can be grouped into different dispatch group isolated from default group.

.. code-block:: python

    from argclz import *
    from argclz.dispatch import Dispatch, dispatch, dispatch_group

    class Main(AbstractParser, Dispatch):
        interface: str = argument('--int') # [1]
        interface_group = dispatch_group('interface') # [2]

        @interface_group('local') # [3]
        def get_local_interface(self) -> Interface:
            ...
        @interface_group('remote') # [3]
        def get_remote_interface(self) -> Interface:
            ...

        def run(self):
            # [4] without dispatch
            match self.interface:
                case 'local':
                    interface = self.get_local_interface()
                case 'remote':
                    interface = self.get_remote_interface()
                case _:
                    raise ValueError(f'unknown interface : {self.interface}')

            # [5] with dispatch
            interface = self.interface_group.invoke_command(self.interface)

            # [6]
            self.run_with_interface(interface, ...)

        def run_with_interface(self, inf: Interface):
            ...

1. This argument accept the value for dispatching group ``interface``
2. Create a dispatch group named ``interface``
3. declare functions as dispatch function under ``interface`` group.
4. If we do not use dispatch, we have to do match-case-like code-block manually.
5. with dispatch, it becomes one function call.
   Moreover, variable ``interface`` can be inlined into following method call.
6. remaining program logics.

Grouping
--------

The following code do the same thing.

.. code-block:: python

    from argclz import *
    from argclz.dispatch import Dispatch, dispatch

    class Main(AbstractParser, Dispatch):

        # ----------------------------------
        @dispatch('A', group='group') # [1]
        def group_a(self): ...

        # ----------------------------------
        group_a = dispatch_group('group') # [2]
        @dispatch('A', group=group_a) # [3]
        def group_a(self): ...

        # ----------------------------------
        @group_a('A') # [4]
        def group_a(self): ...

1. Label a dispatch function under group ``group`` (literal str).
2. Declare a dispatch group with a name ``group``.
3. Label a dispatch function under group ``group`` (a dispatch group).
4. use the dispatch group ``group`` to label a dispatch function.

**Invoke command under particular group**

.. code-block:: python

    class Main(AbstractParser, Dispatch): # [1]
        def run(self):
            # ----------------------------------
            self.invoke_group_command('group', 'A') # [2]

            # ----------------------------------
            self.invoke_group_command(self.group_a, 'A') # [3]

            # ----------------------------------
            self.group_a.invoke_command('A') # [4]

1. Continuous from above example, but adding following contents.
2. use :meth:`~argclz.dispatch.core.Dispatch.invoke_group_command` with literal str group name
3. use :meth:`~argclz.dispatch.core.Dispatch.invoke_group_command` with a dispatch group
4. use the dispatch group

**More methods**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - **Method**
     - **Description**
   * - :meth:`list_commands() <argclz.dispatch.core.BoundDispatchGroup.list_commands>`
     - todo
   * - :meth:`find_command(command) <argclz.dispatch.core.BoundDispatchGroup.find_command>`
     - todo

Validation
----------

TODO

Help Document
-------------

The help text generating of :class:`~argclz.dispatch.core.Dispatch` is cooperated with
:class:`~argclz.core.AbstractParser`.

**Basic structure**

.. code-block:: python

    from argclz import *
    from argclz.dispatch import Dispatch, dispatch

    class Main(AbstractParser, Dispatch):

        DESCRIPTION = 'Description text' # [1]
        EPILOG = 'Epilog text' # [1]
        COMMAND_HELP_DOC = """\
    My Command list:
      run           document of command run
    """# [2]

        command: str = pos_argument('CMD') # [3]

        @dispatch('run') # [4]
        def run_command(self):
            ...

1. class attributes from :class:`~argclz.core.AbstractParser` to set description and epilog
   of the help text.
2. class attributes from :class:`~argclz.dispatch.core.Dispatch` to set the dispatch functions
   help text. It will be put at the beginning of the epilog (as part of the epilog).
3. A dispatch arguments setup.
4. Label a dispatch function with command name ``A``.

- **run the script with -h**

.. code-block:: text

    usage: my_script.py [-h] CMD

    Description text

    positional arguments:
      CMD

    options:
      -h, --help  show this help message and exit

    My Command list:
      run           document of command run

    Epilog text

In above example, we hardcode the command list and description. :class:`~argclz.dispatch.core.Dispatch`
has helper function :func:`~argclz.dispatch.core.Dispatch.build_command_usages` to generate the content
dynamic. Be default, keep ``COMMAND_HELP_DOC`` ``None`` will used the default setup during the help text generating.
We modify the above example by:

.. code-block:: python

    class Main(AbstractParser, Dispatch): # [1]
        COMMAND_HELP_DOC = None # [2] can be removed

        @dispatch('run')
        def run_command(self):
            """document of command run""" # [3]
            ...

1. Continuous from above example, but changing following contents.
2. Be default, ``COMMAND_HELP_DOC``  is ``None``
3. The help text of the dispatch function ``A``. :func:`~argclz.dispatch.core.Dispatch.build_command_usages`
   can read the content of function docstring.

.. code-block:: text

    usage: my_script.py [-h] CMD

    Description text

    positional arguments:
      CMD

    options:
      -h, --help  show this help message and exit

    Commands:
      run         document of command run

    Epilog text

Moreover, ``COMMAND_HELP_DOC`` can be a function to allow user to generate the content dynamically and
has move control over content. We modify the above example by:

.. code-block:: python

    class Main(AbstractParser, Dispatch): # [1]
        @classmethod # [2]
        def COMMAND_HELP_DOC(cls) -> str:
            return cls.build_command_usages() # [3]

1. Continuous from above example, but changing following contents.
2. Let ``COMMAND_HELP_DOC`` as a function.
3. This function call with return the same content as the above example.
