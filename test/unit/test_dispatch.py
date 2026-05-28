import contextlib
import io
import unittest
from typing import Any, Literal

from argclz import *
from argclz.core import print_help
from argclz.dispatch import *


class SimpleDispatch(AbstractParser, Dispatch):
    c: str = pos_argument('cmd')
    a: list[str] = var_argument('args')
    r: Any

    def run(self):
        self.invoke_command(self.c, *self.a)


class AbstractDispatchTester(unittest.TestCase):
    def assert_command_list(self, left, right):
        def to_command_name(cmd):
            if not isinstance(cmd, str):
                from argclz.dispatch.core import DispatchCommand
                self.assertIsInstance(cmd, DispatchCommand)
                return cmd.command
            else:
                return cmd

        a = list(map(to_command_name, left))
        b = list(map(to_command_name, right))
        self.assertListEqual(a, b)

    def assert_command_group_list(self, left, right):
        def to_command_name(cmd):
            from argclz.dispatch.core import DispatchCommand

            match cmd:
                case str():
                    return None, cmd
                case (str() | None, str()):
                    return cmd
                case DispatchCommand(group=group, command=command):
                    return group, command
                case _:
                    raise TypeError(str(cmd))

        a = list(map(to_command_name, left))
        b = list(map(to_command_name, right))
        self.assertListEqual(a, b)


class TestDispatch(AbstractDispatchTester):
    def test_dispatch_command(self):
        class Opt(SimpleDispatch):
            @dispatch('A')
            def run_a(self):
                self.r = 'AAA'

            @dispatch('B')
            def run_b(self):
                self.r = 'BBB'

        opt = Opt()
        ret = opt.main(['A'])
        self.assertIs(ret, opt)
        self.assertEqual(opt.r, 'AAA')

        ret = opt.main(['B'])
        self.assertIs(ret, opt)
        self.assertEqual(opt.r, 'BBB')

        with self.assertRaises(DispatchCommandNotFound):
            opt.main(['C'])

    def test_list_commands(self):
        class Opt(SimpleDispatch):
            @dispatch('A')
            def run_a(self):
                pass

            @dispatch('B')
            def run_b(self):
                pass

            @dispatch('C', group='A')
            def run_c(self):
                pass

        self.assert_command_list(Opt.list_commands(), ['A', 'B', 'C'])
        self.assert_command_list(Opt.list_commands(None), ['A', 'B'])
        self.assert_command_list(Opt.list_commands('A'), ['C'])
        self.assert_command_list(Opt.list_commands('C'), [])

    def test_list_hidden_commands(self):
        class Opt(SimpleDispatch):
            @dispatch('A')
            def run_a(self):
                pass

            @dispatch('B', hidden=True)
            def run_b(self):
                pass

        self.assert_command_list(Opt.list_commands(), ['A'])
        self.assert_command_list(Opt.list_commands(include_hidden=True), ['A', 'B'])

    def test_dispatch_find_command(self):
        class Opt(SimpleDispatch):
            @dispatch('A')
            def run_a(self):
                pass

        cmd = Opt.find_command('A')
        self.assertIsNotNone(cmd)
        assert cmd is not None
        self.assertEqual(cmd.command, 'A')

        cmd = Opt.find_command('B')
        self.assertIsNone(cmd)

    def test_dispatch_command_not_found(self):
        class Opt(SimpleDispatch):
            @dispatch('A')
            def run_a(self):
                pass

            @dispatch('B', group='B')
            def run_b(self):
                pass

        opt = Opt()

        with self.assertRaises(DispatchCommandNotFound) as capture:
            opt.invoke_command('B')
        self.assertIsNone(capture.exception.group)
        self.assertEqual(capture.exception.command, 'B')

        opt.invoke_group_command('B', 'B')

        with self.assertRaises(DispatchCommandNotFound) as capture:
            opt.invoke_group_command('B', 'A')
        self.assertEqual(capture.exception.group, 'B')
        self.assertEqual(capture.exception.command, 'A')

    def test_dispatch_command_alias(self):
        class Opt(SimpleDispatch):
            @dispatch('A', 'a')
            def run_a(self):
                self.r = 'AAA'

        opt = Opt()
        ret = opt.main(['A'])
        self.assertIs(ret, opt)
        self.assertEqual(opt.r, 'AAA')

        ret = opt.main(['a'])
        self.assertIs(ret, opt)
        self.assertEqual(opt.r, 'AAA')

    def test_dispatch_group(self):
        class Opt(SimpleDispatch):
            def run(self):
                self.invoke_group_command('B', self.c, *self.a)

            @dispatch('A', group=None)
            def run_a(self):
                self.r = 'AAA'

            @dispatch('A', group='B')
            def run_b(self):
                self.r = 'BBB'

        opt = Opt()
        ret = opt.main(['A'])
        self.assertIs(ret, opt)
        self.assertEqual(opt.r, 'BBB')

    def test_dispatch_command_argument(self):
        class Opt(SimpleDispatch):
            r: tuple[str, ...]

            @dispatch('A')
            def run_a(self, *a):
                self.r = a

        opt = Opt()
        ret = opt.main(['A'])
        self.assertIs(ret, opt)
        self.assertTupleEqual(opt.r, ())

        ret = opt.main(['A', '1', '2'])
        self.assertIs(ret, opt)
        self.assertTupleEqual(opt.r, ('1', '2'))

    def test_dispatch_command_keyword_arguments(self):
        class Opt(SimpleDispatch):
            r: dict[str, str]

            @dispatch('A')
            def run_a(self, **a):
                self.r = a

        opt = Opt()
        ret = opt.main(['A'])
        self.assertIs(ret, opt)
        self.assertDictEqual(opt.r, {})

        ret = opt.main(['A', 'a=1', 'b=2'])
        self.assertIs(ret, opt)
        self.assertDictEqual(opt.r, {'a': '1', 'b': '2'})

    def test_dispatch_command_keyword_argument_mapping(self):
        class Opt(SimpleDispatch):
            r: tuple[str, ...]

            @dispatch('A')
            def run_a(self, a, b, c='none'):
                self.r = (a, b, c)

        opt = Opt()

        with self.assertRaises(TypeError):
            opt.main(['A'])

        ret = opt.main(['A', '1', '2'])
        self.assertIs(ret, opt)
        self.assertTupleEqual(opt.r, ('1', '2', 'none'))

        ret = opt.main(['A', '1', '2', '3'])
        self.assertIs(ret, opt)
        self.assertTupleEqual(opt.r, ('1', '2', '3'))

        ret = opt.main(['A', 'b=1', 'a=2'])
        self.assertIs(ret, opt)
        self.assertTupleEqual(opt.r, ('2', '1', 'none'))

        ret = opt.main(['A', 'c=1', 'b=2', 'a=3'])
        self.assertIs(ret, opt)
        self.assertTupleEqual(opt.r, ('3', '2', '1'))

    def test_dispatch_command_keyword_argument_mapping_with_remaining(self):
        class Opt(SimpleDispatch):
            ra: str
            rb: str
            rc: dict[str, str]

            @dispatch('A')
            def run_a(self, a, b='none', **c):
                self.ra = a
                self.rb = b
                self.rc = c

        opt = Opt()

        with self.assertRaises(TypeError):
            opt.main(['A'])

        ret = opt.main(['A', '1'])
        self.assertIs(ret, opt)
        self.assertEqual(opt.ra, '1')
        self.assertEqual(opt.rb, 'none')
        self.assertDictEqual(opt.rc, {})

        ret = opt.main(['A', '10', '20'])
        self.assertIs(ret, opt)
        self.assertEqual(opt.ra, '10')
        self.assertEqual(opt.rb, '20')
        self.assertDictEqual(opt.rc, {})

        ret = opt.main(['A', 'b=10', 'a=20'])
        self.assertIs(ret, opt)
        self.assertEqual(opt.ra, '20')
        self.assertEqual(opt.rb, '10')
        self.assertDictEqual(opt.rc, {})

        ret = opt.main(['A', '11', '12', 'c=10'])
        self.assertIs(ret, opt)
        self.assertEqual(opt.ra, '11')
        self.assertEqual(opt.rb, '12')
        self.assertDictEqual(opt.rc, {'c': '10'})

        ret = opt.main(['A', '11', 'd=12', 'c=13'])
        self.assertIs(ret, opt)
        self.assertEqual(opt.ra, '11')
        self.assertEqual(opt.rb, 'none')
        self.assertDictEqual(opt.rc, {'c': '13', 'd': '12'})

    def test_dispatch_command_argument_casting(self):
        class Opt(SimpleDispatch):
            r: int

            @dispatch('A')
            @validator_for('a')
            def run_a(self, a: int):
                self.r = a

        opt = Opt()
        ret = opt.main(['A', '1'])
        self.assertIs(ret, opt)
        self.assertEqual(opt.r, 1)

    def test_dispatch_command_argument_with_default(self):
        class Opt(SimpleDispatch):
            ra: int
            rb: int

            @dispatch('A')
            @validator_for('a')
            @validator_for('b')
            def run_a(self, a: int, b: int = 0):
                self.ra = a
                self.rb = b

        opt = Opt()
        ret = opt.main(['A', '1'])
        self.assertIs(ret, opt)
        self.assertEqual(opt.ra, 1)
        self.assertEqual(opt.rb, 0)

        ret = opt.main(['A', '10', '20'])
        self.assertIs(ret, opt)
        self.assertEqual(opt.ra, 10)
        self.assertEqual(opt.rb, 20)

    def test_dispatch_command_validator_on_wrong_parameter(self):
        with self.assertWarns(RuntimeWarning) as capture:
            class Opt(SimpleDispatch):

                @dispatch('A')
                @validator_for('b')
                def run_a(self, a: int):
                    pass

        self.assertEqual(capture.warnings[0].message.args[0],
                         'unknown parameter name : b for function run_a')

    def test_dispatch_command_validator_on_no_type_hint_parameter(self):
        with self.assertRaises(RuntimeError) as capture:
            class Opt(SimpleDispatch):

                @dispatch('A')
                @validator_for('a')
                def run_a(self, a):
                    pass

        self.assertEqual(capture.exception.args[0],
                         'unknown parameter type : a for function run_a')

    def test_dispatch_command_argument_casting_validator(self):
        class Opt(SimpleDispatch):
            r: int

            @dispatch('A')
            @validator_for('a', validator.int.positive(include_zero=False))
            def run_a(self, a: int):
                self.r = a

        opt = Opt()
        ret = opt.main(['A', '1'])
        self.assertIs(ret, opt)
        self.assertEqual(opt.r, 1)

        with self.assertRaises(ValueError) as capture:
            opt.main(['A', '0'])
        self.assertEqual(capture.exception.args[0],
                         'command A argument "a" : not a positive value : 0')

    def test_dispatch_command_argument_casting_and_validator(self):
        class Opt(SimpleDispatch):
            r: int | None

            @dispatch('A')
            @validator_for('a', try_int_type,
                           validator.str | validator.int.positive(include_zero=False))
            def run_a(self, a):
                self.r = a

        opt = Opt()
        ret = opt.main(['A', '1'])
        self.assertIs(ret, opt)
        self.assertEqual(opt.r, 1)

        ret = opt.main(['A', 'a'])
        self.assertIs(ret, opt)
        self.assertEqual(opt.r, 'a')

        with self.assertRaises(ValueError) as capture:
            opt.main(['A', '0'])
        self.assertEqual(capture.exception.args[0], 'command A argument "a" : not a positive value : 0')

    def test_dispatch_command_argument_casting_fail(self):
        class Opt(SimpleDispatch):
            @dispatch('A')
            @validator_for('a')
            def run_a(self, a: int):
                pass

        with self.assertRaises(ValueError) as capture:
            Opt().main(['A', 'a'])
        self.assertEqual(capture.exception.args[0],
                         'command A argument "a" : cannot cast "a" to type int')

    def test_dispatch_command_argument_validator_fail(self):
        class Opt(SimpleDispatch):
            @dispatch('A')
            @validator_for('a', validator(lambda it: it.startswith("a")))
            def run_a(self, a: str):
                pass

        with self.assertRaises(ValueError) as capture:
            Opt().main(['A', 'b'])
        self.assertEqual(capture.exception.args[0],
                         'command A argument "a" : fail validation : "b"')

    def test_dispatch_command_argument_validator_error_fail(self):
        class Opt(SimpleDispatch):
            @dispatch('A')
            @validator_for('a', validator.str.starts_with('a'))
            def run_a(self, a: str):
                pass

        with self.assertRaises(ValueError) as capture:
            Opt().main(['A', 'b'])
        self.assertEqual(capture.exception.args[0],
                         'command A argument "a" : str does not start with "a": "b"')

    def test_dispatch_command_argument_validator_misorder(self):
        with self.assertRaises(RuntimeError) as capture:
            class Opt(SimpleDispatch):
                r: int | None

                @validator_for('a')
                @dispatch('A')
                def run_a(self, a: int):
                    self.r = a

        self.assertEqual(capture.exception.args[0], 'run_a already frozen')

    def test_dispatch_on_literal_parameter(self):
        class Opt(SimpleDispatch):
            @dispatch('A')
            @validator_for('a')
            def run_a(self, a: Literal['AAA', 'BBB']):
                self.r = a

        main = Opt()
        ret = main.main(['A', 'AAA'])
        self.assertEqual(ret.r, 'AAA')

        with self.assertRaises(ValueError) as capture:
            main.main(['A', 'A'])

        self.assertEqual(capture.exception.args[0],
                         'command A argument "a" : cannot cast "A"')

    def test_dispatch_on_literal_parameter_complete(self):
        class Opt(SimpleDispatch):
            @dispatch('A')
            @validator_for('a', literal_type(complete=True))
            def run_a(self, a: Literal['AAA', 'BBB']):
                self.r = a

        main = Opt()
        ret = main.main(['A', 'AAA'])
        self.assertEqual(ret.r, 'AAA')

        ret = main.main(['A', 'A'])
        self.assertEqual(ret.r, 'AAA')


class TestDispatchGroup(AbstractDispatchTester):

    def test_dispatch_group(self):
        class Opt(SimpleDispatch):
            g = dispatch_group('A')

            @dispatch('A')
            def run_a(self):
                self.r = 'AAA'

            @g('A')
            def run_a_in_g(self):
                self.r = 'GGG'

            def run(self):
                self.g.invoke_command(self.c, *self.a)

        ret = Opt().main(['A'])
        self.assertEqual(ret.r, 'GGG')

    def test_dispatch_group_by_literal_str(self):
        class Opt(SimpleDispatch):

            @dispatch('A', group='G')
            def run_a(self):
                ...

            @dispatch('A', group='H')
            def run_b(self):
                ...

        self.assertSetEqual(Opt.list_groups(), {'G', 'H'})
        self.assert_command_group_list(Opt.list_commands('G'), [('G', 'A')])
        self.assert_command_group_list(Opt.list_commands('H'), [('H', 'A')])

    def test_dispatch_group_by_dispatch_group(self):
        class Opt(SimpleDispatch):
            a = dispatch_group('G')

            @dispatch('A', group=a)
            def run_a(self):
                ...

            @dispatch('B', group=a)
            def run_b(self):
                ...

        self.assertSetEqual(Opt.list_groups(), {'G'})
        self.assert_command_group_list(Opt.list_commands('G'), [('G', 'A'), ('G', 'B')])
        self.assert_command_group_list(Opt.list_commands(Opt.a), [('G', 'A'), ('G', 'B')])
        self.assert_command_group_list(Opt.a.list_commands(), [('G', 'A'), ('G', 'B')])

    def test_dispatch_group_from_outer_scope(self):
        a = dispatch_group('a')

        class Opt(SimpleDispatch):
            @a('A')
            def run_a(self):
                pass

        self.assertSetEqual(Opt.list_groups(), {'a'})
        self.assert_command_list(Opt.list_commands('a'), ['A'])
        self.assert_command_list(Opt.list_commands(a), ['A'])

    def test_list_groups(self):
        class Opt(SimpleDispatch):
            a = dispatch_group('a')
            b = dispatch_group('b')
            c = dispatch_group('c')
            d = dispatch_group('d')  # no function under this group, is not counted

            @a('A')
            def run_a(self):
                pass

            @b('B')
            def run_b(self):
                pass

            @c('C')
            def run_c(self):
                pass

        self.assertSetEqual(Opt.list_groups(), {'a', 'b', 'c'})

    def test_list_commands(self):
        class Opt(SimpleDispatch):
            g = dispatch_group('A')

            @dispatch('A')
            def run_a(self):
                pass

            @g('B')
            def run_b_in_g(self):
                pass

            @g('C')
            def run_c_in_g(self):
                pass

        self.assert_command_group_list(Opt.list_commands(None), ['A'])
        self.assert_command_group_list(Opt.list_commands('A'), [('A', 'B'), ('A', 'C')])
        self.assert_command_group_list(Opt.list_commands(Opt.g), [('A', 'B'), ('A', 'C')])
        self.assert_command_group_list(Opt.g.list_commands(), [('A', 'B'), ('A', 'C')])

    def test_use_group(self):
        class Opt(SimpleDispatch):
            g = dispatch_group('A')
            r: str | None = None

            @g('A')
            def run_a(self):
                self.r = 'A'

        opt = Opt()

        with self.subTest('list_commands'):
            self.assert_command_group_list(opt.list_commands('A'), [('A', 'A')])
            self.assert_command_group_list(opt.list_commands(opt.g), [('A', 'A')])

        with self.subTest('find_command'):
            command = opt.find_command('A', Opt.g)
            self.assert_command_list([command], ['A'])
            command = opt.find_command('A', opt.g)
            self.assert_command_list([command], ['A'])

        with self.subTest('invoke_group_command(str)'):
            opt.r = None
            self.assertIsNone(opt.r)
            opt.invoke_group_command('A', 'A')
            self.assertEqual(opt.r, 'A')

        with self.subTest('invoke_group_command(cls)'):
            opt.r = None
            self.assertIsNone(opt.r)
            opt.invoke_group_command(Opt.g, 'A')
            self.assertEqual(opt.r, 'A')

        with self.subTest('invoke_group_command(ins)'):
            opt.r = None
            self.assertIsNone(opt.r)
            opt.invoke_group_command(opt.g, 'A')
            self.assertEqual(opt.r, 'A')

    def test_use_group_outside_class(self):
        g = dispatch_group('A')

        class Opt(SimpleDispatch):
            r: str | None = None

            @g('A')
            def run_a(self):
                self.r = 'A'

        opt = Opt()
        with self.subTest('list_commands'):
            self.assert_command_group_list(opt.list_commands('A'), [('A', 'A')])
            self.assert_command_group_list(opt.list_commands(g), [('A', 'A')])

        with self.subTest('find_command'):
            command = opt.find_command('A', g)
            self.assert_command_group_list([command], [('A', 'A')])

        with self.subTest('invoke_group_command'):
            opt.r = None
            self.assertIsNone(opt.r)
            opt.invoke_group_command(g, 'A')
            self.assertEqual(opt.r, 'A')

    def test_use_in_non_Dispatch(self):
        # python version: >= 3.12 (TypeError), otherwise RuntimeError
        with self.assertRaises((RuntimeError, TypeError)):
            class Opt:  # not a subclass of Dispatch
                g = dispatch_group('A')

    def test_dispatch_command_not_found(self):
        class Opt(SimpleDispatch):
            g = dispatch_group('B')

            @g('B')
            def run_b(self):
                pass

        opt = Opt()

        with self.assertRaises(DispatchCommandNotFound) as capture:
            opt.invoke_group_command(Opt.g, 'A')
        self.assertEqual(capture.exception.group, 'B')
        self.assertEqual(capture.exception.command, 'A')


class PrintHelpTest(unittest.TestCase):

    def test_build_command_usages(self):
        class Opt(SimpleDispatch):
            @dispatch('A', 'a')
            def run_a(self):
                """
                text for A.

                more text.
                """
                pass

            @dispatch('B')
            def run_b(self):
                """
                text for B.

                more text.
                """
                pass

        self.assertEqual(Opt.build_command_usages(), """\
Commands:
  A (a)             text for A.
  B                 text for B.""")

    def test_build_command_with_custom_usages(self):
        class Opt(SimpleDispatch):
            @dispatch('A', 'a', usage='A B C D')
            def run_a(self):
                """text for A.

                more text.
                """
                pass

        self.assertEqual(Opt.build_command_usages(), """\
Commands:
  A B C D           text for A.""")

    def test_build_command_usages_with_empty_doc(self):
        class Opt(SimpleDispatch):
            @dispatch('A')
            def run_a(self):
                """

                """
                pass

        self.assertEqual(Opt.build_command_usages(), """\
Commands:
  A""")

    def test_build_command_usages_with_para(self):
        class Opt(SimpleDispatch):
            @dispatch('A')
            def run_a(self, a: str, b: str):
                """text for A."""
                pass

        self.assertEqual(Opt.build_command_usages(show_para=True), """\
Commands:
  A A B             text for A.""")

    def test_build_command_usages_with_optional_para(self):
        class Opt(SimpleDispatch):
            @dispatch('A')
            def run_a(self, a: str, b: str | None = None):
                """text for A."""
                pass

        self.assertEqual(Opt.build_command_usages(show_para=True), """\
Commands:
  A A [B]           text for A.""")

    def test_build_command_usages_with_keyword_para(self):
        class Opt(SimpleDispatch):
            @dispatch('A')
            def run_a(self, a: str, *, b: str | None = None):
                """text for A."""
                pass

        self.assertEqual(Opt.build_command_usages(show_para=True), """\
Commands:
  A A [B=]          text for A.""")

    def test_build_command_usages_with_var_para(self):
        class Opt(SimpleDispatch):
            @dispatch('A')
            def run_a(self, a: str, *b: str, **c):
                """text for A."""
                pass

        self.assertEqual(Opt.build_command_usages(show_para=True), """\
Commands:
  A A *B **C        text for A.""")

    def test_build_command_with_literal_para(self):
        class Opt(SimpleDispatch):
            @dispatch('A')
            @validator_for('a')
            def run_a(self, a: Literal['AAA', 'BBB']):
                """text for A."""
                pass

        self.assertEqual(Opt.build_command_usages(show_para=True), """\
Commands:
  A {AAA|BBB}       text for A.""")

    def test_build_command_with_literal_para_complete(self):
        class Opt(SimpleDispatch):
            @dispatch('A')
            @validator_for('a', literal_type(complete=True))
            def run_a(self, a: Literal['AAA', 'BBB']):
                """text for A."""
                pass

        self.assertEqual(Opt.build_command_usages(show_para=True), """\
Commands:
  A {AAA|BBB}       text for A.""")

    def test_build_command_with_literal_keyword_para(self):
        class Opt(SimpleDispatch):
            @dispatch('A')
            @validator_for('a')
            def run_a(self, *, a: Literal['AAA', 'BBB']):
                """text for A."""
                pass

        self.assertEqual(Opt.build_command_usages(show_para=True), """\
Commands:
  A A={AAA|BBB}     text for A.""")

    def test_build_command_on_order(self):
        class Opt(SimpleDispatch):
            @dispatch('A', order=7)
            def run_a(self):
                """text for A."""
                pass

            @dispatch('B', order=5)
            def run_b(self):
                """text for B."""
                pass

            @dispatch('C', order=3)
            def run_c(self):
                """text for C."""
                pass

        self.assertEqual(Opt.build_command_usages(show_para=True), """\
Commands:
  C                 text for C.
  B                 text for B.
  A                 text for A.""")

    def test_build_command_with_long_usages(self):
        class Opt(SimpleDispatch):
            @dispatch('A', 'a', usage='A test is a very long usage text that it is over 20 characters')
            def run_a(self):
                """
                it is also a very long command document for dispatch command A that it is over 120 characters,
                and it does not need to be fit into one line.

                more text.
                """
                pass

        self.assertEqual(Opt.build_command_usages(), """\
Commands:
  A test is a very long usage text that it is over 20 characters
                    it is also a very long command document for dispatch command A that it is over 120 characters, and
                    it does not need to be fit into one line.""")

        self.assertEqual(Opt.build_command_usages(doc_indent=10, width=80), """\
Commands:
  A test is a very long usage text that it is over 20 characters
          it is also a very long command document for dispatch command A that it
          is over 120 characters, and it does not need to be fit into one line.""")

    def test_print_help(self):
        class Opt(SimpleDispatch):
            @dispatch('A', 'a')
            def run_a(self):
                """text for A.

                """
                pass

            @dispatch('B')
            def run_b(self):
                """
                text for B.

                """
                pass

        self.assertEqual(print_help(Opt, None, prog='run.py'), """\
usage: run.py [-h] cmd [args ...]

positional arguments:
  cmd
  args

options:
  -h, --help  show this help message and exit

Commands:
  A (a)             text for A.
  B                 text for B.
""")

    def test_print_help_custom_section(self):
        class Opt(SimpleDispatch):
            COMMAND_HELP_DOC = lambda: Opt.build_command_usages(group='A', show_para=True)
            EPILOG = 'A epilog text'

            @dispatch('A', 'a', group='A')
            def run_a(self):
                """text for A.

                """
                pass

            @dispatch('B')
            def run_b(self):
                """
                text for B.

                """
                pass

        self.assertEqual(print_help(Opt, None, prog='run.py'), """\
usage: run.py [-h] cmd [args ...]

positional arguments:
  cmd
  args

options:
  -h, --help  show this help message and exit

Commands:
  A (a)             text for A.

A epilog text
""")

    def test_print_help_custom_section_method(self):
        class Opt(SimpleDispatch):
            EPILOG = 'A epilog text'

            @classmethod
            def COMMAND_HELP_DOC(cls):
                return cls.build_command_usages(group='A', show_para=True)

            @dispatch('A', 'a', group='A')
            def run_a(self):
                """text for A.

                """
                pass

            @dispatch('B')
            def run_b(self):
                """
                text for B.

                """
                pass

        self.assertEqual(print_help(Opt, None, prog='run.py'), """\
usage: run.py [-h] cmd [args ...]

positional arguments:
  cmd
  args

options:
  -h, --help  show this help message and exit

Commands:
  A (a)             text for A.

A epilog text
""")


class UseCaseTest(unittest.TestCase):
    def test_example_1(self):
        # example adjusted from the 'Grouping' section, doc of class Dispatch.
        class Main(AbstractParser, Dispatch):
            DESCRIPTION = 'Description text'
            EPILOG = 'Epilog text'

            mode: Literal['A', 'B'] = argument('--mode', default='A', help='mode text')
            mode_group = dispatch_group('mode')

            command: str = pos_argument('CMD')
            result: str = None

            @classmethod
            def COMMAND_HELP_DOC(cls):
                command_text = cls.build_command_usages(None, doc_indent=16)
                mode_list = cls.build_command_usages(cls.mode_group, header='Available Modes:', doc_indent=16)

                return '\n\n'.join([
                    command_text,
                    mode_list
                ])

            @mode_group('A')
            def get_mode_a(self):
                """mode A text"""
                return 'mode A'

            @mode_group('B')
            def get_mode_b(self):
                """mode B text"""
                return 'mode B'

            @dispatch('run')
            def run_command(self):
                """command run text"""
                try:
                    mode = self.invoke_group_command(self.mode_group, self.mode)
                    return f'run for {mode}'
                except DispatchCommandNotFound:
                    return 'run for unknown mode'

            def run(self):
                self.result = self.invoke_command(self.command)

        with self.subTest('main'):
            main = Main().main(['run'])
            self.assertIsInstance(main, Main)
            self.assertEqual(main.result, 'run for mode A')

            main = Main().main(['run', '--mode=B'])
            self.assertIsInstance(main, Main)
            self.assertEqual(main.result, 'run for mode B')

        with self.subTest('error main'):
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    Main().main(['run', '--mode=C'])

        with self.subTest('error call'):
            main = Main()
            main.command = 'run'
            main.mode = 'C'  # we do not use validator, so no error is raised here.
            main.run()
            self.assertEqual(main.result, 'run for unknown mode')

        with self.subTest('help'):
            self.assertEqual(print_help(Main, None, prog='run.py'), """\
usage: run.py [-h] [--mode A|B] CMD

Description text

positional arguments:
  CMD

options:
  -h, --help  show this help message and exit
  --mode A|B  mode text (default: 'A')

Commands:
  run           command run text

Available Modes:
  A             mode A text
  B             mode B text

Epilog text
""")


if __name__ == '__main__':
    unittest.main()
