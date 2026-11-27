import http.client
import threading
import unittest
from urllib.parse import urlencode

from src.server import create_server
from src.shortener import Shortener


class TableStrategyViewTests(unittest.TestCase):
    def setUp(self):
        self.shortener = Shortener(table_type="linear_probing")
        self.shortener._url_to_code.set("a", "first")
        self.shortener._url_to_code.set("i", "second")
        self.server = create_server(port=0, shortener=self.shortener)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()
        self.host, self.port = self.server.server_address

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def get(self, path):
        connection = http.client.HTTPConnection(self.host, self.port)
        connection.request("GET", path)
        response = connection.getresponse()
        result = response.status, response.read()
        connection.close()
        return result

    def post(self, url):
        body = urlencode({"url": url})
        connection = http.client.HTTPConnection(self.host, self.port)
        connection.request(
            "POST",
            "/",
            body=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Content-Length": str(len(body)),
                "Host": "short.example",
            },
        )
        response = connection.getresponse()
        result = response.status, response.read()
        connection.close()
        return result

    def test_linear_view_shows_probe_path_and_horner_calculation(self):
        status, body = self.get("/table?strategy=linear_probing")

        self.assertEqual(status, 200)
        self.assertIn(b"Linear probing", body)
        self.assertIn(b"probe path: 1 -> 2", body)
        self.assertIn(b"Horner:", body)
        self.assertIn(b"home slot = 1", body)

    def test_strategy_selector_closes_before_rendered_tables_and_submits(self):
        status, body = self.get("/table?strategy=both")

        self.assertEqual(status, 200)
        self.assertIn(b'onchange="this.form.submit()"', body)
        self.assertIn(b"</select> <button", body)
        self.assertLess(body.index(b"</select>"), body.index(b"<h2>Separate chaining</h2>"))

    def test_urls_created_on_home_page_appear_in_both_table_views(self):
        urls = (
            "https://example.com/first",
            "https://example.org/second?x=1&y=2",
        )
        for url in urls:
            status, body = self.post(url)
            self.assertEqual(status, 200)
            self.assertIn(b"Code:", body)

        status, body = self.get("/table?strategy=both")
        self.assertEqual(status, 200)
        self.assertIn(b"https://example.com/first", body)
        self.assertIn(b"https://example.org/second?x=1&amp;y=2", body)
        self.assertIn(b"probe path:", body)
        self.assertIn(b"Horner:", body)
        self.assertEqual(self.shortener.expand("0"), urls[0])
        self.assertEqual(self.shortener.expand("1"), urls[1])

    def test_both_view_renders_both_strategies(self):
        status, body = self.get("/table?strategy=both")

        self.assertEqual(status, 200)
        self.assertIn(b"Separate chaining", body)
        self.assertIn(b"Linear probing", body)

    def test_chaining_view_can_be_selected(self):
        status, body = self.get("/table?strategy=chaining")

        self.assertEqual(status, 200)
        self.assertIn(b"Separate chaining", body)
        self.assertIn(b"search path: bucket 1", body)

    def test_unknown_strategy_is_rejected(self):
        status, body = self.get("/table?strategy=unknown")

        self.assertEqual(status, 400)
        self.assertIn(b"Unknown table strategy", body)


if __name__ == "__main__":
    unittest.main()
