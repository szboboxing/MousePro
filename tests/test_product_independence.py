import re
import unittest
from pathlib import Path

from core import config, updater, version


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_PRODUCT = bytes((77, 111, 117, 115, 101, 114)).decode("ascii")


class ProductIndependenceTests(unittest.TestCase):
    def test_product_owned_runtime_identifiers(self):
        self.assertEqual(version.APP_NAME, "MousePro")
        self.assertEqual(version.MAINTAINER, "szboboxing")
        self.assertEqual(Path(config.CONFIG_DIR).name, "MousePro")
        self.assertEqual(updater.DEFAULT_RELEASE_REPO, "szboboxing/MousePro")

    def test_runtime_and_visible_ui_do_not_reference_upstream_product(self):
        paths = [ROOT / "main_qml.py", *sorted((ROOT / "core").glob("*.py"))]
        paths.extend(sorted((ROOT / "ui").rglob("*.py")))
        paths.extend(sorted((ROOT / "ui" / "qml").rglob("*.qml")))

        matches = []
        for path in paths:
            text = path.read_text(encoding="utf-8")
            if re.search(rf"\b{re.escape(UPSTREAM_PRODUCT)}\b", text, flags=re.IGNORECASE):
                matches.append(str(path.relative_to(ROOT)))

        self.assertEqual(matches, [])


if __name__ == "__main__":
    unittest.main()
