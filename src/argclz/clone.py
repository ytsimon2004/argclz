from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .core import ArgumentParser, copy_argument

if TYPE_CHECKING:
    import polars as pl

__all__ = ['Cloneable']


class Cloneable:
    def __init__(self, ref: ArgumentParser | Cloneable | dict[str, Any] | pl.DataFrame | None = None, /, **kwargs):
        if ref is not None or len(kwargs):
            _copy_argument(self, ref, kwargs)


def _copy_argument(self: Cloneable, ref: Cloneable | dict[str, Any] | pl.DataFrame, kwargs: dict):
    if ref is None or isinstance(ref, Cloneable):
        copy_argument(self, ref, **kwargs)
        return

    if isinstance(ref, dict):
        tmp = dict(ref)
        tmp.update(kwargs)
        copy_argument(self, None, **tmp)
        return

    try:
        import polars as pl
    except ImportError:
        copy_argument(self, ref, **kwargs)
    else:
        if isinstance(ref, pl.DataFrame):
            _copy_argument_polars_dataframe(self, ref, kwargs)
        else:
            copy_argument(self, ref, **kwargs)


def _copy_argument_polars_dataframe(self: Cloneable, ref: pl.DataFrame, kwargs: dict):
    dataset = ref.unique()
    if len(dataset) > 1:
        raise RuntimeError(f'dataset not unique : {ref}')

    for column in dataset.columns:
        kwargs.setdefault(column, dataset[0, column])

    copy_argument(self, None, **kwargs)
