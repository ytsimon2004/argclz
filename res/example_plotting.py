import contextlib
from pathlib import Path
from typing import ContextManager

import matplotlib.pyplot as plt
from matplotlib.axes import Axes

from argclz import argument


class PlottingOptions:
    """A general commandline interface for an experiment project."""

    plt_config: str = argument('--plt', metavar='RC', default=None, help='name of matplotlib rc file')

    @contextlib.contextmanager
    def plot_figure(self, name: Path | None, *args, **kwargs) -> ContextManager[Axes]:
        rc_file = None if self.plt_config is None else f'{self.plt_config}.matplotlibrc'
        with plt.rc_context(fname=rc_file):
            fg, ax = plt.subplots(*args, **kwargs)
            try:
                yield ax
            except KeyboardInterrupt:
                pass
            else:
                if name is None:
                    plt.show()
                else:
                    plt.savefig(name)
            finally:
                plt.close(fg)
