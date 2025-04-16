import unittest
from pathlib import Path
from typing import Optional, Literal

from argp import *


class TypeAnnotationTest(unittest.TestCase):
    def test_bool(self):
        class Opt:
            a: bool = argument('-a')

        opt = parse_args(Opt(), ['-a'])
        self.assertTrue(opt.a)

        opt = parse_args(Opt(), [])
        self.assertFalse(opt.a)

    def test_bool_set_false(self):
        class Opt:
            a: bool = argument('-a', default=True)

        opt = parse_args(Opt(), ['-a'])
        self.assertFalse(opt.a)

        opt = parse_args(Opt(), [])
        self.assertTrue(opt.a)

    def test_str(self):
        class Opt:
            a: str = argument('-a')

        opt = parse_args(Opt(), ['-a', 'test'])
        self.assertEqual(opt.a, 'test')
        opt = parse_args(Opt(), [])
        self.assertIsNone(opt.a)

    def test_optional_str(self):
        class Opt:
            a: Optional[str] = argument('-a')

        opt = parse_args(Opt(), ['-a', 'test'])
        self.assertEqual(opt.a, 'test')
        opt = parse_args(Opt(), [])
        self.assertIsNone(opt.a)

    def test_optional_pipeline_int(self):
        class Opt:
            a: int | None = argument('-a')

        opt = parse_args(Opt(), ['-a', '1'])
        self.assertEqual(opt.a, 1)
        opt = parse_args(Opt(), [])
        self.assertIsNone(opt.a)

    def test_int(self):
        class Opt:
            a: int = argument('-a')

        opt = parse_args(Opt(), ['-a', '10'])
        self.assertEqual(opt.a, 10)
        opt = parse_args(Opt(), [])
        self.assertIsNone(opt.a)

    def test_float(self):
        class Opt:
            a: float = argument('-a')

        opt = parse_args(Opt(), ['-a', '10.321'])
        self.assertEqual(opt.a, 10.321)
        opt = parse_args(Opt(), [])
        self.assertIsNone(opt.a)

    def test_path(self):
        class Opt:
            a: Path = argument('-a')

        opt = parse_args(Opt(), ['-a', 'test_argp.py'])
        self.assertEqual(opt.a, Path('test_argp.py'))
        opt = parse_args(Opt(), [])
        self.assertIsNone(opt.a)

    def test_literal(self):
        class Opt:
            a: Literal['A', 'B'] = argument('-a')

        opt = parse_args(Opt(), ['-a', 'A'])
        self.assertEqual(opt.a, 'A')

        opt = parse_args(Opt(), [])
        self.assertIsNone(opt.a)

        with self.assertRaises(RuntimeError):
            parse_args(Opt(), ['-a', 'C'])

    def test_optional_literal(self):
        class Opt:
            a: Literal['A', 'B', None] = argument('-a')

        opt = parse_args(Opt(), ['-a', 'A'])
        self.assertEqual(opt.a, 'A')

        opt = parse_args(Opt(), [])
        self.assertIsNone(opt.a)

        with self.assertRaises(RuntimeError):
            parse_args(Opt(), ['-a', 'C'])

    def test_optional_literal_2(self):
        class Opt:
            a: Optional[Literal['A', 'B']] = argument('-a')

        opt = parse_args(Opt(), ['-a', 'A'])
        self.assertEqual(opt.a, 'A')

        opt = parse_args(Opt(), [])
        self.assertIsNone(opt.a)

        with self.assertRaises(RuntimeError):
            parse_args(Opt(), ['-a', 'C'])

    def test_optional_literal_3(self):
        class Opt:
            a: Literal['A', 'B'] | None = argument('-a')

        opt = parse_args(Opt(), ['-a', 'A'])
        self.assertEqual(opt.a, 'A')

        opt = parse_args(Opt(), [])
        self.assertIsNone(opt.a)

        with self.assertRaises(RuntimeError):
            parse_args(Opt(), ['-a', 'C'])

    def test_literal_with_choice(self):
        class Opt:
            a: Literal['A', 'B'] = argument('-a', choices=('A', 'B', 'C'))

        with self.assertRaises(RuntimeError):
            parse_args(Opt(), ['-a', 'C'])

    def test_list_type_extend(self):
        class Opt:
            a: list[str] = argument(metavar='...', nargs='*', action='extend')

        opt = parse_args(Opt(), [])
        self.assertListEqual(opt.a, [])

        opt = parse_args(Opt(), ['12', '34'])
        self.assertListEqual(opt.a, ['12', '34'])

    def test_list_type_append(self):
        class Opt:
            a: list[str] = argument('-a', action='append')

        opt = parse_args(Opt(), [])
        self.assertListEqual(opt.a, [])

        opt = parse_args(Opt(), ['-a=1'])
        self.assertListEqual(opt.a, ['1'])

        opt = parse_args(Opt(), ['-a=1', '-a=2'])
        self.assertListEqual(opt.a, ['1', '2'])

    def test_list_type_infer(self):
        class Opt:
            a: list[int] = argument(metavar='...', nargs='*', action='extend')

        opt = parse_args(Opt(), ['12', '34'])
        self.assertListEqual(opt.a, [12, 34])


if __name__ == '__main__':
    unittest.main()
