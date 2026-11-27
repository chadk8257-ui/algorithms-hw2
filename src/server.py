"""Standard-library HTTP interface for the URL shortener."""

import argparse
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import sys
from urllib.parse import parse_qsl, quote, unquote, urlsplit

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.hash_table import HashTable
from src.linear_probing import LinearProbingHashTable
from src.shortener import Shortener


MAX_FORM_BYTES = 1_048_576
Table = HashTable[str] | LinearProbingHashTable[str]


def _page(title: str, content: str) -> str:
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<title>{escape(title)}</title></head><body>"
        f"<main><h1>{escape(title)}</h1>{content}</main></body></html>"
    )


def _hash_explanation(key: str, capacity: int) -> tuple[int, str]:
    result = 0
    steps = ["h = 0"]
    for character in key:
        code_point = ord(character)
        previous = result
        result = (31 * result + code_point) % capacity
        steps.append(
            f"(31 * {previous} + {code_point}) mod {capacity} = {result}"
        )
    return result, "; ".join(steps)


def _render_hash_table(label: str, table: Table) -> str:
    sections = [f"<h2>{escape(label)}</h2>"]
    if isinstance(table, HashTable):
        for bucket_index, bucket in enumerate(table._buckets):
            sections.append(
                f'<section><h3>Bucket {bucket_index}</h3><ol>'
            )
            entry = bucket
            if entry is None:
                sections.append("<li><em>Empty</em></li>")

            while entry is not None:
                key = entry.key
                home_index, calculation = _hash_explanation(key, table.capacity)
                path = []
                visited = bucket
                while visited is not None:
                    path.append(visited.key)
                    if visited is entry:
                        break
                    visited = visited.next
                visited_keys = " -> ".join(
                    f'"{escape(visited_key, quote=True)}"' for visited_key in path
                )
                sections.append(
                    "<li>"
                    f"<code>key={escape(key, quote=True)}</code> "
                    f"<code>value={escape(str(entry.value), quote=True)}</code><br>"
                    f"<small>Horner: {escape(calculation)}; "
                    f"bucket index = {home_index}; search path: "
                    f"bucket {bucket_index} [{visited_keys}]</small>"
                    "</li>"
                )
                entry = entry.next

            sections.append("</ol></section>")
        return "".join(sections)

    for slot_index, slot in enumerate(table._slots):
        sections.append(f'<section><h3>Slot {slot_index}</h3>')
        if slot is None:
            sections.append("<em>Empty</em></section>")
            continue
        if not hasattr(slot, "key"):
            sections.append("<em>Tombstone</em></section>")
            continue

        key = slot.key
        home_index, calculation = _hash_explanation(key, table.capacity)
        path = []
        index = home_index
        for _ in range(table.capacity):
            path.append(index)
            if index == slot_index:
                break
            index = (index + 1) % table.capacity
        visited_slots = " -> ".join(str(index) for index in path)
        sections.append(
            "<p>"
            f"<code>key={escape(key, quote=True)}</code> "
            f"<code>value={escape(str(slot.value), quote=True)}</code><br>"
            f"<small>Horner: {escape(calculation)}; home slot = {home_index}; "
            f"probe path: {visited_slots}</small></p></section>"
        )
    return "".join(sections)


def _table_for_strategy(table: Table, strategy: str) -> Table:
    if strategy == "chaining" and isinstance(table, HashTable):
        return table
    if strategy == "linear_probing" and isinstance(table, LinearProbingHashTable):
        return table

    target: Table
    if strategy == "chaining":
        target = HashTable(capacity=table.capacity, max_load=None)
    else:
        target = LinearProbingHashTable(capacity=table.capacity, max_load=None)
    for key, value in table.items():
        target.set(key, value)
    return target


def _render_table_page(shortener: Shortener, selection: str) -> str:
    options = (
        ("both", "Both strategies"),
        ("chaining", "Separate chaining"),
        ("linear_probing", "Linear probing"),
    )
    selector = [
        '<form method="get" action="/table"><label for="strategy">'
        "Display strategy</label> <select id=\"strategy\" name=\"strategy\">"
    ]
    for value, label in options:
        selected = ' selected="selected"' if value == selection else ""
        selector.append(
            f'<option value="{value}"{selected}>{escape(label)}</option>'
        )
    selector.append('<button type="submit">Show</button></form>')

    strategies = ("chaining", "linear_probing") if selection == "both" else (selection,)
    content = [
        "".join(selector),
        "<p>Search paths show the bucket-chain nodes or linearly probed slots "
        "visited. Horner steps use h = (31 * h + ord(character)) mod capacity.</p>",
    ]
    for strategy in strategies:
        url_table = _table_for_strategy(shortener._url_to_code, strategy)
        code_table = _table_for_strategy(shortener._code_to_url, strategy)
        title = "Separate chaining" if strategy == "chaining" else "Linear probing"
        content.extend(
            [
                f"<h2>{title}</h2>",
                _render_hash_table("URL to code", url_table),
                _render_hash_table("Code to URL", code_table),
            ]
        )
    return _page("Hash table", "".join(content))


def _valid_host(host: str) -> bool:
    if not host or any(character.isspace() or ord(character) < 32 for character in host):
        return False
    if any(character in host for character in "/?#@\\"):
        return False
    try:
        parsed = urlsplit(f"//{host}")
        parsed.port
        return (
            bool(parsed.hostname)
            and not parsed.path
            and not parsed.query
            and not parsed.fragment
            and not host.endswith(":")
        )
    except ValueError:
        return False


def create_server(
    host: str = "", port: int = 8000, shortener: Shortener | None = None
) -> HTTPServer:
    """Create an HTTP server, optionally reusing a shortener for tests."""
    url_shortener = shortener if shortener is not None else Shortener()

    class RequestHandler(BaseHTTPRequestHandler):
        def _send_html(self, status: int, body: str) -> None:
            encoded = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def _public_base_url(self) -> str:
            forwarded_host = self.headers.get("X-Forwarded-Host")
            public_host = (
                forwarded_host.split(",", 1)[0].strip()
                if forwarded_host is not None
                else ""
            )
            if not public_host:
                public_host = self.headers.get("Host", "").strip()
            if not _valid_host(public_host):
                raise ValueError("request host is missing or invalid")

            forwarded_proto = self.headers.get("X-Forwarded-Proto")
            public_proto = (
                forwarded_proto.split(",", 1)[0].strip().lower()
                if forwarded_proto is not None
                else "http"
            )
            if public_proto not in ("http", "https"):
                raise ValueError("request protocol must be HTTP or HTTPS")
            return f"{public_proto}://{public_host}"

        def do_GET(self) -> None:
            path = urlsplit(self.path).path
            if path == "/":
                content = (
                    '<form method="post" action="/">'
                    '<label for="url">URL</label> '
                    '<input id="url" name="url" type="url" required> '
                    '<button type="submit">Shorten</button></form>'
                    '<p><a href="/table">View hash table</a></p>'
                )
                self._send_html(200, _page("URL shortener", content))
                return

            if path == "/table":
                selection = next(
                    (
                        value
                        for name, value in parse_qsl(urlsplit(self.path).query)
                        if name == "strategy"
                    ),
                    "both",
                )
                if selection not in ("both", "chaining", "linear_probing"):
                    self._send_html(
                        400,
                        _page("Bad request", "<p>Unknown table strategy.</p>"),
                    )
                    return
                self._send_html(
                    200, _render_table_page(url_shortener, selection)
                )
                return

            if not path.startswith("/") or "/" in path[1:]:
                self._send_html(404, _page("Not found", "<p>Not found</p>"))
                return

            code = unquote(path[1:])
            try:
                destination = url_shortener.expand(code)
            except KeyError:
                self._send_html(404, _page("Not found", "<p>Not found</p>"))
                return

            location = quote(destination, safe=":/?#[]@!$&'()*+,;=%")
            self.send_response(302)
            self.send_header("Location", location)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_POST(self) -> None:
            if urlsplit(self.path).path != "/":
                self._send_html(404, _page("Not found", "<p>Not found</p>"))
                return

            try:
                content_length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._send_html(400, _page("Bad request", "<p>Invalid form data.</p>"))
                return
            if content_length < 0 or content_length > MAX_FORM_BYTES:
                self._send_html(400, _page("Bad request", "<p>Invalid form data.</p>"))
                return

            try:
                form_body = self.rfile.read(content_length).decode("utf-8")
                fields = parse_qsl(
                    form_body,
                    keep_blank_values=True,
                    max_num_fields=20,
                    encoding="utf-8",
                    errors="strict",
                )
            except (UnicodeDecodeError, ValueError):
                self._send_html(400, _page("Bad request", "<p>Invalid form data.</p>"))
                return

            submitted_url = next(
                (value for name, value in fields if name == "url"), ""
            )
            try:
                code = url_shortener.shorten(submitted_url)
            except ValueError as error:
                content = f"<p>Error: {escape(str(error))}</p><p><a href=\"/\">Try again</a></p>"
                self._send_html(400, _page("Invalid URL", content))
                return

            try:
                short_url = f"{self._public_base_url()}/{code}"
            except ValueError as error:
                self._send_html(400, _page("Bad request", f"<p>{escape(str(error))}</p>"))
                return

            content = (
                "<p>Your shortened URL:</p>"
                f'<p><a href="{escape(short_url, quote=True)}">'
                f"{escape(short_url)}</a></p>"
                f'<p>Code: <code>{escape(code)}</code></p>'
                '<p><a href="/">Shorten another URL</a></p>'
            )
            self._send_html(200, _page("Short URL created", content))

    return HTTPServer((host, port), RequestHandler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the URL shortener web server.")
    parser.add_argument("--port", type=int, default=8000)
    arguments = parser.parse_args()
    server = create_server(port=arguments.port)
    print(
        f"Serving on http://{server.server_address[0]}:{server.server_address[1]}",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
