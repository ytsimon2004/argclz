from typing import Type

from .core import Dispatch

__all__ = ['format_dispatch_commands']


def format_dispatch_commands(d: Type[Dispatch],
                             group: str | None,
                             show_para: bool = False,
                             **kwargs) -> str:
    from rich.console import Console
    from rich.table import Table
    from rich import box
    console = Console()

    with console.capture() as capture:
        table = Table(show_header=False, show_edge=False, box=box.SIMPLE)
        table.add_column('command', min_width=18)
        table.add_column('desp')

        for info in d.list_commands(group):
            header = info.command
            if len(info.aliases) > 0:
                header += ' (' + ', '.join(info.aliases) + ')'

            content = info.doc or ''
            content = content.split('\n')[0].strip()

            table.add_row(header, content)

        console.print(table)

    return capture.get()
