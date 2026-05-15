Advanced usage
===========================

hidden argument
---------------------
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

.. code-block:: bash

    $ python my_script.py --debug

.. code-block:: text

    [DEBUG MODE ON]


aliased_argument
---------------------
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

.. code-block:: bash

    $ python script.py --low

- **output**

.. code-block:: text

    Level selected: low

- **you can also run**

.. code-block:: bash

    $ python script.py --level medium

- **output**

.. code-block:: text

    Level selected: medium


pass options between classes
------------------------------------------

When working with structured data or shared configurations, you may want to **copy values**
into an argument parser class without redefining or parsing them again.
:class:`~argclz.clone.Cloneable` provides an ``__init__`` that accepts an ``AbstractParser``,
``Cloneable``, or ``dict``, then reads and sets all matched arguments or keys.
Keyword arguments can also be used to overwrite individual fields during initialisation.

refer to :class:`~argclz.clone.Cloneable` and underlying :func:`~argclz.core.copy_argument`

.. code-block:: python

    from argclz import Cloneable, argument

    class Config(Cloneable):
        path: str = argument('--path')
        debug: bool = argument('--debug')

    # Copy from another instance
    src = Config(path='/data/file', debug=True)
    dst = Config(src)
    assert dst.path == '/data/file'
    assert dst.debug is True

    # Overwrite a field at copy time
    dst2 = Config(src, debug=False)
    assert dst2.debug is False

If ``polars`` is installed, :class:`~argclz.clone.Cloneable` also accepts a single-row
``pl.DataFrame`` or a plain ``dict`` row, which is useful for iterating a dataframe:

.. code-block:: python

    import polars as pl
    from argclz import Cloneable, argument

    class Config(Cloneable):
        type: str = argument('--type')
        path: str = argument('--path')

    src = pl.DataFrame([{'type': 'file', 'path': '123.txt'}])
    dst = Config(src)
    assert dst.type == 'file'
    assert dst.path == '123.txt'

    # Multi-row dataframe
    for row in df.iter_rows(named=True):
        config = Config(row)
        ...
