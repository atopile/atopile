#%%
import functools

class Field:
    def __init__(self, default_func) -> None:
        self.default_func = default_func

    def __get__(self, instance, objtype=None):
        return self.df(instance)

    def __set__(self, instance, value):
        print(f"set {value}")

    def __delete__(self, instance):
        print("del")

def field(f):
    print(f.__name__)
    return Field(f)

class A:
    def __init__(self, config_data) -> None:
        self._config_data = config_data

    @field
    def path(self, data):
        return data

# %%
