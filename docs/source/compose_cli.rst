Compose cli option-classes
==============================

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