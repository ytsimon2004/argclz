"""
Please look :mod:`gettext` for more information.

**Testing**

>>> import unittest.mock
... unittest.mock.patch('gettext.gettext', ...),
... unittest.mock.patch('argparse._', ...),
... unittest.mock.patch('argclz.i18n._', ...)

"""
from gettext import gettext as _


def gettext(message):
    if message is None:
        return None
    return _(message)
