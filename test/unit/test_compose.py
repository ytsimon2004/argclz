import contextlib
import io
import unittest
from typing import Literal

from argclz import *
from argclz.core import foreach_arguments


class ParserClassTest(unittest.TestCase):

    def test_direct_inherit_parser(self):
        class Parent(AbstractParser):
            a: int = argument('-a')

        class Child(Parent):
            pass

        opt = Child()
        args = [it.options for it in foreach_arguments(opt)]
        self.assertListEqual([('-a',)], args)

        ret = opt.main(['-a=1'], parse_only=True)
        self.assertIs(ret, opt)
        self.assertEqual(opt.a, 1)

    def test_overwrite_argument(self):
        class Parent(AbstractParser):
            a: int = argument('-a')

        class Child(Parent):
            a: int = as_argument(Parent.a).with_options(
                type=lambda it: -int(it)
            )

        opt = Parent()
        opt.main(['-a=1'], parse_only=True)
        self.assertEqual(opt.a, 1)

        opt = Child()
        args = [it.options for it in foreach_arguments(opt)]
        self.assertListEqual([('-a',)], args)
        opt.main(['-a=1'], parse_only=True)
        self.assertEqual(opt.a, -1)

    def test_overwrite_on_unknown_attribute(self):
        class Parent(AbstractParser):
            a: int = 1

        with self.assertRaises(TypeError):
            class Child(Parent):
                a: int = as_argument(Parent.a)

    def test_reuse_argument(self):
        class Parent(AbstractParser):
            a: int = argument('-a')

        with self.assertRaises(RuntimeError):
            class Child(Parent):
                b: int = as_argument(Parent.a)

        with self.assertRaises(RuntimeError):
            class Child(Parent):
                b: int = Parent.a

    def test_remove_argument(self):
        class Parent(AbstractParser):
            a: int = argument('-a')
            b: int = argument('-b')

        class Child(Parent):
            b: int = 0

        opt = Parent()
        args = [it.options for it in foreach_arguments(opt)]
        self.assertListEqual([('-a',), ('-b',)], args)

        opt = Child()
        args = [it.options for it in foreach_arguments(opt)]
        self.assertListEqual([('-a',)], args)

        ret = opt.main(['-b=1'], parse_only=True)
        self.assertNotEqual(ret, 0)

    def test_compose_parser(self):
        class Parent1(AbstractParser):
            a: int = argument('-a')

        class Parent2(AbstractParser):
            b: int = argument('-b')

        class Child(Parent1, Parent2):
            pass

        opt = Child()
        args = [it.options for it in foreach_arguments(opt)]
        self.assertSetEqual({('-a',), ('-b',)}, set(args))

    def test_compose_options(self):
        class Parent1:
            a: int = argument('-a')

        class Parent2:
            b: int = argument('-b')

        class Child(AbstractParser, Parent1, Parent2):
            pass

        opt = Child()
        args = [it.options for it in foreach_arguments(opt)]
        self.assertSetEqual({('-a',), ('-b',)}, set(args))

    def test_redeclare_argument(self):
        class Parent(AbstractParser):
            a: str = argument('-a')

        class Child(Parent):
            a: Literal['1', '2'] = as_argument(Parent.a).with_options()

        opt = Parent().main(['-a=1'])
        self.assertEqual(opt.a, '1')
        opt = Parent().main(['-a=3'])
        self.assertEqual(opt.a, '3')

        opt = Child().main(['-a=1'])
        self.assertEqual(opt.a, '1')

        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                Child().main(['-a=3'])


class PrintHelpTest(unittest.TestCase):
    def test_argument_group_ordering_extend(self):
        class Parent(AbstractParser):
            GROUP_A = 'group A'
            GROUP_B = 'group B'
            a: str = argument('-a', group=GROUP_A, help='text for A')
            b: str = argument('-b', group=GROUP_B, help='text for B')
            ARGUMENT_GROUP_LIST = [
                GROUP_B, GROUP_A,
            ]

        class Child(Parent):
            GROUP_C = 'group C'
            GROUP_D = 'group D'
            c: str = argument('-c', group=GROUP_C, help='text for C')
            d: str = argument('-d', group=GROUP_D, help='text for D')
            ARGUMENT_GROUP_LIST = [
                GROUP_D, Parent.GROUP_B, GROUP_C, Parent.GROUP_A
            ]

        h = print_help(Child, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-d D] [-b B] [-c C] [-a A]

options:
  -h, --help  show this help message and exit

group D:
  -d D        text for D

group B:
  -b B        text for B

group C:
  -c C        text for C

group A:
  -a A        text for A
""")

    def test_argument_group_ordering_preset(self):
        class Parent(AbstractParser):
            GROUP_A = 'group A'
            GROUP_B = 'group B'
            GROUP_C = 'group C'
            GROUP_D = 'group D'
            a: str = argument('-a', group=GROUP_A, help='text for A')
            b: str = argument('-b', group=GROUP_B, help='text for B')
            ARGUMENT_GROUP_LIST = [
                'group D', GROUP_B, 'group C', GROUP_A
            ]

        class Child(Parent):
            GROUP_C = 'group C'
            GROUP_D = 'group D'
            c: str = argument('-c', group=GROUP_C, help='text for C')
            d: str = argument('-d', group=GROUP_D, help='text for D')

        h = print_help(Child, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-d D] [-b B] [-c C] [-a A]

options:
  -h, --help  show this help message and exit

group D:
  -d D        text for D

group B:
  -b B        text for B

group C:
  -c C        text for C

group A:
  -a A        text for A
""")

    def test_argument_group_ordering_overwrite(self):
        class Parent(AbstractParser):
            GROUP_A = 'group A'
            GROUP_B = 'group B'
            a: str = argument('-a', group=GROUP_A, help='text for A')
            b: str = argument('-b', group=GROUP_B, help='text for B')

            @classmethod
            def ARGUMENT_GROUP_LIST(cls, group: str) -> int:
                return [
                    cls.GROUP_B, cls.GROUP_A,
                ].index(group)

        class Child(Parent):
            GROUP_C = 'group C'
            GROUP_D = 'group D'
            c: str = argument('-c', group=GROUP_C, help='text for C')
            d: str = argument('-d', group=GROUP_D, help='text for D')

            @classmethod
            def ARGUMENT_GROUP_LIST(cls, group: str) -> int:
                try:
                    return Parent.ARGUMENT_GROUP_LIST(group)
                except ValueError:
                    return 100 + [
                        cls.GROUP_D, cls.GROUP_C,
                    ].index(group)

        h = print_help(Child, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-b B] [-a A] [-d D] [-c C]

options:
  -h, --help  show this help message and exit

group B:
  -b B        text for B

group A:
  -a A        text for A

group D:
  -d D        text for D

group C:
  -c C        text for C
""")

    def test_argument_group_ordering_reassign(self):
        class Parent(AbstractParser):
            GROUP_A = 'group A'
            GROUP_B = 'group B'
            a: str = argument('-a', group=GROUP_A, help='text for A')
            b: str = argument('-b', group=GROUP_B, help='text for B')

            ARGUMENT_GROUP_LIST = [GROUP_B, GROUP_A]

        class Child(Parent):
            GROUP_C = 'group C'
            GROUP_D = 'group D'
            c: str = argument('-c', group=GROUP_C, help='text for C')
            d: str = argument('-d', group=GROUP_D, help='text for D')

            ARGUMENT_GROUP_LIST = [GROUP_D, GROUP_C]
            ARGUMENT_GROUP_LIST = [
                *ARGUMENT_GROUP_LIST, *Parent.ARGUMENT_GROUP_LIST,
            ]

        h = print_help(Child, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-d D] [-c C] [-b B] [-a A]

options:
  -h, --help  show this help message and exit

group D:
  -d D        text for D

group C:
  -c C        text for C

group B:
  -b B        text for B

group A:
  -a A        text for A
""")

    def test_use_parent_group_literal_str(self):
        class Parent(AbstractParser):
            GROUP = 'Parent Group'
            a: str = argument('-a', group=GROUP)

        class Child(Parent):
            b: str = argument('-b', group=Parent.GROUP)

        h = print_help(Child, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-a A] [-b B]

options:
  -h, --help  show this help message and exit

Parent Group:
  -a A
  -b B
""")

    def test_use_parent_group(self):
        class Parent(AbstractParser):
            GROUP = argument_group('Parent Group', 'Group Description')
            a: str = argument('-a', group=GROUP)

        class Child(Parent):
            b: str = argument('-b', group=Parent.GROUP)

        h = print_help(Child, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-a A] [-b B]

options:
  -h, --help  show this help message and exit

Parent Group:
  Group Description

  -a A
  -b B
""")

    def test_use_parent_ex_group(self):
        class Parent(AbstractParser):
            GROUP = argument_group('Parent Group', 'Group Description', exclusive=True)
            a: str = argument('-a', group=GROUP)

        class Child(Parent):
            b: str = argument('-b', group=Parent.GROUP)

        h = print_help(Child, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-a A | -b B]

options:
  -h, --help  show this help message and exit

Parent Group:
  Group Description

  -a A
  -b B
""")

    def test_use_parent_group_modified(self):
        class Parent(AbstractParser):
            GROUP = argument_group('Parent Group', 'Group Description')
            a: str = argument('-a', group=GROUP)

        class Child(Parent):
            # change group description
            GROUP = argument_group('Child Group', 'Group Description from Child')
            # then we need to update all arguments under this group.
            a: str = as_argument(Parent.a).with_options(group=GROUP)
            b: str = argument('-b', group=GROUP)

        # Parent arguments should not be affected.
        h = print_help(Parent, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-a A]

options:
  -h, --help  show this help message and exit

Parent Group:
  Group Description

  -a A
""")

        h = print_help(Child, None, prog='run.py')
        self.assertEqual(h, """\
usage: run.py [-h] [-a A] [-b B]

options:
  -h, --help  show this help message and exit

Child Group:
  Group Description from Child

  -a A
  -b B
""")

if __name__ == '__main__':
    unittest.main()
