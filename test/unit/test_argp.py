import unittest
from typing import Literal
from unittest import skipIf

from argp import *
from argp.clone import Cloneable
from argp.core import with_defaults, as_dict, parse_args, copy_argument

try:
    import polars as pl
except ImportError:
    pl = None


class WithDefaultTest(unittest.TestCase):
    def test_bool(self):
        class Opt:
            a: bool = argument('-a')

        opt = with_defaults(Opt())
        self.assertFalse(opt.a)

    def test_bool_set_false(self):
        class Opt:
            a: bool = argument('-a', default=True)

        opt = with_defaults(Opt())
        self.assertTrue(opt.a)

    def test_str(self):
        class Opt:
            a: str = argument('-a')

        opt = with_defaults(Opt())
        with self.assertRaises(AttributeError):
            a = opt.a

    def test_default_str(self):
        class Opt:
            a: str = argument('-a', default='default')

        opt = with_defaults(Opt())
        self.assertEqual(opt.a, 'default')

    def test_int(self):
        class Opt:
            a: int = argument('-a')

        opt = with_defaults(Opt())
        with self.assertRaises(AttributeError):
            a = opt.a

    def test_default_int(self):
        class Opt:
            a: int = argument('-a', default=101)

        opt = with_defaults(Opt())
        self.assertEqual(opt.a, 101)

    def test_float(self):
        class Opt:
            a: float = argument('-a')

        opt = with_defaults(Opt())
        with self.assertRaises(AttributeError):
            a = opt.a

    def test_default_float(self):
        class Opt:
            a: float = argument('-a', default=3.14)

        opt = with_defaults(Opt())
        self.assertEqual(opt.a, 3.14)

    def test_literal(self):
        class Opt:
            a: Literal['A', 'B'] = argument('-a')

        opt = with_defaults(Opt())
        with self.assertRaises(AttributeError):
            a = opt.a

    def test_default_literal(self):
        class Opt:
            a: Literal['A', 'B'] = argument('-a', default='C')

        opt = with_defaults(Opt())
        self.assertEqual(opt.a, 'C')


class AsDictTest(unittest.TestCase):
    def test_emtpy(self):
        class Opt:
            a: str = argument('-a', default='default')

        self.assertDictEqual(as_dict(Opt()), {})

    def test_as_dict(self):
        class Opt:
            a: str = argument('-a', default='default')

        opt = with_defaults(Opt())
        self.assertDictEqual(as_dict(opt), {'a': 'default'})


class AbstractParserTest(unittest.TestCase):
    def test_exit_on_error(self):
        class Main(AbstractParser):
            a: str = argument('-a', default='default')

        with self.assertRaises(SystemExit):
            Main().main(['-b'], system_exit=True)

        with self.assertRaises(RuntimeError):
            Main().main(['-b'], system_exit=False)


class CopyArgsTest(unittest.TestCase):
    def test_copy_argument(self):
        class Opt:
            a: str = argument('-a')

        opt = parse_args(Opt(), ['-a=2'])
        self.assertEqual(opt.a, '2')
        ano = copy_argument(Opt(), opt)
        self.assertEqual(ano.a, '2')

    def test_copy_argument_from_dict(self):
        class Opt:
            a: str = argument('-a')

        ano = copy_argument(Opt(), None, a='2')
        self.assertEqual(ano.a, '2')

    def test_copy_argument_from_distinct(self):
        class Opt1:
            a: str = argument('-a')

        class Opt2:
            a: str = argument('-a')

        opt = parse_args(Opt1(), ['-a=2'])
        self.assertEqual(opt.a, '2')

        ano = copy_argument(Opt2(), opt)
        self.assertEqual(ano.a, '2')

    def test_cloneable(self):
        class Opt(Cloneable):
            a: str = argument('-a')

        opt = parse_args(Opt(), ['-a=2'])
        self.assertEqual(opt.a, '2')

        ano = Opt(opt)
        self.assertEqual(ano.a, '2')

    @skipIf(pl is None, reason='no polars installed')
    def test_cloneable_from_dataframe(self):
        class Opt(Cloneable):
            a: str = argument('-a')

        data = pl.DataFrame([{'a': '2'}])
        opt = Opt(data)
        self.assertEqual(opt.a, '2')


if __name__ == '__main__':
    unittest.main()
