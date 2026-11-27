"""A string-keyed hash table using separate chaining and Horner hashing."""

from typing import Generic, TypeVar


Value = TypeVar("Value")


class _Entry(Generic[Value]):
    __slots__ = ("key", "value", "next")

    def __init__(
        self, key: str, value: Value, next_entry: "_Entry[Value] | None" = None
    ) -> None:
        self.key = key
        self.value = value
        self.next = next_entry


class HashTable(Generic[Value]):
    """Store values by string key in separate-chaining buckets."""

    def __init__(self, capacity: int = 8, max_load: float | None = 0.75) -> None:
        if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        if max_load is not None and max_load <= 0:
            raise ValueError("max_load must be positive or None")

        self.capacity = capacity
        self.max_load = max_load
        self._size = 0
        self._buckets: list[_Entry[Value] | None] = [None] * capacity

    def _index(self, key: str, capacity: int | None = None) -> int:
        if not isinstance(key, str):
            raise TypeError("key must be a string")
        modulus = self.capacity if capacity is None else capacity
        result = 0
        for character in key:
            result = (31 * result + ord(character)) % modulus
        return result

    def _find(self, key: str) -> _Entry[Value] | None:
        index = self._index(key)
        entry = self._buckets[index]
        while entry is not None:
            if entry.key == key:
                return entry
            entry = entry.next
        return None

    def set(self, key: str, value: Value) -> None:
        entry = self._find(key)
        if entry is not None:
            entry.value = value
            return

        index = self._index(key)
        self._buckets[index] = _Entry(key, value, self._buckets[index])
        self._size += 1

        if self.max_load is not None and self._size / self.capacity > self.max_load:
            self._resize()

    def get(self, key: str) -> Value | None:
        entry = self._find(key)
        return None if entry is None else entry.value

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        return self._find(key) is not None

    def __len__(self) -> int:
        return self._size

    def _resize(self) -> None:
        old_buckets = self._buckets
        self.capacity *= 2
        self._buckets = [None] * self.capacity

        for bucket in old_buckets:
            entry = bucket
            while entry is not None:
                next_entry = entry.next
                index = self._index(entry.key)
                entry.next = self._buckets[index]
                self._buckets[index] = entry
                entry = next_entry
