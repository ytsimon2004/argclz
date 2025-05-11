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
``Clonable`` provides an ``__init__`` that accept an ``AbstractParser``, ``Clonable`` or ``dict``,
then read and set all matched arguments or keys. It also allows to use keyword argument to overwrite
the referred data during initialization.

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

If ``polars`` is installed, then ``Clonable`` allows to read values from a single row dataframe.

.. code-block:: python

    import polars as pl
    from argclz import Cloneable, argument

    class Config(Clonable):
        type: str = argument('--type')
        path: str = argument('--path')

    src = pl.DataFrame([{'type':'file', 'path':'123.txt'}])
    dst = Clonable(src)
    assert dst.type == 'file'
    assert dst.path == '123.txt'

For a multi-row dataframe, you can use ``Config`` likes:

.. code-block:: python

    for data in df.item_rows(named=True):
        config = Config(data)
        ...
