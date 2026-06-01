from typing import Protocol

ARGCLZ_NAMESPACE = '__argclz_namespace__'


class ArgumentDescriptor(Protocol):
    def __get_arg__(self, instance, name: str):
        pass

    def __set_arg__(self, instance, name: str, value):
        pass

    def __del_arg__(self, instance, name: str):
        pass


class DefaultArgumentDescriptor(ArgumentDescriptor):
    def __get_arg__(self, instance, name: str):
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
        try:
            namespace = getattr(instance, ARGCLZ_NAMESPACE)
        except AttributeError:
            namespace = {}
            setattr(instance, ARGCLZ_NAMESPACE, namespace)

        namespace[name] = value

    def __del_arg__(self, instance, name: str):
        try:
            namespace = getattr(instance, ARGCLZ_NAMESPACE)
            del namespace[name]
        except (AttributeError, KeyError):
            pass
