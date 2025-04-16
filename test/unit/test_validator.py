import unittest

from argp import *
from argp.validator import ValidatorFailOnTypeError


class TestValidator(unittest.TestCase):
    def test_validator(self):
        class Opt:
            a: str = argument('-a', validator=lambda it: len(it) > 0)

        opt = parse_args(Opt(), ['-a=1'])
        self.assertEqual(opt.a, '1')

        with self.assertRaises(RuntimeError):
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

        with self.assertRaises(RuntimeError):
            parse_args(Opt(), ['-a=10,2,3'])

        with self.assertRaises(RuntimeError):
            parse_args(Opt(), ['-b=6,2'])

    def test_validate_on_parse(self):
        class Opt:
            a: str = argument('-a', validator=lambda it: len(it) > 0, validate_on_set=False)

        opt = parse_args(Opt(), ['-a=1'])
        self.assertEqual(opt.a, '1')

        with self.assertRaises(RuntimeError):
            parse_args(Opt(), ['-a='])

        opt.a = '2'
        self.assertEqual(opt.a, '2')
        opt.a = ''
        self.assertEqual(opt.a, '')
        opt.a = None
        self.assertIsNone(opt.a, None)

    def test_validator_with_type_caster(self):
        class Opt:
            a: int = argument('-a', validator=lambda it: it >= 0)

        opt = parse_args(Opt(), ['-a=1'])
        self.assertEqual(opt.a, 1)

        with self.assertRaises(RuntimeError):
            parse_args(Opt(), ['-a=-1'])

        opt.a = 1
        self.assertEqual(opt.a, 1)

        with self.assertRaises(ValueError):
            opt.a = -1

    def test_validate_on_set_on_normal_attr(self):
        class Opt:
            a: str = argument('-a', validator=lambda it: len(it) > 0)

        with self.assertRaises(RuntimeError):
            parse_args(Opt(), ['-a='])

        with self.assertRaises(ValueError):
            Opt().a = ''

    def test_validate_on_set_on_protected_attr(self):
        class Opt:
            _a: str = argument('-a', validator=lambda it: len(it) > 0)

        with self.assertRaises(RuntimeError):
            parse_args(Opt(), ['-a='])

        opt = Opt()
        opt._a = ''
        self.assertEqual(opt._a, '')


class TestValidateBuilder(unittest.TestCase):

    def test_type_error(self):
        class Opt:
            a: str = argument('-a', validator.str)

        opt = Opt()
        with self.assertRaises(ValidatorFailOnTypeError):
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

    def test_str_is_in(self):
        class Opt:
            a: str = argument('-a', validator.str.is_in(['opt1', 'opt2']))

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

    def test_list_element_type(self):
        class Opt:
            a: list[int] = argument('-a', validator.list(int))

        opt = Opt()
        opt.a = []
        opt.a = [1, 2]

        with self.assertRaises(ValueError):
            opt.a = ['a']

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


if __name__ == '__main__':
    unittest.main()
