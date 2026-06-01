import unittest
from pathlib import Path
from typing import Any, Literal
from unittest.mock import patch

from argclz import *
from argclz.core import parse_args

try:
    import numpy as np
except ImportError:
    np = None


class TestValidator(unittest.TestCase):
    """This test case focus on lambda form of validator"""

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

    def test_validator_message_literal_str(self):
        class Opt:
            a: str = argument('-a', validator(lambda _: False, 'fail message'))

        with self.assertRaises(ValueError) as capture:
            Opt().a = ''
        self.assertEqual(capture.exception.args[0],
                         'fail message')

    def test_validator_message_mod_format(self):
        class Opt:
            a: str = argument('-a', validator(lambda _: False, 'fail message : "%s"'))

        with self.assertRaises(ValueError) as capture:
            Opt().a = 'bad'
        self.assertEqual(capture.exception.args[0],
                         'fail message : "bad"')

    def test_validator_message_format(self):
        class Opt:
            a: str = argument('-a', validator(lambda _: False, 'fail message : "{}"'))

        with self.assertRaises(ValueError) as capture:
            Opt().a = 'bad'
        self.assertEqual(capture.exception.args[0],
                         'fail message : "bad"')

    def test_validator_message_callable(self):
        class Opt:
            a: str = argument('-a', validator(lambda _: False, lambda it: f'fail message : "{it}"'))

        with self.assertRaises(ValueError) as capture:
            Opt().a = 'bad'
        self.assertEqual(capture.exception.args[0],
                         'fail message : "bad"')


class TestValidateBuilder(unittest.TestCase):
    """This test case focus on validator builder"""

    # noinspection PyTypeChecker
    def test_type_error(self):
        class Opt:
            a: str = argument('-a', validator.str)

        opt = Opt()
        with self.assertRaises(ValueError):
            opt.a = 1

    # noinspection PyTypeChecker
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

    # noinspection PyUnusedLocal
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

    # noinspection PyTypeChecker
    def test_int_round(self):
        class Opt:
            a: int = argument('-a', validator.int.round(True))
            b: int = argument('-b', validator.int.round(False))

        opt = Opt()
        opt.a = 2
        self.assertEqual(opt.a, 2)
        opt.b = 2
        self.assertEqual(opt.b, 2)

        opt.a = 2.2
        self.assertEqual(opt.a, 2)

        with self.assertRaises(ValueError) as capture:
            opt.b = 2.2
        self.assertEqual(capture.exception.args[0],
                         'not an int : 2.2')

    @unittest.skipIf(np is None, reason='no numpy installed')
    def test_numpy_int(self):
        class Opt:
            a: int = argument('-a', validator.int)

        opt = Opt()
        value = np.int16(16)
        self.assertNotIsInstance(value, int)
        opt.a = value
        self.assertIsInstance(opt.a, int)
        self.assertEqual(opt.a, 16)

    def test_str_upper_case(self):
        class Opt:
            a: str = argument('-a', validator.str.upper(transform=True))
            b: str = argument('-b', validator.str.upper(transform=False))

        opt = Opt()
        opt.a = 'AAA'
        self.assertEqual(opt.a, 'AAA')
        opt.b = 'AAA'
        self.assertEqual(opt.b, 'AAA')

        opt.a = 'aaa'
        self.assertEqual(opt.a, 'AAA')

        with self.assertRaises(ValueError) as capture:
            opt.b = 'aaa'
        self.assertEqual(capture.exception.args[0],
                         'not in UPPER case : "aaa"')

    def test_str_lower_case(self):
        class Opt:
            a: str = argument('-a', validator.str.lower(transform=True))
            b: str = argument('-b', validator.str.lower(transform=False))

        opt = Opt()
        opt.a = 'aaa'
        self.assertEqual(opt.a, 'aaa')
        opt.b = 'aaa'
        self.assertEqual(opt.b, 'aaa')

        opt.a = 'AAA'
        self.assertEqual(opt.a, 'aaa')

        with self.assertRaises(ValueError) as capture:
            opt.b = 'AAA'
        self.assertEqual(capture.exception.args[0],
                         'not in lower case : "AAA"')

    # noinspection PyUnusedLocal,PyRedeclaration
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

    # noinspection PyUnusedLocal,PyRedeclaration
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

    @unittest.skipIf(np is None, reason='no numpy installed')
    def test_numpy_float(self):
        class Opt:
            a: int = argument('-a', validator.float)

        opt = Opt()
        value = np.float32(3.14)
        self.assertNotIsInstance(value, float)
        opt.a = value
        self.assertIsInstance(opt.a, float)
        self.assertEqual(round(opt.a, 2), 3.14)

    def test_list_type(self):
        class Opt:
            a: list[int] = argument('-a')
            b: list[int] = argument('-b', validator.list(int))

        self.assertIs(as_argument(Opt.a).type, int)
        self.assertIs(as_argument(Opt.b).type, int)

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

    # noinspection PyUnusedLocal,PyRedeclaration
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

    # noinspection PyTypeChecker
    def test_list_element_type(self):
        class Opt:
            a: list[int] = argument('-a', validator.list(int))

        opt = Opt()
        opt.a = []
        opt.a = [1, 2]

        with self.assertRaises(ValueError):
            opt.a = ['a']

    # noinspection PyTypeChecker
    def test_list_type_append_element(self):
        class Opt:
            a: list[int] = argument('-a', action='append', validator=validator.list(int))

        opt = Opt()
        with self.subTest('setattr'):
            opt.a = []
            opt.a = [1, 2]

            with self.assertRaises(ValueError):
                opt.a = 1

        with self.subTest('parse_args'):
            self.assertListEqual(parse_args(Opt(), ['-a=1']).a, [1])
            self.assertListEqual(parse_args(Opt(), ['-a=1', '-a=2']).a, [1, 2])

    # noinspection PyTypeChecker
    def test_list_type_extend_element(self):
        class Opt:
            a: list[int] = argument('-a', action='extend', type=list_type(int), validator=validator.list(int))

        opt = Opt()

        with self.subTest('setattr'):
            opt.a = []
            opt.a = [1, 2]

            with self.assertRaises(ValueError):
                opt.a = 1

        with self.subTest('parse_args'):
            self.assertListEqual(parse_args(Opt(), ['-a=1']).a, [1])
            self.assertListEqual(parse_args(Opt(), ['-a=1', '-a=2']).a, [1, 2])
            self.assertListEqual(parse_args(Opt(), ['-a=1,2']).a, [1, 2])
            self.assertListEqual(parse_args(Opt(), ['-a=1,2', '-a=3']).a, [1, 2, 3])

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

    # noinspection PyTypeChecker
    def test_list_auto_casting(self):
        class Opt:
            a: list[str] = argument('-a', validator.list(str).auto_casting(True))
            b: list[str] = argument('-a', validator.list(str).auto_casting(False))

        opt = Opt()
        opt.a = ['A', 'B']
        self.assertListEqual(opt.a, ['A', 'B'])
        opt.b = ['A', 'B']
        self.assertListEqual(opt.b, ['A', 'B'])

        opt.a = ('A', 'B')
        self.assertListEqual(opt.a, ['A', 'B'])

        with self.assertRaises(ValueError) as capture:
            opt.b = ('A', 'B')
        self.assertEqual(capture.exception.args[0],
                         "not a list : ('A', 'B')")

        ## set does not preserve ordering?
        # opt.a = {'A', 'B'}
        # self.assertTupleEqual(opt.a, ('A', 'B'))

        opt.a = {'A': 1, 'B': 2}
        self.assertListEqual(opt.a, ['A', 'B'])

    def test_list_item_transform(self):
        class Opt:
            a: list[str] = argument('-a', validator.list(str).on_item(validator.str.upper(transform=True)))

        opt = Opt()
        opt.a = ['A', 'B', 'C']
        self.assertListEqual(opt.a, ['A', 'B', 'C'])
        opt.a = ['a', 'b', 'c']
        self.assertListEqual(opt.a, ['A', 'B', 'C'])

    def test_tuple_type(self):
        class Opt:
            a: tuple[int, int] = argument('-a')
            b: tuple[int, int] = argument('-b', validator.tuple(int, int))

        self.assertIs(as_argument(Opt.a).type, tuple)

        f = as_argument(Opt.b).type
        self.assertNotEqual(f, tuple)
        self.assertTrue(str(f).startswith('<function tuple_type.<locals>._type at '))
        self.assertTupleEqual(f('1,2'), (1, 2))

    # noinspection PyTypeChecker
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

    # noinspection PyTypeChecker
    def test_tuple_type_fix_length(self):
        class Opt:
            a: tuple[int, int] = argument('-a', validator.tuple(2, int))

        opt = Opt()
        opt.a = (1, 2)

        with self.assertRaises(ValueError):
            opt.a = ()

        with self.assertRaises(ValueError):
            opt.a = [1, 2]

        with self.assertRaises(ValueError):
            opt.a = (1,)

        with self.assertRaises(ValueError):
            opt.a = (1, 2, 3)

    # noinspection PyTypeChecker
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

    def test_tuple_in_range(self):
        class Opt:
            a: tuple[str, ...] = argument('-a', validator.tuple().length_in_range(2, None))
            b: tuple[str, ...] = argument('-a', validator.tuple().length_in_range(None, 2))
            c: tuple[str, ...] = argument('-a', validator.tuple().length_in_range(2, 4))

        opt = Opt()
        opt.a = ('1', '2', '3')
        opt.b = ()
        opt.b = ('1',)
        opt.c = ('1', '2')

        with self.assertRaises(ValueError):
            opt.a = ()
        with self.assertRaises(ValueError):
            opt.c = ()

    # noinspection PyUnusedLocal,PyRedeclaration
    def test_tuple_in_range_error(self):
        class Opt:
            a: tuple[str, ...] = argument('-a', validator.tuple().length_in_range(2, 3))
            b: tuple[str, ...] = argument('-a', validator.tuple(...).length_in_range(2, 3))

        with self.assertRaises(RuntimeError):
            class Opt:
                a: tuple[str, ...] = argument('-a', validator.tuple(2).length_in_range(2, 3))

        with self.assertRaises(RuntimeError):
            class Opt:
                a: tuple[str, ...] = argument('-a', validator.tuple(2, ...).length_in_range(2, 3))

        with self.assertRaises(RuntimeError):
            class Opt:
                a: tuple[str, ...] = argument('-a', validator.tuple(int).length_in_range(2, 3))

        with self.assertRaises(RuntimeError):
            class Opt:
                a: tuple[str, ...] = argument('-a', validator.tuple(int, ...).length_in_range(2, 3))

    # noinspection PyTypeChecker
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
            a: tuple[Any, ...] = argument(
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

    def test_tuple_multiple_element_validating(self):
        class Opt:
            a: tuple[str, int, str, int] = argument(
                '-a',
                validator.tuple(str, int, str, int)
                .on_item((0, 2), validator.str.length_in_range(None, 2))
                .on_item((1, 3), validator.int.in_range(0, 10))
            )

        opt = Opt()
        opt.a = ('', 0, '1', 1)

        with self.assertRaises(ValueError) as capture:
            opt.a = ('1234', 0, '1', 1)
        self.assertEqual(capture.exception.args[0],
                         'at index 0, str length over 2: "1234"')

        with self.assertRaises(ValueError) as capture:
            opt.a = ('', 100, '1', 1)
        self.assertEqual(capture.exception.args[0],
                         'at index 1, value out of range [0, 10]: 100')

        with self.assertRaises(ValueError) as capture:
            opt.a = ('1', 0, '1234', 1)
        self.assertEqual(capture.exception.args[0],
                         'at index 2, str length over 2: "1234"')

        with self.assertRaises(ValueError) as capture:
            opt.a = ('', 1, '1', 100)
        self.assertEqual(capture.exception.args[0],
                         'at index 3, value out of range [0, 10]: 100')

        # TODO how to handle multiple failure?
        with self.assertRaises(ValueError) as capture:
            opt.a = ('', 1000, '1234', 1)  # validator.str comes first
        self.assertEqual(capture.exception.args[0],
                         'at index 2, str length over 2: "1234"')

    # noinspection PyTypeChecker
    def test_tuple_n_element_validating(self):
        class Opt:
            a: tuple[str, int, float] = argument(
                '-a',
                validator.tuple(3)
                .on_item(0, validator.str.length_in_range(None, 2))
                .on_item(1, validator.int.in_range(0, 10))
            )

        opt = Opt()
        opt.a = ('', 0, 0.0)

        with self.assertRaises(ValueError) as capture:
            opt.a = ('',)
        self.assertEqual(capture.exception.args[0],
                         "length not match to 3 : ('',)")

        with self.assertRaises(ValueError) as capture:
            opt.a = ('', 1)
        self.assertEqual(capture.exception.args[0],
                         "length not match to 3 : ('', 1)")

        with self.assertRaises(ValueError) as capture:
            opt.a = ('', 1, 2.0, False)
        self.assertEqual(capture.exception.args[0],
                         "length not match to 3 : ('', 1, 2.0, False)")

        with self.assertRaises(ValueError) as capture:
            opt.a = ('1234', 0, 0.0)
        self.assertEqual(capture.exception.args[0],
                         'at index 0, str length over 2: "1234"')

        with self.assertRaises(ValueError) as capture:
            opt.a = ('12', 100, 0.0)
        self.assertEqual(capture.exception.args[0],
                         'at index 1, value out of range [0, 10]: 100')

    # noinspection PyTypeChecker
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
            opt.a = ('a',)
        with self.assertRaises(ValueError):
            opt.a = (0, 'b')

    # noinspection PyTypeChecker
    def test_tuple_auto_casting(self):
        class Opt:
            a: tuple[str, ...] = argument('-a', validator.tuple(str, ...).auto_casting(True))
            b: tuple[str, ...] = argument('-a', validator.tuple(str, ...).auto_casting(False))

        opt = Opt()
        opt.a = ('A', 'B')
        self.assertTupleEqual(opt.a, ('A', 'B'))
        opt.b = ('A', 'B')
        self.assertTupleEqual(opt.b, ('A', 'B'))

        opt.a = ['A', 'B']
        self.assertTupleEqual(opt.a, ('A', 'B'))

        with self.assertRaises(ValueError) as capture:
            opt.b = ['A', 'B']
        self.assertEqual(capture.exception.args[0],
                         "not a tuple : ['A', 'B']")

        ## set does not preserve ordering?
        # opt.a = {'A', 'B'}
        # self.assertTupleEqual(opt.a, ('A', 'B'))

        opt.a = {'A': 1, 'B': 2}
        self.assertTupleEqual(opt.a, ('A', 'B'))

    def test_tuple_item_transform(self):
        class Opt:
            a: tuple[str, str, str] = argument(
                '-a',
                validator.tuple(3, str)
                .on_item(0, validator.str.upper(transform=True))
                .on_item(1, validator.str.lower(transform=True)))

        opt = Opt()
        opt.a = ('A', 'B', 'C')
        self.assertTupleEqual(opt.a, ('A', 'b', 'C'))
        opt.a = ('a', 'b', 'c')
        self.assertTupleEqual(opt.a, ('A', 'b', 'c'))

    # noinspection PyTypeChecker
    def test_dict(self):
        class Opt:
            a: dict[str, int] = argument('-a', validator.dict(int))

        opt = Opt()
        opt.a = {}
        opt.a = {'a': 1}
        opt.a = {'a': 1, 'b': 2}

        with self.assertRaises(ValueError) as capture:
            opt.a = {'a': '1'}
        self.assertEqual(capture.exception.args[0],
                         'wrong element type for key "a" : 1')

    def test_dict_type(self):
        class Opt:
            a: dict[str, int] = argument('-a')
            b: dict[str, int] = argument('-b', validator.dict(int))

        self.assertIs(as_argument(Opt.a).type, dict)

        f = as_argument(Opt.b).type
        self.assertNotEqual(f, dict)
        self.assertIsInstance(f, dict_type)
        self.assertDictEqual(f('a=1'), {'a': 1})

    def test_dict_non_empty(self):
        class Opt:
            a: dict[str, int] = argument('-a', validator.dict(int).allow_empty(False))

        opt = Opt()
        opt.a = {'a': 1}
        opt.a = {'a': 1, 'b': 2}

        with self.assertRaises(ValueError) as capture:
            opt.a = {}
        self.assertEqual(capture.exception.args[0],
                         'empty dict : {}')

    def test_dict_on_restricted_keyset(self):
        class Opt:
            a: dict[str, int] = argument('-a', validator.dict(int).allow_keys(['A', 'B', 'C']))

        opt = Opt()
        opt.a = {}
        opt.a = {'A': 1}
        opt.a = {'A': 1, 'B': 2}
        opt.a = {'A': 1, 'B': 2, 'C': 3}
        opt.a = {'B': 2, 'C': 3}

        with self.assertRaises(ValueError) as capture:
            opt.a = {'B': 2, 'D': 3}
        self.assertEqual(capture.exception.args[0],
                         'key "D" is not allowed')

    # noinspection PyUnusedLocal
    def test_dict_on_empty_allow_keyset(self):
        with self.assertRaises(ValueError):
            class Opt:
                a: dict[str, int] = argument('-a', validator.dict(int).allow_keys([]))

    def test_dict_on_restricted_keyset_dropping(self):
        class Opt:
            a: dict[str, int] = argument('-a', validator.dict(int).allow_keys(['A', 'B', 'C'], drop_key=True))

        opt = Opt()

        with self.subTest('normal case'):
            opt.a = {}
            opt.a = {'A': 1, 'B': 2}
            opt.a = {'B': 2, 'D': 3}
            self.assertDictEqual(opt.a, {'B': 2})

        with self.subTest('modify case'):
            ori = {'B': 2, 'D': 3}
            opt.a = ori
            self.assertDictEqual(opt.a, {'B': 2})
            self.assertDictEqual(ori, {'B': 2, 'D': 3})  # ori is not changed

    def test_dict_on_key_completion(self):
        class Opt:
            a: dict[str, int] = argument('-a', validator.dict(int).allow_keys(['AAA', 'BBB', 'CCC'], complete=True))

        opt = Opt()

        with self.subTest('normal case'):
            opt.a = {}
            self.assertDictEqual(opt.a, {})
            opt.a = {'A': 1}
            self.assertDictEqual(opt.a, {'AAA': 1})
            opt.a = {'A': 1, 'B': 2}
            self.assertDictEqual(opt.a, {'AAA': 1, 'BBB': 2})
            opt.a = {'A': 1, 'B': 2, 'C': 3}
            self.assertDictEqual(opt.a, {'AAA': 1, 'BBB': 2, 'CCC': 3})

        with self.subTest('modify case'):
            ori = {'A': 1, 'B': 2, 'C': 3}
            opt.a = ori

            expect = {'AAA': 1, 'BBB': 2, 'CCC': 3}
            self.assertDictEqual(opt.a, expect)
            self.assertDictEqual(ori, {'A': 1, 'B': 2, 'C': 3})  # ori is not changed

    def test_dict_on_key_completion_case_insensitive(self):
        class Opt:
            a: dict[str, int] = argument('-a', validator.dict(int).allow_keys(['AAA', 'BBB', 'CCC'], complete=True, case_sensitive=False))

        opt = Opt()
        opt.a = {}
        self.assertDictEqual(opt.a, {})
        opt.a = {'a': 1}
        self.assertDictEqual(opt.a, {'AAA': 1})
        opt.a = {'a': 1, 'b': 2}
        self.assertDictEqual(opt.a, {'AAA': 1, 'BBB': 2})
        opt.a = {'a': 1, 'b': 2, 'c': 3}
        self.assertDictEqual(opt.a, {'AAA': 1, 'BBB': 2, 'CCC': 3})

    def test_dict_on_key_setting_chain(self):
        class Opt:
            a: dict[str, int] = argument(
                '-a', validator.dict(int) \
                    .allow_keys(['AAA', 'BBB', 'CCC'])
                    .allow_keys(complete=True))

        opt = Opt()
        opt.a = {'A': 1}
        self.assertDictEqual(opt.a, {'AAA': 1})

    # noinspection PyTypeChecker
    def test_dict_on_key_with_literal_type(self):
        class Opt:
            MODE = Literal['AAA', 'BBB', 'CCC']
            a: dict[MODE, int] = argument('-a', validator.dict(int).allow_keys(MODE, complete=True, case_sensitive=False))

        opt = Opt()
        opt.a = {}
        self.assertDictEqual(opt.a, {})
        opt.a = {'a': 1}
        self.assertDictEqual(opt.a, {'AAA': 1})
        opt.a = {'a': 1, 'b': 2}
        self.assertDictEqual(opt.a, {'AAA': 1, 'BBB': 2})
        opt.a = {'a': 1, 'b': 2, 'c': 3}
        self.assertDictEqual(opt.a, {'AAA': 1, 'BBB': 2, 'CCC': 3})

    # noinspection PyUnusedLocal,PyRedeclaration
    def test_dict_on_key_with_literal_type_but_contain_bad_key(self):
        with self.assertRaises(ValueError):
            class Opt:
                MODE = Literal['AAA', 'BBB', 'CCC', None]  # non-None
                a: dict[MODE, int] = argument('-a', validator.dict(int).allow_keys(MODE))

        with self.assertRaises(ValueError):
            class Opt:
                MODE = Literal['AAA', 'BBB', 'CCC', 1]  # only str
                a: dict[MODE, int] = argument('-a', validator.dict(int).allow_keys(MODE))

    def test_dict_on_key_completion_but_duplicated(self):
        class Opt:
            a: dict[str, int] = argument('-a', validator.dict(int).allow_keys(['AAA', 'BBB', 'CCC'], complete=True))

        opt = Opt()
        with self.assertRaises(ValueError) as capture:
            opt.a = {'A': 1, 'AA': 2, 'AAA': 3}
        self.assertEqual(capture.exception.args[0],
                         'duplicated key : "A" and "AAA"')

    def test_dict_with_key_checking(self):
        class Opt:
            a: dict[str, int] = argument('-a', validator.dict(int).on_key(lambda it: 'A' in it))

        opt = Opt()
        opt.a = {'A': 1}
        opt.a = {'AA': 1}

        with self.assertRaises(ValueError) as capture:
            opt.a = {'B': 1}
        self.assertEqual(capture.exception.args[0],
                         "at key B, validate fail : {'B': 1}")

    def test_dict_with_key_checking_with_message(self):
        class Opt:
            a: dict[str, int] = argument('-a', validator.dict(int).on_key(validator(lambda it: 'A' in it, 'does not contain A')))

        opt = Opt()
        opt.a = {'A': 1}
        opt.a = {'AA': 1}

        with self.assertRaises(ValueError) as capture:
            opt.a = {'B': 1}
        self.assertEqual(capture.exception.args[0],
                         'at key B, does not contain A')

    def test_dict_with_value_checking(self):
        class Opt:
            a: dict[str, int] = argument('-a', validator.dict(int).on_value(validator.int.positive()))

        opt = Opt()
        opt.a = {}
        opt.a = {'A': 1}

        with self.assertRaises(ValueError) as capture:
            opt.a = {'A': 1, 'B': -1}
        self.assertEqual(capture.exception.args[0],
                         'at key B, not a non-negative value : -1')

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

    def test_path_file_system(self):
        class Opt:
            p: Path = argument('-f', validator.path.is_exists())
            f: Path = argument('-f', validator.path.is_file())
            d: Path = argument('-d', validator.path.is_dir())

        def exists(self):
            return self.name == "123.txt"

        def is_file(self):
            return self.name == "123.txt"

        def is_dir(self):
            return self.name == "123"

        opt = Opt()
        with self.subTest('is_exists'):
            with patch.object(Path, 'exists', new=exists):
                opt.p = Path('123.txt')

                with self.assertRaises(ValueError) as capture:
                    opt.p = Path('456.txt')
                self.assertEqual(capture.exception.args[0],
                                 'path is not exist: 456.txt')

        with self.subTest('is_file'):
            with patch.object(Path, 'is_file', new=is_file):
                opt.f = Path('123.txt')

                with self.assertRaises(ValueError) as capture:
                    opt.f = Path('456.txt')
                self.assertEqual(capture.exception.args[0],
                                 'path is not a file: 456.txt')

        with self.subTest('is_dir'):
            with patch.object(Path, 'is_dir', new=is_dir):
                opt.d = Path('123/')

                with self.assertRaises(ValueError) as capture:
                    opt.d = Path('456/')
                self.assertEqual(capture.exception.args[0],
                                 'path is not a directory: 456')

    # noinspection PyTypeChecker
    def test_path_casting(self):
        class Opt:
            a: Path = argument('-a', validator.path)

        opt = Opt()
        opt.a = '123.txt'
        self.assertIsInstance(opt.a, Path)
        self.assertEqual(str(opt.a), '123.txt')

    # noinspection PyTypeChecker
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

    # noinspection PyTypeChecker
    def test_empty_any(self):
        class Opt:
            a: str = argument('-a', validator.any())

        opt = Opt()
        opt.a = 0
        opt.a = ''

    def test_any_oper(self):
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

    # noinspection PyTypeChecker
    def test_any_then_or(self):
        class Opt:
            a: int | str = argument('-a', (
                    validator.int.in_range(0, 10) | validator.float.in_range(0, 10) | validator.str.length_in_range(0, 10)
            ))

        opt = Opt()
        opt.a = 3
        opt.a = 3.0
        opt.a = '123'

    # noinspection PyTypeChecker
    def test_or_then_any(self):
        class Opt:
            a: int | str = argument('-a', (
                    validator.int.in_range(0, 10) | (validator.float.in_range(0, 10) | validator.str.length_in_range(0, 10))
            ))

        opt = Opt()
        opt.a = 3
        opt.a = 3.0
        opt.a = '123'

    def test_or_transform(self):
        class Opt:
            a: int | str = argument(
                '-a',
                validator.int | validator.str.upper(transform=True)
            )

        opt = Opt()
        opt.a = 10
        self.assertEqual(opt.a, 10)
        opt.a = 'AAA'
        self.assertEqual(opt.a, 'AAA')
        opt.a = 'aaa'
        self.assertEqual(opt.a, 'AAA')

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

    # noinspection PyTypeChecker
    def test_empty_all(self):
        class Opt:
            a: str = argument('-a', validator.all())

        opt = Opt()
        opt.a = 0
        opt.a = ''

    def test_all_oper(self):
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

    # noinspection PyTypeChecker
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

    # noinspection PyTypeChecker
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

    # noinspection PyTypeChecker
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

    # noinspection PyUnusedLocal
    def test_list_type_but_validator(self):
        with self.assertRaises(TypeError) as capture:
            class Opt:
                a: list[int] = argument('-a', validator.list(validator.int))

    # noinspection PyTypeChecker
    def test_nested_list(self):
        class Opt:
            a: list[tuple[int, list[list[int]]]] = argument(
                '-a',
                validator.list()
                .on_item(validator.tuple(int, None)
                         .on_item(0, validator.int)
                         .on_item(1, validator.list().on_item(validator.list(int)))))

        opt = Opt()
        opt.a = []
        opt.a = [(0, [[0]]), (1, [[1]])]

        with self.assertRaises(ValueError) as capture:
            opt.a = [([[0]])]
        self.assertEqual(capture.exception.args[0],
                         'at index 0, not a tuple : [[0]]')
        with self.assertRaises(ValueError) as capture:
            opt.a = [(0, [0])]
        self.assertEqual(capture.exception.args[0],
                         'at index (0, 1, 0), not a list : 0')

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

    # noinspection PyTypeChecker
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
        self.assertEqual(capture.exception.args[0],
                         'length not match to 2 : (0,)')

        with self.assertRaises(ValueError) as capture:
            opt.a = (0, 1, 2)
        self.assertEqual(capture.exception.args[0],
                         'length not match to 2 : (0, 1, 2)')

        opt.a = ('0', '1')

    # noinspection PyTypeChecker
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
        self.assertEqual(capture.exception.args[0],
                         'at index 0, not an int : 0')

    # noinspection PyUnusedLocal
    def test_tuple_type_but_validator(self):
        with self.assertRaises(TypeError) as capture:
            class Opt:
                a: tuple[int, ...] = argument('-a', validator.tuple(validator.int))

        message = str(capture.exception.args[0])
        self.assertTrue(message.startswith('not a type'))

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
