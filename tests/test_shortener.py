import unittest

from src.shortener import Shortener


class ShortenerTests(unittest.TestCase):
    def setUp(self):
        self.shortener = Shortener()

    def test_http_and_https_urls_round_trip(self):
        urls = (
            "http://example.com/path",
            "https://example.com/another-path?query=value",
        )

        for url in urls:
            with self.subTest(url=url):
                code = self.shortener.shorten(url)
                self.assertEqual(self.shortener.expand(code), url)

    def test_strips_surrounding_whitespace_before_storing(self):
        code = self.shortener.shorten("  https://example.com/page  ")

        self.assertEqual(self.shortener.expand(code), "https://example.com/page")

    def test_duplicate_url_reuses_code_and_distinct_url_gets_another(self):
        first_code = self.shortener.shorten("https://example.com/page")
        duplicate_code = self.shortener.shorten("https://example.com/page")
        other_code = self.shortener.shorten("https://example.com/other")

        self.assertEqual(first_code, duplicate_code)
        self.assertNotEqual(first_code, other_code)
        self.assertEqual(self.shortener.expand(first_code), "https://example.com/page")
        self.assertEqual(self.shortener.expand(other_code), "https://example.com/other")

    def test_unknown_code_raises_key_error(self):
        with self.assertRaises(KeyError):
            self.shortener.expand("unknown")

    def test_rejects_invalid_urls(self):
        invalid_urls = (
            "",
            "   ",
            "/relative/path",
            "ftp://example.com/file",
            "https:///missing-host",
            "https://example.com/path with space",
            "https://example.com/" + "a" * 2049,
        )

        for url in invalid_urls:
            with self.subTest(url=url[:40]):
                with self.assertRaises(ValueError):
                    self.shortener.shorten(url)


if __name__ == "__main__":
    unittest.main()
