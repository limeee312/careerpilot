"""Verify production preflight rejects unsafe configuration before startup."""

import tempfile
import unittest
from pathlib import Path

from check_env import check_file

VALID = """\
APP_DOMAIN=careerpilot.example.org
BASIC_AUTH_USER=demo
BASIC_AUTH_HASH='$2a$14$valid-shaped-demo-hash'
POSTGRES_DB=careerpilot
POSTGRES_USER=careerpilot
POSTGRES_PASSWORD=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
JWT_SECRET=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
OPENAI_API_KEY=non-production-test-key
OPENAI_MODEL=test-model
"""


class CheckEnvTests(unittest.TestCase):
    def check(self, content: str) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env.production"
            path.write_text(content, encoding="utf-8")
            check_file(path)

    def test_accepts_valid_configuration(self) -> None:
        self.check(VALID)

    def test_rejects_placeholder_domain_and_secret(self) -> None:
        with self.assertRaisesRegex(ValueError, "APP_DOMAIN"):
            self.check(VALID.replace("careerpilot.example.org", "careerpilot.example.com"))
        with self.assertRaisesRegex(ValueError, "JWT_SECRET"):
            self.check(VALID.replace("bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "REPLACE_ME"))

    def test_rejects_password_unsafe_in_database_url(self) -> None:
        with self.assertRaisesRegex(ValueError, "POSTGRES_PASSWORD"):
            self.check(VALID.replace("a" * 64, "a" * 31 + "@"))

    def test_rejects_duplicate_keys(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate APP_DOMAIN"):
            self.check(VALID + "APP_DOMAIN=other.example.org\n")


if __name__ == "__main__":
    unittest.main()
