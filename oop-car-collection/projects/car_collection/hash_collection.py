from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, Iterable, Iterator, List, Optional, Tuple, TypeVar
import json
from pathlib import Path

K = TypeVar("K")
V = TypeVar("V")


@dataclass
class _Entry(Generic[K, V]):
    key: K
    value: V


class HashCollection(Generic[K, V]):
    """
    Собственная реализация хеш-таблицы (цепочки).
    Запрещено использовать dict/set для хранения данных — здесь только list.
    """

    def __init__(
        self,
        other: Optional["HashCollection[K, V]"] = None,
        initial_capacity: int = 16,
        hash_func: Callable[[K], int] = hash,
    ) -> None:
        if initial_capacity < 4:
            initial_capacity = 4
        self._hash_func = hash_func
        self._size = 0
        self._buckets: List[List[_Entry[K, V]]] = [[] for _ in range(initial_capacity)]

        if other is not None:
            for k, v in other.items():
                self.add(k, v)

    def __del__(self) -> None:
        self.clear()

    def copy(self) -> "HashCollection[K, V]":
        return HashCollection(self)

    def _bucket_index(self, key: K) -> int:
        h = self._hash_func(key)
        return (h & 0x7FFFFFFF) % len(self._buckets)

    def _maybe_rehash(self) -> None:
        if self._size <= int(0.75 * len(self._buckets)):
            return

        old_items = list(self.items())
        new_capacity = len(self._buckets) * 2
        self._buckets = [[] for _ in range(new_capacity)]
        self._size = 0
        for k, v in old_items:
            self.add(k, v)

    def add(self, key: K, value: V) -> None:
        if key is None:
            raise ValueError("key must not be None")

        idx = self._bucket_index(key)
        bucket = self._buckets[idx]
        for entry in bucket:
            if entry.key == key:
                entry.value = value
                return
        bucket.append(_Entry(key, value))
        self._size += 1
        self._maybe_rehash()

    def __lshift__(self, pair: Tuple[K, V]) -> "HashCollection[K, V]":
        k, v = pair
        self.add(k, v)
        return self

    def remove(self, key: K) -> bool:
        idx = self._bucket_index(key)
        bucket = self._buckets[idx]
        for i, entry in enumerate(bucket):
            if entry.key == key:
                bucket.pop(i)
                self._size -= 1
                return True
        return False

    def clear(self) -> None:
        for b in self._buckets:
            b.clear()
        self._size = 0

    def count(self) -> int:
        return self._size

    def __len__(self) -> int:
        return self._size

    def contains(self, key: K) -> bool:
        return self._find_entry(key) is not None

    def __contains__(self, key: K) -> bool:
        return self.contains(key)

    def _find_entry(self, key: K) -> Optional[_Entry[K, V]]:
        idx = self._bucket_index(key)
        for entry in self._buckets[idx]:
            if entry.key == key:
                return entry
        return None

    def __getitem__(self, key: K) -> V:
        entry = self._find_entry(key)
        if entry is None:
            raise KeyError(key)
        return entry.value

    def __setitem__(self, key: K, value: V) -> None:
        self.add(key, value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, HashCollection):
            return False
        if len(self) != len(other):
            return False
        for k, v in self.items():
            if not other.contains(k):
                return False
            if other[k] != v:
                return False
        return True

    def __and__(self, other: "HashCollection[K, V]") -> "HashCollection[K, V]":
        out: HashCollection[K, V] = HashCollection(initial_capacity=8, hash_func=self._hash_func)
        for k, v in self.items():
            if other.contains(k) and other[k] == v:
                out.add(k, v)
        return out

    def items(self) -> Iterator[Tuple[K, V]]:
        for bucket in self._buckets:
            for entry in bucket:
                yield entry.key, entry.value

    def keys(self) -> Iterator[K]:
        for k, _ in self.items():
            yield k

    def values(self) -> Iterator[V]:
        for _, v in self.items():
            yield v

    def save(self, path: str | Path, serializer: Callable[[V], object]) -> None:
        p = Path(path)
        data = []
        for k, v in self.items():
            data.append([k, serializer(v)])
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self, path: str | Path, deserializer: Callable[[object], V]) -> None:
        p = Path(path)
        raw = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("Invalid collection file format")
        self.clear()
        for item in raw:
            if not (isinstance(item, list) and len(item) == 2):
                raise ValueError("Invalid entry format")
            k = item[0]
            v = deserializer(item[1])
            self.add(k, v)
