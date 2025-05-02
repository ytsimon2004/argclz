Utility usage
=========================
Refer to :mod:`argclz.core`

parse_args
------------------
Parse the provided list of command-line arguments and apply the parsed values to the given instance

refer to :func:`~argclz.core.parse_args()`

- **Example usage**

.. code-block:: python

    from argclz import parse_args

    class Opt(AbstractParser):
        name: str = argument('--name', required=True)
        count: int = argument('--count', type=int, default=1)


    opt = Opt()
    args = ['--name', 'Alice', '--count', '3']  # same as ['--name=Alice', '--count=3']
    parse_args(opt, args)

    print(opt.name)   # Alice
    print(opt.count)  # 3



as_dict
------------------
collect all argument attributes into a dictionary with attribute name to its value

refer to :func:`~argclz.core.as_dict()`

- **Example usage**

.. code-block:: python

    from argclz import as_dict

    class Opt(AbstractParser):
        name: str = argument('--name', default='guest')
        age: int = argument('--age')

    opt = Opt()
    opt.name = 'Alice'
    opt.age = 20

    print(as_dict(opt))

- **Output**

.. code-block:: text

    {'name': 'Alice', 'age': 20}


with_options
------------------
Option class can be composed by inherition. Child option class can also change the value from parent's
argument. As well as disable it (by replacing a value)

refer to :doc:`argument.with_option <../api/_autosummary/argclz.core.Argument.with_option>`

Use together with :func:`~argclz.core.as_argument()`

- **Example usage**

.. code-block:: python

    class Parent(AbstractParser):
        mode: str = argument('--mode', choices=['train', 'test'], default='train')

    class Child(Parent):
        # Override mode to change the default
        mode = as_argument(Parent.mode).with_options(default='test')

    print_help(Child)

- **Output**

.. code-block:: text

  usage: test.py [-h] [--mode {train,test}]

  options:
    -h, --help           show this help message and exit
    --mode {train,test}

with_defaults
------------------
Initialize argument attributes with a proper default.

refer to :func:`~argclz.core.with_defaults()`

Option class can be any class contains :func:`~argclz.core.argument()` or other argument kinds.
The difference between a class inherit from :func:`~argclz.core.AbstractParser` and a class does not is that
the former will initialize its argument attributes when creating via :func:`~argclz.core.with_defaults()`.


.. code-block:: python

    from argclz.core import with_defaults

    class Option:
        a: bool = argument('-a') #1

    print(Option().a) # [2] raise AttributeError
    print(with_defaults(Option()).a) # False

1. A normal class with a bool attribute ``a``, which has a proper default value ``False`` in common sense.
2. An ``AttributeError`` was raised, because attribute is not initialized yet.

