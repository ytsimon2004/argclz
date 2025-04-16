import unittest

from argp import *
from argp.core import print_help

RUNNER = ''


class PrintHelpTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global RUNNER

        class Opt(AbstractParser):
            pass

        h = print_help(Opt, None)
        RUNNER = h.split('\n')[0].split(' ')[1]

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
