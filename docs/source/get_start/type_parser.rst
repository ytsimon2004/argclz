Type parser
===============

This module provides utility functions and classes that cast command-line string arguments into typed Python values.
These can be used directly as ``type=...`` in any argument specification, offering flexible and reusable conversions.


Tuple types
-----------

``float_tuple_type``, ``int_tuple_type``, ``str_tuple_type`` split a comma-separated string into a typed tuple.

.. code-block:: python

    from argclz import AbstractParser, argument
    from argclz.types import float_tuple_type, int_tuple_type, str_tuple_type

    class MyArgs(AbstractParser):

        weights: tuple[float, ...] = argument('--weights', type=float_tuple_type)
        indices: tuple[int, ...]   = argument('--indices', type=int_tuple_type)
        labels:  tuple[str, ...]   = argument('--labels',  type=str_tuple_type)

        def run(self):
            print(self.weights)  # (0.3, 0.5, 0.9)
            print(self.indices)  # (1, 2, 3)
            print(self.labels)   # ('a', 'b', 'c')

.. code-block:: bash

    $ python script.py --weights 0.3,0.5,0.9 --indices 1,2,3 --labels a,b,c

For mixed-type tuples use :func:`~argclz.types.tuple_type` directly:

.. code-block:: python

    from argclz.types import tuple_type

    # parse "sample,0:10" → ("sample", slice(0, 10))
    from argclz.types import slice_type
    named_slice = tuple_type(str, slice_type)


list_type
---------

:func:`~argclz.types.list_type` converts a delimited string into a list.  The ``prepend`` parameter lets
users extend a base list by prefixing the value with ``+`` or ``+,`` (where ``,`` is a splitter that can be set
by keyword parameter ``split``).

.. code-block:: python

    from argclz import AbstractParser, argument
    from argclz.types import list_type

    BASE = ['debug', 'info']

    class MyArgs(AbstractParser):

        tags:   list[str] = argument('--tags',   type=list_type(str))
        levels: list[str] = argument('--levels', type=list_type(str, prepend=BASE))

        def run(self):
            print(self.tags)    # ['a', 'b', 'c']
            print(self.levels)  # ['debug', 'info', 'warning']   (prepended)

.. code-block:: bash

    $ python script.py --tags a,b,c --levels +warning


bool_type
---------

:func:`~argclz.types.bool_type` accepts flexible truthy/falsy strings (case insensitive).

* Truthy: ``+``, ``1``, ``t``, ``true``, ``yes``, ``y``, ``on``, ``enable``
* Falsy:  ``-``, ``0``, ``f``, ``false``, ``no``, ``n``, ``x``, ``off``, ``disable``

.. code-block:: python

    from argclz import AbstractParser, argument
    from argclz.types import bool_type

    class MyArgs(AbstractParser):

        verbose: bool = argument('--verbose', type=bool_type) # `type=bool_type` can be omitted

        def run(self):
            print(self.verbose)

.. code-block:: bash

    $ python script.py --verbose yes   # True
    $ python script.py --verbose no    # False
    $ python script.py --verbose 1     # True


dict_type
---------

:func:`~argclz.types.dict_type` accumulates ``key=value`` or ``key:value`` pairs across repeated calls.

.. code-block:: python

    from argclz import AbstractParser, argument
    from argclz.types import dict_type

    class MyArgs(AbstractParser):

        env: dict[str, str] = argument('--env', type=dict_type(str))

        def run(self):
            print(self.env)  # {'HOST': 'localhost', 'PORT': '8080'}

.. code-block:: bash

    $ python script.py --env HOST=localhost --env PORT=8080


slice_type
----------

:func:`~argclz.types.slice_type` converts a ``start:end`` string into a :class:`slice` object.

.. code-block:: python

    from argclz import AbstractParser, argument
    from argclz.types import slice_type

    class MyArgs(AbstractParser):

        window: slice = argument('--window', type=slice_type)

        def run(self):
            data = list(range(100))
            print(data[self.window])  # [10, 11, ..., 19]

.. code-block:: bash

    $ python script.py --window 10:20


union_type
----------

:func:`~argclz.types.union_type` tries converters in order and returns the first that succeeds.
Useful when an argument may be one of several types.

.. code-block:: python

    from argclz import AbstractParser, argument
    from argclz.types import union_type

    int_or_str = union_type(int, str)

    class MyArgs(AbstractParser):

        value: int | str = argument('--value', type=int_or_str)

        def run(self):
            print(type(self.value), self.value)

.. code-block:: bash

    $ python script.py --value 42      # <class 'int'> 42
    $ python script.py --value hello   # <class 'str'> hello


literal_type
------------

:func:`~argclz.types.literal_type` restricts a string argument to a fixed set of values.
With ``complete=True`` it additionally supports unique prefix matching.

.. code-block:: python

    from argclz import AbstractParser, argument
    from argclz.types import literal_type

    class MyArgs(AbstractParser):

        mode: Literal['fast', 'show', 'auto'] = argument('--mode')
        # Equivalent to
        mode: str = argument('--mode', type=literal_type(['fast', 'slow', 'auto']))

        def run(self):
            print(self.mode)

.. code-block:: bash

    $ python script.py --mode fast    # fast
    $ python script.py --mode xyz     # ValueError

With prefix completion:

.. code-block:: python

    mode: Literal['fast', 'show', 'auto'] = argument('--mode', type=literal_type(complete=True))
    # or
    mode: str = argument('--mode', type=literal_type(['fast', 'slow', 'auto'], complete=True))
    # --mode f  →  "fast"


try_int_type / try_float_type
------------------------------

:func:`~argclz.types.try_int_type` and :func:`~argclz.types.try_float_type` attempt numeric conversion
and fall back to the original string (or ``None`` for an empty input) instead of raising an error.

.. code-block:: python

    from argclz import AbstractParser, argument
    from argclz.types import try_int_type, try_float_type

    class MyArgs(AbstractParser):

        count:  int | str | None   = argument('--count',  type=try_int_type)
        ratio:  float | str | None = argument('--ratio',  type=try_float_type)

        def run(self):
            print(self.count)   # 5  (int) or "abc" (str) or None (empty)
            print(self.ratio)   # 3.14 (float) or "n/a" (str) or None (empty)

.. code-block:: bash

    $ python script.py --count 5      # 5
    $ python script.py --count abc    # 'abc'


.. seealso ::

    Full API reference: :doc:`argclz.types <../api/argclz.types>`
