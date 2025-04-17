try:
    import rich
except ImportError:
    from ._format_text import *
else:
    from ._format_rich import *

__all__ = [
    'format_dispatch_commands'
]
