"""URL shortening backed by the project's custom hash table."""

from typing import Literal
from urllib.parse import urlsplit

from src.base62 import encode
from src.hash_table import HashTable
from src.linear_probing import LinearProbingHashTable


class Shortener:
    """Assign deterministic base62 codes to valid HTTP(S) URLs."""

    def __init__(
        self, table_type: Literal["chaining", "linear_probing"] = "chaining"
    ) -> None:
        if table_type == "chaining":
            table_class = HashTable
        elif table_type == "linear_probing":
            table_class = LinearProbingHashTable
        else:
            raise ValueError("table_type must be 'chaining' or 'linear_probing'")

        self._url_to_code: HashTable[str] | LinearProbingHashTable[str] = table_class()
        self._code_to_url: HashTable[str] | LinearProbingHashTable[str] = table_class()
        self._next_id = 0

    def shorten(self, url: str) -> str:
        if not isinstance(url, str):
            raise TypeError("url must be a string")

        normalized_url = url.strip()
        self._validate_url(normalized_url)

        existing_code = self._url_to_code.get(normalized_url)
        if existing_code is not None:
            return existing_code

        code = encode(self._next_id)
        self._next_id += 1
        self._url_to_code.set(normalized_url, code)
        self._code_to_url.set(code, normalized_url)
        return code

    def expand(self, code: str) -> str:
        if code not in self._code_to_url:
            raise KeyError(code)
        url = self._code_to_url.get(code)
        if url is None:
            raise KeyError(code)
        return url

    @staticmethod
    def _validate_url(url: str) -> None:
        if not url:
            raise ValueError("url must not be empty")
        if len(url) > 2048:
            raise ValueError("url must not exceed 2048 characters")
        if any(character.isspace() for character in url):
            raise ValueError("url must not contain whitespace")

        try:
            parsed = urlsplit(url)
            hostname = parsed.hostname
            parsed.port
        except ValueError as error:
            raise ValueError("url is invalid") from error

        if parsed.scheme.lower() not in ("http", "https") or not hostname:
            raise ValueError("url must be an absolute HTTP(S) URL with a host")
