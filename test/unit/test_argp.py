import unittest
from typing import Literal

from argp import *
from argp.core import with_defaults, as_dict


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
    # TODO
    pass


if __name__ == '__main__':
    unittest.main()
