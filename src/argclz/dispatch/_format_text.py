import textwrap
from typing import Type

from .core import Dispatch
from .formats import CommandHelps

__all__ = ['format_dispatch_commands']


def format_dispatch_commands(d: Type[Dispatch],
                             group: str | None,
                             show_para: bool = False,
                             **kwargs) -> str:
    ret = []

    for info in d.list_commands(group):
        info = CommandHelps.of(info)

        header = info.build_command_usage()
        content = info.brief_doc()

        if show_para:
            pass  # TODO

        if len(header) < 20:
            content = header + ' ' * (20 - len(header)) + content
            ret.extend(textwrap.wrap(content, 120,
                                     subsequent_indent=' ' * 20,
                                     break_long_words=True,
                                     break_on_hyphens=True))
        else:
            ret.append(header)
            ret.extend(textwrap.wrap(content, 120,
                                     initial_indent=' ' * 20,
                                     subsequent_indent=' ' * 20,
                                     break_long_words=True,
                                     break_on_hyphens=True))

    return '\n'.join(ret)
