Utility usage
=========================
Refer to :mod:`argclz.core`

parse_args
------------------
Parse the provided list of command-line arguments and apply the parsed values to the given instance

- **Example usage**

.. code-block:: python

    from argclz import parse_args

    class Opt(AbstractParser):
        name: str = argument('--name', required=True)
        count: int = argument('--count', type=int, default=1)


    opt = Opt()
    args = ['--name', 'Alice', '--count', '3']  # same as ['--name=Alice', '--count=3']
    parse_args(opt, args)

    print(opt.name)   # Alice
    print(opt.count)  # 3



as_dict
------------------
collect all argument attributes into a dictionary with attribute name to its value

- **Example usage**

.. code-block:: python

    from argclz import as_dict

    class Opt(AbstractParser):
        name: str = argument('--name', default='guest')
        age: int = argument('--age')

    opt = Opt()
    opt.name = 'Alice'
    opt.age = 20

    print(as_dict(opt))

- **Output**

.. code-block:: text

    {'name': 'Alice', 'age': 20}


with_options
------------------
Option class can be composed by inherition. Child option class can also change the value from parent's
argument. As well as disable it (by replacing a value)

Use together with :func:`~argclz.core.as_argument()`

- **Example usage**

.. code-block:: python

    class Parent(AbstractParser):
        mode: str = argument('--mode', choices=['train', 'test'], default='train')

    class Child(Parent):
        # Override mode to change the default
        mode = as_argument(Parent.mode).with_options(default='test')

    print_help(Child)

- **Output**

.. code-block:: text

  usage: test.py [-h] [--mode {train,test}]

  options:
    -h, --help           show this help message and exit
    --mode {train,test}


