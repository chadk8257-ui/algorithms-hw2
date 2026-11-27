import unittest

from src.hash_table import HashTable
from src.linear_probing import LinearProbingHashTable


class HashTableContractTests:
    table_class = HashTable

    def test_empty_table_returns_none_for_missing_key(self):
        table = self.table_class()

        self.assertEqual(len(table), 0)
        self.assertIsNone(table.get("missing"))
        self.assertNotIn("missing", table)

    def test_insert_lookup_and_update(self):
        table = self.table_class()

        table.set("course", "algorithms")
        self.assertEqual(table.get("course"), "algorithms")
        self.assertIn("course", table)
        self.assertEqual(len(table), 1)

        table.set("course", "data structures")
        self.assertEqual(table.get("course"), "data structures")
        self.assertEqual(len(table), 1)

    def test_distinct_keys_in_same_bucket_are_retrievable(self):
        table = self.table_class(capacity=8)
        # "a" and "i" collide because their code points differ by 8.
        table.set("a", "first")
        table.set("i", "second")

        self.assertEqual(table.get("a"), "first")
        self.assertEqual(table.get("i"), "second")
        self.assertEqual(len(table), 2)

    def test_resize_preserves_entries_and_count(self):
        table = self.table_class(capacity=8, max_load=0.75)
        entries = [(f"key-{index}", f"value-{index}") for index in range(7)]

        for key, value in entries:
            table.set(key, value)

        self.assertEqual(table.capacity, 16)
        self.assertEqual(len(table), len(entries))
        for key, value in entries:
            with self.subTest(key=key):
                self.assertEqual(table.get(key), value)

    def test_none_max_load_disables_resize(self):
        table = self.table_class(capacity=3, max_load=None)
        entries = [("one", "1"), ("two", "2"), ("three", "3")]

        for key, value in entries:
            table.set(key, value)

        self.assertEqual(table.capacity, 3)
        self.assertEqual(len(table), len(entries))
        for key, value in entries:
            with self.subTest(key=key):
                self.assertEqual(table.get(key), value)

    def test_delete_removes_existing_and_missing_keys(self):
        table = self.table_class(capacity=8, max_load=None)
        table.set("a", "first")
        table.set("i", "second")

        self.assertTrue(table.delete("a"))
        self.assertFalse(table.delete("missing"))
        self.assertNotIn("a", table)
        self.assertEqual(table.get("i"), "second")
        self.assertEqual(len(table), 1)


class HashTableTests(HashTableContractTests, unittest.TestCase):
    def test_none_max_load_allows_load_factor_over_one(self):
        table = HashTable(capacity=2, max_load=None)
        for key in ("one", "two", "three"):
            table.set(key, key)

        self.assertEqual(table.capacity, 2)
        self.assertEqual(len(table), 3)


class LinearProbingHashTableTests(HashTableContractTests, unittest.TestCase):
    table_class = LinearProbingHashTable

    def test_probe_wraps_from_last_slot_to_zero(self):
        table = self.table_class(capacity=8, max_load=None)
        table.set("g", "last slot")
        table.set("o", "wrapped to zero")

        self.assertEqual(table._index("g"), 7)
        self.assertEqual(table._index("o"), 7)
        self.assertEqual(table.get("g"), "last slot")
        self.assertEqual(table.get("o"), "wrapped to zero")

    def test_tombstone_preserves_probe_chain_and_can_be_reused(self):
        table = self.table_class(capacity=4, max_load=None)
        table.set("a", "first")
        table.set("e", "second")
        table.set("i", "third")

        self.assertTrue(table.delete("e"))
        self.assertEqual(table.get("i"), "third")
        table.set("i", "updated")
        table.set("m", "reuses tombstone")

        self.assertEqual(table.get("i"), "updated")
        self.assertEqual(table.get("m"), "reuses tombstone")
        self.assertEqual(len(table), 3)

    def test_full_table_raises_on_new_key_but_allows_update_and_delete(self):
        table = self.table_class(capacity=3, max_load=None)
        for key in ("a", "b", "c"):
            table.set(key, key.upper())

        table.set("b", "updated")
        with self.assertRaises(OverflowError):
            table.set("d", "D")
        self.assertTrue(table.delete("a"))
        table.set("d", "D")

        self.assertEqual(table.get("b"), "updated")
        self.assertEqual(table.get("d"), "D")
        self.assertEqual(len(table), 3)

    def test_full_table_with_resize_enabled_grows_on_next_insert(self):
        table = self.table_class(capacity=2, max_load=1)
        table.set("a", "A")
        table.set("b", "B")
        table.set("c", "C")

        self.assertEqual(table.capacity, 4)
        self.assertEqual(table.get("a"), "A")
        self.assertEqual(table.get("b"), "B")
        self.assertEqual(table.get("c"), "C")


if __name__ == "__main__":
    unittest.main()
