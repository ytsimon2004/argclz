Type parser
===============

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

.. code-block:: bash

    $ python script.py --anno 0.3,0.5,0.9

- **output**

.. code-block:: text

    annotation values: 0.3,0.5,0.9

.. seealso ::

    see more types options :doc:`argclz.types <../api/argclz.types>`