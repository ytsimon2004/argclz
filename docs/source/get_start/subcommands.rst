Sub-Commands
========================

parse_command_args
---------------------
Parse command-line arguments for subcommands, each associated with a different parser class

refer to :func:`~argclz.commands.parse_command_args()`

**Example usage**

.. code-block:: python

    # example_1.py
    class InitCmd(AbstractParser): # [1]
        DESCRIPTION = 'run init'
        name: str = argument('--name', required=True)

        def run(self):
            print(f"Initializing project: {self.name}")

    # example_2.py
    class BuildCmd(AbstractParser): # [1]
        DESCRIPTION = 'run build'
        release: bool = argument('--release')

        def run(self):
          print("Building in release mode" if self.release else "Building in debug mode")

    # __main__.py
    from argclz.commands import parse_command_args
    parse_command_args( # [2]
        {'init': InitCmd,
        'build': BuildCmd}
     )

1. sub-commands classes, which could be put at different python files.
2. a function-interface entry point, which could be put at ``__main__.py`` to provide module-wise command-line interface.

- **Run the script with -h**

.. code-block:: text

    usage: my_module [-h] {init,build} ...

    options:
      -h, --help    show this help message and exit

    commands:
      {init,build}
        init        run init
        build       run build

- **Run the script**

.. code-block:: bash

   $ python -m my_module init --name demo

- **Output**

.. code-block:: text

  Initializing project: demo


sub_command_group
---------------------
The :func:`~argclz.commands.sub_command_group()` helper lets you declare nested subcommands directly on a single :class:`~argclz.core.AbstractParser` class.
Under the hood it creates a top‐level positional choice of subcommand names, then delegates parsing to the matching inner class.


.. code-block:: python

    class Main(AbstractParser):
        def run(self):
            print_help(self)

        command_group = sub_command_group()

        @command_group('a')
        class SubCommandA(AbstractParser):
            def run(self):
                print('do A')

        @command_group('b')
        class SubCommandB(AbstractParser):
            a: int = argument('-a', help='option for B')

            def run(self):
                print('do B', self.a)

    Main().main()

- **Run the script with -h**

.. code-block:: text

    usage: my_script.py [-h] {a,b} ...

    positional arguments:
      {a,b}
        a
        b

- **Run the script**

.. code-block:: bash

    $ python my_script.py b -a 100

- **Output**

.. code-block:: text

    do B 100