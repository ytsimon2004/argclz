from __future__ import annotations

from typing import TYPE_CHECKING, Any

from . import i18n
from .core import ArgumentParser, copy_argument

if TYPE_CHECKING:
    import polars as pl  # pyright: ignore[reportMissingImports]

__all__ = ['Cloneable']


class Cloneable:
    """Mixin that initializes argument attributes from another object.

    ``Cloneable`` copies matching :func:`argclz.core.argument` attributes from:

    * another parser-like object,
    * another ``Cloneable`` instance,
    * a mapping, or
    * a single-row ``polars.DataFrame`` when Polars is installed.
    * Keyword arguments override values have the highest priority.
    """

    def __init__(self, ref: ArgumentParser | Cloneable | dict[str, Any] | pl.DataFrame | None = None, /, **kwargs):
        """
        :param ref: source object to copy values from. ``None`` means only keyword overrides are used.
        :param kwargs: values that override or supply copied argument attributes.
        """
        if ref is not None or len(kwargs):
            _copy_argument(self, ref, kwargs)


def _copy_argument(self: Cloneable, ref: ArgumentParser | Cloneable | dict[str, Any] | pl.DataFrame | None, kwargs: dict):
    if ref is None or isinstance(ref, Cloneable):
        copy_argument(self, ref, **kwargs)
        return

    if isinstance(ref, dict):
        tmp = dict(ref)
        tmp.update(kwargs)
        copy_argument(self, None, **tmp)
        return

    try:
        import polars as pl  # pyright: ignore[reportMissingImports]
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
        raise RuntimeError(i18n.gettext('dataset not unique : %s') % str(ref))

    for column in dataset.columns:
        kwargs.setdefault(column, dataset[0, column])

    copy_argument(self, None, **kwargs)
