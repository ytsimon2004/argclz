from typing import NamedTuple

from typing_extensions import Self

from .core import DispatchCommand

__all__ = ['CommandHelps']


class CommandHelps(NamedTuple):
    commands: list[str]
    order: float
    usage: list[str]
    # TODO params
    doc: str

    @classmethod
    def of(cls, command: DispatchCommand) -> Self:
        return CommandHelps(command.commands, command.order, command.usage, command.doc or '')

    def build_command_usage(self) -> str:
        # TODO usage case

        match self.commands:
            case [command]:
                return command
            case [command, *aliases]:
                return command + ' (' + ', '.join(aliases) + ')'
            case _:
                raise RuntimeError()

    def brief_doc(self) -> str:
        contents = self.doc.split('\n')

        if len(ret := contents[0].strip()) == 0:
            try:
                while len(ret := contents.pop(0).strip()) == 0:
                    pass
            except IndexError:
                ret = ''

        try:
            i = ret.index('. ')
        except ValueError:
            pass
        else:
            ret = ret[:i + 1]

        return ret
