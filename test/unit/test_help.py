import unittest

from argclz import *
from argclz.core import print_help

RUNNER = ''


class PrintHelpTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global RUNNER

        class Opt(AbstractParser):
            pass

        h = print_help(Opt, None)
        RUNNER = h.split('\n')[0].split(' ')[1]

    def test_print_help_required_argument(self):
        class Opt(AbstractParser):
            a: bool = argument('-a', help='text', required=True)

        h = print_help(Opt, None)
        self.assertEqual(h, f"""\
usage: {RUNNER} [-h] -a

options:
  -h, --help  show this help message and exit
  -a          text
""")

    def test_print_help_empty(self):
        class Opt(AbstractParser):
            pass

        h = print_help(Opt, None)
        self.assertEqual(h, f"""\
usage: {RUNNER} [-h]

options:
  -h, --help  show this help message and exit
""")

    def test_print_help_with_options(self):
        class Opt(AbstractParser):
            a: bool = argument('-a', help='text')

        h = print_help(Opt, None)
        self.assertEqual(h, f"""\
usage: {RUNNER} [-h] [-a]

options:
  -h, --help  show this help message and exit
  -a          text
""")

    def test_print_help_for_alias_argument(self):
        class Opt:
            a: str = aliased_argument('-a', aliases={
                '-b': 'B',
                '-c': 'C',
            }, help='text')

        h = print_help(Opt, None)
        self.assertEqual(h, f"""\
usage: {RUNNER} [-h] [-a A | -b | -c]

options:
  -h, --help  show this help message and exit
  -a A        text
  -b          short for -a=B.
  -c          short for -a=C.
""")

    def test_print_help_with_grouped_arguments(self):
        class Opt:
            a: str = argument('-a', group='group A', help='text for A')
            b: str = argument('-b', group='group A', help='text for B')
            c: str = argument('-c', group='group C', help='text for C')

        h = print_help(Opt, None)
        self.assertEqual(h, f"""\
usage: {RUNNER} [-h] [-a A] [-b B] [-c C]

options:
  -h, --help  show this help message and exit

group A:
  -a A        text for A
  -b B        text for B

group C:
  -c C        text for C
""")

    def test_print_help_with_ex_grouped_arguments(self):
        class Opt:
            a: str = argument('-a', ex_group='group A', help='text for A')
            b: str = argument('-b', ex_group='group A', help='text for B')
            c: str = argument('-c', group='group C', help='text for C')

        h = print_help(Opt, None)
        self.assertEqual(h, f"""\
usage: {RUNNER} [-h] [-a A | -b B] [-c C]

options:
  -h, --help  show this help message and exit
  -a A        text for A
  -b B        text for B

group C:
  -c C        text for C
""")

    def test_print_help_with_named_ex_grouped_arguments(self):
        class Opt:
            a: str = argument('-a', group='group A', ex_group='group A', help='text for A')
            b: str = argument('-b', group='group A', ex_group='group A', help='text for B')
            c: str = argument('-c', group='group C', help='text for C')

        h = print_help(Opt, None)
        self.assertEqual(h, f"""\
usage: {RUNNER} [-h] [-a A | -b B] [-c C]

options:
  -h, --help  show this help message and exit

group A:
  -a A        text for A
  -b B        text for B

group C:
  -c C        text for C
""")

    def test_print_help_with_usage(self):
        class Opt(AbstractParser):
            USAGE = 'test.py [-h] [options]'
            a: bool = argument('-a', help='text')

        h = print_help(Opt, None)
        self.assertEqual(h, """\
usage: test.py [-h] [options]

options:
  -h, --help  show this help message and exit
  -a          text
""")

    def test_print_help_with_usages(self):
        class Opt(AbstractParser):
            USAGE = [
                'test.py [-h]',
                'test.py [-a]',
            ]
            a: bool = argument('-a', help='text')

        h = print_help(Opt, None)
        self.assertEqual(h, """\
usage: test.py [-h]
       test.py [-a]

options:
  -h, --help  show this help message and exit
  -a          text
""")

    def test_print_help_with_description(self):
        class Opt(AbstractParser):
            DESCRIPTION = 'text'

        h = print_help(Opt, None)
        self.assertEqual(h, f"""\
usage: {RUNNER} [-h]

text

options:
  -h, --help  show this help message and exit
""")

    def test_print_help_with_epilog(self):
        class Opt(AbstractParser):
            EPILOG = 'text'

        h = print_help(Opt, None)
        self.assertEqual(h, f"""\
usage: {RUNNER} [-h]

options:
  -h, --help  show this help message and exit

text
""")


if __name__ == '__main__':
    unittest.main()
