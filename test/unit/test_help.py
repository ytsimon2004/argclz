import unittest
from typing import Literal

from argclz import *
from argclz.core import print_help


class PrintHelpTest(unittest.TestCase):

    def test_print_help_required_argument(self):
        class Opt(AbstractParser):
            a: bool = argument('-a', help='text', required=True)

        h = print_help(Opt, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] -a

options:
  -h, --help  show this help message and exit
  -a          text (default: False)
""")

    def test_print_help_empty(self):
        class Opt(AbstractParser):
            pass

        h = print_help(Opt, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h]

options:
  -h, --help  show this help message and exit
""")

    def test_print_help_with_options(self):
        class Opt(AbstractParser):
            a: bool = argument('-a', help='text')

        h = print_help(Opt, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-a]

options:
  -h, --help  show this help message and exit
  -a          text (default: False)
""")

    def test_print_help_with_hidden_options(self):
        class Opt(AbstractParser):
            a: bool = argument('-a', help='text')
            b: bool = argument('-b', help='text', hidden=True)

        h = print_help(Opt, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-a]

options:
  -h, --help  show this help message and exit
  -a          text (default: False)
""")

    def test_print_help_for_alias_argument(self):
        class Opt:
            a: str = aliased_argument('-a', aliases={
                '-b': 'B',
                '-c': 'C',
            }, help='text')

        h = print_help(Opt, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-a A | -b | -c]

options:
  -h, --help  show this help message and exit
  -a A        text
  -b          short for -a=B.
  -c          short for -a=C.
""")

    def test_print_help_with_grouped_arguments(self):
        class Opt:
            g = argument_group('group A', 'group text')
            a: str = argument('-a', group=g, help='text for A')
            b: str = argument('-b', group=g, help='text for B')
            c: str = argument('-c', group='group C', help='text for C')

        h = print_help(Opt, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-a A] [-b B] [-c C]

options:
  -h, --help  show this help message and exit

group A:
  group text

  -a A        text for A
  -b B        text for B

group C:
  -c C        text for C
""")

    def test_print_help_with_unnamed_group(self):
        class Opt:
            g1 = argument_group()
            g2 = argument_group()
            a: str = argument('-a', group=g1, help='text for A')
            b: str = argument('-b', group=g1, help='text for B')
            c: str = argument('-c', group=g2, help='text for C')
            d: str = argument('-d', group=g2, help='text for D')
            e: str = argument('-e', help='text for E')

        h = print_help(Opt, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-e E] [-a A] [-b B] [-c C] [-d D]

options:
  -h, --help  show this help message and exit
  -e E        text for E

  -a A        text for A
  -b B        text for B

  -c C        text for C
  -d D        text for D
""")

    def test_print_help_with_order_grouped_arguments_with_predefined_list(self):
        class Opt(AbstractParser):
            GROUP_A = 'group A'
            GROUP_B = 'group B'
            GROUP_C = 'group C'

            ARGUMENT_GROUP_LIST = [
                GROUP_C, GROUP_A, GROUP_B,
            ]

            a: str = argument('-a', group=GROUP_A, help='text for A')
            b: str = argument('-b', group=GROUP_B, help='text for B')
            c: str = argument('-c', group=GROUP_C, help='text for C')

        with self.subTest('with list'):
            h = print_help(Opt, None, prog='run.py')
            self.assertEqual(h, """\
usage: run.py [-h] [-c C] [-a A] [-b B]

options:
  -h, --help  show this help message and exit

group C:
  -c C        text for C

group A:
  -a A        text for A

group B:
  -b B        text for B
""")

        with self.subTest('without list'):
            Opt.ARGUMENT_GROUP_LIST = None
            h = print_help(Opt, None, prog='run.py')
            self.assertEqual(h, """\
usage: run.py [-h] [-a A] [-b B] [-c C]

options:
  -h, --help  show this help message and exit

group A:
  -a A        text for A

group B:
  -b B        text for B

group C:
  -c C        text for C
""")

    def test_print_help_with_order_grouped_arguments_with_subset_list(self):
        class Opt(AbstractParser):
            GROUP_A = 'group A'
            GROUP_B = 'group B'
            GROUP_C = 'group C'
            GROUP_D = 'group D'

            ARGUMENT_GROUP_LIST = [
                GROUP_B, GROUP_C,
            ]

            a: str = argument('-a', group=GROUP_A, help='text for A')
            b: str = argument('-b', group=GROUP_B, help='text for B')
            c: str = argument('-c', group=GROUP_C, help='text for C')
            d: str = argument('-d', group=GROUP_D, help='text for D')

        h = print_help(Opt, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-b B] [-c C] [-a A] [-d D]

options:
  -h, --help  show this help message and exit

group B:
  -b B        text for B

group C:
  -c C        text for C

group A:
  -a A        text for A

group D:
  -d D        text for D
""")

    def test_print_help_with_order_grouped_arguments_with_callable(self):
        class Opt(AbstractParser):
            GROUP_A = 'group A'
            GROUP_B = 'group B'
            GROUP_C = 'group C'
            GROUP_D = 'group D'

            a: str = argument('-a', group=GROUP_A, help='text for A')
            b: str = argument('-b', group=GROUP_B, help='text for B')
            c: str = argument('-c', group=GROUP_C, help='text for C')
            d: str = argument('-d', group=GROUP_D, help='text for D')

            @classmethod
            def ARGUMENT_GROUP_LIST(cls, group: str) -> int:
                try:
                    return [cls.GROUP_B, cls.GROUP_D].index(group)
                except ValueError:
                    return 1000

        h = print_help(Opt, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-b B] [-d D] [-a A] [-c C]

options:
  -h, --help  show this help message and exit

group B:
  -b B        text for B

group D:
  -d D        text for D

group A:
  -a A        text for A

group C:
  -c C        text for C
""")

    def test_print_help_with_ex_grouped_arguments(self):
        class Opt:
            ex_group = argument_group('Group A', 'Ex Group Text', exclusive=True)
            a: str = ex_group.argument('-a', help='text for A')
            b: str = ex_group.argument('-b', help='text for B')
            c: str = argument('-c', group='group C', help='text for C')

        h = print_help(Opt, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-a A | -b B] [-c C]

options:
  -h, --help  show this help message and exit

Group A:
  Ex Group Text

  -a A        text for A
  -b B        text for B

group C:
  -c C        text for C
""")

    def test_print_help_with_unnamed_ex_grouped_arguments(self):
        class Opt:
            g1 = argument_group(exclusive=True)
            g2 = argument_group()
            a: str = argument('-a', group=g1, help='text for A')
            b: str = argument('-b', group=g1, help='text for B')
            c: str = argument('-c', group=g2, help='text for C')
            d: str = argument('-d', group=g2, help='text for D')
            e: str = argument('-e', help='text for E')

        h = print_help(Opt, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-a A | -b B] [-e E] [-c C] [-d D]

options:
  -h, --help  show this help message and exit
  -a A        text for A
  -b B        text for B
  -e E        text for E

  -c C        text for C
  -d D        text for D
""")

    def test_print_help_with_usage(self):
        class Opt(AbstractParser):
            USAGE = 'test.py [-h] [options]'
            a: bool = argument('-a', help='text')

        h = print_help(Opt, None, prog='run.py')
        self.assertEqual(h, """\
usage: test.py [-h] [options]

options:
  -h, --help  show this help message and exit
  -a          text (default: False)
""")

    def test_print_help_with_usages(self):
        class Opt(AbstractParser):
            USAGE = [
                'test.py [-h]',
                'test.py [-a]',
            ]
            a: bool = argument('-a', help='text')

        h = print_help(Opt, None, prog='run.py')
        self.assertEqual(h, """\
usage: test.py [-h]
       test.py [-a]

options:
  -h, --help  show this help message and exit
  -a          text (default: False)
""")

    def test_print_help_with_description(self):
        class Opt(AbstractParser):
            DESCRIPTION = 'text'

        h = print_help(Opt, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h]

text

options:
  -h, --help  show this help message and exit
""")

    def test_print_help_with_epilog(self):
        class Opt(AbstractParser):
            EPILOG = 'text'

        h = print_help(Opt, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h]

options:
  -h, --help  show this help message and exit

text
""")

    def test_print_help_with_epilog_method(self):
        class Opt(AbstractParser):
            @classmethod
            def EPILOG(cls):
                return 'text'

        h = print_help(Opt, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h]

options:
  -h, --help  show this help message and exit

text
""")

    def test_print_default_bool_value(self):
        class Opt(AbstractParser):
            a: bool = argument('-a', help='A')

        h = print_help(Opt, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-a]

options:
  -h, --help  show this help message and exit
  -a          A (default: False)
""")

    def test_print_default_str_value(self):
        class Opt(AbstractParser):
            a: str = argument('-a', default="", help='A')
            b: str = argument('-b', default=None, help='B')
            c: str = argument('-c', default="default", help='C')
            d: str = argument('-d', help='D')

        h = print_help(Opt, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-a A] [-b B] [-c C] [-d D]

options:
  -h, --help  show this help message and exit
  -a A        A (default: '')
  -b B        B (default: None)
  -c C        C (default: 'default')
  -d D        D
""")

    def test_print_default_int_value(self):
        class Opt(AbstractParser):
            a: int = argument('-a', default=0, help='A')
            b: int = argument('-b', default=100, help='B')
            c: int = argument('-c', help='C')

        h = print_help(Opt, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-a A] [-b B] [-c C]

options:
  -h, --help  show this help message and exit
  -a A        A (default: 0)
  -b B        B (default: 100)
  -c C        C
""")

    def test_print_default_str_value_with_place_holder(self):
        class Opt(AbstractParser):
            a: str = argument('-a', default="", help='A (default={DEFAULT})')
            b: str = argument('-b', default=None, help='B. use default value: {DEFAULT}')

        h = print_help(Opt, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-a A] [-b B]

options:
  -h, --help  show this help message and exit
  -a A        A (default='')
  -b B        B. use default value: None
""")

    def test_print_literal_choices(self):
        class Opt(AbstractParser):
            a: Literal['A', 'B', 'C'] = argument('-a', help='one of them')

        h = print_help(Opt, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-a A|B|C]

options:
  -h, --help  show this help message and exit
  -a A|B|C    one of them
""")

    def test_print_literal_choices_on_declare_instead_of_real_value(self):
        class Opt(AbstractParser):
            a: Literal['A', 'B', 'C'] = argument('-a', type=literal_type(['D', 'E', 'F']), help='one of them')

        h = print_help(Opt, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-a A|B|C]

options:
  -h, --help  show this help message and exit
  -a A|B|C    one of them
""")

    def test_print_literal_for_choices_completion(self):
        class Opt(AbstractParser):
            # `complete=True` should not change the help text, but changing on paring behavior.
            a: Literal['A', 'B', 'C'] = argument('-a', type=literal_type(complete=True), help='one of them')

        h = print_help(Opt, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-a A|B|C]

options:
  -h, --help  show this help message and exit
  -a A|B|C    one of them
""")

    def test_print_dict_type(self):
        class Opt(AbstractParser):
            a: dict[str, int] = argument('-a', type=dict_type(int), help='a dict')

        h = print_help(Opt, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-a Key=Value]

options:
  -h, --help    show this help message and exit
  -a Key=Value  a dict
""")

    def test_print_dict_type_with_custom_kv_split(self):
        class Opt(AbstractParser):
            a: dict[str, int] = argument('-a', type=dict_type(int, kv_split=':'), metavar=('A', 'B'), help='a dict')

        h = print_help(Opt, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-a A:B]

options:
  -h, --help  show this help message and exit
  -a A:B      a dict
""")

    def test_print_dict_type_with_custom_split(self):
        class Opt(AbstractParser):
            a: dict[str, int] = argument('-a', type=dict_type(int, split=','), metavar=('A', 'B'), help='a dict')

        h = print_help(Opt, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-a A=B,...]

options:
  -h, --help  show this help message and exit
  -a A=B,...  a dict
""")


if __name__ == '__main__':
    unittest.main()
