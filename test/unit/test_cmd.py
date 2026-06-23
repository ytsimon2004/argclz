import contextlib
import io
import re
import sys
import unittest

from argclz import *
from argclz.commands import parse_command_args, new_command_parser, get_sub_command_group
from argclz.core import print_help, parse_args


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

    def test_sub_command_unknown_argument(self):
        class P(AbstractParser):
            a: str = argument('-a')

            sub_command = sub_command_group()

            @sub_command('a')
            class P1(AbstractParser):
                b: str = argument('-b')

        with self.assertRaises(RuntimeError) as capture:
            parse_args(P(), ['a', '-c'])
        self.assertEqual(capture.exception.args[0],
                         'exit 2: unrecognized arguments: -c')

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

        p = P()
        r = p.main(['-a1', 'a', '-a2'])
        self.assertIsInstance(r, P.P1)
        self.assertIsInstance(r.parent, P)
        self.assertEqual(r.parent, p)
        self.assertEqual(r.parent.a, 2)  # argparse doesn't distinct between P.a and P1.a
        self.assertEqual(r.a, 2)
        self.assertEqual(result, r)

    def test_sub_from_outer_class(self):
        class Sub(AbstractParser):
            a: int = argument('-a')

        class Par(AbstractParser):
            sub_command = sub_command_group()
            sub_command('a')(Sub)

        p = Par()
        r = p.main(['a', '-a2'])
        self.assertIsInstance(p, Par)
        self.assertIsInstance(r, Sub)
        self.assertIs(p.sub_command, Sub)
        self.assertEqual(r.a, 2)

    def test_sub_from_outer_parser(self):
        class Sub(AbstractParser):
            a: int = argument('-a')

        sub = Sub()

        class Par(AbstractParser):
            sub_command = sub_command_group()

            # we do not suggest this usage.
            sub_command('a')(sub)

        p = Par()
        r = p.main(['a', '-a2'])
        self.assertIsInstance(p, Par)
        self.assertIsInstance(r, Sub)
        self.assertIs(r, sub)
        self.assertIs(p.sub_command, sub)
        self.assertEqual(r.a, 2)
        self.assertEqual(sub.a, 2)

    def test_sub_inherit_from_outer_class(self):
        class Outer(AbstractParser):
            a: int = argument('-a')

        class Par(AbstractParser):
            sub_command = sub_command_group()

            @sub_command('a')
            class Inner(Outer):
                def __init__(self, parent):
                    self.parent = parent

        p = Par()
        r = p.main(['a', '-a2'])
        self.assertIsInstance(p, Par)
        self.assertIsInstance(r, Par.Inner)
        self.assertIs(p.sub_command, Par.Inner)
        self.assertEqual(r.a, 2)
        self.assertEqual(r.parent, p)

    def test_multiple_sub_groups(self):
        with self.assertRaises(RuntimeError) as capture:
            class Par(AbstractParser):
                g1 = sub_command_group()
                g2 = sub_command_group()

        if sys.version_info >= (3, 12):
            self.assertEqual(capture.exception.args[0],
                             'cannot have multiple sub-commands groups: g1 and g2')
        else:
            # error is wrapped in __set_name__
            self.assertEqual(capture.exception.__cause__.args[0],
                             'cannot have multiple sub-commands groups: g1 and g2')

    def test_sub_command_should_be_a_parser(self):
        with self.assertRaises(TypeError) as capture:
            class Par(AbstractParser):
                sub_command = sub_command_group()

                @sub_command('a')
                class A1:
                    pass

        self.assertEqual(capture.exception.args[0],
                         'A1 is not an AbstractParser')

    def test_same_sub_command_name(self):
        with self.assertRaises(RuntimeError) as capture:
            class Par(AbstractParser):
                sub_command = sub_command_group()

                @sub_command('a')
                class A1(AbstractParser):
                    pass

                @sub_command('a')
                class A2(AbstractParser):
                    pass

        self.assertEqual(capture.exception.args[0],
                         'sub-command "a" has been used.')

    def test_sub_parser_inherit_parent_parser_kwargs(self):
        # there are two properties, fromfile_prefix_chars and allow_abbrev,
        # will be inherited from parent parser.
        # Here we only test allow_abbrev only.
        enable_allow_abbrev = True

        class Parent(AbstractParser):
            a: str = argument('--a-long-name-option')

            sub_command = sub_command_group()

            @sub_command('a')
            class Sub(AbstractParser):
                o: str = argument('--other-long-name-option')

            @classmethod
            def new_parser(cls, **kwargs):
                return super().new_parser(**kwargs, allow_abbrev=enable_allow_abbrev)

        with self.subTest('enable'):
            enable_allow_abbrev = True
            ret = Parent().main(['a', '--other=TEXT'], system_exit=RuntimeError)
            self.assertIsInstance(ret, Parent.Sub)
            self.assertEqual(ret.o, 'TEXT')

        with self.subTest('disable'):
            enable_allow_abbrev = False
            with self.assertRaises(RuntimeError) as capture:
                Parent().main(['a', '--other=TEXT'], system_exit=RuntimeError)
            self.assertEqual(capture.exception.args[0],
                             'unrecognized arguments: --other=TEXT')


class UtilMethodTest(unittest.TestCase):
    def test_get_sub_command_group(self):
        class Par(AbstractParser):
            sub_command = sub_command_group()

        r = get_sub_command_group(Par)
        self.assertIs(r, Par.sub_command)

    def test_get_sub_command_group_on_null(self):
        class Par(AbstractParser):
            pass

        r = get_sub_command_group(Par)
        self.assertIsNone(r)

    def test_list_sub_commands(self):
        class Par(AbstractParser):
            sub_command = sub_command_group()

            @sub_command('a')
            class A(AbstractParser): ...

            @sub_command('b')
            class B(AbstractParser): ...

            @sub_command('c')
            class C(AbstractParser): ...

        g = get_sub_command_group(Par)
        self.assertIsNotNone(g)
        self.assertSetEqual({'a', 'b', 'c'}, set(g.sub_parsers))


class PrintHelpTest(unittest.TestCase):
    def test_print_help(self):
        class P1(AbstractParser):
            DESCRIPTION = 'P1 description'

            a: str = argument('-a', default='default', help='P1.a help')

        class P2(AbstractParser):
            DESCRIPTION = 'P2 description'

            a: str = argument('-a', default='default', help='P2.a help')

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

    def test_sub_cmd_print_help(self):
        class P(AbstractParser):
            DESCRIPTION = 'parent description'
            EPILOG = 'parent epilog'

            sub_command = sub_command_group(title='title', description='commands description')

            @sub_command('a')
            class P1(AbstractParser):
                DESCRIPTION = 'sub command a'
                EPILOG = 'sub command a epilog'
                a: str = argument('-a', default='default P1', help='sub command a -a help')

            @sub_command('b')
            class P2(AbstractParser):
                DESCRIPTION = 'sub command b'
                EPILOG = 'sub command b epilog'
                a: str = argument('-a', default='default P2', help='sub command b -a help')

        def get_buffer_value(output):
            return re.sub(r'usage: (python -m unittest|pytest|.*\.py)', 'usage: run.py', output.getvalue())

        with self.subTest('parent case'):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                P().main(['-h'], parse_only=True)

                self.assertEqual(get_buffer_value(buf), """\
usage: run.py [-h] {a,b} ...

parent description

options:
  -h, --help  show this help message and exit

title:
  commands description

  {a,b}
    a         sub command a
    b         sub command b

parent epilog
""")

        with self.subTest('subcmd case'):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                P().main(['a', '-h'], parse_only=True)

                self.assertEqual(get_buffer_value(buf), """\
usage: run.py a [-h] [-a A]

sub command a

options:
  -h, --help  show this help message and exit
  -a A        sub command a -a help (default: 'default P1')

sub command a epilog
""")


if __name__ == '__main__':
    unittest.main()
