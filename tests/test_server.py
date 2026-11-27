import http.client
import subprocess
import sys
import threading
import unittest
from pathlib import Path
from urllib.parse import urlencode

from src.server import create_server
from src.shortener import Shortener


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.shortener = Shortener()
        self.server = create_server(port=0, shortener=self.shortener)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()
        self.host, self.port = self.server.server_address

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection(self.host, self.port)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        result = response.status, response.getheaders(), response.read()
        connection.close()
        return result

    def test_home_page_contains_url_form(self):
        status, _, body = self.request("GET", "/")

        self.assertEqual(status, 200)
        self.assertIn(b'<form method="post" action="/">', body)
        self.assertIn(b'name="url"', body)

    def test_post_shortens_url_and_uses_forwarded_headers(self):
        body = urlencode({"url": "https://example.com/page"})
        status, _, response_body = self.request(
            "POST",
            "/",
            body=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Content-Length": str(len(body)),
                "Host": "internal.example:8000",
                "X-Forwarded-Host": "short.example, proxy.internal",
                "X-Forwarded-Proto": "https, http",
            },
        )

        self.assertEqual(status, 200)
        self.assertIn(b"https://short.example/0", response_body)
        self.assertEqual(self.shortener.expand("0"), "https://example.com/page")

    def test_post_invalid_url_returns_escaped_error(self):
        body = urlencode({"url": "<script>alert(1)</script>"})
        status, _, response_body = self.request(
            "POST",
            "/",
            body=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        self.assertEqual(status, 400)
        self.assertIn(b"Invalid URL", response_body)
        self.assertNotIn(b"<script>", response_body)

    def test_short_link_uses_host_header_when_forwarded_host_is_absent(self):
        body = urlencode({"url": "https://example.com/redirect"})
        status, _, response_body = self.request(
            "POST",
            "/",
            body=body,
            headers={"Host": "public.example:8080"},
        )

        self.assertEqual(status, 200)
        self.assertIn(b"http://public.example:8080/0", response_body)

    def test_redirect_forwards_to_original_url_and_unknown_code_is_404(self):
        code = self.shortener.shorten("https://example.com/redirect")
        status, headers, _ = self.request("GET", f"/{code}")

        self.assertEqual(status, 302)
        self.assertIn(("Location", "https://example.com/redirect"), headers)

        status, _, body = self.request("GET", "/not-registered")
        self.assertEqual(status, 404)
        self.assertIn(b"Not found", body)

    def test_invalid_forwarded_host_is_rejected(self):
        body = urlencode({"url": "https://example.com/redirect"})
        status, _, _ = self.request(
            "POST",
            "/",
            body=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Content-Length": str(len(body)),
                "X-Forwarded-Host": "public.example/invalid",
            },
        )

        self.assertEqual(status, 400)

    def test_table_shows_chains_horner_steps_and_escaped_keys(self):
        self.shortener.shorten("https://example.com/<script>alert(1)</script>")
        status, _, body = self.request("GET", "/table")

        self.assertEqual(status, 200)
        self.assertIn(b"Bucket 0", body)
        self.assertIn(b"Horner", body)
        self.assertIn(b"mod 8", body)
        self.assertIn(b"&lt;script&gt;", body)
        self.assertNotIn(b"<script>", body)

    def test_server_script_starts_with_custom_port_argument(self):
        server_script = Path(__file__).resolve().parents[1] / "src" / "server.py"
        process = subprocess.Popen(
            [sys.executable, str(server_script), "--port", "0"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        try:
            output = process.stdout.readline()
            self.assertTrue(output.startswith("Serving on http://"), output)
            port = int(output.rsplit(":", 1)[1])
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
            connection.request("GET", "/")
            response = connection.getresponse()
            body = response.read()
            connection.close()
            self.assertEqual(response.status, 200)
            self.assertIn(b"URL shortener", body)
        finally:
            process.terminate()
            process.wait(timeout=5)
            if process.stdout is not None:
                process.stdout.close()


if __name__ == "__main__":
    unittest.main()
