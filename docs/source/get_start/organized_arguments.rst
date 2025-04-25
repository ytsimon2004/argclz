organize arguments
====================

grouping
------------

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
------------------------------------

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