organize arguments
====================

grouping
------------

You can organize related command-line arguments under labeled sections using the ``group=...`` keyword.
This helps structure the help message when you have many options and want to categorize them clearly.
Each ``group`` name creates a new labeled section in the ``--help`` output.


.. code-block:: python

    class MyArgs(AbstractParser):

        GROUP_GENERAL =  'general'
        #^^^^^^^^^^^^[1] ^^^^^^^^^[2]
        GROUP_OUTPUT =  'output'
        #^^^^^^^^^^^[1] ^^^^^^^^[2]

        # Group for general options
        verbose: bool = argument('--verbose', group=GROUP_GENERAL, help='Enable verbose logging')
        #                                     ^^^^^^^^^^^^^^^^^^^[3]
        config: str = argument('--config', group=GROUP_GENERAL, help='Path to configuration file')
        #                                  ^^^^^^^^^^^^^^^^^^^[3]

        # Group for output options
        output_dir: str = argument('--output', group=GROUP_OUTPUT, help='Directory to save results')
        #                                      ^^^^^^^^^^^^^^^^^^^[3]
        overwrite: bool = argument('--overwrite', group=GROUP_OUTPUT, help='Overwrite existing files')
        #                                         ^^^^^^^^^^^^^^^^^^^[3]

1. Use a class attribute to store the group name.
2. The name of group
3. Assign argument under certain group.

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

There is another way to group arguments by using :class:`~argclz.core.argument_group`.


.. code-block:: python

    class MyArgs(AbstractParser): # [1]
        GROUP_GENERAL = argument_group('general', 'General options') # [2]
        GROUP_OUTPUT = argument_group('output', 'Output options') # [2]

        verbose: bool = argument('--verbose', group=GROUP_GENERAL, help='Enable verbose logging')
        #                                     ^^^^^^^^^^^^^^^^^^^[3]
        config: str = GROUP_GENERAL.argument('--config', help='Path to configuration file')
        #             ^^^^^^^^^^^^^[4]

1. Continuous from above example, but changing following contents.
2. Use :class:`~argclz.core.argument_group`, which gives more information.
3. ``GROUP_GENERAL`` can pass into ``group``, as same as the first example.
4. Or use its method :meth:`~argclz.core.argument_group.argument` to create an argument.

- **run the script with -h**

.. code-block:: text

    usage: my_script.py [-h] [--verbose] [--config CONFIG] [--output OUTPUT_DIR] [--overwrite]

    options:
      -h, --help           show this help message and exit

    general:
      General options

      --verbose            Enable verbose logging
      --config CONFIG      Path to configuration file

    output:
      Output options

      --output OUTPUT_DIR  Directory to save results
      --overwrite          Overwrite existing files



mutually exclusive grouping
------------------------------------

Use ``argument_group(exclusive=True)`` to group arguments into a **mutually exclusive group**,
meaning that only one of the arguments in the group can be specified at a time.

This is useful when two or more options conflict and cannot be used together.

.. code-block:: python

    class MyArgs(AbstractParser):
        OUTPUT_GROUP = argument_group(exclusive=True)

        output_json: bool = argument('--json', group=OUTPUT_GROUP, help='Output as JSON')
        output_yaml: bool = argument('--yaml', group=OUTPUT_GROUP, help='Output as YAML')


- **run the script with mutually exclusive options**

.. code-block:: bash

    $ python my_script.py --json test.json --yaml test.yaml


.. code-block:: text

    usage: test.py [-h] [--json | --yaml]
    argument --yaml: not allowed with argument --json

The older ``ex_group=...`` keyword is deprecated. Existing code may still use it, but new code should prefer
``argument_group(exclusive=True)``.

.. code-block:: python

    class MyArgs(AbstractParser):
        output_json: bool = argument('--json', ex_group='output', help='Output as JSON')
        output_yaml: bool = argument('--yaml', ex_group='output', help='Output as YAML')
