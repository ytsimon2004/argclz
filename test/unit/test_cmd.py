import unittest

from argclz import *
from argclz.commands import parse_command_args, new_command_parser
from argclz.core import print_help


class CommandParserTest(unittest.TestCase):
    def test_command_parser(self):
        class P1(AbstractParser):
            a: str = argument('-a', default='default')

        class P2(AbstractParser):
            a: str = argument('-a', default='default')

        parsers = new_command_parser(dict(a=P1, b=P2))
        opt = parse_command_args(parsers, ['a'], parse_only=True)
        self.assertIsInstance(opt, P1)

        opt = parse_command_args(parsers, ['b'], parse_only=True)
        self.assertIsInstance(opt, P2)

        opt = parse_command_args(parsers, [], parse_only=True)
        self.assertIsNone(opt)

    def test_command_parse_option(self):
        class P1(AbstractParser):
            a: str = argument('-a', default='default P1')

            def run(self):
                pass

        class P2(AbstractParser):
            a: str = argument('-a', default='default P2')

            def run(self):
                pass

        parsers = new_command_parser(dict(a=P1, b=P2))
        opt = parse_command_args(parsers, ['a'], parse_only=True)
        self.assertIsInstance(opt, P1)
        self.assertEqual('default P1', opt.a)

        opt = parse_command_args(parsers, ['b'], parse_only=True)
        self.assertIsInstance(opt, P2)
        self.assertEqual('default P2', opt.a)

        opt = parse_command_args(parsers, [], parse_only=True)
        self.assertIsNone(opt)

    def test_command_run(self):
        class P1(AbstractParser):
            a: str = argument('-a', default='default P1')

            def run(self):
                nonlocal result
                result = self

        class P2(AbstractParser):
            a: str = argument('-a', default='default P2')

            def run(self):
                nonlocal result
                result = self

        with self.subTest('case a'):
            result = None
            parsers = new_command_parser(dict(a=P1, b=P2))
            opt = parse_command_args(parsers, ['a'])
            self.assertIsInstance(opt, P1)
            self.assertIsInstance(result, P1)
            self.assertEqual(opt.a, 'default P1')

        with self.subTest('case b'):
            result = None  # reset
            opt = parse_command_args(parsers, ['b'])
            self.assertIsInstance(opt, P2)
            self.assertIsInstance(result, P2)
            self.assertEqual(opt.a, 'default P2')

        with self.subTest('case none'):
            result = None  # reset
            opt = parse_command_args(parsers, [])
            self.assertIsNone(result)
            self.assertIsNone(opt)


class CommandParserClassTest(unittest.TestCase):
    def test_command_class(self):
        class P(AbstractParser):
            sub_command = sub_command_group()

            @sub_command('a')
            class P1(AbstractParser):
                a: str = argument('-a', default='default P1')

                def run(self):
                    nonlocal result
                    result = self

            @sub_command('b')
            class P2(AbstractParser):
                a: str = argument('-a', default='default P2')

                def run(self):
                    nonlocal result
                    result = self

        main = P()

        with self.subTest('case a'):
            result = None  # reset
            ret = main.main(['a'], parse_only=True)
            self.assertIs(main.sub_command, P.P1)
            self.assertIsInstance(ret, P.P1)
            self.assertIsNone(result)  # because parse_only=True

        with self.subTest('case b'):
            result = None  # reset
            ret = main.main(['b'], parse_only=True)
            self.assertIs(main.sub_command, P.P2)
            self.assertIsInstance(ret, P.P2)
            self.assertIsNone(result)  # because parse_only=True

        with self.subTest('case none'):
            result = None  # reset
            ret = main.main([], parse_only=True)
            self.assertIsNone(main.sub_command)
            self.assertIsInstance(ret, P)
            self.assertIsNone(result)  # because parse_only=True

    def test_sub_command_init_with_parent(self):
        result = None

        class P(AbstractParser):
            a: bool = argument('-a')
            sub_command = sub_command_group()

            @sub_command('a')
            class P1(AbstractParser):
                b: bool = argument('-b')

                def __init__(self, parent):
                    self.parent = parent

                def run(self):
                    nonlocal result
                    result = self

        p = P().main(['-a', 'a', '-b'])
        self.assertIsInstance(p, P.P1)
        self.assertIsInstance(p.parent, P)
        self.assertTrue(p.parent.a)
        self.assertTrue(p.b)
        self.assertIsInstance(result, P.P1)

    def test_sub_share_same_name_arg_with_parent(self):
        result = None

        class P(AbstractParser):
            a: int = argument('-a')
            sub_command = sub_command_group()

            @sub_command('a')
            class P1(AbstractParser):
                a: int = argument('-a')

                def __init__(self, parent):
                    self.parent = parent

                def run(self):
                    nonlocal result
                    result = self

        p = P().main(['-a1', 'a', '-a2'])
        self.assertIsInstance(p, P.P1)
        self.assertIsInstance(p.parent, P)
        self.assertEqual(p.parent.a, 2)  # XXX overwrite by P1 parser
        self.assertEqual(p.a, 2)
        self.assertIsInstance(result, P.P1)


class PrintHelpTest(unittest.TestCase):
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

        parser = new_command_parser(dict(a=P1, b=P2), prog='run.py', description='DESCRIPTION')
        self.assertEqual(print_help(parser, None), """\
usage: run.py [-h] {a,b} ...

DESCRIPTION

options:
  -h, --help  show this help message and exit

commands:
  {a,b}
    a         P1 description
    b         P2 description
""")

    def test_class_print_help(self):
        class P(AbstractParser):
            DESCRIPTION = 'description'
            EPILOG = 'epilog'

            sub_command = sub_command_group(title='title', description='commands description')

            @sub_command('a')
            class P1(AbstractParser):
                DESCRIPTION = 'sub command a'
                a: str = argument('-a', default='default P1')

            @sub_command('b')
            class P2(AbstractParser):
                DESCRIPTION = 'sub command b'
                a: str = argument('-a', default='default P2')

        self.assertEqual(print_help(P, None, prog='run.py'), """\
usage: run.py [-h] {a,b} ...

description

options:
  -h, --help  show this help message and exit

title:
  commands description

  {a,b}
    a         sub command a
    b         sub command b

epilog
""")


if __name__ == '__main__':
    unittest.main()
