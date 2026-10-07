import os
import re
import stat
import struct
import unittest

from build_support import normalized_qt_library_stem, should_keep_linux_qt_asset


class LinuxQtAssetFilterTests(unittest.TestCase):
    def test_normalizes_versioned_abi3_shared_library_names(self):
        cases = {
            "/tmp/_internal/PySide6/libpyside6.abi3.so.6.11": "pyside6",
            "/tmp/_internal/PySide6/libpyside6qml.abi3.so.6.11": "pyside6qml",
            "/tmp/_internal/PySide6/libshiboken6.abi3.so.6.11": "shiboken6",
        }

        for path, expected in cases.items():
            with self.subTest(path=path):
                self.assertEqual(normalized_qt_library_stem(path), expected)

    def test_keeps_versioned_pyside6_abi3_runtime_library(self):
        runtime_paths = [
            "/tmp/_internal/PySide6/libpyside6.abi3.so.6.11",
            "/tmp/_internal/PySide6/libpyside6qml.abi3.so.6.11",
            "/tmp/_internal/PySide6/libshiboken6.abi3.so.6.11",
        ]

        for path in runtime_paths:
            with self.subTest(path=path):
                self.assertTrue(should_keep_linux_qt_asset(path))

    def test_keeps_core_qt_dependency_libraries(self):
        dependency_paths = [
            "/tmp/_internal/PySide6/Qt/lib/libQt6DBus.so.6",
            "/tmp/_internal/PySide6/Qt/lib/libQt6XcbQpa.so.6",
            "/tmp/_internal/PySide6/Qt/lib/libicui18n.so.73",
            "/tmp/_internal/PySide6/Qt/lib/libicuuc.so.73",
            "/tmp/_internal/PySide6/Qt/lib/libicudata.so.73",
        ]

        for path in dependency_paths:
            with self.subTest(path=path):
                self.assertTrue(should_keep_linux_qt_asset(path))

    def test_drops_unneeded_qt_webengine_binary(self):
        path = "/tmp/_internal/PySide6/Qt/lib/libQt6WebEngineCore.so.6"
        self.assertFalse(should_keep_linux_qt_asset(path))

    def test_drops_optional_qml_style_family(self):
        path = "/tmp/_internal/PySide6/qml/QtQuick/Controls/Fusion/Button.qml"
        self.assertFalse(should_keep_linux_qt_asset(path))


class LinuxPermissionPackagingTests(unittest.TestCase):
    def _git_index_mode(self, relpath):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        index = os.path.join(root, ".git", "index")
        if not os.path.isfile(index):
            return None
        with open(index, "rb") as index_file:
            data = index_file.read()
        if data[:4] != b"DIRC":
            return None
        count = struct.unpack("!L", data[8:12])[0]
        offset = 12
        relpath = relpath.replace(os.sep, "/")
        for _ in range(count):
            start = offset
            fields = struct.unpack("!LLLLLLLLLL20sH", data[offset:offset + 62])
            offset += 62
            end = data.index(b"\0", offset)
            entry_path = data[offset:end].decode("utf-8")
            offset = end + 1
            while (offset - start) % 8:
                offset += 1
            if entry_path == relpath:
                return fields[6]
        return None

    def test_linux_permission_helper_files_exist(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        helper = os.path.join(
            root, "packaging", "linux", "install-linux-permissions.sh"
        )
        rules = os.path.join(
            root, "packaging", "linux", "69-mousepro-logitech.rules"
        )

        self.assertTrue(os.path.isfile(helper))
        if os.name == "nt":
            self.assertEqual(
                self._git_index_mode("packaging/linux/install-linux-permissions.sh"),
                stat.S_IFREG | 0o755,
            )
        else:
            self.assertTrue(os.stat(helper).st_mode & stat.S_IXUSR)
        self.assertTrue(os.path.isfile(rules))

    def test_linux_spec_packages_linux_files_into_linux_directory(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        spec_path = os.path.join(root, "MousePro-linux.spec")
        with open(spec_path, encoding="utf-8") as spec_file:
            spec_text = spec_file.read()

        linux_assets = (
            "69-mousepro-logitech.rules",
            "install-linux-permissions.sh",
            "io.github.szboboxing.mousepro.desktop.in",
        )
        for asset_name in linux_assets:
            with self.subTest(asset=asset_name):
                self.assertRegex(
                    spec_text,
                    re.compile(
                        rf'os\.path\.join\(ROOT, "packaging", "linux", '
                        rf'"{re.escape(asset_name)}"\),\s*"linux",',
                        re.MULTILINE,
                    ),
                )
                self.assertNotIn(
                    f'os.path.join("linux", "{asset_name}")',
                    spec_text,
                )


if __name__ == "__main__":
    unittest.main()
