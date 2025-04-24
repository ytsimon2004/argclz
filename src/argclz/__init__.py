"""
Basic example
=========================

This module provide a way to integrate python ``argparse`` module into class attribute
and annotation type, that allow options have type information, and allow parser combination
easily.

core usage
------------------------------------

Import ... TODO

.. code-block:: python

    from argclz import *

argument
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Create an argument attribute

refer to :func:`~argclz.core.argument()`

.. code-block:: python

    class MyArgs(AbstractParser): # [1]

        verbose: bool = argument('--verbose', help='Enable verbose output') # [2]
        #        ^^^^ [3]

        name: str = argument('-n', '--name', required=True, metavar='NAME', help='Name of the user')

        count: int = argument('--count', default=1, help='Number of times to greet')

        def run(self): # [4]
            for _ in range(self.count):
                if self.verbose:
                    print(f"Greeting with enthusiasm: Hello, {self.name}!")
                else:
                    print(f"Hello, {self.name}!")


    MyArgs().main()  # [5]

1. TODO why AbstractParser here?
2. TODO why argument here?
3. TODO does bool matter?
4. TODO why run here?
5. call run() TODO wrong description here. not exact call run.

**run the script with -h**

.. code-block:: text

    usage: example_1.py [-h] [--verbose] -n NAME [--count COUNT]

    options:
      -h, --help            show this help message and exit
      --verbose             Enable verbose output
      -n NAME, --name NAME  Name of the user
      --count COUNT         Number of times to greet

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

    class MyArgs(AbstractParser):

        filename: str = pos_argument('FILENAME', help='Input file to process') # [1]

        def run(self):
          print(f"Processing file: {self.filename}")

1. TODO

**run the script with -h**

.. code-block:: text

    TODO

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

    class MyArgs(AbstractParser):

        items: list[str] = var_argument('ITEMS', help='Items to process') # [2]
        #      ^^^^^^^^^ [1]

1. TODO why list[str]
2. TODO why var_argument here

**run the script with -h**

.. code-block:: text

  TODO

**run the script with**

.. prompt:: bash $

  python script.py apple banana cherry

**output**

.. code-block:: text

  # Resulting value:
  items = ['apple', 'banana', 'cherry']

Description
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    class MyArgs(AbstractParser):

        USAGE = '...' # [1]
        DESCRIPTION = '...' # [2]
        EPILOG = '...' # [3]

1. TODO
2. TODO
3. TODO

**run the script with -h**

.. code-block:: text

  TODO

organize arguments
------------------------------------

grouping
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

TODO argument(group)

mutually exclusive grouping
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

TODO argument(ex_group)

advance examples
=========================

different argument kinds
------------------------------------

hidden argument
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

TODO argument(hidden)

aliased_argument
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Create an argument that supports shorthand aliases for specific constant values

refer to :func:`~argclz.core.aliased_argument()`

.. code-block:: python

    class MyArgs(AbstractParser):

        level: str = aliased_argument( # [1]
            '--level',
            aliases={'--low': 'low', '--high': 'high'}, # [2]
            choices=['low', 'medium', 'high'], # [3]
            help='Set the difficulty level'
        )

        def run(self):
            print(f"Level selected: {self.level}")

1. TODO
2. TODO
3. TODO

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

Pass options between classes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

TODO clonable


type parser
------------------------------------
This module provides utility functions and classes that cast command-line string arguments into typed Python values.
These can be used directly as `type=...` in any argument specification, offering flexible and reusable conversions.

- Example for create a parser that splits a comma-separated string into a typed tuple

.. code-block:: python

    class MyArgs(AbstractParser):

        annotation: tuple[float, ...] = argument(
            '--anno',
            type=float_tuple_type, # [1]
            help='annotation values'
        )

        def run(self):
            print(f"annotation values: {self.annotation}")

1. TODO

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


- Example for customized ``lambda``

.. code-block:: python

    class Opt(AbstractParser):
        # Accepts only even integers
        value: int = argument('-v', validator=lambda it: it % 2 == 0)
        #                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ [1]

    opt = Opt()
    opt.value = 4    # OK
    opt.value = 5    # Raises ValueError


1. TODO

- Example for our builtin validator

.. code-block:: python

    class Opt(AbstractParser):
        value: int = argument('-v', validator.int.in_range(10, 99))
        #                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ [1]

        directory: Path = argument('--path', validator.path.is_dir().is_exists())
        #                                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ [2]

    opt = Opt()
    opt.value = 42    # OK
    opt.value = 7     # Raises ValueError

    opt.directory = '*/not_exist/' # Raises ValueError (not exists)
    opt.directory = '*/file.csv' # Raises ValueError (not a dir)


1. Accepts only integers in [10, 99]. TODO
2. Accepts only exited directory. TODO

.. seealso ::

    see more validation options :mod:`argclz.validator`


Dispatch usage
------------------------------------

.. seealso ::

    see dispatch usage in :mod:`argclz.dispatch`

TODO DOC

Compose cli option-classes
------------------------------------

utility usage
------------------------------------
Refer to :mod:`argclz.core`

parse_args
^^^^^^^^^^^^^^^^^^^
Parse the provided list of command-line arguments and apply the parsed values to the given instance

**Example usage**

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
^^^^^^^^^^^^^^^^^^^
collect all argument attributes into a dictionary with attribute name to its value

**Example usage**

.. code-block:: python

    from argclz import as_dict

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

    from argclz import print_help

    class Parent(AbstractParser):
        mode: str = argument('--mode', choices=['train', 'test'], default='train')

    class Child(Parent):
        # Override mode to change the default
        mode = as_argument(Parent.mode).with_options(default='test')

    print_help(Parent)
    print_help(Child)

**Output**

.. code-block:: text

  TODO

parse_command_args
^^^^^^^^^^^^^^^^^^^
Parse command-line arguments for subcommands, each associated with a different parser class

**Example usage**

.. code-block:: python

    from argclz import parse_command_args

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

**run the script with -h**

**Output**

.. code-block:: text

  TODO

"""
from ._validator import *
from .clone import *
from .commands import sub_command_group
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
