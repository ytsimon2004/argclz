import abc
from pathlib import Path

from argp import AbstractParser, argument, validator


class GeneralOptions(AbstractParser, metaclass=abc.ABCMeta):
    """A general commandline interface for an experiment project."""

    exp_animal: str = argument('-A', help='name of animal')
    exp_date: str = argument('-D', help='date of experiment')
    data_root: Path = argument('-S', validator.path.is_exists(), help='data source root')
    output_root: Path = argument('-O', help='data source root')

    data_path: Path
    output_path: Path

    def run(self):
        self.check()
        self.compute()

    def check(self):
        self.data_path = self.data_root / self.exp_animal / self.exp_date
        self.output_path = self.output_root / self.exp_animal / self.exp_date

    @abc.abstractmethod
    def compute(self):
        pass
