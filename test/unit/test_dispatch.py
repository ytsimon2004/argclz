import unittest
from typing import Any

from argclz import *
from argclz.core import print_help
from argclz.dispatch import *


class SimpleDispatch(AbstractParser, Dispatch):
    c: str = pos_argument('cmd')
    a: list[str] = var_argument('args')
    r: Any

    def run(self):
        self.invoke_command(self.c, *self.a)


class TestDispatch(unittest.TestCase):
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

        commands = Opt.list_commands()
        commands = [it.command for it in commands]
        self.assertListEqual(commands, ['A', 'B', 'C'])

        commands = Opt.list_commands(None)
        commands = [it.command for it in commands]
        self.assertListEqual(commands, ['A', 'B'])

        commands = Opt.list_commands('A')
        commands = [it.command for it in commands]
        self.assertListEqual(commands, ['C'])

        commands = Opt.list_commands('C')
        commands = [it.command for it in commands]
        self.assertListEqual(commands, [])

    def test_list_hidden_commands(self):
        class Opt(SimpleDispatch):
            @dispatch('A')
            def run_a(self):
                pass

            @dispatch('B', hidden=True)
            def run_b(self):
                pass

        commands = Opt.list_commands()
        commands = [it.command for it in commands]
        self.assertListEqual(commands, ['A'])

        commands = Opt.list_commands(all=True)
        commands = [it.command for it in commands]
        self.assertListEqual(commands, ['A', 'B'])

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

        with self.assertRaises(DispatchCommandNotFound):
            opt.invoke_command('B')

        opt.invoke_group_command('B', 'B')

        with self.assertRaises(DispatchCommandNotFound):
            opt.invoke_group_command('B', 'A')

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
        print(capture.exception)

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


class TestDispatchGroup(unittest.TestCase):
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

        commands = Opt.g.list_commands()
        commands = [it.command for it in commands]
        self.assertListEqual(commands, ['B', 'C'])

    def test_use_group(self):
        class Opt(SimpleDispatch):
            g = dispatch_group('A')
            r: str | None = None

            @g('A')
            def run_a(self):
                self.r = 'A'

        opt = Opt()
        commands = opt.list_commands(Opt.g)
        commands = [it.command for it in commands]
        self.assertListEqual(commands, ['A'])

        commands = opt.list_commands(opt.g)
        commands = [it.command for it in commands]
        self.assertListEqual(commands, ['A'])

        command = opt.find_command('A', Opt.g)
        assert command is not None
        self.assertEqual(command.command, 'A')
        command = opt.find_command('A', opt.g)
        assert command is not None
        self.assertEqual(command.command, 'A')

        opt.r = None
        self.assertIsNone(opt.r)
        opt.invoke_group_command(Opt.g, 'A')
        self.assertEqual(opt.r, 'A')

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
        commands = opt.list_commands(g)
        commands = [it.command for it in commands]
        self.assertListEqual(commands, ['A'])

        command = opt.find_command('A', g)
        assert command is not None
        self.assertEqual(command.command, 'A')

        opt.r = None
        self.assertIsNone(opt.r)
        opt.invoke_group_command(g, 'A')
        self.assertEqual(opt.r, 'A')

    def test_use_in_non_Dispatch(self):
        # python version: >= 3.12 (TypeError), otherwise RuntimeError
        with self.assertRaises((RuntimeError, TypeError)):
            class Opt:
                g = dispatch_group('A')


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
A (a)               text for A.
B                   text for B.""")

    def test_build_command_with_custom_usages(self):
        class Opt(SimpleDispatch):
            @dispatch('A', 'a', usage='A B C D')
            def run_a(self):
                """text for A.

                more text.
                """
                pass

        self.assertEqual(Opt.build_command_usages(), """\
A B C D             text for A.""")

    def test_build_command_usages_with_empty_doc(self):
        class Opt(SimpleDispatch):
            @dispatch('A')
            def run_a(self):
                """

                """
                pass

        self.assertEqual(Opt.build_command_usages(), """\
A""")

    def test_build_command_usages_with_para(self):
        class Opt(SimpleDispatch):
            @dispatch('A')
            def run_a(self, a: str, b: str):
                """text for A."""
                pass

        self.assertEqual(Opt.build_command_usages(show_para=True), """\
A A B               text for A.""")

    def test_build_command_usages_with_optional_para(self):
        class Opt(SimpleDispatch):
            @dispatch('A')
            def run_a(self, a: str, b: str | None = None):
                """text for A."""
                pass

        self.assertEqual(Opt.build_command_usages(show_para=True), """\
A A [B]             text for A.""")

    def test_build_command_usages_with_keyword_para(self):
        class Opt(SimpleDispatch):
            @dispatch('A')
            def run_a(self, a: str, *, b: str | None = None):
                """text for A."""
                pass

        self.assertEqual(Opt.build_command_usages(show_para=True), """\
A A [B=]            text for A.""")

    def test_build_command_usages_with_var_para(self):
        class Opt(SimpleDispatch):
            @dispatch('A')
            def run_a(self, a: str, *b: str, **c):
                """text for A."""
                pass

        self.assertEqual(Opt.build_command_usages(show_para=True), """\
A A *B **C          text for A.""")

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
C                   text for C.
B                   text for B.
A                   text for A.""")

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
A test is a very long usage text that it is over 20 characters
                    it is also a very long command document for dispatch command A that it is over 120 characters, and
                    it does not need to be fit into one line.""")

        self.assertEqual(Opt.build_command_usages(doc_indent=10, width=80), """\
A test is a very long usage text that it is over 20 characters
          it is also a very long command document for dispatch command A that it
          is over 120 characters, and it does not need to be fit into one line.""")

    def test_print_help(self):
        class Opt(SimpleDispatch):
            EPILOG = (lambda: f"""\
Commands:
{Opt.build_command_usages()}
""")

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
A (a)               text for A.
B                   text for B.
""")


if __name__ == '__main__':
    unittest.main()
