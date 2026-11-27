import http.client
import threading
import unittest

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

    def test_linear_view_shows_probe_path_and_horner_calculation(self):
        status, body = self.get("/table?strategy=linear_probing")

        self.assertEqual(status, 200)
        self.assertIn(b"Linear probing", body)
        self.assertIn(b"probe path: 1 -> 2", body)
        self.assertIn(b"Horner:", body)
        self.assertIn(b"home slot = 1", body)

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
