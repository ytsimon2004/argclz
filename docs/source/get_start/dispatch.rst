Dispatch usage
====================

An alternative to ``argparse`` subcommands, ``Dispatch`` provides a way to call distinct functions
by the given command name. Unlike ``argparse`` subcommands, the user has more freedom to decide when
and how to use it, and it does not restrict the command-line parsing control flow.


.. seealso ::

    see dispatch usage in :mod:`argclz.dispatch`

**Normal use case with commandline**

.. code-block:: python

    from argclz import *
    from argclz.dispatch import Dispatch, dispatch

    class Main(AbstractParser, Dispatch): # [1]

        command:str = pos_argument('CMD') # [2]
        command_args:list[str] = var_argument('ARGS') # [2]

        EPILOG = lambda : f""" \\
        Sub-Commands:
        {Main.build_command_usages()}
        """ # [3]

        def run(self):
            self.invoke_command(self.command, *self.command_args) # [4]

        @dispatch('A') # [5]
        def run_a(self):
            print('A')

        @dispatch('B') # [5]
        def run_b(self):
            print('B')

    Main().main()

1. inherit ``Dispatch`` to gain related methods, such as ``invoke_command``.
2. we use command to decide which dispatch command need to be run.
3. add dispatch commands into help epilog. Note that it is a lambda form because the content is dynamic generated.
4. run dispatch commands. User has more control on when to call.
5. method labeled as dispatch command.

**Other use case**

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
            self.run_with_interface(interface, ...)

            # [5] with dispatch
            self.run_with_interface(
                self.interface_group.invoke_command(self.interface),
                ...
            )

        def run_with_interface(self, inf: Interface): # [6]
            ...

1. The value of this argument will be the command of the dispatch group ``interface``
2. Create a dispatch group named ``interface``
3. declare functions as dispatch function under ``interface`` group.
4. If we do not use dispatch, we have to do match-case-like code-block manually.
5. with dispatch, it becomes one function call.
6. remaining program logics.

With ``Dispatch``, it packs logic control flow, help document and source code together, which
makes codebase maintainability easier.