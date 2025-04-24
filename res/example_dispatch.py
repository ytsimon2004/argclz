from argclz import AbstractParser, pos_argument, var_argument
from argclz.dispatch import Dispatch, dispatch


class Main(AbstractParser, Dispatch):
    command: str = pos_argument('CMD')
    command_args: list[str] = var_argument('ARGS')

    EPILOG = lambda: f"""\
Sub-Commands:
{Main.build_command_usages()}
"""

    def run(self):
        self.invoke_command(self.command, *self.command_args)

    @dispatch('A')
    def run_a(self):
        print('A')

    @dispatch('B')
    def run_b(self):
        print('B')


Main().main()
