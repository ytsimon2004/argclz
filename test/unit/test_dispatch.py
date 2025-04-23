import builtins
import unittest
from unittest.mock import patch

from argclz import *
from argclz.core import print_help
from argclz.dispatch import *

try:
    import rich
except ImportError:
    rich = None

IMPORT = builtins.__import__


def block_rich_import(name, globals, locals, fromlist, level):
    if name == 'rich':
        raise ImportError

    return IMPORT(name, globals, locals, fromlist, level)


def ensure_rich_raise_error(self):
    try:
        import rich
    except ImportError:
        pass
    else:
        self.fail()


class SimpleDispatch(AbstractParser, Dispatch):
    c: str = pos_argument('cmd')
    a: list[str] = var_argument('args')
    r: str

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
        ret = opt.main(['A'], system_exit=False)
        self.assertIsNone(ret.exit_status)
        self.assertEqual(opt.r, 'AAA')

        ret = opt.main(['B'], system_exit=False)
        self.assertIsNone(ret.exit_status)
        self.assertEqual(opt.r, 'BBB')

        with self.assertRaises(DispatchCommandNotFound):
            opt.main(['C'], system_exit=False)

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

    def test_dispatch_command_alias(self):
        class Opt(SimpleDispatch):
            @dispatch('A', 'a')
            def run_a(self):
                self.r = 'AAA'

        opt = Opt()
        ret = opt.main(['A'], system_exit=False)
        self.assertIsNone(ret.exit_status)
        self.assertEqual(opt.r, 'AAA')

        ret = opt.main(['a'], system_exit=False)
        self.assertIsNone(ret.exit_status)
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
        ret = opt.main(['A'], system_exit=False)
        self.assertIsNone(ret.exit_status)
        self.assertEqual(opt.r, 'BBB')

    def test_dispatch_command_argument(self):
        class Opt(SimpleDispatch):
            r: tuple[str, ...]

            @dispatch('A')
            def run_a(self, *a):
                self.r = a

        opt = Opt()
        ret = opt.main(['A'], system_exit=False)
        self.assertIsNone(ret.exit_status)
        self.assertTupleEqual(opt.r, ())

        ret = opt.main(['A', '1', '2'], system_exit=False)
        self.assertIsNone(ret.exit_status)
        self.assertTupleEqual(opt.r, ('1', '2'))

    def test_dispatch_command_argument_casting(self):
        class Opt(SimpleDispatch):
            r: int

            @dispatch('A')
            @validator_for('a')
            def run_a(self, a: int):
                self.r = a

        opt = Opt()
        ret = opt.main(['A', '1'], system_exit=False)
        self.assertIsNone(ret.exit_status)
        self.assertEqual(opt.r, 1)

    def test_dispatch_command_argument_casting_validator(self):
        class Opt(SimpleDispatch):
            r: int

            @dispatch('A')
            @validator_for('a', validator.int.positive(include_zero=False))
            def run_a(self, a: int):
                self.r = a

        opt = Opt()
        ret = opt.main(['A', '1'], system_exit=False)
        self.assertIsNone(ret.exit_status)
        self.assertEqual(opt.r, 1)

        with self.assertRaises(ValueError) as capture:
            opt.main(['A', '0'], system_exit=False)
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
        ret = opt.main(['A', '1'], system_exit=False)
        self.assertIsNone(ret.exit_status)
        self.assertEqual(opt.r, 1)

        ret = opt.main(['A', 'a'], system_exit=False)
        self.assertIsNone(ret.exit_status)
        self.assertEqual(opt.r, 'a')

        with self.assertRaises(ValueError) as capture:
            opt.main(['A', '0'], system_exit=False)
        print(capture.exception)

    def test_dispatch_command_argument_validator_misorder(self):
        with self.assertRaises(RuntimeError) as capture:
            class Opt(SimpleDispatch):
                r: int | None

                @validator_for('a')
                @dispatch('A')
                def run_a(self, a: int):
                    self.r = a

        self.assertEqual(capture.exception.args[0], 'run_a already frozen')


RUNNER = ''


class PrintHelpTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        global RUNNER

        class Opt(AbstractParser):
            pass

        h = print_help(Opt, None)
        RUNNER = h.split('\n')[0].split(' ')[1]

    @patch('builtins.__import__', block_rich_import)
    def test_build_command_usages(self):
        ensure_rich_raise_error(self)

        class Opt(SimpleDispatch):
            @dispatch('A', 'a')
            def run_a(self):
                """text for A.

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

    @patch('builtins.__import__', block_rich_import)
    def test_build_command_usages_with_empty_doc(self):
        ensure_rich_raise_error(self)

        class Opt(SimpleDispatch):
            @dispatch('A')
            def run_a(self):
                """

                """
                pass

        self.assertEqual(Opt.build_command_usages(), """\
A""")

    @patch('builtins.__import__', block_rich_import)
    def test_build_command_usages_with_para(self):
        ensure_rich_raise_error(self)

        class Opt(SimpleDispatch):
            @dispatch('A')
            def run_a(self, a: str, b: str):
                """text for A."""
                pass

            @dispatch('B')
            def run_b(self, a: str, b: str = None):
                """text for B."""
                pass

        self.assertEqual(Opt.build_command_usages(), """\
A a b               text for A.
B a b?              text for B.""")

    @patch('builtins.__import__', block_rich_import)
    def test_build_command_usages(self):
        ensure_rich_raise_error(self)

        class Opt(SimpleDispatch):
            EPILOG = lambda: f"""\
Commands:
{Opt.build_command_usages()}
"""

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

        self.assertEqual(print_help(Opt, None), f"""\
usage: {RUNNER} [-h] cmd [args ...]

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
