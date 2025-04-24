import unittest

from argclz import *
from argclz.core import parse_command_args, print_help, new_command_parser


class CommandParserTest(unittest.TestCase):
    def test_command_parser(self):
        class P1(AbstractParser):
            a: str = argument('-a', default='default')

        class P2(AbstractParser):
            a: str = argument('-a', default='default')

        parsers = dict(a=P1, b=P2)
        opt = parse_command_args(parsers, ['a'], parse_only=True)
        self.assertIsNotNone(opt)
        self.assertIsInstance(opt.main, P1)

        opt = parse_command_args(parsers, ['b'], parse_only=True)
        self.assertIsNotNone(opt)
        self.assertIsInstance(opt.main, P2)

        opt = parse_command_args(parsers, [], parse_only=True)
        self.assertIsNotNone(opt)
        self.assertIsNone(opt.main)

    def test_command_parser_main(self):
        class P1(AbstractParser):
            a: str = argument('-a', default='default P1')

            def run(self):
                pass

        class P2(AbstractParser):
            a: str = argument('-a', default='default P2')

            def run(self):
                pass

        parsers = dict(a=P1, b=P2)
        opt = parse_command_args(parsers, ['a'])
        self.assertIsNotNone(opt)
        self.assertIsInstance(opt.main, P1)
        self.assertEqual('default P1', opt.main.a)

        opt = parse_command_args(parsers, ['b'])
        self.assertIsNotNone(opt)
        self.assertIsInstance(opt.main, P2)
        self.assertEqual('default P2', opt.main.a)

        opt = parse_command_args(parsers, [])
        self.assertIsNotNone(opt)
        self.assertIsNone(opt.main)


RUNNER = ''


class PrintHelpTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        global RUNNER

        class Opt(AbstractParser):
            pass

        h = print_help(Opt, None)
        RUNNER = h.split('\n')[0].split(' ')[1]

    def test_print_help(self):
        class P1(AbstractParser):
            DESCRIPTION = 'P1 description'

            a: str = argument('-a', default='default', help='P1.a help')

            def run(self):
                pass

        class P2(AbstractParser):
            DESCRIPTION = 'P2 description'

            a: str = argument('-a', default='default', help='P2.a help')

            def run(self):
                pass

        parser = new_command_parser(dict(a=P1, b=P2), description='DESCRIPTION')
        self.assertEqual(print_help(parser, None), f"""\
usage: {RUNNER} [-h] {{a,b}} ...

DESCRIPTION

positional arguments:
  {{a,b}}
    a         P1 description
    b         P2 description

options:
  -h, --help  show this help message and exit
""")

if __name__ == '__main__':
    unittest.main()
