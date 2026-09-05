import os
import subprocess
import sys
import unittest
from pathlib import Path


class AuthenticationApiBootTests(unittest.TestCase):
    def test_authentication_api_imports_without_optional_ai_preview_package(self):
        backend = Path(__file__).resolve().parents[1]
        environment = {
            **os.environ,
            "MONGO_URL": "mongodb://127.0.0.1:27017",
            "DB_NAME": "eov_test_auth_boot",
            "EOV_SESSION_SECRET": "0123456789abcdef0123456789abcdef",
        }
        result = subprocess.run(
            [sys.executable, "-c", "import server; print(server.app.title)"],
            cwd=backend,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
