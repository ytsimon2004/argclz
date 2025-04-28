Validator usage
=====================
The validator system provides a fluent, chainable API for building type-specific validation rules.
It works by defining specialized “builder” classes (e.g., for strings, integers, floats, lists, and tuples)
that let you specify constraints like numeric ranges, string length ranges, regex checks, or container length/item rules


- Example for customized ``lambda``

.. code-block:: python

    class Opt(AbstractParser):
        # Accepts only even integers
        value: int = argument('-v', validator=lambda it: it % 2 == 0)
        #                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ [1]

    opt = Opt()
    opt.value = 4    # OK
    opt.value = 5    # Raises ValueError


1. A simple lambda-based validator. Any callable returning a boolean can be used.
   If it returns ``False`` or raises an exception, validation fails.

- Example for our builtin validator

.. code-block:: python

    class Opt(AbstractParser):
        value: int = argument('-v', validator.int.in_range(10, 99))
        #                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ [1]

        directory: Path = argument('--path', validator.path.is_dir().is_exists())
        #                                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ [2]

    opt = Opt()
    opt.value = 42    # OK
    opt.value = 7     # Raises ValueError

    opt.directory = '*/not_exist/' # Raises ValueError (not exists)
    opt.directory = '*/file.csv' # Raises ValueError (not a dir)


1. Accepts only integers in the range [10, 99] (inclusive). Built using :class:`~argclz.validator.IntValidatorBuilder`
2. Accepts only a valid directory path that exists. Composed using :class:`~argclz.validator.PathValidatorBuilder`




String Validation
-------------------

use :doc:`validator.str <../api/_autosummary/argclz.validator.StrValidatorBuilder>`

Examples
^^^^^^^^^^
**Minimum String Length**

.. code-block:: python

    from argclz import validator

    class Opt:
        # Must be at least 2 characters long
        a: str = argument('-a', validator.str.length_in_range(2, None))

    opt = Opt()
    opt.a = 'Hi'    # OK
    opt.a = ''      # Raises ValueError

**Regex Matching**

.. code-block:: python

        class Opt:
            # Must match a letter followed by a digit, e.g. 'a1', 'b9'
            a: str = argument('-a', validator.str.match(r'[a-z][0-9]'))

        opt = Opt()
        opt.a = 'a1'    # OK
        opt.a = 'A1'    # Raises ValueError


Method Reference
^^^^^^^^^^^^^^^^^^^^
refer to :class:`~argclz.validator.StrValidatorBuilder`

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - **Method**
     - **Description**
   * - :meth:`length_in_range(a, b) <argclz.validator.StrValidatorBuilder.length_in_range>`
     - Enforces a string length in [a, b]. Either bound may be ``None``.
   * - :meth:`match(pattern) <argclz.validator.StrValidatorBuilder.match>`
     - Checks if the string matches a given regex pattern.
   * - :meth:`starts_with(prefix) <argclz.validator.StrValidatorBuilder.starts_with>`
     - Checks if the string starts with ``prefix``.
   * - :meth:`ends_with(suffix) <argclz.validator.StrValidatorBuilder.ends_with>`
     - Checks if the string ends with ``suffix``.
   * - :meth:`contains(substring) <argclz.validator.StrValidatorBuilder.contains>`
     - Checks if the string contains the given substring.
   * - :meth:`is_in(options) <argclz.validator.StrValidatorBuilder.is_in>`
     - Checks if the string is in the provided collection of allowed options.


Integer Validation
-------------------
use :doc:`validator.int <../api/_autosummary/argclz.validator.IntValidatorBuilder>`

Examples
^^^^^^^^^^

**Integer Range**

.. code-block:: python

    class Opt:
        # Must be >= 2
        a: int = argument('-a', validator.int.in_range(2, None))

    opt = Opt()
    opt.a = 5   # OK
    opt.a = 0   # Raises ValueError

**Positivity**

.. code-block:: python

    class Opt:
        # Must be strictly positive
        a: int = argument('-a', validator.int.positive(include_zero=False))

    opt = Opt()
    opt.a = 10  # OK
    opt.a = 0   # Raises ValueError


Method Reference
^^^^^^^^^^^^^^^^^^^^
refer to :class:`~argclz.validator.IntValidatorBuilder`

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - **Method**
     - **Description**
   * - :meth:`in_range(a, b) <argclz.validator.IntValidatorBuilder.in_range>`
     - Checks if integer is in [a, b]. Either bound may be ``None``.
   * - :meth:`positive(include_zero=True) <argclz.validator.IntValidatorBuilder.positive>`
     - Checks if integer is >= 0 (if ``include_zero=True``) or > 0 otherwise.
   * - :meth:`negative(include_zero=True) <argclz.validator.IntValidatorBuilder.negative>`
     - Checks if integer is <= 0 (if ``include_zero=True``) or < 0 otherwise.


Float Validation
-------------------
use :doc:`validator.float <../api/_autosummary/argclz.validator.FloatValidatorBuilder>`

Examples
^^^^^^^^^^^
**Range + NaN Handling**

.. code-block:: python

    class Opt:
        # Must be < 100, NaN not allowed
        a: float = argument('-a',
            validator.float.in_range(None, 100).allow_nan(False)
        )

    opt = Opt()
    opt.a = 3.14        # OK
    opt.a = 123.45      # Raises ValueError (out of range)
    opt.a = float('nan')# Raises ValueError (NaN not allowed)

Method Reference
^^^^^^^^^^^^^^^^^^^^
refer to :class:`argclz.validator.FloatValidatorBuilder`

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - **Method**
     - **Description**
   * - :meth:`in_range(a, b) <argclz.validator.FloatValidatorBuilder.in_range>`
     - Checks if float is in the open interval ``(a, b)``.
   * - :meth:`in_range_closed(a, b) <argclz.validator.FloatValidatorBuilder.in_range_closed>`
     - Checks if float is in the closed interval ``[a, b]``.
   * - :meth:`allow_nan(allow=True) <argclz.validator.FloatValidatorBuilder.allow_nan>`
     - Allows or disallows NaN values.
   * - :meth:`positive(include_zero=True) <argclz.validator.FloatValidatorBuilder.positive>`
     - Checks if float is >= 0 (if ``include_zero=True``) or > 0 otherwise.
   * - :meth:`negative(include_zero=True) <argclz.validator.FloatValidatorBuilder.negative>`
     - Checks if float is <= 0 (if ``include_zero=True``) or < 0 otherwise.


List Validation
----------------
use :doc:`validator.list <../api/_autosummary/argclz.validator.ListValidatorBuilder>`

Examples
^^^^^^^^^^^
**List of Integers**

.. code-block:: python

    class Opt:
        # Must be a list of integers
        a: list[int] = argument('-a', validator.list(int))

    opt = Opt()
    opt.a = [1, 2, 3]    # OK
    opt.a = ['a', 2]     # Raises ValueError

**Item Validation**

.. code-block:: python

    class Opt:
        # Each item must be non-negative
        a: list[int] = argument('-a',
            validator.list(int).on_item(validator.int.positive(True))
        )

    opt = Opt()
    opt.a = [0, 2, 5]    # OK
    opt.a = [1, -1]      # Raises ValueError

Method Reference
^^^^^^^^^^^^^^^^^^^^
refer to :class:`argclz.validator.ListValidatorBuilder`

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - **Method**
     - **Description**
   * - :meth:`length_in_range(a, b) <argclz.validator.ListValidatorBuilder.length_in_range>`
     - Enforces list length in [a, b].
   * - :meth:`allow_empty(allow=True) <argclz.validator.ListValidatorBuilder.allow_empty>`
     - Allows or disallows an empty list.
   * - :meth:`on_item(validator) <argclz.validator.ListValidatorBuilder.on_item>`
     - Applies a validator to each list item.


Tuple Validation
-----------------
use :doc:`validator.tuple <../api/_autosummary/argclz.validator.TupleValidatorBuilder>`

Examples
^^^^^^^^^^
**Fixed-Length Tuple**

.. code-block:: python

    class Opt:
        # Must be (str, int, float)
        a: tuple[str, int, float] = argument(
            '-a', validator.tuple(str, int, float)
        )

    opt = Opt()
    opt.a = ('abc', 42, 3.14)   # OK
    opt.a = ('abc', 42)        # Raises ValueError (too few elements)

**Variable-Length**

.. code-block:: python

    class Opt:
        # Must be (str, int, ...) i.e. at least 'str + int', optionally more ints
        a: tuple[str, int, ...] = argument(
            '-a', validator.tuple(str, int, ...)
        )

    opt = Opt()
    opt.a = ('x', 10)            # OK
    opt.a = ('x', 10, 20, 30)    # OK
    opt.a = ('x',)               # Raises ValueError (missing int)

**Item-Validation**

.. code-block:: python

    class Opt:
        # Must be (str, int, float).
        # The string must have a length <= 5,
        # and the int must be >= 0 and <= 100.
        a: tuple[str, int, float] = argument(
            '-a',
            validator.tuple(str, int, float)
                .on_item(0, validator.str.length_in_range(None, 5))
                .on_item(1, validator.int.in_range(0, 100))
        )

    opt = Opt()

    # Passes all checks: str length=3, int in range [0..100], float is fine
    opt.a = ('hey', 42, 3.14)

    # Fails because the string is too long:
    opt.a = ('excessive', 42, 1.2)
    # Raises ValueError: str length over 5: "excessive"

    # Fails because integer is out of range:
    opt.a = ('hi', 999, 2.5)
    # Raises ValueError: value out of range [0, 100]: 999

Method Reference
^^^^^^^^^^^^^^^^^^^^
refer to :class:`~argclz.validator.TupleValidatorBuilder`

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - **Method**
     - **Description**
   * - :meth:`on_item(indexes, validator) <argclz.validator.TupleValidatorBuilder.on_item>`
     - Apply a validator to specific tuple positions, or ``None`` for all.
   * - *(constructor)*
     - Pass one int (e.g. 3) to enforce a fixed-length tuple with no type checks, or a tuple of types
       like ``(str, int, float)``. The last type can be ``...`` for variable length.


Path Validation
-----------------
use :doc:`validator.path <../api/_autosummary/argclz.validator.PathValidatorBuilder>`

Examples
^^^^^^^^^^^^^^^^^^^^
**Path suffix**

.. code-block:: python

    class Opt:
        a: Path = argument('-a', validator.path.is_suffix(['.csv', '.npy']))

    opt = Opt()
    opt.a = Path('.../*.csv')    # OK
    opt.a = Path('.../*.txt')    # Raises ValueError


Method Reference
^^^^^^^^^^^^^^^^^^^^
refer to :class:`argclz.validator.PathValidatorBuilder`

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - **Method**
     - **Description**
   * - :meth:`is_suffix(suffix) <argclz.validator.PathValidatorBuilder.is_suffix>`
     - Check path suffix or in a list of suffixes
   * - :meth:`is_exists() <argclz.validator.PathValidatorBuilder.is_exists>`
     - Check if path exists
   * - :meth:`is_file() <argclz.validator.PathValidatorBuilder.is_file>`
     - Check if path is a file
   * - :meth:`is_dir() <argclz.validator.PathValidatorBuilder.is_dir>`
     - Check if path is a directory




Logical Combinators
---------------------

Examples
^^^^^^^^^^^^
**OR Combination**

.. code-block:: python

    class Opt:
        # Must be int in [0,10] OR str length in [0,10]
        a: int | str = argument(
            '-a',
            validator.any(
                validator.int.in_range(0, 10),
                validator.str.length_in_range(0, 10)
            )
        )

    opt = Opt()
    opt.a = 5            # OK (int in [0..10])
    opt.a = 'abc'        # OK (length=3)
    opt.a = 50           # Raises ValueError

**AND Combination**

.. code-block:: python

    class Opt:
        # Must be non-negative AND non-positive => zero
        a: int = argument('-a', validator.all(
            validator.int.positive(include_zero=True),
            validator.int.negative(include_zero=True)
        ))

    opt = Opt()
    opt.a = 0   # OK
    opt.a = 1   # Raises ValueError
    opt.a = -1  # Raises ValueError

Method Reference
^^^^^^^^^^^^^^^^^^^^^^^^
.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - **Method/Class**
     - **Description**
   * - :meth:`validator.any(...) <argclz.validator.ValidatorBuilder.any>` or ``|``
     - Combine validators with logical OR; passing at least one is enough.
   * - :meth:`validator.all(...) <argclz.validator.ValidatorBuilder.all>` or ``&``
     - Combine validators with logical AND; must pass them all.
   * - :attr:`~argclz.validator.OrValidatorBuilder`
     - The class implementing OR logic.
   * - :attr:`~argclz.validator.AndValidatorBuilder`
     - The class implementing AND logic.


Error Handling
--------------
If any validation fails:

- A :class:`~argclz.validator.ValidatorFailError` (or subclass) is raised. It can be captured as a ``ValueError``
  in higher-level frameworks.

