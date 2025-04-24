import unittest

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
        opt.main(['-a=1'], system_exit=False, parse_only=True)
        self.assertEqual(opt.a, 1)

        opt = Child()
        args = [it.options for it in foreach_arguments(opt)]
        self.assertListEqual([('-a',)], args)
        opt.main(['-a=1'], system_exit=False, parse_only=True)
        self.assertEqual(opt.a, -1)

    def test_reuse_argument(self):
        class Parent(AbstractParser):
            a: int = argument('-a')

        with self.assertRaises(RuntimeError):
            class Child(Parent):
                b: int = as_argument(Parent.a)

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

        ret = opt.main(['-b=1'], system_exit=False, parse_only=True)
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


if __name__ == '__main__':
    unittest.main()
