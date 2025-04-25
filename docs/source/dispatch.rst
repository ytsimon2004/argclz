Dispatch usage
====================
An alternative sub-commands.



.. seealso ::

    see dispatch usage in :mod:`argclz.dispatch`

.. code-block:: python

    from argclz.dispatch import Dispatch, dispatch

    class Main(AbstractParser, Dispatch): # [1]

        command:str = pos_argument('CMD') # [2]
        command_args:list[str] = var_argument('ARGS') # [2]

        EPILOG = lambda : f\""" \\
        Sub-Commands:
        {Main.build_command_usages()}
        \""" # [3]

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