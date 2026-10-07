import unittest

from core import version


class VersionMetadataTests(unittest.TestCase):
    def test_about_dialog_maintainer_metadata_uses_current_owner(self):
        self.assertEqual(version.APP_NAME, "MousePro")
        self.assertEqual(version.MAINTAINER, "szboboxing")
        self.assertFalse(hasattr(version, "ORIGINAL_PROJECT"))


if __name__ == "__main__":
    unittest.main()
