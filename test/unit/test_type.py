import unittest
from pathlib import Path
from typing import Optional, Literal

from argclz import *
from argclz.core import parse_args


class TypeFunctionTest(unittest.TestCase):
    def test_literal_value_type(self):
        self.assertEqual(True, literal_value_type('true'))
        self.assertEqual(True, literal_value_type('TRUE'))
        self.assertEqual(False, literal_value_type('false'))
        self.assertEqual(False, literal_value_type('False'))
        self.assertEqual(0, literal_value_type('0'))
        self.assertEqual(10, literal_value_type('10'))
        self.assertEqual(10.0, literal_value_type('10.0'))
        self.assertEqual(1e3, literal_value_type('1e3'))
        self.assertEqual('abc', literal_value_type('abc'))
        with self.assertRaises(TypeError):
            bool_type(True)
        with self.assertRaises(TypeError):
            bool_type(False)
        with self.assertRaises(TypeError):
            bool_type(0)

    def test_bool_type(self):
        self.assertTrue(bool_type('+'))
        self.assertTrue(bool_type('1'))
        self.assertTrue(bool_type('t'))
        self.assertTrue(bool_type('true'))
        self.assertTrue(bool_type('T'))
        self.assertTrue(bool_type('TRUE'))
        self.assertTrue(bool_type('yes'))
        self.assertTrue(bool_type('Yes'))
        self.assertTrue(bool_type('YES'))
        self.assertTrue(bool_type('y'))
        self.assertTrue(bool_type('Y'))
        self.assertTrue(bool_type('on'))
        self.assertTrue(bool_type('On'))
        self.assertTrue(bool_type('ON'))
        self.assertTrue(bool_type('enable'))
        self.assertTrue(bool_type('Enable'))
        self.assertFalse(bool_type('-'))
        self.assertFalse(bool_type('0'))
        self.assertFalse(bool_type('f'))
        self.assertFalse(bool_type('F'))
        self.assertFalse(bool_type('false'))
        self.assertFalse(bool_type('False'))
        self.assertFalse(bool_type('FALSE'))
        self.assertFalse(bool_type('n'))
        self.assertFalse(bool_type('no'))
        self.assertFalse(bool_type('No'))
        self.assertFalse(bool_type('NO'))
        self.assertFalse(bool_type('x'))
        self.assertFalse(bool_type('X'))
        self.assertFalse(bool_type('off'))
        self.assertFalse(bool_type('Off'))
        self.assertFalse(bool_type('OFF'))
        self.assertFalse(bool_type('disable'))
        self.assertFalse(bool_type('Disable'))
        with self.assertRaises(ValueError):
            bool_type('other')
        with self.assertRaises(TypeError):
            bool_type(True)
        with self.assertRaises(TypeError):
            bool_type(False)

    def test_tuple_type(self):
        self.assertTupleEqual(('a', 1, True), tuple_type(str, int, bool_type)('a,1,y'))

        with self.assertRaises(ValueError):
            tuple_type()

    def test_tuple_type_index_error(self):
        t = tuple_type(int, int)

        self.assertTupleEqual((1, 2), t('1,2'))

        with self.assertRaises(ValueError):
            t('')
        with self.assertRaises(ValueError):
            t('1')
        with self.assertRaises(ValueError):
            t('1,2,3')

    def test_tuple_type_var_length(self):
        t = tuple_type(int, ...)
        self.assertTupleEqual((), t(''))
        self.assertTupleEqual((1,), t('1'))
        self.assertTupleEqual((1, 2), t('1,2'))
        self.assertTupleEqual((1, 2, 3), t('1,2,3'))

        with self.assertRaises(ValueError):
            tuple_type(...)

        with self.assertRaises(ValueError):
            tuple_type(..., int)

        with self.assertRaises(ValueError):
            tuple_type(int, ..., int)

        with self.assertRaises(ValueError):
            tuple_type(int, ..., ...)

    def test_list_type(self):
        self.assertListEqual([], list_type(int)(''))
        self.assertListEqual([1], list_type(int)('1'))
        self.assertListEqual([1, 2, 3], list_type(int)('1,2,3'))
        self.assertListEqual([1, 2, 3], list_type(int, split=':')('1:2:3'))

        with self.assertRaises(ValueError):
            list_type(str, split='')
        with self.assertRaises(ValueError):
            list_type(str, split=',,')

    def test_list_type_prepend(self):
        self.assertListEqual([], list_type(int, prepend=[0])(''))
        self.assertListEqual([1, 2, 3], list_type(int, prepend=[0])('1,2,3'))

        self.assertListEqual([0], list_type(int, prepend=[0])('+,'))
        self.assertListEqual([0, 1, 2, 3], list_type(int, prepend=[0])('+1,2,3'))
        self.assertListEqual([0, 1, 2, 3], list_type(int, prepend=[0])('+,1,2,3'))

        with self.assertRaises(ValueError):
            list_type(int)('++')  # str '+' cast int

    def test_unit_type(self):
        t = union_type(int, float, bool_type)

        self.assertEqual(1, t('1'))
        self.assertEqual(1.1, t('1.1'))
        self.assertEqual(True, t('y'))
        with self.assertRaises(ValueError):
            t('a')

    def test_dict_type(self):
        # dict_type has internal structure that cannot be invoked repeated.
        # otherwise, it will give unexpected results.

        # we do not test this special behavior here.
        # t = dict_type(int)
        # self.assertDictEqual({'a': 1}, t('a:1'))
        # self.assertDictEqual({'a': 1, 'b': 2}, t('b:2'))

        self.assertDictEqual({}, dict_type(int)(''))
        self.assertDictEqual({'a': 1}, dict_type(int)('a=1'))

        with self.assertRaises(ValueError):
            dict_type(int)('a')

        self.assertDictEqual({'a': '1'}, dict_type(str)('a=1'))
        self.assertDictEqual({'a': ''}, dict_type(str)('a'))

        self.assertDictEqual({'a': '1'}, dict_type(None)('a=1'))
        self.assertDictEqual({'a': None}, dict_type(None)('a'))

    def test_dict_type_with_kv_split(self):
        self.assertDictEqual({'a': 1}, dict_type(int, kv_split='=')('a=1'))
        self.assertDictEqual({'a': 1}, dict_type(int, kv_split=':')('a:1'))
        self.assertDictEqual({'a=1': ''}, dict_type(str, kv_split=':')('a=1'))
        self.assertDictEqual({'a=1': None}, dict_type(try_int_type, kv_split=':')('a=1'))

    def test_dict_type_with_split(self):
        self.assertDictEqual({}, dict_type(int, split=',')(''))
        self.assertDictEqual({'a': 1, 'b': 2}, dict_type(int, split=',')('a=1,b=2'))
        self.assertDictEqual({'a': 1, 'b': 2}, dict_type(int, split=',')('a=1,,b=2'))
        self.assertDictEqual({'a': '1', 'b': '2', 'c': ''}, dict_type(str, split=',')('a=1,c,b=2'))
        self.assertDictEqual({'a': 1, 'b': 2, 'c': None}, dict_type(try_int_type, split=',')('a=1,c,b=2'))

    def test_dict_type_with_wrong_split(self):
        with self.assertRaises(ValueError):
            dict_type(str, split='')
        with self.assertRaises(ValueError):
            dict_type(str, kv_split='')
        with self.assertRaises(ValueError):
            dict_type(str, split=',', kv_split=',')

    def test_slice_type(self):
        self.assertEqual(slice(0, 10), slice_type('0:10'))
        self.assertEqual(slice(None, 10), slice_type(':10'))
        self.assertEqual(slice(10, None), slice_type('10:'))
        self.assertEqual(slice(0, 10, 2), slice_type('0:10:2'))
        self.assertEqual(slice(0, None, 2), slice_type('0::2'))
        self.assertEqual(slice(None, None, 2), slice_type('::2'))

    def test_try_int_type(self):
        self.assertEqual(None, try_int_type(''))
        self.assertEqual(0, try_int_type('0'))
        self.assertEqual('0.0', try_int_type('0.0'))
        self.assertEqual('1.2', try_int_type('1.2'))
        self.assertEqual('abc', try_int_type('abc'))

    def test_try_float_type(self):
        self.assertEqual(None, try_float_type(''))
        self.assertEqual(0.0, try_float_type('0'))
        self.assertEqual(1.2, try_float_type('1.2'))
        self.assertEqual('abc', try_float_type('abc'))

    def test_literal_type(self):
        tt = [
            ('literal_type[list]', literal_type(['AAA', 'BBB', 'CCC'])),
            ('literal_type[Literal]', literal_type(Literal['AAA', 'BBB', 'CCC'])),
        ]

        for message, t in tt:
            with self.subTest(message):
                self.assertEqual('AAA', t('AAA'))
                self.assertEqual('BBB', t('BBB'))
                self.assertEqual('CCC', t('CCC'))
                with self.assertRaises(ValueError):
                    t('DDD')
                with self.assertRaises(ValueError):
                    t('')

    def test_literal_type_case_insensitive(self):
        t = literal_type(['AAA', 'BBB', 'CCC'], case_sensitive=False)

        self.assertEqual('AAA', t('aaa'))
        self.assertEqual('BBB', t('bbb'))

    def test_literal_type_unique(self):
        with self.assertRaises(ValueError):
            literal_type(['AAA', 'AAA'])

        with self.assertRaises(ValueError):
            literal_type(['AAA', 'aaa'], case_sensitive=False)

    def test_literal_type_optional(self):
        t = literal_type(['AAA', 'BBB', None])
        self.assertEqual('AAA', t('AAA'))
        self.assertEqual('BBB', t('BBB'))
        self.assertEqual(None, t(''))
        with self.assertRaises(ValueError):
            t('DDD')

        t = literal_type(['AAA', 'BBB', ''])
        self.assertEqual('', t(''))

    def test_literal_type_of_non_str_types(self):
        with self.assertRaises(ValueError):
            literal_type([1])
        with self.assertRaises(ValueError):
            literal_type(Literal[1])

    def test_literal_type_complete(self):
        t = literal_type(['AAA', 'BBB', 'CCC'], complete=True)
        self.assertEqual('AAA', t('A'))
        self.assertEqual('BBB', t('B'))
        self.assertEqual('CCC', t('C'))
        with self.assertRaises(ValueError):
            t('D')
        with self.assertRaises(ValueError):
            t('')

    def test_literal_type_complete_case_insensitive(self):
        t = literal_type(['AAA', 'BBB', 'CCC'], complete=True, case_sensitive=False)
        self.assertEqual('AAA', t('a'))
        self.assertEqual('BBB', t('b'))
        self.assertEqual('CCC', t('c'))
        with self.assertRaises(ValueError):
            t('d')
        with self.assertRaises(ValueError):
            t('')

    def test_literal_type_complete_confuse(self):
        t = literal_type(['AAA', 'ABC', 'BBB'], complete=True)
        self.assertEqual('AAA', t('AA'))
        self.assertEqual('ABC', t('AB'))

        with self.assertRaises(ValueError) as capture:
            t('A')
        self.assertEqual(capture.exception.args[0],
                         "'A' is confused for ['AAA', 'ABC']")


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

    def test_literal_complete_case_insensitive(self):
        class Opt:
            a: Literal['AAA', 'BBB'] = argument('-a', type=literal_type(complete=True, case_sensitive=False))

        opt = parse_args(Opt(), ['-a', 'a'])
        self.assertEqual(opt.a, 'AAA')

    def test_literal_candidate_confusion(self):
        class Opt:
            a: Literal['AAA', 'BBB'] = argument('-a', type=literal_type(['CCC', 'DDD']))

        with self.assertRaises(RuntimeError) as capture:
            # raise from argparse choices checking
            parse_args(Opt(), ['-a', 'CCC'])
        self.assertEqual(capture.exception.args[0], "exit 2: argument -a: invalid choice: 'CCC' (choose from AAA, BBB)")

        with self.assertRaises(RuntimeError) as capture:
            # raise from literal_type validation
            parse_args(Opt(), ['-a', 'AAA'])
        self.assertEqual(capture.exception.args[0], "exit 2: argument -a: invalid Literal[CCC, DDD] value: 'AAA'")

    def test_literal_candidate_confusion_cancelled(self):
        class Opt:
            # add `choices` to force unset choices.
            a: Literal['AAA', 'BBB'] = argument('-a', type=literal_type(['CCC', 'DDD']), choices=None)

        opt = parse_args(Opt(), ['-a', 'CCC'])
        self.assertEqual(opt.a, 'CCC')

        with self.assertRaises(RuntimeError):
            # raise from literal_type validation
            parse_args(Opt(), ['-a', 'AAA'])

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
        opt = parse_args(Opt(), ['-a=+1,2'])
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

    def test_dict_type(self):
        class Opt:
            a: dict[str, int] = argument('-a', type=dict_type(literal_value_type))

        opt = parse_args(Opt(), ['-a=a=1'])
        self.assertDictEqual(opt.a, {'a': 1})

        opt = parse_args(Opt(), ['-a=a=1', '-a=b:2'])
        self.assertDictEqual(opt.a, {'a': 1, 'b': 2})

        opt = parse_args(Opt(), ['-a=a=1', '-a=b:2', '-a=c'])
        self.assertDictEqual(opt.a, {'a': 1, 'b': 2, 'c': ''})

    def test_dict_type_recall_should_not_append(self):
        class Opt:
            a: dict[str, int] = argument('-a', type=dict_type(int))

        opt = parse_args(Opt(), ['-a=a=1'])
        self.assertDictEqual(opt.a, {'a': 1})

        opt = parse_args(Opt(), ['-a=b=2'])
        self.assertDictEqual(opt.a, {'b': 2})

        opt = parse_args(opt, ['-a=c=3'])
        self.assertDictEqual(opt.a, {'c': 3})

    def test_shared_dict_type(self):
        t = dict_type(int)

        class Opt:
            a: dict[str, int] = argument('-a', type=t)
            b: dict[str, int] = argument('-b', type=t)

        opt = parse_args(Opt(), ['-a=a=1', '-b=b=2'])
        self.assertDictEqual(opt.a, {'a': 1})
        self.assertDictEqual(opt.b, {'b': 2})


if __name__ == '__main__':
    unittest.main()
