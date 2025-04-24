"""
Basic example
=========================

This module integrates Python’s ``argparse`` with class-based configuration, allowing
you to declare command-line arguments as class attributes with type annotations. This approach
automatically infers type conversion, supports validators, and makes it easy to compose and reuse parsers.


core usage
------------------------------------

Import the top-level interface

.. code-block:: python

    from argclz import *


argument
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Create an argument attribute

refer to :func:`~argclz.core.argument()`

.. code-block:: python

    class MyArgs(AbstractParser): # [1]

        verbose: bool = argument('--verbose', help='Enable verbose output')
        #        ^^^^ [2] ^^^^^^^ [3]

        name: str = argument('-n', '--name', required=True, metavar='NAME', help='Name of the user')

        count: int = argument('--count', default=1, help='Number of times to greet')

        def run(self): # [4]
            for _ in range(self.count):
                if self.verbose:
                    print(f"Greeting with enthusiasm: Hello, {self.name}!")
                else:
                    print(f"Hello, {self.name}!")


    MyArgs().main()  # [5]

1. :class:`~argclz.core.AbstractParser` provides the base class that defines `.main()` and `.run()` methods,
   and manages automatic argument parsing and attribute injection.
2. When type annotation with ``bool``, the argument automatically becomes a flag, which inferred using ``action='store_true'``
3. :func:`~argclz.core.argument()` creates a command-line argument bound to this attribute.
   Its parameters are passed to `argparse.ArgumentParser.add_argument()`.
4. The ``run()`` method is invoked after arguments are parsed and set on the instance.
   It serves as the main entry point for your script’s logic.
5. This calls ``.main()``, which first parses command-line arguments
   and then automatically calls ``.run()`` if parsing succeeds.

- **run the script with -h**

.. code-block:: text

    usage: my_script.py [-h] [--verbose] -n NAME [--count COUNT]

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

    MyArgs().main()

1. This creates a required positional argument. The `'FILENAME'` string is used as the metavar
shown in help messages and documentation, not the actual variable name.

- **run the script with -h**

.. code-block:: text

    usage: my_script.py [-h] FILENAME

    positional arguments:
      FILENAME    Input file to process

    options:
      -h, --help  show this help message and exit

- **run the script with**

.. prompt:: bash $

    python my_script.py data.npy

- **output**

.. code-block:: text

    Processing file: data.npy



var_argument
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Create a variable-length positional argument, suitable for capturing multiple values into a list

This is useful when your CLI tool expects an arbitrary number of values

refer to :func:`~argclz.core.var_argument()`

.. code-block:: python

    class MyArgs(AbstractParser):

        items: list[str] = var_argument('ITEMS', help='Items to process')
        #      ^^^^^^^^^[1]^^^^^^^^^^^^[2]

1. ``list[str]`` tells the parser to expect multiple values and return them as a list of strings
2. :func:`~argclz.core.var_argument()` creates a positional argument that accepts multiple inputs.
   Internally, it sets ``nargs='*'`` and ``action='extend'`` to gather values into a list.

- **run the script with -h**

.. code-block:: text

    usage: my_script.py [-h] [ITEMS ...]

    positional arguments:
      ITEMS       Items to process

    options:
      -h, --help  show this help message and exit

- **run the script with**

.. prompt:: bash $

  python script.py apple banana cherry

- **output**

.. code-block:: text

  # Resulting value:
  items = ['apple', 'banana', 'cherry']

description
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    class MyArgs(AbstractParser):

        USAGE = 'my_script.py [OPTIONS] FILES...'       # [1]
        DESCRIPTION = 'Process one or more files.'      # [2]
        EPILOG = 'For more information, see our docs.'  # [3]

1. ``USAGE`` overrides the default usage string shown at the top of the help message. You can
   specify a custom format to explain the expected input layout.
2. ``DESCRIPTION`` sets the introductory description text shown before the list of arguments.
   It is displayed in the help output after the usage line.
3. ``EPILOG`` appears at the end of the help message. It’s useful for additional notes, links,
   or examples that don't belong in the main description.

- **run the script with -h**

.. code-block:: text

    usage: my_script.py [OPTIONS] FILES...

    Process one or more files.

    options:
      -h, --help  show this help message and exit

    For more information, see our docs.

organize arguments
------------------------------------

grouping
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can organize related command-line arguments under labeled sections using the ``group=...`` keyword.
This helps structure the help message when you have many options and want to categorize them clearly.
Each ``group`` name creates a new labeled section in the ``--help`` output.


.. code-block:: python

    class MyArgs(AbstractParser):

        GROUP_GENERAL = 'general'
        GROUP_OUTPUT = 'output'

        # Group for general options
        verbose: bool = argument('--verbose', group=GROUP_GENERAL, help='Enable verbose logging')
        config: str = argument('--config', group=GROUP_GENERAL, help='Path to configuration file')

        # Group for output options
        output_dir: str = argument('--output', group=GROUP_OUTPUT, help='Directory to save results')
        overwrite: bool = argument('--overwrite', group=GROUP_OUTPUT, help='Overwrite existing files')

- **run the script with -h**

.. code-block:: text

    usage: my_script.py [-h] [--verbose] [--config CONFIG] [--output OUTPUT_DIR] [--overwrite]

    options:
      -h, --help           show this help message and exit

    general:
      --verbose            Enable verbose logging
      --config CONFIG      Path to configuration file

    output:
      --output OUTPUT_DIR  Directory to save results
      --overwrite          Overwrite existing files

mutually exclusive grouping
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use the ``ex_group=...`` keyword to group arguments into a **mutually exclusive group**,
meaning that only one of the arguments in the group can be specified at a time.

This is useful when two or more options conflict and cannot be used together.

.. code-block:: python

    class MyArgs(AbstractParser):

        output_json: bool = argument('--json', ex_group='output', action='store_true', help='Output as JSON')
        output_yaml: bool = argument('--yaml', ex_group='output', action='store_true', help='Output as YAML')


- **run the script with mutually exclusive options**

.. prompt:: bash $

    python my_script.py --json test.json --yaml test.yaml


.. code-block:: text

    usage: test.py [-h] [--json | --yaml]
    argument --yaml: not allowed with argument --json




Advance examples
=========================

Different argument kinds
------------------------------------

hidden argument
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
You can hide an argument from the help message by passing ``hidden=True``. The argument will still be recognized
and parsed if passed on the command line, but it won't appear in ``--help`` output.

This is useful for developer-only flags, debugging tools, or deprecated options.

.. code-block:: python

    class MyArgs(AbstractParser):

        debug_mode: bool = argument('--debug', hidden=True)

        def run(self):
            if self.debug_mode:
                print("[DEBUG MODE ON]")

- **Run the script with -h**

.. code-block:: text

    usage: my_script.py [OPTIONS]

    optional arguments:
      -h, --help  show this help message and exit

    # --debug is not shown

- **But the script still accepts the argument:**

.. prompt:: bash $

    python my_script.py --debug

.. code-block:: text

    [DEBUG MODE ON]


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

1. This defines a primary ``--level`` option that accepts a value like ``--level medium``
2. The ``aliases`` map defines shorthand flags like ``--low`` and ``--high``, which are treated as constant presets
   and internally rewritten as ``--level=low`` and ``--level=high``
3. The ``choices`` parameter limits valid values to a predefined set, ensuring that even aliased values
   are validated properly

- **run the script with**

.. prompt:: bash $

    python script.py --low

- **output**

.. code-block:: text

    Level selected: low

- **you can also run**

.. prompt:: bash $

    python script.py --level medium

- **output**

.. code-block:: text

    Level selected: medium


pass options between classes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When working with structured data or shared configurations, you may want to **copy values**
into an argument parser class without redefining or parsing them again.

refer to :class:`~argclz.clone.Cloneable`

.. code-block:: python

    from argclz import Cloneable, argument

    class Config(Cloneable):
        path: str = argument('--path')
        debug: bool = argument('--debug', action='store_true')

    # Copy from another instance
    src = Config(path='/data/file', debug=True)
    dst = Config(src)
    assert dst.path == '/data/file'
    assert dst.debug is True


Type parser
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

1. ``float_tuple_type`` is a predefined parser from :mod:`argclz.types` that converts a string
   like ``0.3,0.5,0.9`` into a ``tuple[float, ...]``.

- **run the script with**

.. prompt:: bash $

    python script.py --anno 0.3,0.5,0.9

- **output**

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


1. A simple lambda-based validator. Any callable returning a boolean can be used.
   If it returns ``False`` or raises an exception, validation fails.

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


1. Accepts only integers in the range [10, 99] (inclusive). Built using :class:`~argclz.validator.IntValidatorBuilder`
2. Accepts only a valid directory path that exists. Composed using :class:`~argclz.validator.PathValidatorBuilder`

.. seealso ::

    see more validation options :mod:`argclz.validator`

Sub-Commands
------------------------------------

parse_command_args
^^^^^^^^^^^^^^^^^^^
Parse command-line arguments for subcommands, each associated with a different parser class

**Example usage**

.. code-block:: python

    # example_1.py
    class InitCmd(AbstractParser): # [1]

        name: str = argument('--name', required=True)

        def run(self):
            print(f"Initializing project: {self.name}")

    # example_2.py
    class BuildCmd(AbstractParser): # [1]

        release: bool = argument('--release', action='store_true')

        def run(self):
          print("Building in release mode" if self.release else "Building in debug mode")

    # __init__.py
    from argclz.commands import parse_command_args
    parse_command_args( # [2]
        {'init': InitCmd, 'build': BuildCmd},
         args=['init', '--name', 'demo']
     )

1. sub-commands classes, which could be put at different python files.
2. a function-interface entry point, which could be put at `__init__.py` to provide module-wise command-line interface.

- **Run the script with -h**

.. code-block:: text

    TODO

**Output**

.. code-block:: text

  Initializing project: demo

sub_command_group
^^^^^^^^^^^^^^^^^^^
TODO

.. code-block:: python

    class Main(AbstractParser):
        def run(self):
            print_help(self)

        command_group = sub_command_group()

        @command_group('a')
        class SubCommandA(AbstractParser):
            def run(self):
                print('do A')

        @command_group('b')
        class SubCommandB(AbstractParser):
            a: int = argument('-a', help='option for B')

            def run(self):
                print('do B', self.a)

    Main().main()

- **Run the script with -h**

.. code-block:: text

    TODO


Dispatch usage
------------------------------------
An alternative sub-commands.



.. seealso ::

    see dispatch usage in :mod:`argclz.dispatch`

.. code-block:: python
    from argclz.dispatch import Dispatch, dispatch

    class Main(AbstractParser, Dispatch): # [1]

        command:str = pos_argument('CMD') # [2]
        command_args:list[str] = var_argument('ARGS') # [2]

        EPILOG = lambda : f\""" \\
    Sub-Commands:
    {Main.build_command_usages()}
    \""" # [3]

        def run(self):
            self.invoke_command(self.command, *self.command_args) # [4]

        @dispatch('A') # [5]
        def run_a(self):
            print('A')

        @dispatch('B') # [5]
        def run_b(self):
            print('B')

    Main().main()

1. inherit ``Dispatch`` to gain related methods, such as ``invoke_command``.
2. we use command to decide which dispatch command need to be run.
3. add dispatch commands into help epilog. Note that it is a lambda form because the content is dynamic generated.
4. run dispatch commands. User has more control on when to call.
5. method labeled as dispatch command.

Compose cli option-classes
------------------------------------

When building complex CLI tools, it's common to reuse and combine sets of arguments across multiple commands or components.
Within the `argclz` system, you can define reusable *option classes*. These can be composed together through standard Python class inheritance.
This enables **modular** and **maintainable** CLI definitions.


.. code-block:: python

    class IOOptions: # [1]

        input_path: str = argument('--input', metavar='FILE', help='Input file')

        output_path: str = argument('--output', metavar='FILE', help='Output file')


    class LoggingOptions: # [1]

        verbose: bool = argument('--verbose', help='Enable verbose logging')

        log_level: Literal['info', 'debug', 'warn'] = argument('--log', default='info', help='Log level')

    class MyOptions(IOOptions, LoggingOptions): # [2]
        # [3]
        input_path = as_argument(IOOptions.input_path).with_options(
            validator.is_file().is_suffix('.csv'),
            required=True,
            help='(required) Input file'
        )

        # [4]
        log_level = as_argument(LoggingOptions.log_level).with_options(
            choices=['info', 'debug'],
            hidden=True
        )

        # [5]
        other_option = argument(...)

1. reusable options classes, which might be put at different files.
2. class ``MyOptions`` inherit arguments from ``IOOptions`` and ``LoggingOptions``.
3. overwrite ``IOOptions.input_path`` by adding a file validator that only accept .csv suffix, and setting ``required=True``
4. overwrite ``LoggingOptions.log_level`` by limiting accepted choices for ``log_level`` only ``info`` or ``debug``, and hiding it from help output.
5. class ``MyOptions`` specific arguments.


Utility usage
------------------------------------
Refer to :mod:`argclz.core`

parse_args
^^^^^^^^^^^^^^^^^^^
Parse the provided list of command-line arguments and apply the parsed values to the given instance

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
^^^^^^^^^^^^^^^^^^^
collect all argument attributes into a dictionary with attribute name to its value

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
^^^^^^^^^^^^^^^^^^^
Option class can be composed by inherition. Child option class can also change the value from parent's
argument. As well as disable it (by replacing a value)

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
    copy_argument,
    print_help
)
from .types import *
