import unittest
from app.config import Settings


#1 test setting origin as *
#2 test setting origin as list of urls
#3 test setting other staff like port, host , database host
class TestSettings(unittest.TestCase):
    def test_cors_origins_star(self):
        settings = Settings(allowed_origins="*")
        self.assertEqual(settings.cors_origins, ["*"])

    def test_cors_origins_comma_separated_trimmed(self):
        settings = Settings(
            allowed_origins="http://localhost:3000, https://example.com ,http://127.0.0.1:8080"
        )
        self.assertEqual(
            settings.cors_origins,
            ["http://localhost:3000", "https://example.com", "http://127.0.0.1:8080"],
        )

    def test_defaults_for_host_port_and_database_host(self):
        settings = Settings()
        self.assertEqual(settings.host, "0.0.0.0")
        self.assertEqual(settings.port, 5000)
        self.assertEqual(settings.database_host, "localhost")