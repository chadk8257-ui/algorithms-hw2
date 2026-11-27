import unittest

from src.base62 import decode, encode


class Base62Tests(unittest.TestCase):
    def test_zero_round_trips_as_zero(self):
        self.assertEqual(encode(0), "0")
        self.assertEqual(decode("0"), 0)

    def test_digits_and_alphabet_boundaries(self):
        self.assertEqual(encode(61), "Z")
        self.assertEqual(encode(62), "10")
        self.assertEqual(decode("z"), 35)
        self.assertEqual(decode("Z"), 61)

    def test_large_integer_round_trips(self):
        number = 2**128
        self.assertEqual(decode(encode(number)), number)

    def test_rejects_invalid_values(self):
        for value in (-1,):
            with self.subTest(value=value), self.assertRaises(ValueError):
                encode(value)
        for code in ("", "a-"):
            with self.subTest(code=code), self.assertRaises(ValueError):
                decode(code)

    def test_rejects_wrong_types(self):
        with self.assertRaises(TypeError):
            encode("1")
        with self.assertRaises(TypeError):
            decode(1)


if __name__ == "__main__":
    unittest.main()
