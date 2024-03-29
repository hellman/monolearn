import os
import shutil
# import json
# import gzip
import bz2
import logging
from tempfile import NamedTemporaryFile

from collections import Counter
from queue import Queue

from monolearn.SparseSet import SparseSet
from monolearn.utils import loads, dumps

from .LevelLearn import LevelCache


class ExtraPrec:
    def reduce(self, vec: SparseSet):
        return vec

    def expand(self, vec: SparseSet):
        return vec


class LowerSetLearn:
    DATA_VERSION = 4
    log = logging.getLogger(f"{__name__}:LowerSetLearn")

    def __init__(
        self,
        n: int,
        file: str = None,
        extra_prec: ExtraPrec = None,
    ):
        self.n = int(n)

        self.file = file
        self.extra_prec = extra_prec

        # "final" vectors, ideally prime elements
        # but not always practical to check/push
        self._lower = set()
        self._upper = set()
        self.is_complete_lower = False
        self.is_complete_upper = False

        self.meta = {}  # info per elements of lower/upper

        self.saved = False
        if self.file and os.path.exists(self.file):
            self.load()

    @property
    def is_complete(self):
        return self.is_complete_lower and self.is_complete_upper

    def set_complete(self):
        self.is_complete_lower = True
        self.is_complete_upper = True
        self.saved = False

    def set_complete_lower(self):
        self.is_complete_lower = True
        self.saved = False

    def set_complete_upper(self):
        self.is_complete_upper = True
        self.saved = False

    def clean(self):
        self.meta = {
            vec: meta for vec, meta in self.meta.items()
            if vec in self._lower or vec in self._upper
        }

    def save(self):
        if self.file and not self.saved:
            try:
                self.save_to_file(self.file)
                self.saved = True
            except KeyboardInterrupt:
                self.log.error(
                    "interrupted saving! trying again, please be patient"
                )
                self.save_to_file(self.file)
                self.saved = True
                raise
        self.log_info()

    def load(self):
        if self.file:
            if self.load_from_file(self.file):
                self.log_info()
                self.saved = True

    def load_from_file(self, filename):
        prevn = self.n
        with bz2.open(filename, "rt") as f:
            try:
                data = loads(f.read())
            except EOFError as err:
                self.log.error(f"loading system {filename} failed: {err}")
                return False
        (
            version,
            self._lower, self._upper,
            self.is_complete_lower, self.is_complete_upper,
            self.meta, self.n,
        ) = data
        assert version == self.DATA_VERSION, "system format updated?"
        assert self.n == prevn
        self.log.info(f"loaded state from file {filename}")
        return True

    def save_to_file(self, filename):
        data = (
            self.DATA_VERSION,
            self._lower, self._upper,
            self.is_complete_lower, self.is_complete_upper,
            self.meta, self.n,
        )

        with NamedTemporaryFile() as f:
            with bz2.open(f.name, "wt") as fz:
                fz.write(dumps(data))

            # does not work across devices...
            # https://stackoverflow.com/questions/42392600/oserror-errno-18-invalid-cross-device-link
            # os.rename(f.name, filename)
            shutil.move(f.name, filename)
            open(f.name, "w").close()
        self.log.info(f"saved state to file {filename}")

    def log_info(self):
        for (name, s) in [
            ("lower", self._lower),
            ("upper", self._upper),
        ]:
            freq = Counter(len(v) for v in s)
            freqstr = " ".join(
                f"{sz}:{cnt}" for sz, cnt in sorted(freq.items())
            )
            self.log.info(f"  {name} {len(s)}: {freqstr}")

        if self.is_complete_lower:
            self.log.info("  system is complete for lower!")
        if self.is_complete_upper:
            self.log.info("  system is complete for upper!")

    def is_known_lower(self, vec):
        return vec in self._lower

    def is_known_upper(self, vec):
        return vec in self._upper

    def add_lower(self, vec, meta=None, is_prime=False):
        assert isinstance(vec, SparseSet)

        if self.extra_prec:
            vec = self.extra_prec.expand(vec)

        # in case of interrupt, consistency is kept
        if not self.is_known_lower(vec):
            self.saved = False

            if meta is not None:
                self.meta[vec] = meta

            self._lower.add(vec)

    def add_upper(self, vec, meta=None, is_prime=False):
        assert isinstance(vec, SparseSet)

        if self.extra_prec:
            vec = self.extra_prec.reduce(vec)

        # in case of interrupt, consistency is kept
        if not self.is_known_upper(vec):
            self.saved = False

            if meta is not None:
                self.meta[vec] = meta

            self._upper.add(vec)

    def iter_lower(self):
        return iter(self._lower)

    def iter_upper(self):
        return iter(self._upper)

    def n_lower(self):
        return len(self._lower)

    def n_upper(self):
        return len(self._upper)


def support(pt):
    return SparseSet(i for i, v in enumerate(pt) if v)


class ExtraPrec_LowerSet(ExtraPrec):
    def __init__(self, int2point: list, point2int: map):
        self.int2point = [support(v) for v in int2point]
        self.point2int = {support(v): i for v, i in point2int.items()}

    def reduce(self, vec: SparseSet):
        """MaxSet"""
        res = set()
        qs = [self.int2point[i] for i in vec]
        assert all(isinstance(q, SparseSet) for q in qs)
        for pi, p in enumerate(qs):
            if not any(p < q for q in qs):
                res.add(self.point2int[p])
        return SparseSet(res)

    def expand(self, vec: SparseSet):
        """LowerClosure"""
        res = set()
        qs = [self.int2point[i] for i in vec]
        assert all(isinstance(q, SparseSet) for q in qs)

        # simple BFS-like algorithm
        pq = Queue()
        for q in qs:
            pq.put(q)

        visited = set(qs)
        while pq.qsize():
            q = pq.get()
            for sub in q.neibs_down():
                if sub not in visited:
                    visited.add(sub)
                    pq.put(sub)
        res = []
        for q in visited:
            if q in self.point2int:
                res.append(self.point2int[q])
        return SparseSet(res)


class Oracle:
    class UnknownMeta:
        pass

    def __init__(self):
        self._lower_cache = LevelCache()
        self._upper_cache = LevelCache()
        self._cache = {}
        self.n_calls = 0
        self.n_queries = 0

    def disable_cache(self):
        self._cache = None

    def clean(self, levels=True, main=True):
        if levels:
            self._lower_cache = LevelCache()
            self._upper_cache = LevelCache()
        if main:
            self._cache = {}

    @property
    def data(self):
        return (
            self._lower_cache,
            self._upper_cache,
            self._cache,
        )

    @data.setter
    def data(self, data):
        (
            self._lower_cache,
            self._upper_cache,
            self._cache,
        ) = data

    def __call__(self, vec: SparseSet):
        self.n_calls += 1
        if self._cache and vec in self._cache:
            return self._cache[vec]

        if self._lower_cache.has(vec):
            meta = self._lower_cache.meta.get(vec, self.UnknownMeta)
            return True, meta

        if self._upper_cache.has(vec):
            meta = self._upper_cache.meta.get(vec, self.UnknownMeta)
            return False, meta

        self.n_queries += 1
        ret = self._query(vec)
        if self._cache is not None:
            self._cache[vec] = ret
        return ret


class OracleFunction(Oracle):
    def __init__(self, func):
        self.func = func
        super().__init__()

    def _query(self, vec: SparseSet):
        return self.func(vec), None


class OracleFunctionWithMeta(Oracle):
    def __init__(self, func):
        self.func = func
        super().__init__()

    def _query(self, vec: SparseSet):
        return self.func(vec)
