"""A string-keyed hash table using linear probing and tombstones."""

from typing import Generic, Iterator, TypeVar


Value = TypeVar("Value")


class _Tombstone:
    __slots__ = ()


_TOMBSTONE = _Tombstone()


class LinearProbingHashTable(Generic[Value]):
    """Store values in an open-addressed table with linear probing."""

    def __init__(self, capacity: int = 8, max_load: float | None = 0.75) -> None:
        if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        if max_load is not None and max_load <= 0:
            raise ValueError("max_load must be positive or None")

        self.capacity = capacity
        self.max_load = max_load
        self._size = 0
        self._tombstones = 0
        self._slots: list[_Entry[Value] | _Tombstone | None] = [None] * capacity

    def _index(self, key: str) -> int:
        if not isinstance(key, str):
            raise TypeError("key must be a string")
        result = 0
        for character in key:
            result = (31 * result + ord(character)) % self.capacity
        return result

    def _find_index(self, key: str) -> int | None:
        index = self._index(key)
        for _ in range(self.capacity):
            slot = self._slots[index]
            if slot is None:
                return None
            if slot is not _TOMBSTONE and slot.key == key:
                return index
            index = (index + 1) % self.capacity
        return None

    def set(self, key: str, value: Value) -> None:
        start = self._index(key)
        first_tombstone = None
        index = start

        for _ in range(self.capacity):
            slot = self._slots[index]
            if slot is None:
                insertion_index = (
                    first_tombstone if first_tombstone is not None else index
                )
                self._insert_at(insertion_index, key, value)
                return
            if slot is _TOMBSTONE:
                if first_tombstone is None:
                    first_tombstone = index
            elif slot.key == key:
                slot.value = value
                return
            index = (index + 1) % self.capacity

        if first_tombstone is not None:
            self._insert_at(first_tombstone, key, value)
            return
        if self.max_load is not None:
            self._resize()
            self.set(key, value)
            return
        raise OverflowError("hash table is full")

    def _insert_at(self, index: int, key: str, value: Value) -> None:
        if self._slots[index] is _TOMBSTONE:
            self._tombstones -= 1
        self._slots[index] = _Entry(key, value)
        self._size += 1
        if self.max_load is not None and self._size / self.capacity > self.max_load:
            self._resize()

    def get(self, key: str) -> Value | None:
        index = self._find_index(key)
        if index is None:
            return None
        slot = self._slots[index]
        if slot is None or slot is _TOMBSTONE:
            return None
        return slot.value

    def delete(self, key: str) -> bool:
        index = self._find_index(key)
        if index is None:
            return False
        self._slots[index] = _TOMBSTONE
        self._size -= 1
        self._tombstones += 1
        return True

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        return self._find_index(key) is not None

    def __len__(self) -> int:
        return self._size

    def items(self) -> Iterator[tuple[str, Value]]:
        for slot in self._slots:
            if slot is not None and slot is not _TOMBSTONE:
                yield slot.key, slot.value

    def _resize(self) -> None:
        old_slots = self._slots
        self.capacity *= 2
        self._slots = [None] * self.capacity
        self._size = 0
        self._tombstones = 0

        for slot in old_slots:
            if slot is not None and slot is not _TOMBSTONE:
                self._insert_without_resize(slot.key, slot.value)

    def _insert_without_resize(self, key: str, value: Value) -> None:
        index = self._index(key)
        for _ in range(self.capacity):
            if self._slots[index] is None:
                self._slots[index] = _Entry(key, value)
                self._size += 1
                return
            index = (index + 1) % self.capacity
        raise RuntimeError("resized table has no free slot")


class _Entry(Generic[Value]):
    __slots__ = ("key", "value")

    def __init__(self, key: str, value: Value) -> None:
        self.key = key
        self.value = value
