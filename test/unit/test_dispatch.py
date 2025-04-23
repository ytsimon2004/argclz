import unittest

from argclz import *
from argclz.dispatch import *


class SimpleDispatch(AbstractParser, Dispatch):
    c: str = pos_argument('cmd')
    a: list[str] = var_argument('...')
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


if __name__ == '__main__':
    unittest.main()
