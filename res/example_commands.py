from __future__ import annotations

from argclz import AbstractParser, sub_command_group, argument
from argclz.core import print_help


class Main(AbstractParser):
    DESCRIPTION = 'An overall cli'

    verbose: bool = argument('--verbose', '-v')

    def run(self):
        print_help(self)

    command_group = sub_command_group(title='sub commands')

    @command_group('a')
    class SubCommandA(AbstractParser):
        DESCRIPTION = 'do A'

        a: int = argument('-a', help='option for A')

        def run(self):
            print('do A', self.a)

    @command_group('b')
    class SubCommandB(AbstractParser):
        DESCRIPTION = 'do B'

        a: int = argument('-a', help='option for B')

        def __init__(self, parent: Main):
            self.parent = parent

        def run(self):
            print('do B', self.parent.verbose, self.a)


Main().main()
