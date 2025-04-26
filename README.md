# argclz

[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/argclz)](https://pypi.org/project/argclz/)
[![PyPI version](https://badge.fury.io/py/argclz.svg)](https://badge.fury.io/py/argclz)

[![Documentation Status](https://readthedocs.org/projects/argp/badge/?version=latest)](https://argp.readthedocs.io/en/latest/)
[![codecov](https://codecov.io/gh/ytsimon2004/argclz/branch/main/graph/badge.svg?token=HfO5frntJe)](https://codecov.io/gh/ytsimon2004/argclz)

Class-based command-line argument parsing for Python that combines the power of `argparse` with class definitions and
type annotations.

## Features

- **Type-safe arguments** - Automatically infer type conversion from Python type annotations
- **Clean syntax** - Define arguments as class attributes with straightforward decorators
- **Composable** - Easily reuse and extend argument definitions through inheritance
- **Validation** - Built-in validation system with chainable API
- **Subcommands** - Support for command hierarchies with minimal boilerplate
- **Organized help** - Group arguments into logical sections for better documentation

## Installation

```bash
pip install argclz
```

## [See Documentation](https://argp.readthedocs.io/en/latest/)

## Quick Start

```python
from argclz import *


class MyArgs(AbstractParser):
    verbose: bool = argument('--verbose', help='Enable verbose output')
    name: str = argument('-n', '--name', required=True, help='Name of the user')
    count: int = argument('--count', default=1, help='Number of times to greet')

    def run(self):
        for _ in range(self.count):
            if self.verbose:
                print(f"Greeting with enthusiasm: Hello, {self.name}!")
            else:
                print(f"Hello, {self.name}!")


if __name__ == '__main__':
    MyArgs().main()
```

Show help:

```bash
python my_script.py -h
```

Expected output:

```text
usage: my_script.py [-h] [--verbose] -n NAME [--count COUNT]

options:
  -h, --help            show this help message and exit
  --verbose             Enable verbose output
  -n NAME, --name NAME  Name of the user
  --count COUNT         Number of times to greet
```

Run with:

```bash
python my_script.py --name Alice --count 3 --verbose
```

## Core Features

### Argument Types

```python
# Regular argument
name: str = argument('-n', '--name', help='Name of the user')

# Boolean flag
verbose: bool = argument('--verbose', help='Enable verbose output')

# Positional argument
filename: str = pos_argument('FILENAME', help='Input file to process')

# Variable-length argument
items: list[str] = var_argument('ITEMS', help='Items to process')
```

### Type Parsers

```python
# Comma-separated values to a tuple of floats
coords: tuple[float, ...] = argument('--coords', type=float_tuple_type)

# Value range (min:max)
ranging: tuple[int, int] = argument('--range', type=int_tuple_type)
```

### Argument Organization

```python
# Grouped arguments
verbose: bool = argument('--verbose', group='general')
output_dir: str = argument('--output', group='output')

# Mutually exclusive arguments
output_json: bool = argument('--json', ex_group='output')
output_yaml: bool = argument('--yaml', ex_group='output')
```

### Validators

```python
# Range validator
age: int = argument('--age', validator.int.in_range(18, 99))

# Path validator
path: Path = argument('--path', validator.path.is_dir().is_exists())
```

### Subcommands

```python
class InitCmd(AbstractParser):
    name: str = argument('--name', required=True)

    def run(self):
        print(f"Initializing project: {self.name}")


class BuildCmd(AbstractParser):
    release: bool = argument('--release')

    def run(self):
        print("Building in release mode" if self.release else "Building in debug mode")


# Entry point
from argclz.commands import parse_command_args

if __name__ == '__main__':
    parse_command_args({
        'init': InitCmd,
        'build': BuildCmd
    })
```

### Reusable Option Classes

```python
class IOOptions:
    input_path: str = argument('--input', help='Input file')
    output_path: str = argument('--output', help='Output file')


class LoggingOptions:
    verbose: bool = argument('--verbose', help='Enable verbose logging')


class MyOptions(IOOptions, LoggingOptions):
    # Override an inherited argument
    input_path = as_argument(IOOptions.input_path).with_options(required=True)
```

## License

[BSD 3-Clause License](LICENSE)