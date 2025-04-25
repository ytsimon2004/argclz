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

.. seealso ::

    see more validation options :mod:`argclz.validator`