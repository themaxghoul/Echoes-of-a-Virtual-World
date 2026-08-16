import unittest

from mail import internal_mailbox, normalize_custom_domain


class MailDomainTests(unittest.TestCase):
    def test_internal_mailbox_is_deterministic(self):
        self.assertEqual(internal_mailbox("New_User"), "new_user@eov.local")

    def test_invalid_or_reserved_custom_domains_are_rejected(self):
        for value in ("eov.local", "localhost", "bad domain.example", "-bad.example"):
            with self.assertRaises(ValueError):
                normalize_custom_domain(value)

    def test_custom_domain_is_normalized_but_not_verified(self):
        self.assertEqual(normalize_custom_domain("Example.COM."), "example.com")


if __name__ == "__main__":
    unittest.main()
