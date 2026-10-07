from types import SimpleNamespace
import tempfile
from pathlib import Path
import unittest

from tools.generate_update_manifest import build_payload


class GenerateUpdateManifestTests(unittest.TestCase):
    def _args(self, asset_dir):
        return SimpleNamespace(
            asset_dir=str(asset_dir),
            repo="szboboxing/MousePro",
            tag="v1.0.0",
            commit="abc123",
            expires_days="30",
            build_number="",
        )

    def test_versioned_windows_asset_is_official_windows_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            asset_dir = Path(tmp)
            (asset_dir / "MousePro-Windows.zip").write_bytes(b"legacy")
            (asset_dir / "MousePro-v1.0.0-Windows.zip").write_bytes(b"official")

            payload = build_payload(self._args(asset_dir))

        asset = payload["assets"]["windows-x64"]
        self.assertEqual(asset["name"], "MousePro-v1.0.0-Windows.zip")
        self.assertEqual(
            asset["url"],
            "https://github.com/szboboxing/MousePro/releases/download/"
            "v1.0.0/MousePro-v1.0.0-Windows.zip",
        )


if __name__ == "__main__":
    unittest.main()
