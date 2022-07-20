import json
import math
import time
import logging
from functools import wraps

from binteger import Bin

from monolearn.SparseSet import SparseSet

log = logging.getLogger(__name__)

CLASSES = {"SparseSet": SparseSet}


def truncrepr(s, n=100):
    s = repr(s)
    if len(s) > n:
        s = s[:n] + "..."
    return s


def truncstr(s, n=100):
    s = str(s)
    if len(s) > n:
        s = s[:n] + "..."
    return s


def dictify(obj):
    if hasattr(obj, "__dictify__"):
        return {"t": type(obj).__name__, "l": obj.__dictify__()}
    if isinstance(obj, set):
        return {"t": "set", "l": tuple(map(dictify, obj))}
    if isinstance(obj, tuple) and not type(obj) == tuple:
        return {"t": type(obj).__name__, "l": tuple(map(dictify, obj))}
    if isinstance(obj, list) and not type(obj) == list:
        return {"t": type(obj).__name__, "l": list(map(dictify, obj))}
    if isinstance(obj, Bin):
        return {"t": "Bin", "x": obj.int, "n": obj.n}

    if isinstance(obj, dict):
        # to allow dicts in keys (hashable)
        return {
            "t": "dict",
            "d": [(dictify(k), dictify(v)) for k, v in obj.items()]
        }
    if isinstance(obj, tuple):
        return tuple(dictify(v) for v in obj)
    if isinstance(obj, list):
        return list(dictify(v) for v in obj)
    return obj


def undictify(obj):
    if isinstance(obj, dict):
        t = obj["t"]
        if t == "dict":
            return {undictify(k): undictify(v) for k, v in obj["d"]}
        elif t == "set":
            return set(map(undictify, obj["l"]))
        elif t == "Bin":
            return Bin(obj["x"], obj["n"])
        elif t in CLASSES:
            return CLASSES[t](obj["l"])

        raise TypeError(f"Unrecognized type {t}")

    if isinstance(obj, tuple):
        return tuple(undictify(v) for v in obj)
    if isinstance(obj, list):
        return list(undictify(v) for v in obj)
    return obj


def dictify_add_class(cls):
    # hacks..
    name = cls.__name__
    if CLASSES.get(name, cls) is not cls:
        raise KeyError(
            f"dictify already has class for {name}: {CLASSES[name]}"
        )
    CLASSES[name] = cls
    return cls


def dumps(obj):
    return json.dumps(dictify(obj))


def loads(s):
    return undictify(json.loads(s))



class TimeStat:
    Stat = {}

    def __init__(self):
        self.n_calls = 0
        self.total_time = 0

    def __str__(self):
        if self.n_calls == 0:
            return "TimeStat:N/A"
        return (
            "["
            f"2^{math.log(self.n_calls,2):5.2f} calls"
            f" x {self.total_time / self.n_calls:.3f}s avg"
            f" = {self.total_time:10.1f}s"
            "]"
        )

    def add(self, time: float, num=1):
        self.n_calls += num
        self.total_time += time

    __repr__ = __str__

    def reset(self):
        self.n_calls = 0
        self.total_time = 0

    @classmethod
    def log(cls, func):
        try:
            name = func.__qualname__
        except AttributeError:
            name = type(func).__qualname__

        if name in TimeStat.Stat:
            log.warning(f"double time_stat? {func}")
        else:
            cls.Stat[name] = cls()

        @wraps(func)
        def time_func(*args, **kwargs):
            t0 = time.time()
            ret = func(*args, **kwargs)
            t = time.time() - t0

            cls.Stat[name].add(time=t)
            return ret
        return time_func

    def __bool__(self):
        return self.n_calls > 0


if __name__ == '__main__':
    o = [SparseSet((1, 2, 3)), Bin(100, 10)]
    print(o)
    o = loads(dumps(o))
    print(o)
    print(type(o[0]))
