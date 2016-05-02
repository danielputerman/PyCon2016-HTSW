"""Utility functions for meta-programming"""

import types


def create_proxy_property(property_name, target_name, is_settable=False):
    """
    Creates a property object which forwards "name" to target.
    """
    # noinspection PyUnusedLocal
    def _proxy_get(self):
        return getattr(getattr(self, target_name), property_name)

    # noinspection PyUnusedLocal
    def _proxy_set(self, val):
        return setattr(getattr(self, target_name), property_name, val)

    if not is_settable:
        return property(_proxy_get)
    else:
        return property(_proxy_get, _proxy_set)


def create_forwarded_method(from_, to, func_name):
    """
    Creates a method(i.e., bound func) to be set on 'from_', which activates 'func_name' on 'to'.
    """
    # noinspection PyUnusedLocal
    def forwarded_method(self_, *args, **kwargs):
        return getattr(to, func_name)(*args, **kwargs)

    return types.MethodType(forwarded_method, from_)


def create_proxy_interface(from_, to, ignore_list=None, override_existing=False):
    """
    Copies the public interface of the destination object, excluding names in the ignore_list,
    and creates an identical interface in 'src', which forwards calls to dst.
    If 'override_existing' is False, then attributes already existing in 'src' will not be
    overridden.
    """
    if not ignore_list:
        ignore_list = []
    for attr_name in dir(to):
        if not attr_name.startswith('_') and not attr_name in ignore_list:
            if callable(getattr(to, attr_name)):
                if override_existing or not hasattr(from_, attr_name):
                    setattr(from_, attr_name, create_forwarded_method(from_, to, attr_name))
