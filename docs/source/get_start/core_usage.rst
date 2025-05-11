Core usage
=======================

Import the top-level interface

.. code-block:: python

    from argclz import *


argument
-----------------------------------
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

.. code-block:: bash

   $ python my_script.py --name Alice --count 3 --verbose

**output**

.. code-block:: text

   Greeting with enthusiasm: Hello, Alice!
   Greeting with enthusiasm: Hello, Alice!
   Greeting with enthusiasm: Hello, Alice!



pos_argument
-----------------------------------
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

.. code-block:: bash

    $ python my_script.py data.npy

- **output**

.. code-block:: text

    Processing file: data.npy



var_argument
-----------------------------------
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

.. code-block:: bash

  $ python script.py apple banana cherry

- **output**

.. code-block:: text

  # Resulting value:
  items = ['apple', 'banana', 'cherry']


description
-----------------------------------

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