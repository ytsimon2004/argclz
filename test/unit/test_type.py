import unittest
from pathlib import Path
from typing import Optional, Literal

from argclz import *
from argclz.core import parse_args


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

    def test_bool_value(self):
        class Opt:
            a: bool = argument('-a', type=bool_type)

        self.assertTrue(parse_args(Opt(), ['-a=1']).a)
        self.assertTrue(parse_args(Opt(), ['-a+']).a)
        self.assertTrue(parse_args(Opt(), ['-a=+']).a)
        self.assertTrue(parse_args(Opt(), ['-a=t']).a)
        self.assertTrue(parse_args(Opt(), ['-a=true']).a)
        self.assertTrue(parse_args(Opt(), ['-a=y']).a)
        self.assertTrue(parse_args(Opt(), ['-a=yes']).a)
        self.assertTrue(parse_args(Opt(), ['-a=Y']).a)
        self.assertFalse(parse_args(Opt(), ['-a-']).a)
        self.assertFalse(parse_args(Opt(), ['-a=-']).a)
        self.assertFalse(parse_args(Opt(), ['-a=0']).a)
        self.assertFalse(parse_args(Opt(), ['-a=f']).a)
        self.assertFalse(parse_args(Opt(), ['-a=false']).a)
        self.assertFalse(parse_args(Opt(), ['-a=n']).a)
        self.assertFalse(parse_args(Opt(), ['-a=no']).a)
        self.assertFalse(parse_args(Opt(), ['-a=x']).a)
        self.assertFalse(parse_args(Opt(), ['-a=N']).a)
        self.assertFalse(parse_args(Opt(), ['-a=X']).a)

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

    def test_literal_complete(self):
        class Opt:
            a: Literal['AAA', 'BBB'] = argument('-a', type=literal_type(complete=False))

        with self.assertRaises(RuntimeError):
            opt = parse_args(Opt(), ['-a', 'A'])

        class Opt:
            a: Literal['AAA', 'BBB'] = argument('-a', type=literal_type(complete=True))

        opt = parse_args(Opt(), ['-a', 'A'])
        self.assertEqual(opt.a, 'AAA')

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

    def test_list_type_var_arg(self):
        class Opt:
            a: list[str] = var_argument('...')

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

    def test_list_type_infer_var_arg(self):
        class Opt:
            a: list[int] = var_argument('...')

        opt = parse_args(Opt(), ['12', '34'])
        self.assertListEqual(opt.a, [12, 34])

    def test_list_type_comma(self):
        class Opt:
            a: list[int] = argument('-a', type=list_type(int))

        opt = parse_args(Opt(), ['-a=1,2'])
        self.assertListEqual(opt.a, [1, 2])

    def test_list_type_comma_prepend(self):
        class Opt:
            a: list[int] = argument('-a', type=list_type(int, prepend=[0]))

        opt = parse_args(Opt(), ['-a=1,2'])
        self.assertListEqual(opt.a, [1, 2])
        opt = parse_args(Opt(), ['-a=+,1,2'])
        self.assertListEqual(opt.a, [0, 1, 2])

    def test_tuple_type(self):
        class Opt:
            a: tuple[int, str] = argument('-a', type=tuple_type(int, str))

        opt = parse_args(Opt(), ['-a=1,2'])
        self.assertTupleEqual(opt.a, (1, '2'))

    def test_tuple_type_ellipse(self):
        class Opt:
            a: tuple[int, ...] = argument('-a', type=tuple_type(int, ...))

        opt = parse_args(Opt(), ['-a=1,2'])
        self.assertTupleEqual(opt.a, (1, 2))
        opt = parse_args(Opt(), ['-a=1,2,3'])
        self.assertTupleEqual(opt.a, (1, 2, 3))

    def test_tuple_type_func(self):
        _ = tuple_type(int)
        _ = tuple_type(int, int)
        _ = tuple_type(int, ...)

        with self.assertRaises(RuntimeError):
            tuple_type(...)

        with self.assertRaises(RuntimeError):
            tuple_type(..., int)

        with self.assertRaises(RuntimeError):
            tuple_type(int, ..., int)

        with self.assertRaises(RuntimeError):
            tuple_type(int, ..., ...)

    def test_dict_type(self):
        class Opt:
            a: dict[str, int] = argument('-a', type=dict_type(literal_value_type))

        opt = parse_args(Opt(), ['-a=a=1'])
        self.assertDictEqual(opt.a, {'a': 1})

        opt = parse_args(Opt(), ['-a=a=1', '-a=b:2'])
        self.assertDictEqual(opt.a, {'a': 1, 'b': 2})

        opt = parse_args(Opt(), ['-a=a=1', '-a=b:2', '-a=c'])
        self.assertDictEqual(opt.a, {'a': 1, 'b': 2, 'c': ''})


if __name__ == '__main__':
    unittest.main()
