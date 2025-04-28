import unittest
from pathlib import Path
from typing import Any

from argclz import *
from argclz.core import parse_args


class TestValidator(unittest.TestCase):
    def test_validator(self):
        class Opt:
            a: str = argument('-a', validator=lambda it: len(it) > 0)

        opt = parse_args(Opt(), ['-a=1'])
        self.assertEqual(opt.a, '1')

        with self.assertRaises(ValueError):
            parse_args(Opt(), ['-a='])

        opt.a = '2'
        self.assertEqual(opt.a, '2')

        with self.assertRaises(ValueError):
            opt.a = ''

        with self.assertRaises(ValueError):
            opt.a = None

    def test_validator_tuple(self):
        class Opt:
            a: tuple[str, str] = argument('-a', type=str_tuple_type, validator=lambda it: len(it) == 2)
            b: tuple[int, ...] | None = argument('-b', type=int_tuple_type,
                                                 validator=lambda it: it is None or all([i < 5 for i in it]))

        with self.assertRaises(ValueError):
            parse_args(Opt(), ['-a=10,2,3'])

        with self.assertRaises(ValueError):
            parse_args(Opt(), ['-b=6,2'])

    def test_validator_with_type_caster(self):
        class Opt:
            a: int = argument('-a', validator=lambda it: it >= 0)

        opt = parse_args(Opt(), ['-a=1'])
        self.assertEqual(opt.a, 1)

        with self.assertRaises(ValueError):
            parse_args(Opt(), ['-a=-1'])

        opt.a = 1
        self.assertEqual(opt.a, 1)

        with self.assertRaises(ValueError):
            opt.a = -1

    def test_validate_on_set_on_normal_attr(self):
        class Opt:
            a: str = argument('-a', validator=lambda it: len(it) > 0)

        with self.assertRaises(ValueError):
            parse_args(Opt(), ['-a='])

        with self.assertRaises(ValueError):
            Opt().a = ''


class TestValidateBuilder(unittest.TestCase):

    def test_type_error(self):
        class Opt:
            a: str = argument('-a', validator.str)

        opt = Opt()
        with self.assertRaises(ValueError):
            opt.a = 1

    def test_validator_wrap_lambda(self):
        class Opt:
            a: str = argument('-a', validator(lambda it: isinstance(it, str)))

        opt = Opt()
        with self.assertRaises(ValueError):
            opt.a = 1

    def test_str_in_range(self):
        class Opt:
            a: str = argument('-a', validator.str.length_in_range(2, None))
            b: str = argument('-b', validator.str.length_in_range(None, 2))
            c: str = argument('-c', validator.str.length_in_range(2, 4))

        opt = Opt()
        opt.a = '12'
        opt.b = '12'
        opt.c = '12'

        with self.assertRaises(ValueError):
            opt.a = ''
        with self.assertRaises(ValueError):
            opt.b = '1234'
        with self.assertRaises(ValueError):
            opt.c = ''
        with self.assertRaises(ValueError):
            opt.c = '12345678'

    def test_str_in_range_type_error(self):
        with self.assertRaises(TypeError):
            class Opt:
                a: str = argument('-a', validator.str.length_in_range('a', None))

    def test_str_match(self):
        class Opt:
            a: str = argument('-a', validator.str.match(r'[a-z][0-9]'))

        opt = Opt()
        opt.a = 'a1'

        with self.assertRaises(ValueError):
            opt.a = 'A1'

    def test_str_starts_ends(self):
        class Opt:
            a: str = argument('-a', validator.str.starts_with('X').ends_with('Y'))

        opt = Opt()
        opt.a = 'XasdY'

        with self.assertRaises(ValueError):
            opt.a = 'Y!@#X'

    def test_str_contains(self):
        class Opt:
            a: str = argument('-a', validator.str.contains('00'))
            b: str = argument('-a', validator.str.contains('00', '11'))

        opt = Opt()
        opt.a = 'x001'

        with self.assertRaises(ValueError):
            opt.a = 'x110'

        opt.b = 'x001'
        opt.b = 'x011'

        with self.assertRaises(ValueError):
            opt.b = 'x101'

    def test_str_one_of(self):
        class Opt:
            a: str = argument('-a', validator.str.one_of(['opt1', 'opt2']))

        opt = Opt()
        opt.a = 'opt1'

        with self.assertRaises(ValueError):
            opt.a = 'opt3'

    def test_int_in_range(self):
        class Opt:
            a: int = argument('-a', validator.int.in_range(2, None))
            b: int = argument('-b', validator.int.in_range(None, 2))
            c: int = argument('-c', validator.int.in_range(2, 4))

        opt = Opt()
        opt.a = 2
        opt.b = 2
        opt.c = 2

        with self.assertRaises(ValueError):
            opt.a = 0
        with self.assertRaises(ValueError):
            opt.b = 10
        with self.assertRaises(ValueError):
            opt.c = 0
        with self.assertRaises(ValueError):
            opt.c = 10

    def test_int_in_range_type_error(self):
        with self.assertRaises(TypeError):
            class Opt:
                a: int = argument('-a', validator.int.in_range('2', None))

        with self.assertRaises(TypeError):
            class Opt:
                a: int = argument('-a', validator.int.in_range(2.1, None))

    def test_float_in_range(self):
        class Opt:
            a: float = argument('-a', validator.float.in_range(2.5, None))
            b: float = argument('-b', validator.float.in_range(None, 2.5))
            c: float = argument('-c', validator.float.in_range(2.1, 3.9))

        opt = Opt()
        opt.a = 3
        opt.b = 2
        opt.c = 2.5

        with self.assertRaises(ValueError):
            opt.a = 0
        with self.assertRaises(ValueError):
            opt.b = 10
        with self.assertRaises(ValueError):
            opt.c = 0
        with self.assertRaises(ValueError):
            opt.c = 10
        with self.assertRaises(ValueError):
            opt.a = 2.5
        with self.assertRaises(ValueError):
            opt.b = 2.5
        with self.assertRaises(ValueError):
            opt.c = 2.1

    def test_float_in_range_closed(self):
        class Opt:
            a: float = argument('-a', validator.float.in_range_closed(2.5, None))
            b: float = argument('-b', validator.float.in_range_closed(None, 2.5))
            c: float = argument('-c', validator.float.in_range_closed(2.1, 3.9))

        opt = Opt()
        opt.a = 3
        opt.b = 2
        opt.c = 2.5

        with self.assertRaises(ValueError):
            opt.a = 0
        with self.assertRaises(ValueError):
            opt.b = 10
        with self.assertRaises(ValueError):
            opt.c = 0
        with self.assertRaises(ValueError):
            opt.c = 10

        opt.a = 2.5
        opt.b = 2.5
        opt.c = 2.1

    def test_float_in_range_type_error(self):
        class Opt:
            a: float = argument('-a', validator.float.in_range(2.0, None))
            b: float = argument('-a', validator.float.in_range(2, None))

        with self.assertRaises(TypeError):
            class Opt:
                a: float = argument('-a', validator.float.in_range('2', None))

        with self.assertRaises(TypeError):
            class Opt:
                a: float = argument('-a', validator.float.in_range_closed('2', None))

    def test_float_positive(self):
        class Opt:
            a: float = argument('-a', validator.float.positive())
            b: float = argument('-b', validator.float.negative())

        opt = Opt()

        opt.a = 10
        with self.assertRaises(ValueError):
            opt.a = -10

        opt.b = -10
        with self.assertRaises(ValueError):
            opt.b = 10

        opt.a = 0
        opt.b = 0

    def test_float_allow_nan(self):
        class Opt:
            a: float = argument('-a', validator.float.allow_nan(True))
            b: float = argument('-b', validator.float.allow_nan(False))

        opt = Opt()
        opt.a = float('nan')

        with self.assertRaises(ValueError):
            opt.b = float('nan')

    def test_float_allow_nan_then(self):
        class Opt:
            a: float = argument('-a', validator.float.allow_nan(False).positive())

        opt = Opt()
        opt.a = 10

        with self.assertRaises(ValueError):
            opt.a = float('nan')

        with self.assertRaises(ValueError):
            opt.a = -10

    def test_list_in_range(self):
        class Opt:
            a: list[str] = argument('-a', validator.list().length_in_range(2, None))
            b: list[str] = argument('-a', validator.list().length_in_range(None, 2))
            c: list[str] = argument('-a', validator.list().length_in_range(2, 4))

        opt = Opt()
        opt.a = ['1', '2', '3']
        opt.b = []
        opt.b = ['1']
        opt.c = ['1', '2']

        with self.assertRaises(ValueError):
            opt.a = []
        with self.assertRaises(ValueError):
            opt.c = []

    def test_list_in_range_type_error(self):
        with self.assertRaises(TypeError):
            class Opt:
                a: list[str] = argument('-a', validator.list().length_in_range(2.0, None))
        with self.assertRaises(TypeError):
            class Opt:
                a: list[str] = argument('-a', validator.list().length_in_range('2', None))

    def test_list_allow_empty(self):
        class Opt:
            a: list[str] = argument('-a', validator.list().allow_empty(True))
            b: list[str] = argument('-b', validator.list().allow_empty(False))

        opt = Opt()
        opt.a = ['a']
        opt.b = ['a']

        opt.a = []

        with self.assertRaises(ValueError):
            opt.b = []

    def test_list_element_type(self):
        class Opt:
            a: list[int] = argument('-a', validator.list(int))

        opt = Opt()
        opt.a = []
        opt.a = [1, 2]

        with self.assertRaises(ValueError):
            opt.a = ['a']

    def test_list_type_append_element(self):
        class Opt:
            a: list[int] = argument('-a', action='append', validator=validator.list(int))

        opt = Opt()
        opt.a = []
        opt.a = [1, 2]

        self.assertListEqual(parse_args(Opt(), ['-a=1']).a, [1])
        self.assertListEqual(parse_args(Opt(), ['-a=1', '-a=2']).a, [1, 2])

        with self.assertRaises(ValueError):
            opt.a = 1

    def test_list_type_extend_element(self):
        class Opt:
            a: list[int] = argument('-a', action='extend', type=list_type(int), validator=validator.list(int))

        opt = Opt()
        opt.a = []
        opt.a = [1, 2]

        self.assertListEqual(parse_args(Opt(), ['-a=1']).a, [1])
        self.assertListEqual(parse_args(Opt(), ['-a=1', '-a=2']).a, [1, 2])
        self.assertListEqual(parse_args(Opt(), ['-a=1,2']).a, [1, 2])
        self.assertListEqual(parse_args(Opt(), ['-a=1,2', '-a=3']).a, [1, 2, 3])

        with self.assertRaises(ValueError):
            opt.a = 1

    def test_list_element_validating(self):
        class Opt:
            a: list[int] = argument('-a', validator.list(int).on_item(validator.int.positive(include_zero=True)))

        opt = Opt()
        opt.a = []
        opt.a = [1, 2]

        with self.assertRaises(ValueError):
            opt.a = [-1]

        with self.assertRaises(ValueError) as capture:
            opt.a = [1, -1]

        self.assertEqual(capture.exception.args[0],
                         'at index 1, not a non-negative value : -1')

    def test_tuple_length(self):
        class Opt:
            a: tuple[str, str] = argument('-a', validator.tuple(2))

        opt = Opt()
        opt.a = ('a', 'b')

        with self.assertRaises(ValueError):
            opt.a = ()

        with self.assertRaises(ValueError):
            opt.a = ['a', 'b']

        with self.assertRaises(ValueError):
            opt.a = ('a',)

        with self.assertRaises(ValueError):
            opt.a = ('a', 'b', 'c')

    def test_tuple_at_least_length(self):
        class Opt:
            a: tuple[str, ...] = argument('-a', validator.tuple(2, ...))

        opt = Opt()
        opt.a = ('a', 'b')
        opt.a = ('a', 'b', 'c')
        opt.a = ('a', 'b', 'c', 'd')

        with self.assertRaises(ValueError):
            opt.a = ()

        with self.assertRaises(ValueError):
            opt.a = ['a', 'b']

        with self.assertRaises(ValueError):
            opt.a = ('a',)

    def test_tuple_at_least_length_from_zero(self):
        class Opt:
            a: tuple[str, ...] = argument('-a', validator.tuple(0, ...))

        opt = Opt()
        opt.a = ()
        opt.a = ('a',)
        opt.a = ('a', 'b')
        opt.a = ('a', 'b', 'c')

    def test_tuple_element_type(self):
        class Opt:
            a: tuple[str, int, float] = argument(
                '-a',
                validator.tuple(str, int, float)
            )

        opt = Opt()
        opt.a = ('', 0, 0.0)

        with self.assertRaises(ValueError):
            opt.a = ()

        with self.assertRaises(ValueError):
            opt.a = ('', 0)

        with self.assertRaises(ValueError):
            opt.a = ('', 0, 0)

        with self.assertRaises(ValueError):
            opt.a = (0, 0)

    def test_tuple_element_type_var_length(self):
        class Opt:
            a: tuple[str, int, ...] = argument(
                '-a',
                validator.tuple(str, int, ...)
            )

        opt = Opt()
        opt.a = ('', 0)
        opt.a = ('', 0, 0)
        opt.a = ('', 0, 0, 0)

        with self.assertRaises(ValueError):
            opt.a = ()

        with self.assertRaises(ValueError):
            opt.a = ('',)

        with self.assertRaises(ValueError):
            opt.a = (0, 0)
        with self.assertRaises(ValueError):
            opt.a = ('0', 1, '2')

    def test_tuple_element_validating(self):
        class Opt:
            a: tuple[str, int, float] = argument(
                '-a',
                validator.tuple(str, int, float)
                .on_item(0, validator.str.length_in_range(None, 2))
                .on_item(1, validator.int.in_range(0, 10))
            )

        opt = Opt()
        opt.a = ('', 0, 0.0)

        with self.assertRaises(ValueError) as capture:
            opt.a = ('1234', 0, 0.0)
        self.assertEqual(capture.exception.args[0],
                         'at index 0, str length over 2: "1234"')

        with self.assertRaises(ValueError) as capture:
            opt.a = ('12', 100, 0.0)
        self.assertEqual(capture.exception.args[0],
                         'at index 1, value out of range [0, 10]: 100')

    def test_tuple_element_validating_on_last(self):
        class Opt:
            a: tuple[Any, ...] = argument('-a', validator.tuple(...).on_item(-1, validator.int))

        opt = Opt()
        opt.a = (0,)
        opt.a = ('0', 1)
        opt.a = ('0', '1', 2)

        with self.assertRaises(ValueError):
            opt.a = ()
        with self.assertRaises(ValueError):
            opt.a = ('a')
        with self.assertRaises(ValueError):
            opt.a = (0, 'b')

    def test_path_is_suffix(self):
        class Opt:
            a: Path = argument('-a', validator.path.is_suffix(['.txt', '.csv']))

        opt = Opt()
        opt.a = Path('123.txt')
        opt.a = Path('123.csv')
        opt.a = Path('.123.csv')
        opt.a = Path('a_folder/123.csv')
        opt.a = Path('a_folder/321.csv.txt')
        opt.a = Path('a_folder/321.backup.txt')

        with self.assertRaises(ValueError):
            opt.a = Path('a_folder/.txt')

        with self.assertRaises(ValueError):
            opt.a = Path('a_folder/')

        with self.assertRaises(ValueError):
            opt.a = Path('a_folder/123.txt.backup')

    def test_optional(self):
        class Opt:
            a: int = argument('-a', validator.int)
            b: int | None = argument('-b', validator.int.optional())
            c: int | None = argument('-c', validator.any(validator.optional(), validator.int))

        opt = Opt()
        opt.a = 0
        opt.b = 0
        opt.c = 0

        with self.assertRaises(ValueError):
            opt.a = None
        opt.b = None
        opt.c = None

    def test_any(self):
        class Opt:
            a: int | str = argument('-a', validator.any(
                validator.int.in_range(0, 10),
                validator.str.length_in_range(0, 10)
            ))

        opt = Opt()
        opt.a = 3
        opt.a = '123'

        with self.assertRaises(ValueError) as capture:
            opt.a = 30

        self.assertEqual(capture.exception.args[0],
                         'value out of range [0, 10]: 30')

        with self.assertRaises(ValueError) as capture:
            opt.a = '1' * 13

        self.assertEqual(capture.exception.args[0],
                         'str length out of range [0, 10]: "1111111111111"')

    def test_any_literal(self):
        class Opt:
            a: int | str = argument('-a', (
                    validator.int.in_range(0, 10) | validator.str.length_in_range(0, 10)
            ))

        opt = Opt()
        opt.a = 3
        opt.a = '123'

        with self.assertRaises(ValueError) as capture:
            opt.a = 30

        self.assertEqual(capture.exception.args[0],
                         'value out of range [0, 10]: 30')

        with self.assertRaises(ValueError) as capture:
            opt.a = '1' * 13

        self.assertEqual(capture.exception.args[0],
                         'str length out of range [0, 10]: "1111111111111"')

    def test_any_then_or(self):
        class Opt:
            a: int | str = argument('-a', (
                    validator.int.in_range(0, 10) | validator.float.in_range(0, 10) | validator.str.length_in_range(0, 10)
            ))

        opt = Opt()
        opt.a = 3
        opt.a = 3.0
        opt.a = '123'

    def test_or_then_any(self):
        class Opt:
            a: int | str = argument('-a', (
                    validator.int.in_range(0, 10) | (validator.float.in_range(0, 10) | validator.str.length_in_range(0, 10))
            ))

        opt = Opt()
        opt.a = 3
        opt.a = 3.0
        opt.a = '123'

    def test_all(self):
        class Opt:
            a: int = argument('-a', validator.all(
                validator.int.positive(include_zero=True),
                validator.int.negative(include_zero=True),
            ))

        opt = Opt()
        opt.a = 0

        with self.assertRaises(ValueError) as capture:
            opt.a = 1

        self.assertEqual(capture.exception.args[0],
                         'not a non-positive value : 1')

        with self.assertRaises(ValueError) as capture:
            opt.a = -1

        self.assertEqual(capture.exception.args[0],
                         'not a non-negative value : -1')

    def test_all_literal(self):
        class Opt:
            a: int = argument('-a', (
                    validator.int.positive(include_zero=True) & validator.int.negative(include_zero=True)
            ))

        opt = Opt()
        opt.a = 0

        with self.assertRaises(ValueError) as capture:
            opt.a = 1

        self.assertEqual(capture.exception.args[0],
                         'not a non-positive value : 1')

        with self.assertRaises(ValueError) as capture:
            opt.a = -1

        self.assertEqual(capture.exception.args[0],
                         'not a non-negative value : -1')

    def test_all_then_and(self):
        class Opt:
            a: str = argument('-a', (
                    validator.str.length_in_range(2, None) & validator.str.length_in_range(None, 5) & validator.str.contains('A')
            ))

        opt = Opt()
        opt.a = '00A00'

        with self.assertRaises(ValueError):
            opt.a = 0

        with self.assertRaises(ValueError):
            opt.a = '0'

        with self.assertRaises(ValueError):
            opt.a = '01234'

    def test_and_then_all(self):
        class Opt:
            a: str = argument('-a', (
                    validator.str.length_in_range(2, None) & (validator.str.length_in_range(None, 5) & validator.str.contains('A'))
            ))

        opt = Opt()
        opt.a = '00A00'

        with self.assertRaises(ValueError):
            opt.a = 0

        with self.assertRaises(ValueError):
            opt.a = '0'

        with self.assertRaises(ValueError):
            opt.a = '01234'

    def test_tuple_union_length(self):
        class Opt:
            a: tuple[int, int] | tuple[int, int, int] = argument(
                '-a',
                validator.tuple(int, int) | validator.tuple(int, int, int)
            )

        opt = Opt()
        opt.a = (0, 1)
        opt.a = (0, 1, 2)

        with self.assertRaises(ValueError) as capture:
            opt.a = (0,)
        # print(capture.exception.args)
        # length not match to 2 : (0,); length not match to 3 : (0,)

        with self.assertRaises(ValueError) as capture:
            opt.a = (0, 1, 2, 3)
        # print(capture.exception.args)
        # length not match to 2 : (0, 1, 2, 3); length not match to 3 : (0, 1, 2, 3)

    def test_nested_list(self):
        class Opt:
            a: list[tuple[int, list[list[int]]]] = argument('-a', validator.list(
                validator.tuple(int, None)
                .on_item(0, validator.int)
                .on_item(1, validator.list().on_item(validator.list(int)))
            ))

        opt = Opt()
        opt.a = []
        opt.a = [(0, [[0]]), (1, [[1]])]

        with self.assertRaises(ValueError) as capture:
            opt.a = [([[0]])]
        self.assertEqual(capture.exception.args[0],
                         'not a tuple : [[0]]')
        with self.assertRaises(ValueError) as capture:
            opt.a = [(0, [0])]
        self.assertEqual(capture.exception.args[0],
                         'at index 1, at index 0, not a list : 0')

    def test_tuple_on_multiple_item(self):
        class Opt:
            a: tuple[int, float, int, float] = argument(
                '-a',
                validator.tuple()
                .on_item([0, 2], validator.int.positive())
                .on_item(1, v := validator.float.positive())
                .on_item(3, v)
            )

        opt = Opt()
        opt.a = (1, 1, 1, 1)

        with self.assertRaises(ValueError) as capture:
            opt.a = (1, 1, -1, 1)
        with self.assertRaises(ValueError) as capture:
            opt.a = (1, 1, 1, -1)

    def test_tuple_fix_length(self):
        class Opt:
            a: tuple[int, int] = argument(
                '-a',
                validator.tuple(2)
            )

        opt = Opt()
        opt.a = (0, 1)

        with self.assertRaises(ValueError) as capture:
            opt.a = (0,)

        with self.assertRaises(ValueError) as capture:
            opt.a = (0, 1, 2)

        opt.a = ('0', '1')

    def test_tuple_on_all_item(self):
        class Opt:
            a: tuple[int, int] = argument(
                '-a',
                validator.tuple(2).on_item(None, validator.int)
            )

        opt = Opt()
        opt.a = (0, 1)

        with self.assertRaises(ValueError) as capture:
            opt.a = ('0', '1')

    def test_reuse_validator(self):
        class Opt:
            a: int = argument('-a', (v := validator.int))
            b: int = argument('-b', v.positive())

        opt = Opt()
        opt.a = -1


class TestValidateBuilderOnOtherArgument(unittest.TestCase):
    def test_on_pos_argument(self):
        class Opt:
            a: int = pos_argument('A', validator.int.positive(include_zero=False))

        self.assertEqual(parse_args(Opt(), ['1']).a, 1)

        with self.assertRaises(ValueError):
            parse_args(Opt(), ['0'])

    def test_on_var_argument(self):
        class Opt:
            a: list[int] = var_argument('A', validator.list(int).on_item(validator.int.positive(include_zero=False)))

        self.assertListEqual(parse_args(Opt(), ['1']).a, [1])
        self.assertListEqual(parse_args(Opt(), ['1', '2']).a, [1, 2])

        with self.assertRaises(ValueError):
            parse_args(Opt(), ['0'])

        with self.assertRaises(ValueError):
            parse_args(Opt(), ['1', '0'])


if __name__ == '__main__':
    unittest.main()
