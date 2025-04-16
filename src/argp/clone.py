from typing import TypeVar, TYPE_CHECKING

from .core import ArgumentParser, copy_argument

if TYPE_CHECKING:
    import polars as pl

__all__ = ['Cloneable']

T = TypeVar('T', bound=ArgumentParser)


class Cloneable:
    def __init__(self, ref: T | pl.DataFrame | None = None, /, **kwargs):
        if ref is not None:
            copy_argument(self, ref, **kwargs)


def _copy_argument(self: Cloneable, ref: T | pl.DataFrame, kwargs: dict):
    assert isinstance(self, ArgumentParser)

    try:
        import polars as pl
    except ImportError:
        copy_argument(self, ref, **kwargs)
    else:
        _copy_argument_polars_dataframe(self, ref, kwargs)


def _copy_argument_polars_dataframe(self: ArgumentParser, ref: pl.DataFrame, kwargs: dict):
    dataset = ref.unique()
    if len(dataset) > 1:
        raise RuntimeError(f'dataset not unique : {ref}')

    for column in dataset.columns:
        kwargs.setdefault(column, dataset[0, column])

    copy_argument(self, None, **kwargs)
