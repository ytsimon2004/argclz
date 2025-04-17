import unittest

from argp import *
from argp.core import parse_command_args


class CommandParserTest(unittest.TestCase):
    def test_command_parser(self):
        class P1(AbstractParser):
            a: str = argument('-a', default='default')

        class P2(AbstractParser):
            a: str = argument('-a', default='default')

        parsers = dict(a=P1, b=P2)
        opt = parse_command_args(parsers, ['a'], parse_only=True)
        self.assertIsInstance(opt, P1)
        opt = parse_command_args(parsers, ['b'], parse_only=True)
        self.assertIsInstance(opt, P2)
        opt = parse_command_args(parsers, [], parse_only=True)
        self.assertIsNone(opt)

    def test_command_parser_main(self):
        class P1(AbstractParser):
            a: str = argument('-a', default='default')

            def run(self):
                pass

        class P2(AbstractParser):
            a: str = argument('-a', default='default')

            def run(self):
                pass

        parsers = dict(a=P1, b=P2)
        opt = parse_command_args(parsers, ['a'])
        self.assertIsInstance(opt, P1)
        self.assertEqual('default', opt.a)
        opt = parse_command_args(parsers, ['b'])
        self.assertIsInstance(opt, P2)
        self.assertEqual('default', opt.a)
        opt = parse_command_args(parsers, [])
        self.assertIsNone(opt)


if __name__ == '__main__':
    unittest.main()
