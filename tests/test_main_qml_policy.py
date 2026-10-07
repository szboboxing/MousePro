import inspect
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

try:
    import main_qml
except Exception:  # pragma: no cover - env without PySide6 / project deps
    main_qml = None


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipIf(main_qml is None, "main_qml / PySide6 not available")
class LinuxInputPolicyTests(unittest.TestCase):
    def test_main_window_lifecycle_does_not_toggle_linux_passthrough(self):
        source = inspect.getsource(main_qml.main)

        self.assertNotIn("set_ui_passthrough", source)
        self.assertNotIn("_sync_linux_ui_passthrough", source)


@unittest.skipIf(main_qml is None, "main_qml / PySide6 not available")
class ScreenshotControllerStartupPolicyTests(unittest.TestCase):
    def test_windows_controller_is_imported_and_retained_for_packaged_runtime(self):
        source = inspect.getsource(main_qml.main)

        self.assertIn("from ui.windows_screenshot import WindowsScreenshotController", source)
        self.assertIn("app._MOUSEPRO_screenshot_controller = screenshot_controller", source)
        self.assertIn("set_screenshot_action_handler(screenshot_controller.request_action)", source)


@unittest.skipIf(main_qml is None, "main_qml / PySide6 not available")
class EngineStartupPolicyTests(unittest.TestCase):
    def test_startup_strictly_loads_existing_config_and_shares_it_with_engine(self):
        source = inspect.getsource(main_qml.main)

        self.assertIn(
            "cfg = load_config(strict=os.path.lexists(CONFIG_FILE))",
            source,
        )
        self.assertIn("engine = Engine(initial_config=cfg)", source)

    def test_queued_start_failure_logs_inactive_and_never_active(self):
        engine = Mock()
        engine.start.return_value = False

        with (
            patch.object(
                main_qml.QTimer,
                "singleShot",
                side_effect=lambda _delay, callback: callback(),
            ),
            patch("builtins.print") as log,
        ):
            self.assertTrue(
                main_qml._schedule_engine_start(
                    engine,
                    accessibility_granted=True,
                )
            )

        engine.start.assert_called_once_with()
        messages = [str(item.args[0]) for item in log.call_args_list]
        self.assertIn(
            "[MousePro] Engine start failed -- remapping is inactive",
            messages,
        )
        self.assertNotIn(
            "[MousePro] Engine started -- remapping is active",
            messages,
        )


class LanguageSwitchingQmlPolicyTests(unittest.TestCase):
    def test_settings_language_selector_uses_locale_manager(self):
        source = (ROOT / "ui" / "qml" / "ScrollPage.qml").read_text(encoding="utf-8")

        self.assertIn('s["scroll.language"]', source)
        self.assertIn("model: lm.availableLanguages", source)
        self.assertIn("lm.setLanguage(modelData.code)", source)

    def test_mouse_page_user_visible_debug_strings_use_locale_manager(self):
        source = (ROOT / "ui" / "qml" / "MousePage.qml").read_text(encoding="utf-8")

        self.assertIn('s["mouse.dpi_presets"]', source)
        self.assertIn('s["mouse.press_button_to_cycle"]', source)
        self.assertIn('s["mouse.copy_device_info"]', source)
        self.assertIn('s["mouse.device_info_copied"]', source)
        self.assertIn('s["mouse.no_device_connected"]', source)
        self.assertIn("backend.deviceStatusKind", source)
        self.assertIn('s["mouse.generic_ready"]', source)
        self.assertIn('s["mouse.no_supported_mouse_detected"]', source)
        self.assertNotIn('text: "DPI PRESETS"', source)
        self.assertNotIn('text: "Copy device info"', source)

    def test_mouse_layout_labels_retranslate_when_language_changes(self):
        source = (ROOT / "ui" / "qml" / "MousePage.qml").read_text(encoding="utf-8")

        self.assertIn("readonly property string selectedButtonName", source)
        self.assertIn("(lm.strings, lm.trButton(mapping.name))", source)
        self.assertIn("(lm.strings, lm.trButton(modelData.name))", source)
        self.assertIn("(lm.strings, lm.trAction(modelData.actionLabel))", source)

    def test_mouse_fallbacks_and_default_profile_retranslate(self):
        source = (ROOT / "ui" / "qml" / "MousePage.qml").read_text(encoding="utf-8")

        self.assertIn('localeStrings["mouse.device_fallback_name"]', source)
        self.assertIn('s["mouse.default_profile"]', source)
        self.assertIn('s["mouse.generic_layout_note"]', source)
        self.assertIn('backend.effectiveDeviceLayoutKey === "generic_mouse"', source)
        self.assertIn('profile.name === "default"', source)
        self.assertIn('return profile.label || ""', source)

    def test_about_build_mode_retranslates_without_changing_metadata(self):
        source = (ROOT / "ui" / "qml" / "Main.qml").read_text(encoding="utf-8")

        self.assertIn("readonly property string displayBuildMode", source)
        self.assertIn('s["about.build_mode.packaged"]', source)
        self.assertIn('s["about.build_mode.source"]', source)
        self.assertEqual(source.count("text: displayBuildMode"), 2)

    def test_key_capture_validation_fallback_uses_locale_manager(self):
        source = (ROOT / "ui" / "qml" / "KeyCaptureDialog.qml").read_text(encoding="utf-8")

        self.assertIn('s["key_capture.error.invalid"]', source)
        self.assertIn('s["key_capture.error.unsupported"]', source)


@unittest.skipIf(main_qml is None, "main_qml / PySide6 not available")
class LanguageSwitchingStartupPolicyTests(unittest.TestCase):
    def test_startup_restores_and_persists_locale_manager_language(self):
        source = inspect.getsource(main_qml.main)

        self.assertIn('initial_lang = cfg_settings.get("language", "zh_CN")', source)
        self.assertIn("LocaleManager(language=initial_lang)", source)
        self.assertIn("backend = Backend(engine, root_dir=ROOT, locale_manager=locale_mgr)", source)
        self.assertIn(
            'engine.cfg.setdefault("settings", {})["language"] = locale_mgr.language',
            source,
        )
        self.assertIn("save_config(engine.cfg)", source)
        self.assertIn("locale_mgr.languageChanged.connect(_save_language)", source)


if __name__ == "__main__":
    unittest.main()
