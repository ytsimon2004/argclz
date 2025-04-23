"""
Basic example
=========================

This module provide a way to integrate python ``argparse`` module into class attribute
and annotation type, that allow options have type information, and allow parser combination
easily.

core usage
------------------------------------

argument
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Create an argument attribute

refer to :func:`~argclz.core.argument()`

.. code-block:: python

    from argclz import AbstractParser, argument

    class MyArgs(AbstractParser):

        verbose: bool = argument('--verbose', help='Enable verbose output')

        name: str = argument('-n', '--name', required=True, metavar='NAME', help='Name of the user')

        count: int = argument('--count', default=1, help='Number of times to greet')

        def run(self):
            for _ in range(self.count):
                if self.verbose:
                    print(f"Greeting with enthusiasm: Hello, {self.name}!")
                else:
                    print(f"Hello, {self.name}!")


    if __name__ == '__main__':
        MyArgs().main()  # call run()


**run the script with**

.. prompt:: bash $

    python my_script.py --name Alice --count 3 --verbose

**output**

.. code-block:: text

   Greeting with enthusiasm: Hello, Alice!
   Greeting with enthusiasm: Hello, Alice!
   Greeting with enthusiasm: Hello, Alice!



pos_argument
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Create a positional (non-flag) command-line argument attribute

refer to :func:`~argclz.core.pos_argument()`

.. code-block:: python

    from argclz import AbstractParser, argument

    class MyArgs(AbstractParser):

        filename: str = pos_argument('FILENAME', help='Input file to process')

        def run(self):
          print(f"Processing file: {self.filename}")

**run the script with**

.. prompt:: bash $

    python my_script.py data.npy

**output**

.. code-block:: text

    Processing file: data.npy



var_argument
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Create a variable-length positional argument, suitable for capturing multiple values into a list

refer to :func:`~argclz.core.var_argument()`

.. code-block:: python

    from argclz import AbstractParser, var_argument

    class MyArgs(AbstractParser):

        items: list[str] = var_argument('ITEMS', help='Items to process'

**run the script with**

.. prompt:: bash $

  python script.py apple banana cherry

**output**

.. code-block:: text

  # Resulting value:
  items = ['apple', 'banana', 'cherry']


aliased_argument
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Create an argument that supports shorthand aliases for specific constant values

refer to :func:`~argclz.core.aliased_argument()`

.. code-block:: python

    from argclz import AbstractParser, aliased_argument

    class MyArgs(AbstractParser):

        level: str = aliased_argument(
            '--level',
            aliases={'--low': 'low', '--high': 'high'},
            choices=['low', 'medium', 'high'],
            help='Set the difficulty level'
        )

        def run(self):
            print(f"Level selected: {self.level}")

**run the script with**

.. prompt:: bash $

    python script.py --low

**output**

.. code-block:: text

    Level selected: low

**you can also run**

.. prompt:: bash $

    python script.py --level medium

**output**

.. code-block:: text

    Level selected: medium



type parser
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This module provides utility functions and classes that cast command-line string arguments into typed Python values.
These can be used directly as `type=...` in any argument specification, offering flexible and reusable conversions.

- Example for create a parser that splits a comma-separated string into a typed tuple

.. code-block:: python

    from argclz import AbstractParser, float_tuple_type

    class MyArgs(AbstractParser):

        annotation: tuple[float, ...] = argument(
            '--anno',
            type=float_tuple_type,
            help='annotation values'
        )

        def run(self):
            print(f"annotation values: {self.annotation}")


**run the script with**

.. prompt:: bash $

    python script.py --anno 0.3,0.5,0.9

**output**

.. code-block:: text

    annotation values: 0.3,0.5,0.9

.. seealso ::

    see more types options :mod:`argclz.types`



Validator usage
------------------------------------
The validator system provides a fluent, chainable API for building type-specific validation rules.
It works by defining specialized “builder” classes (e.g., for strings, integers, floats, lists, and tuples)
that let you specify constraints like numeric ranges, string length ranges, regex checks, or container length/item rules


- Example for customed ``lambda``

.. code-block:: python

    from argclz import AbstractParser, argument

    class Opt(AbstractParser):
        # Accepts only even integers
        value: int = argument('-v', validator=lambda it: it % 2 == 0)

    opt = Opt()
    opt.value = 4    # OK
    opt.value = 5    # Raises ValueError


- Example for our buitin validator

.. code-block:: python

    from argclz import AbstractParser, argument, validator

    class Opt(AbstractParser):
        # Accepts only integers in [10, 99]
        value: int = argument('-v', validator.int.in_range(10, 99))

        # Accepts only exited directory
        directory: Path = argument('--path', validator.path.is_dir().is_exists())

    opt = Opt()
    opt.value = 42    # OK
    opt.value = 7     # Raises ValueError

    opt.directory = '*/not_exist/' # Raises ValueError (not exists)
    opt.directory = '*/file.csv' # Raises ValueError (not a dir)


.. seealso ::

    see more validation options :mod:`argclz.validator`


Dispatch usage
------------------------------------

.. seealso ::

    see dispatch usage in :mod:`argclz.dispatch`

TODO DOC


utility usage
------------------------------------
Refer to :mod:`argclz.core`

parse_args
^^^^^^^^^^^^^^^^^^^
Parse the provided list of command-line arguments and apply the parsed values to the given instance

**Example usage**

.. code-block:: python

    from argclz import AbstractParser, argument, parse_args

    class Opt(AbstractParser):
        name: str = argument('--name', required=True)
        count: int = argument('--count', type=int, default=1)


    opt = Opt()
    args = ['--name', 'Alice', '--count', '3']  # same as ['--name=Alice', '--count=3']
    parse_args(opt, args)

    print(opt.name)   # Alice
    print(opt.count)  # 3



as_dict
^^^^^^^^^^^^^^^^^^^
collect all argument attributes into a dictionary with attribute name to its value

**Example usage**

.. code-block:: python

    from argclz import AbstractParser, argument, as_dict

    class Opt(AbstractParser):
        name: str = argument('--name', default='guest')
        age: int = argument('--age')

    opt = Opt()
    opt.name = 'Alice'
    opt.age = 20

    print(as_dict(opt))

**Output**

.. code-block:: text

    {'name': 'Alice', 'age': 20}


with_options
^^^^^^^^^^^^^^^^^^^
Option class can be composed by inherition. Child option class can also change the value from parent's
argument. As well as disable it (by replacing a value)

Use together with :func:`~argclz.core.as_argument()`

.. code-block:: python

    from argclz import AbstractParser, argument, as_argument

    class Parent(AbstractParser):
        mode: str = argument('--mode', choices=['train', 'test'], default='train')

    class Child(Parent):
        # Override mode to change the default
        mode = as_argument(Parent.mode).with_options(default='test')



parse_command_args
^^^^^^^^^^^^^^^^^^^
Parse command-line arguments for subcommands, each associated with a different parser class

**Example usage**

.. code-block:: python

    from argclz import AbstractParser, argument, parse_command_args

    class InitCmd(AbstractParser):

        name: str = argument('--name', required=True)

        def run(self):
            print(f"Initializing project: {self.name}")

    class BuildCmd(AbstractParser):

        release: bool = argument('--release', action='store_true')

        def run(self):
          print("Building in release mode" if self.release else "Building in debug mode")

    parse_command_args(
        {'init': InitCmd, 'build': BuildCmd},
         args=['init', '--name', 'demo']
     )

**Output**

.. code-block:: text

  Initializing project: demo

"""
from ._validator import *
from .clone import *
from .core import (
    AbstractParser,
    argument,
    pos_argument,
    var_argument,
    aliased_argument,
    as_argument,
    copy_argument
)
from .types import *
