import unittest

from src.hash_table import HashTable


class HashTableTests(unittest.TestCase):
    def test_empty_table_returns_none_for_missing_key(self):
        table = HashTable()

        self.assertEqual(len(table), 0)
        self.assertIsNone(table.get("missing"))
        self.assertNotIn("missing", table)

    def test_insert_lookup_and_update(self):
        table = HashTable()

        table.set("course", "algorithms")
        self.assertEqual(table.get("course"), "algorithms")
        self.assertIn("course", table)
        self.assertEqual(len(table), 1)

        table.set("course", "data structures")
        self.assertEqual(table.get("course"), "data structures")
        self.assertEqual(len(table), 1)

    def test_distinct_keys_in_same_bucket_are_chained(self):
        table = HashTable(capacity=8)
        # With h = ord(character) % 8, "a" and "i" collide.
        table.set("a", "first")
        table.set("i", "second")

        self.assertEqual(table.get("a"), "first")
        self.assertEqual(table.get("i"), "second")
        self.assertEqual(len(table), 2)

    def test_resize_preserves_entries_and_count(self):
        table = HashTable(capacity=8, max_load=0.75)
        entries = [(f"key-{index}", f"value-{index}") for index in range(7)]

        for key, value in entries:
            table.set(key, value)

        self.assertEqual(table.capacity, 16)
        self.assertEqual(len(table), len(entries))
        for key, value in entries:
            with self.subTest(key=key):
                self.assertEqual(table.get(key), value)

    def test_none_max_load_disables_resize(self):
        table = HashTable(capacity=2, max_load=None)
        entries = [("one", "1"), ("two", "2"), ("three", "3")]

        for key, value in entries:
            table.set(key, value)

        self.assertEqual(table.capacity, 2)
        self.assertEqual(len(table), 3)
        for key, value in entries:
            with self.subTest(key=key):
                self.assertEqual(table.get(key), value)


if __name__ == "__main__":
    unittest.main()
