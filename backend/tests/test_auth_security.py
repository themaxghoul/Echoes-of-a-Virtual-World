import unittest

from auth_security import SessionTokenError, issue_session_token, verify_session_token


SECRET = "test-only-secret-that-is-longer-than-thirty-two-bytes"


class AuthSecurityTests(unittest.TestCase):
    def test_signed_session_binds_subject_and_version(self):
        token, issued = issue_session_token("user-1", 3, SECRET, ttl_seconds=60, now=100)
        claims = verify_session_token(token, SECRET, now=120)
        self.assertEqual(claims["sub"], "user-1")
        self.assertEqual(claims["ver"], 3)
        self.assertEqual(claims["sid"], issued["sid"])

    def test_tampering_is_rejected(self):
        token, _ = issue_session_token("user-1", 0, SECRET, now=100)
        with self.assertRaises(SessionTokenError):
            verify_session_token(token[:-2] + "xx", SECRET, now=101)

    def test_expiration_is_rejected(self):
        token, _ = issue_session_token("user-1", 0, SECRET, ttl_seconds=10, now=100)
        with self.assertRaises(SessionTokenError):
            verify_session_token(token, SECRET, now=110)

    def test_weak_secret_is_rejected(self):
        with self.assertRaises(SessionTokenError):
            issue_session_token("user-1", 0, "weak", now=100)


if __name__ == "__main__":
    unittest.main()
