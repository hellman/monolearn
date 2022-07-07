import json
from binteger import Bin

from monolearn.SparseSet import SparseSet


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
    if isinstance(obj, set):
        return {"t": "set", "l": tuple(map(dictify, obj))}
    elif isinstance(obj, SparseSet):
        return {"t": "SparseSet", "l": tuple(obj)}
    elif isinstance(obj, Bin):
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
        elif t == "SparseSet":
            return SparseSet(obj["l"])
        elif t == "Bin":
            return Bin(obj["x"], obj["n"])
        raise TypeError()

    if isinstance(obj, tuple):
        return tuple(undictify(v) for v in obj)
    if isinstance(obj, list):
        return list(undictify(v) for v in obj)
    return obj


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
