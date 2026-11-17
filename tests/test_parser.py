import unittest

from main import extract, normalize


class ProxyParserTests(unittest.TestCase):
    def test_mtproto_link(self):
        item = normalize("tg://proxy?server=149.154.167.50&port=443&secret=abcdef0123456789")
        self.assertIsNotNone(item)
        self.assertEqual(item["type"], "MTProto")
        self.assertEqual(item["port"], 443)

    def test_socks_url(self):
        item = normalize("socks5://127.0.0.1:1080")
        self.assertEqual(item["type"], "SOCKS5")
        self.assertEqual(item["host"], "127.0.0.1")

    def test_http_url(self):
        item = normalize("http://192.0.2.10:8080")
        self.assertEqual(item["type"], "HTTP")

    def test_invalid_port_is_rejected(self):
        self.assertIsNone(normalize("socks5://127.0.0.1:99999"))

    def test_extract_deduplicates(self):
        text = "socks5://127.0.0.1:1080\nsocks5://127.0.0.1:1080"
        self.assertEqual(len(extract(text)), 1)


if __name__ == "__main__":
    unittest.main()
