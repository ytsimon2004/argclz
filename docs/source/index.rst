Welcome to Argclz documentation!
====================================

Argclz integrates Python’s ``argparse`` with class-based configuration, allowing
you to declare command-line arguments as class attributes with type annotations. This approach
automatically infers type conversion, supports validators, and makes it easy to compose and reuse parsers.


Features
--------

- **Type-safe arguments** - Automatically infer type conversion from Python type annotations
- **Clean syntax** - Define arguments as class attributes with straightforward decorators
- **Composable** - Easily reuse and extend argument definitions through inheritance
- **Validation** - Built-in validation system with chainable API
- **Subcommands** - Support for command hierarchies with minimal boilerplate
- **Organized help** - Group arguments into logical sections for better documentation


Installation
------------

.. code-block:: bash

    pip install argclz


Quick Example
-------------

.. code-block:: python

    class MyTool(AbstractParser):
            verbose: bool = argument('-v', '--verbose', help='Enable verbose logging')
            name:    str  = argument('-n', '--name', required=True, help='User name')
            count:   int  = argument('-c', '--count', default=1, help='Repeat count (1–5)')
            mode:    Literal['fast', 'slow'] = argument('--mode', default='fast', help='Operating mode')
            output:  Path | None = argument('-o', '--output', default=None, help='Output directory')
            input_file: Path     = pos_argument('INPUT', help='Input file to process')
            tags:       list[str] = var_argument('TAG', help='Tags to attach')

            def run(self):
                for i in range(self.count):
                    print(f"Hello {self.name}! ({i + 1}/{self.count})")

        if __name__ == '__main__':
            MyTool().main()

Help output:

.. code-block:: text

    usage: my_tool.py [-h] [-v] -n NAME [-c COUNT] [--mode {fast,slow}] [-o OUTPUT]
                      INPUT [TAG ...]

    options:
      -h, --help            show this help message and exit
      -v, --verbose         Enable verbose logging
      -n NAME, --name NAME  User name
      -c COUNT, --count     Repeat count (1–5)
      --mode {fast,slow}    Operating mode
      -o OUTPUT, --output OUTPUT
                            Output directory

    positional arguments:
      INPUT                 Input file to process
      TAG                   Tags to attach


Getting Started
---------------

.. toctree::
   :maxdepth: 3
   :caption: Examples

   get_start/index



API Reference
-----------------

.. toctree::
   :maxdepth: 1
   :caption: Modules

   api/argclz.core
   api/argclz.types
   api/argclz.validator
   api/argclz.dispatch
   api/argclz.clone

