import json
from binteger import Bin

from monolearn.SparseSet import SparseSet


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

        raise TypeError()

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


if __name__ == '__main__':
    o = [SparseSet((1, 2, 3)), Bin(100, 10)]
    print(o)
    o = loads(dumps(o))
    print(o)
    print(type(o[0]))
