from typing import Protocol

__all__ = [
    'ArgumentDescriptor',
    'DefaultArgumentDescriptor'
]

ARGCLZ_NAMESPACE = '__argclz_namespace__'


class ArgumentDescriptor(Protocol):
    """Protocol for custom argument value storage.

    :class:`argclz.core.Argument` delegates attribute reads, writes, and deletes
    to these hooks after command-line parsing and validation. Implement this
    protocol when an argument value should be stored somewhere other than the
    default per-instance namespace.
    """

    def __get_arg__(self, instance, name: str):
        """Return the stored value for argument ``name`` on ``instance``.

        :raise AttributeError: if the value is not available.
        """
        pass

    def __set_arg__(self, instance, name: str, value):
        """Store ``value`` for argument ``name`` on ``instance``."""
        pass

    def __del_arg__(self, instance, name: str):
        """Remove the stored value for argument ``name`` on ``instance`` if present."""
        pass


class DefaultArgumentDescriptor(ArgumentDescriptor):
    """Default storage backend for argument attributes.

    Values are stored in a dictionary attached to each parser instance.
    """

    def __get_arg__(self, instance, name: str):
        """Return the stored value for argument ``name``.

        The namespace dictionary is created lazily. If ``name`` has not been
        stored, this method raises :class:`AttributeError`.
        """
        try:
            namespace = getattr(instance, ARGCLZ_NAMESPACE)
        except AttributeError:
            namespace = {}
            setattr(instance, ARGCLZ_NAMESPACE, namespace)

        try:
            return namespace[name]
        except KeyError:
            pass

        raise AttributeError(name)

    def __set_arg__(self, instance, name: str, value):
        """Store ``value`` in the instance namespace under ``name``."""
        try:
            namespace = getattr(instance, ARGCLZ_NAMESPACE)
        except AttributeError:
            namespace = {}
            setattr(instance, ARGCLZ_NAMESPACE, namespace)

        namespace[name] = value

    def __del_arg__(self, instance, name: str):
        """Delete ``name`` from the instance namespace if it exists."""
        try:
            namespace = getattr(instance, ARGCLZ_NAMESPACE)
            del namespace[name]
        except (AttributeError, KeyError):
            pass
