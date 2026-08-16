import unittest

from owner_policy import OWNER_ABILITIES, OWNER_ROLE, authorize_world_capability, is_bound_owner, is_owner_session_subject


class OwnerPolicyTests(unittest.TestCase):
    def test_bound_owner_has_global_and_private_capabilities(self):
        self.assertEqual(OWNER_ROLE, "sirix_1")
        self.assertIn("all", OWNER_ABILITIES)
        self.assertIn("owner_console", OWNER_ABILITIES)
        self.assertIn("jarvis_private", OWNER_ABILITIES)
        self.assertIn("create_world_content", OWNER_ABILITIES)

    def test_uuid_role_and_owner_flag_must_all_agree(self):
        actor = {"id": "owner-uuid", "username": "renamed", "is_owner": True, "permission_level": OWNER_ROLE}
        self.assertTrue(is_bound_owner(actor, "owner-uuid"))
        self.assertFalse(is_bound_owner({**actor, "id": "impostor"}, "owner-uuid"))
        self.assertFalse(is_bound_owner({**actor, "is_owner": False}, "owner-uuid"))
        self.assertFalse(is_bound_owner({**actor, "permission_level": "admin"}, "owner-uuid"))
        self.assertFalse(is_bound_owner(actor, None))

    def test_signed_cross_service_subject_must_match_owner_uuid(self):
        self.assertTrue(is_owner_session_subject({"sub": "owner-uuid"}, "owner-uuid"))
        self.assertFalse(is_owner_session_subject({"sub": "impostor"}, "owner-uuid"))
        self.assertFalse(is_owner_session_subject({"sub": "owner-uuid"}, None))

    def test_world_capability_requires_bound_subject_scope_and_capability(self):
        claims = {"sub": "owner-uuid", "world_capabilities": {"founders-settlement": ["inspect", "amend", "pause"]}}

        self.assertTrue(authorize_world_capability(claims, "owner-uuid", "founders-settlement", "amend"))
        self.assertFalse(authorize_world_capability({**claims, "sub": "impostor", "username": "sirix_1"}, "owner-uuid", "founders-settlement", "amend"))
        self.assertFalse(authorize_world_capability(claims, "owner-uuid", "another-world", "amend"))
        self.assertFalse(authorize_world_capability(claims, "owner-uuid", "founders-settlement", "delete"))


if __name__ == "__main__":
    unittest.main()
