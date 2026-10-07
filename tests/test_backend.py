import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from types import MappingProxyType
from types import SimpleNamespace
from unittest.mock import patch

from core import config as core_config
from core.config import DEFAULT_CONFIG
from core.mouse_hook import MouseEvent
from core.mouse_hook_types import BindingBuilder, BindingSnapshot, HidRuntimeState
from core.updater import UpdateCheckState


# Backend update timers can outlive an individual mock context. Keep every
# delayed save in a process-local sandbox instead of the user's real AppData.
_CONFIG_SANDBOX = tempfile.TemporaryDirectory(prefix="mousepro-backend-tests-")
core_config.CONFIG_DIR = os.path.join(_CONFIG_SANDBOX.name, "MousePro")
core_config.CONFIG_FILE = os.path.join(core_config.CONFIG_DIR, "config.json")

try:
    from PySide6.QtCore import QCoreApplication, Qt, QUrl
    from ui.backend import Backend
    from ui.locale_manager import LocaleManager
except ModuleNotFoundError:
    Backend = None
    LocaleManager = None
    QCoreApplication = None
    Qt = None
    QUrl = None


def _ensure_qapp():
    app = QCoreApplication.instance()
    if app is None:
        return QCoreApplication(sys.argv)
    return app


class _FakeEngine:
    def __init__(
        self,
        device_connected=False,
        connected_device=None,
        hid_features_ready=False,
        smart_shift_supported=False,
        cfg=None,
    ):
        self.cfg = copy.deepcopy(cfg or DEFAULT_CONFIG)
        self.device_connected = device_connected
        self.connected_device = connected_device
        self.hid_features_ready = hid_features_ready
        self.smart_shift_supported = smart_shift_supported
        self.profile_callback = None
        self.dpi_callback = None
        self.connection_callback = None
        self.battery_callback = None
        self.debug_callback = None
        self.gesture_callback = None
        self.status_callback = None
        self.debug_enabled = None
        self.start_count = 0
        self.stop_count = 0
        self.reload_count = 0
        self.start_error = None

    def set_profile_change_callback(self, cb):
        self.profile_callback = cb

    def set_dpi_read_callback(self, cb):
        self.dpi_callback = cb

    def set_connection_change_callback(self, cb):
        self.connection_callback = cb

    def set_battery_callback(self, cb):
        self.battery_callback = cb

    def set_debug_callback(self, cb):
        self.debug_callback = cb

    def set_gesture_event_callback(self, cb):
        self.gesture_callback = cb

    def set_status_callback(self, cb):
        self.status_callback = cb

    def set_debug_enabled(self, enabled):
        self.debug_enabled = enabled

    def start(self):
        self.start_count += 1
        if self.start_error:
            raise self.start_error

    def stop(self):
        self.stop_count += 1

    def reload_mappings(self):
        self.reload_count += 1


class _InspectableMouseHook:
    def __init__(self):
        self.invert_vscroll = False
        self.invert_hscroll = False
        self.debug_mode = False
        self.device_connected = True
        self.connected_device = SimpleNamespace(
            supported_buttons=("middle", "xbutton1", "xbutton2"),
            capabilities=SimpleNamespace(
                reprogrammable_buttons=("middle", "xbutton1", "xbutton2"),
            ),
            capability_inventory=SimpleNamespace(has_reprog_controls=True),
        )
        self._hid_gesture = None
        self._callbacks = {}
        self._blocked_events = set()
        self._binding_snapshot = BindingSnapshot.empty()
        self.divert_mode_shift = False
        self.divert_dpi_switch = False
        self.sync_hid_extra_diverts_calls = 0

    @property
    def hid_runtime_state(self):
        return HidRuntimeState(
            input_ready=self.device_connected,
            hid_ready=False,
            connected_device=self.connected_device,
        )

    def set_debug_callback(self, cb):
        self._debug_callback = cb

    def set_gesture_callback(self, cb):
        self._gesture_callback = cb

    def set_status_callback(self, cb):
        self._status_callback = cb

    def set_connection_change_callback(self, cb):
        self._connection_change_callback = cb

    def configure_gestures(self, **kwargs):
        self._gesture_config = kwargs

    def block(self, event_type):
        self._blocked_events.add(event_type)

    def register(self, event_type, callback):
        self._callbacks.setdefault(event_type, []).append(callback)

    def reset_bindings(self, wait_timeout=None):
        return self.publish_bindings(BindingBuilder())

    def new_binding_builder(self):
        return BindingBuilder()

    def publish_bindings(self, builder):
        self._callbacks = {
            event_type: list(callbacks)
            for event_type, callbacks in builder.callbacks.items()
        }
        self._blocked_events = set(builder.blocked_events)
        self._binding_snapshot = BindingSnapshot(
            generation=self._binding_snapshot.generation + 1,
            callbacks=MappingProxyType(
                {key: tuple(value) for key, value in self._callbacks.items()}
            ),
            blocked_events=frozenset(builder.blocked_events),
            routes=MappingProxyType(dict(builder.routes)),
        )
        return self._binding_snapshot

    def capture_binding_snapshot(self):
        return self._binding_snapshot

    def sync_hid_extra_diverts(self):
        self.sync_hid_extra_diverts_calls += 1
        return True

    def start(self):
        return True

    def stop(self):
        return None


class _DisconnectedInspectableMouseHook(_InspectableMouseHook):
    def __init__(self):
        super().__init__()
        self.device_connected = False
        self.connected_device = None


class _FakeAppDetector:
    def __init__(self, callback):
        self.callback = callback

    def start(self):
        return None

    def stop(self):
        return None


@unittest.skipIf(Backend is None, "PySide6 not installed in test environment")
class BackendDeviceLayoutTests(unittest.TestCase):
    def _make_backend(self, engine=None, root_dir=None, cfg=None, locale_manager=None):
        loaded_config = copy.deepcopy(cfg or DEFAULT_CONFIG)
        if engine is not None:
            engine.cfg = loaded_config
        with (
            patch("ui.backend.load_config", return_value=loaded_config),
            patch("ui.backend.save_config"),
            patch("ui.backend.supports_login_startup", return_value=False),
        ):
            return Backend(
                engine=engine,
                root_dir=root_dir,
                locale_manager=locale_manager,
            )

    def test_backend_rebinds_to_engine_config_after_mapping_reload(self):
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        engine = _FakeEngine(cfg=cfg)
        backend = self._make_backend(engine=engine, cfg=cfg)
        self.assertIs(backend._cfg, engine.cfg)

        reloaded = copy.deepcopy(engine.cfg)
        reloaded["profiles"]["default"]["mappings"]["middle"] = "copy"

        def reload_mappings():
            engine.reload_count += 1
            engine.cfg = reloaded

        engine.reload_mappings = reload_mappings
        backend._reload_engine_mappings()
        backend._cfg["settings"]["start_minimized"] = False

        self.assertIs(backend._cfg, engine.cfg)
        self.assertEqual(
            engine.cfg["profiles"]["default"]["mappings"]["middle"],
            "copy",
        )
        self.assertFalse(engine.cfg["settings"]["start_minimized"])
        self.assertEqual(engine.reload_count, 1)

    def test_engine_setting_save_cannot_revert_new_backend_mapping(self):
        from core.engine import Engine

        persisted = copy.deepcopy(DEFAULT_CONFIG)

        def load_persisted(**_):
            return copy.deepcopy(persisted)

        def save_persisted(updated):
            nonlocal persisted
            persisted = copy.deepcopy(updated)

        with (
            patch("ui.backend.load_config", side_effect=load_persisted),
            patch("ui.backend.save_config", side_effect=save_persisted),
            patch("ui.backend.supports_login_startup", return_value=False),
            patch("core.config.save_config", side_effect=save_persisted),
            patch("core.engine.load_config", side_effect=load_persisted),
            patch("core.engine.save_config", side_effect=save_persisted),
            patch("core.engine.MouseHook", _DisconnectedInspectableMouseHook),
            patch("core.engine.AppDetector", _FakeAppDetector),
        ):
            engine = Engine()
            backend = Backend(engine=engine)
            self.assertIs(backend._cfg, engine.cfg)

            backend.setProfileMapping("default", "middle", "copy")
            self.assertIs(backend._cfg, engine.cfg)
            self.assertEqual(
                persisted["profiles"]["default"]["mappings"]["middle"],
                "copy",
            )

            engine.set_dpi(1600)

        self.assertEqual(
            persisted["profiles"]["default"]["mappings"]["middle"],
            "copy",
        )
        self.assertEqual(persisted["settings"]["dpi"], 1600)

    def test_malformed_shared_config_stays_read_only_until_engine_strict_reload(self):
        from core import config
        from core.engine import Engine

        _ensure_qapp()
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.json"
            malformed = "{not-valid-json"
            config_file.write_text(malformed, encoding="utf-8")
            with (
                patch.object(config, "CONFIG_DIR", temp_dir),
                patch.object(config, "CONFIG_FILE", str(config_file)),
                patch("ui.backend.supports_login_startup", return_value=False),
                patch("core.engine.MouseHook", _DisconnectedInspectableMouseHook),
                patch("core.engine.AppDetector", _FakeAppDetector),
            ):
                engine = Engine()
                backend = Backend(engine=engine)
                self.assertIs(backend._cfg, engine.cfg)

                with self.assertRaises(config.ConfigWriteBlockedError):
                    backend.setProfileMapping("default", "middle", "copy")
                self.assertEqual(config_file.read_text(encoding="utf-8"), malformed)

                repaired = copy.deepcopy(DEFAULT_CONFIG)
                config_file.write_text(json.dumps(repaired), encoding="utf-8")
                engine.reload_mappings()
                self.assertIs(backend._cfg, engine.cfg)

                backend.setProfileMapping("default", "middle", "copy")
                persisted = json.loads(config_file.read_text(encoding="utf-8"))

        self.assertEqual(
            persisted["profiles"]["default"]["mappings"]["middle"],
            "copy",
        )

    @staticmethod
    def _fake_create_profile(cfg, name, label=None, copy_from="default", apps=None):
        cfg.setdefault("profiles", {})[name] = {
            "label": label or name,
            "apps": list(apps or []),
            "mappings": {},
        }
        return cfg

    def test_defaults_to_generic_layout_without_connected_device(self):
        backend = self._make_backend()

        self.assertEqual(backend.effectiveDeviceLayoutKey, "generic_mouse")
        self.assertFalse(backend.hasInteractiveDeviceLayout)

    def test_device_image_source_uses_encoded_file_url(self):
        backend = self._make_backend(root_dir="/tmp/MousePro Build")

        expected = QUrl.fromLocalFile(
            "/tmp/MousePro Build/images/icons/mouse-simple.svg"
        ).toString()

        self.assertEqual(backend.deviceImageSource, expected)

    def test_mx_anywhere_2s_hotspots_expose_horizontal_scroll(self):
        device = SimpleNamespace(
            key="mx_anywhere_2s",
            display_name="MX Anywhere 2S",
            dpi_min=200,
            dpi_max=4000,
            ui_layout="mx_anywhere_2s",
            supported_buttons=("middle", "hscroll_left", "hscroll_right"),
        )
        backend = self._make_backend(
            engine=_FakeEngine(device_connected=True, connected_device=device)
        )

        hscroll_hotspots = [
            hotspot
            for hotspot in backend.deviceHotspots
            if hotspot.get("isHScroll")
        ]

        self.assertEqual(len(hscroll_hotspots), 1)
        self.assertEqual(hscroll_hotspots[0]["buttonKey"], "hscroll_left")
        self.assertEqual(hscroll_hotspots[0]["summaryType"], "hscroll")
        self.assertTrue(hscroll_hotspots[0]["isHScroll"])

    def test_update_checks_disabled_do_not_start_timer(self):
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg.setdefault("settings", {})["check_for_updates"] = False

        backend = self._make_backend(cfg=cfg)

        self.assertFalse(backend.checkForUpdates)
        self.assertFalse(backend._update_timer.isActive())

    def test_disabled_automatic_update_check_does_not_start_thread(self):
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg.setdefault("settings", {})["check_for_updates"] = False
        backend = self._make_backend(cfg=cfg)

        with patch("ui.backend.threading.Thread") as thread_cls:
            backend._startUpdateCheck(manual=False)

        thread_cls.assert_not_called()
        self.assertFalse(backend._update_check_in_progress)

    def test_manual_update_check_triggers_immediate_fetch(self):
        backend = self._make_backend()

        with patch.object(backend, "_startUpdateCheck") as start_check:
            backend.manualCheckForUpdates()

        start_check.assert_called_once_with(manual=True)

    def test_prepare_latest_update_uses_manual_fallback_for_macos(self):
        from pathlib import Path

        from core.update_installer import (
            APP_ID,
            RuntimeLocation,
            UpdateAsset,
            UpdateManifest,
        )

        backend = self._make_backend()
        backend._latest_update_version = "3.7.0"
        backend._update_state = UpdateCheckState(highest_trusted_build=30699)
        manifest = UpdateManifest(
            schema=1,
            app_id=APP_ID,
            channel="stable",
            version="3.7.0",
            tag="v3.7.0",
            build_number=30700,
            expires_at="2026-06-01T00:00:00Z",
            commit="abc",
            release_notes_url="https://example.test",
            assets={
                "macos-arm64": UpdateAsset(
                    "macos-arm64",
                    "MousePro-macOS.zip",
                    "https://example.test/MousePro-macOS.zip",
                    1,
                    "a" * 64,
                )
            },
        )
        runtime = RuntimeLocation(
            executable=Path("/Applications/MousePro.app/Contents/MacOS/MousePro"),
            install_root=Path("/Applications/MousePro.app"),
            app_data_dir=Path("/tmp/MousePro"),
            frozen=True,
            platform_key="macos-arm64",
            update_supported=False,
        )

        with (
            patch("ui.backend.fetch_update_manifest_for_release", return_value=manifest) as fetch_manifest,
            patch("ui.backend.locate_runtime", return_value=runtime),
        ):
            backend._runPrepareLatestUpdate()
            _ensure_qapp().processEvents()

        fetch_manifest.assert_called_once_with(
            "v3.7.0",
            repo="szboboxing/MousePro",
            highest_trusted_build=30699,
        )
        self.assertEqual(backend.updateInstallStatus, "manual_fallback")
        self.assertFalse(backend.updateInstallCanInstall)
        self.assertEqual(backend.updateInstallMessage, "macos")

    def test_prepare_latest_update_keeps_windows_install_hidden_by_default(self):
        from pathlib import Path

        from core.update_installer import (
            APP_ID,
            RuntimeLocation,
            UpdateAsset,
            UpdateManifest,
        )

        backend = self._make_backend()
        backend._latest_update_version = "3.7.0"
        manifest = UpdateManifest(
            schema=1,
            app_id=APP_ID,
            channel="stable",
            version="3.7.0",
            tag="v3.7.0",
            build_number=30700,
            expires_at="2026-06-01T00:00:00Z",
            commit="abc",
            release_notes_url="https://example.test",
            assets={
                "windows-x64": UpdateAsset(
                    "windows-x64",
                    "MousePro-Windows.zip",
                    "https://example.test/MousePro-Windows.zip",
                    1,
                    "a" * 64,
                )
            },
        )
        runtime = RuntimeLocation(
            executable=Path("C:/MousePro/MousePro.exe"),
            install_root=Path("C:/MousePro"),
            app_data_dir=Path("C:/Users/test/AppData/Local/MousePro"),
            frozen=True,
            platform_key="windows-x64",
            update_supported=True,
        )

        with (
            patch.dict("os.environ", {}, clear=True),
            patch("ui.backend.fetch_update_manifest_for_release", return_value=manifest),
            patch("ui.backend.locate_runtime", return_value=runtime),
            patch("ui.backend.prepare_downloaded_asset") as prepare_asset,
        ):
            backend._runPrepareLatestUpdate()
            _ensure_qapp().processEvents()
            prepare_asset.assert_not_called()
            self.assertEqual(backend.updateInstallStatus, "manual_fallback")
            self.assertFalse(backend.updateInstallCanInstall)
            self.assertEqual(backend.updateInstallMessage, "windows")
            self.assertFalse(backend.updateInstallEnabled)

    def test_prepare_latest_update_uses_manual_fallback_for_unsupported_windows_runtime(self):
        from pathlib import Path

        from core.update_installer import (
            APP_ID,
            RuntimeLocation,
            UpdateAsset,
            UpdateManifest,
        )

        backend = self._make_backend()
        backend._latest_update_version = "3.7.0"
        manifest = UpdateManifest(
            schema=1,
            app_id=APP_ID,
            channel="stable",
            version="3.7.0",
            tag="v3.7.0",
            build_number=30700,
            expires_at="2026-06-01T00:00:00Z",
            commit="abc",
            release_notes_url="https://example.test",
            assets={
                "windows-x64": UpdateAsset(
                    "windows-x64",
                    "MousePro-Windows.zip",
                    "https://example.test/MousePro-Windows.zip",
                    1,
                    "a" * 64,
                )
            },
        )
        runtime = RuntimeLocation(
            executable=Path("C:/Program Files/MousePro/MousePro.exe"),
            install_root=Path("C:/Program Files/MousePro"),
            app_data_dir=Path("C:/Users/test/AppData/Local/MousePro"),
            frozen=True,
            platform_key="windows-x64",
            update_supported=False,
            reason="install path not writable",
        )

        with (
            patch.dict("os.environ", {"MOUSEPRO_ENABLE_UPDATE_INSTALL": "1"}),
            patch("ui.backend.fetch_update_manifest_for_release", return_value=manifest),
            patch("ui.backend.locate_runtime", return_value=runtime),
            patch("ui.backend.prepare_downloaded_asset") as prepare_asset,
        ):
            backend._runPrepareLatestUpdate()
            _ensure_qapp().processEvents()

            prepare_asset.assert_not_called()
            self.assertEqual(backend.updateInstallStatus, "manual_fallback")
            self.assertFalse(backend.updateInstallCanInstall)
            self.assertEqual(backend.updateInstallMessage, "windows")
            self.assertTrue(backend.updateInstallEnabled)

    def test_prepare_latest_update_stages_windows_bundle_next_to_install_root(self):
        from core.update_installer import (
            APP_ID,
            RuntimeLocation,
            StagedUpdate,
            UpdateAsset,
            UpdateManifest,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            install = root / "MousePro"
            install.mkdir()
            backend = self._make_backend()
            backend._latest_update_version = "3.7.0"
            manifest = UpdateManifest(
                schema=1,
                app_id=APP_ID,
                channel="stable",
                version="3.7.0",
                tag="v3.7.0",
                build_number=30700,
                expires_at="2026-06-01T00:00:00Z",
                commit="abc",
                release_notes_url="https://example.test",
                assets={
                    "windows-x64": UpdateAsset(
                        "windows-x64",
                        "MousePro-Windows.zip",
                        "https://example.test/MousePro-Windows.zip",
                        1,
                        "a" * 64,
                    )
                },
            )
            runtime = RuntimeLocation(
                executable=install / "MousePro.exe",
                install_root=install,
                app_data_dir=root / "data",
                frozen=True,
                platform_key="windows-x64",
                update_supported=True,
            )
            archive = root / "MousePro-Windows.zip"
            staged_app = root / ".MousePro.update-v3.7.0-1234" / "MousePro"
            staged = StagedUpdate(
                archive_path=archive,
                stage_dir=staged_app.parent,
                app_root=staged_app,
                platform_key="windows-x64",
                asset_name="MousePro-Windows.zip",
            )

            with (
                patch.dict("os.environ", {"MOUSEPRO_ENABLE_UPDATE_INSTALL": "1"}),
                patch("ui.backend.fetch_update_manifest_for_release", return_value=manifest),
                patch("ui.backend.locate_runtime", return_value=runtime),
                patch("ui.backend.prepare_downloaded_asset", return_value=archive),
                patch("ui.backend.extract_validated_zip", return_value=staged) as extract_zip,
                patch("ui.backend.os.getpid", return_value=1234),
            ):
                backend._runPrepareLatestUpdate()
                _ensure_qapp().processEvents()

            extract_zip.assert_called_once()
            stage_arg = extract_zip.call_args.args[1]
            self.assertEqual(stage_arg.parent, install.resolve().parent)
            self.assertEqual(stage_arg.name, ".MousePro.update-v3.7.0-1234")
            self.assertEqual(backend.updateInstallStatus, "ready_to_install")
            self.assertTrue(backend.updateInstallCanInstall)

    def test_install_prepared_update_launches_helper_and_quits(self):
        backend = self._make_backend()
        backend._pending_update_plan_path = "/tmp/pending-update.json"
        backend._update_install_can_install = True

        with (
            patch.dict("os.environ", {"MOUSEPRO_ENABLE_UPDATE_INSTALL": "1"}),
            patch("ui.backend.launch_windows_update_helper") as launch_helper,
            patch("ui.backend.QCoreApplication.quit") as quit_app,
        ):
            backend.installPreparedUpdate()

        launch_helper.assert_called_once_with("/tmp/pending-update.json", helper_dir=None)
        quit_app.assert_called_once()
        self.assertEqual(backend.updateInstallStatus, "installing")

    def test_install_prepared_update_restarts_engine_when_helper_launch_fails(self):
        engine = _FakeEngine()
        backend = self._make_backend(engine=engine)
        backend._pending_update_plan_path = "/tmp/pending-update.json"
        backend._update_install_can_install = True

        with (
            patch.dict("os.environ", {"MOUSEPRO_ENABLE_UPDATE_INSTALL": "1"}),
            patch(
                "ui.backend.launch_windows_update_helper",
                side_effect=OSError("helper failed"),
            ),
            patch("ui.backend.QCoreApplication.quit") as quit_app,
        ):
            backend.installPreparedUpdate()

        self.assertEqual(engine.stop_count, 1)
        self.assertEqual(engine.start_count, 1)
        quit_app.assert_not_called()
        self.assertEqual(backend.updateInstallStatus, "error")

    def test_cancel_update_preparation_sets_inline_cancelled_state(self):
        backend = self._make_backend()
        backend._update_install_status = "downloading"

        backend.cancelUpdatePreparation()

        self.assertTrue(backend._update_cancel.is_set())
        self.assertEqual(backend.updateInstallStatus, "cancelled")

    def test_cancel_before_prepare_worker_runs_does_not_fetch_metadata(self):
        from core.update_installer import RuntimeLocation

        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            backend = self._make_backend()
            backend._latest_update_version = "3.7.0"
            runtime = RuntimeLocation(
                executable=data / "MousePro.exe",
                install_root=data,
                app_data_dir=data,
                frozen=True,
                platform_key="windows-x64",
                update_supported=True,
            )
            captured = {}

            def make_thread(*, target, name, daemon):
                captured["target"] = target
                captured["name"] = name
                captured["daemon"] = daemon
                return SimpleNamespace(start=lambda: None)

            with patch("ui.backend.threading.Thread", side_effect=make_thread):
                backend.prepareLatestUpdate()

            self.assertEqual(captured["name"], "MouseProPrepareUpdate")
            self.assertTrue(captured["daemon"])

            backend.cancelUpdatePreparation()
            with (
                patch("ui.backend.fetch_update_manifest_for_release") as fetch_manifest,
                patch("ui.backend.locate_runtime", return_value=runtime),
            ):
                captured["target"]()
                _ensure_qapp().processEvents()

            fetch_manifest.assert_not_called()
            self.assertEqual(backend.updateInstallStatus, "cancelled")
            self.assertFalse(backend.updateInstallCanInstall)

    def test_cancel_during_metadata_fetch_keeps_cancelled_state(self):
        from pathlib import Path

        from core.update_installer import APP_ID, RuntimeLocation, UpdateAsset, UpdateManifest

        backend = self._make_backend()
        backend._latest_update_version = "3.7.0"
        manifest = UpdateManifest(
            schema=1,
            app_id=APP_ID,
            channel="stable",
            version="3.7.0",
            tag="v3.7.0",
            build_number=30700,
            expires_at="2026-06-01T00:00:00Z",
            commit="abc",
            release_notes_url="https://example.test",
            assets={
                "macos-arm64": UpdateAsset(
                    "macos-arm64",
                    "MousePro-macOS.zip",
                    "https://example.test/MousePro-macOS.zip",
                    1,
                    "a" * 64,
                )
            },
        )
        runtime = RuntimeLocation(
            executable=Path("/Applications/MousePro.app/Contents/MacOS/MousePro"),
            install_root=Path("/Applications/MousePro.app"),
            app_data_dir=Path("/tmp/MousePro"),
            frozen=True,
            platform_key="macos-arm64",
            update_supported=False,
        )

        def fetch_and_cancel(*args, **kwargs):
            backend._update_cancel.set()
            return manifest

        with (
            patch("ui.backend.fetch_update_manifest_for_release", side_effect=fetch_and_cancel),
            patch("ui.backend.locate_runtime", return_value=runtime),
        ):
            backend._runPrepareLatestUpdate()
            _ensure_qapp().processEvents()

        self.assertEqual(backend.updateInstallStatus, "cancelled")
        self.assertFalse(backend.updateInstallCanInstall)

    def test_prepare_latest_update_cleans_install_adjacent_stage_on_error(self):
        from core.update_installer import (
            APP_ID,
            RuntimeLocation,
            UpdateAsset,
            UpdateInstallError,
            UpdateManifest,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            install = root / "MousePro"
            install.mkdir()
            backend = self._make_backend()
            backend._latest_update_version = "3.7.0"
            manifest = UpdateManifest(
                schema=1,
                app_id=APP_ID,
                channel="stable",
                version="3.7.0",
                tag="v3.7.0",
                build_number=30700,
                expires_at="2026-06-01T00:00:00Z",
                commit="abc",
                release_notes_url="https://example.test",
                assets={
                    "windows-x64": UpdateAsset(
                        "windows-x64",
                        "MousePro-Windows.zip",
                        "https://example.test/MousePro-Windows.zip",
                        1,
                        "a" * 64,
                    )
                },
            )
            runtime = RuntimeLocation(
                executable=install / "MousePro.exe",
                install_root=install,
                app_data_dir=root / "data",
                frozen=True,
                platform_key="windows-x64",
                update_supported=True,
            )
            archive = root / "MousePro-Windows.zip"
            stage_dir = root / ".MousePro.update-v3.7.0-1234"

            def fail_extract(_archive, stage_arg, **_kwargs):
                self.assertEqual(stage_arg, stage_dir)
                stage_arg.mkdir(parents=True)
                (stage_arg / "partial.txt").write_text("partial", encoding="utf-8")
                raise UpdateInstallError("bad_archive", "bad archive")

            with (
                patch.dict("os.environ", {"MOUSEPRO_ENABLE_UPDATE_INSTALL": "1"}),
                patch("ui.backend.fetch_update_manifest_for_release", return_value=manifest),
                patch("ui.backend.locate_runtime", return_value=runtime),
                patch("ui.backend.prepare_downloaded_asset", return_value=archive),
                patch("ui.backend.same_volume_windows_stage_dir", return_value=stage_dir),
                patch("ui.backend.extract_validated_zip", side_effect=fail_extract),
            ):
                backend._runPrepareLatestUpdate()
                _ensure_qapp().processEvents()

            self.assertEqual(backend.updateInstallStatus, "error")
            self.assertEqual(backend.updateInstallMessage, "bad_archive")
            self.assertFalse(stage_dir.exists())

    def test_startup_consumes_successful_update_marker_and_persists_build_number(self):
        from core.update_installer import RuntimeLocation

        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            marker = data / "last-update-result.txt"
            marker.write_text(
                json.dumps(
                    {"status": "installed", "version": "3.7.0", "build_number": 30700}
                ),
                encoding="utf-8",
            )
            runtime = RuntimeLocation(
                executable=data / "MousePro.exe",
                install_root=data,
                app_data_dir=data,
                frozen=True,
                platform_key="windows-x64",
                update_supported=True,
            )
            cfg = copy.deepcopy(DEFAULT_CONFIG)
            cfg.setdefault("settings", {})["update_check_state"] = {
                "highest_trusted_build": 30600
            }

            with (
                patch("ui.backend.load_config", return_value=cfg),
                patch("ui.backend.save_config") as save_config,
                patch("ui.backend.supports_login_startup", return_value=False),
                patch("ui.backend.locate_runtime", return_value=runtime),
            ):
                backend = Backend(engine=_FakeEngine())

            self.assertFalse(marker.exists())
            self.assertEqual(backend.updateInstallStatus, "installed")
            self.assertEqual(backend.updateInstallMessage, "3.7.0")
            self.assertEqual(backend._update_state.highest_trusted_build, 30700)
            save_config.assert_called_with(backend._cfg)

    def test_update_check_result_persists_state_on_main_thread(self):
        backend = self._make_backend()
        state = {
            "last_check": 10.0,
            "etag": '"abc"',
            "last_modified": "Wed, 13 May 2026 00:00:00 GMT",
            "backoff_until": 0.0,
            "last_seen_latest_version": "v3.7.1",
            "skipped_version": "",
        }

        with patch("ui.backend.save_config") as save_config:
            backend._handleUpdateCheckFinished(False, True, state)

        self.assertEqual(
            backend._cfg["settings"]["update_check_state"]["etag"], '"abc"'
        )
        self.assertEqual(backend._update_state.last_seen_latest_version, "v3.7.1")
        save_config.assert_called_once_with(backend._cfg)

    def test_disconnected_override_request_does_not_persist(self):
        backend = self._make_backend()
        backend._connected_device_key = "mx_master_3"
        backend.setDeviceLayoutOverride("mx_master")

        overrides = backend._cfg.get("settings", {}).get("device_layout_overrides", {})
        self.assertEqual(overrides, {})

    def test_connected_device_can_override_exact_layout_with_family_layout(self):
        device = SimpleNamespace(
            key="mx_master_4",
            display_name="MX Master 4",
            dpi_min=200,
            dpi_max=8000,
            ui_layout="mx_master_4",
            supported_buttons=("middle", "xbutton1", "xbutton2"),
        )

        with (
            patch("ui.backend.load_config", return_value=copy.deepcopy(DEFAULT_CONFIG)),
            patch("ui.backend.save_config"),
            patch("ui.backend.supports_login_startup", return_value=False),
        ):
            backend = Backend(
                engine=_FakeEngine(
                    device_connected=True,
                    connected_device=device,
                )
            )
            backend.setDeviceLayoutOverride("mx_master")

        overrides = backend._cfg.get("settings", {}).get("device_layout_overrides", {})
        self.assertEqual(overrides, {"mx_master_4": "mx_master"})
        self.assertEqual(backend.effectiveDeviceLayoutKey, "mx_master")

    def test_connected_device_supported_buttons_filter_mapping_list(self):
        device = SimpleNamespace(
            key="mx_master_3s",
            display_name="MX Master 3S",
            dpi_min=200,
            dpi_max=8000,
            ui_layout="mx_master_3s",
            supported_buttons=("middle", "xbutton1"),
        )

        with (
            patch("ui.backend.load_config", return_value=copy.deepcopy(DEFAULT_CONFIG)),
            patch("ui.backend.save_config"),
            patch("ui.backend.supports_login_startup", return_value=False),
        ):
            backend = Backend(
                engine=_FakeEngine(
                    device_connected=True,
                    connected_device=device,
                )
            )

        button_keys = [button["key"] for button in backend.buttons]
        self.assertIn("middle", button_keys)
        self.assertIn("xbutton1", button_keys)
        self.assertNotIn("gesture", button_keys)
        self.assertNotIn("mode_shift", button_keys)
        xbutton1 = next(button for button in backend.buttons if button["key"] == "xbutton1")
        self.assertTrue(xbutton1["supportsMultiAction"])
        self.assertEqual(xbutton1["longActionId"], "none")
        self.assertEqual(xbutton1["longActionLabel"], "Do Nothing (Pass-through)")

    def test_connected_device_capability_buttons_filter_mapping_list(self):
        device = SimpleNamespace(
            key="mystery_logitech",
            display_name="Mystery Logitech Mouse",
            dpi_min=200,
            dpi_max=8000,
            ui_layout="generic_mouse",
            supported_buttons=("middle", "gesture", "mode_shift"),
            capabilities=SimpleNamespace(
                reprogrammable_buttons=("middle", "xbutton1", "xbutton2"),
            ),
            capability_inventory=SimpleNamespace(has_reprog_controls=True),
        )

        with (
            patch("ui.backend.load_config", return_value=copy.deepcopy(DEFAULT_CONFIG)),
            patch("ui.backend.save_config"),
            patch("ui.backend.supports_login_startup", return_value=False),
        ):
            backend = Backend(
                engine=_FakeEngine(
                    device_connected=True,
                    connected_device=device,
                )
            )

        button_keys = [button["key"] for button in backend.buttons]
        self.assertEqual(button_keys, ["middle", "xbutton1", "xbutton2"])
        for button in backend.buttons:
            self.assertEqual(
                button["supportsMultiAction"],
                button["key"] in ("middle", "xbutton1", "xbutton2"),
            )

    def test_generic_mouse_mode_exposes_standard_buttons_without_logitech_connection(self):
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg["settings"]["generic_mouse_enabled"] = True

        with patch("ui.backend.sys.platform", "win32"):
            backend = self._make_backend(cfg=cfg)

            button_keys = [button["key"] for button in backend.buttons]
            self.assertEqual(
                button_keys,
                ["middle", "generic_xbutton1", "generic_xbutton2"],
            )
            button_names = [button["name"] for button in backend.buttons]
            self.assertEqual(
                button_names,
                [
                    "Middle Button",
                    "Side Button 1 — Back",
                    "Side Button 2 — Forward",
                ],
            )
            for button in backend.buttons:
                self.assertTrue(button["supportsMultiAction"])
                self.assertEqual(button["actionId"], "none")
                self.assertEqual(button["longActionId"], "none")

            mapping_keys = [
                mapping["key"] for mapping in backend.getProfileMappings("default")
            ]
            self.assertEqual(
                mapping_keys,
                ["middle", "generic_xbutton1", "generic_xbutton2"],
            )

    @patch("ui.backend.sys.platform", "win32")
    def test_generic_mouse_layout_localizes_labels_without_changing_action_ids(self):
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg["settings"]["generic_mouse_enabled"] = True
        mappings = cfg["profiles"]["default"]["mappings"]
        mappings["middle"] = "screenshot_region_clip"
        mappings["generic_xbutton1"] = "copy"
        mappings["generic_xbutton2"] = "paste"
        locale_manager = LocaleManager("en")

        backend = self._make_backend(
            engine=_FakeEngine(device_connected=False, connected_device=None),
            cfg=cfg,
            locale_manager=locale_manager,
        )
        saved_mappings = copy.deepcopy(
            backend._cfg["profiles"]["default"]["mappings"]
        )

        self.assertFalse(backend.mouseConnected)
        self.assertEqual(backend.effectiveDeviceLayoutKey, "generic_mouse")

        def visible_labels():
            return [
                (
                    locale_manager.trButton(button["name"]),
                    locale_manager.trAction(button["actionLabel"]),
                )
                for button in backend.buttons
            ]

        action_ids = [button["actionId"] for button in backend.buttons]
        self.assertEqual(
            visible_labels(),
            [
                ("Middle Button", "Screenshot Region → Clipboard"),
                ("Side Button 1 — Back", "Copy (Ctrl+C)"),
                ("Side Button 2 — Forward", "Paste (Ctrl+V)"),
            ],
        )
        self.assertFalse(
            any(
                "\u4e00" <= char <= "\u9fff"
                for label_pair in visible_labels()
                for label in label_pair
                for char in label
            )
        )

        locale_manager.setLanguage("zh_CN")

        self.assertEqual(
            visible_labels(),
            [
                ("\u4e2d\u952e", "\u533a\u57df\u622a\u56fe → \u526a\u8d34\u677f"),
                ("\u4fa7\u952e 1 — \u540e\u9000", "\u590d\u5236 (Ctrl+C)"),
                ("\u4fa7\u952e 2 — \u524d\u8fdb", "\u7c98\u8d34 (Ctrl+V)"),
            ],
        )
        self.assertEqual(
            [button["actionId"] for button in backend.buttons],
            action_ids,
        )
        self.assertEqual(
            backend._cfg["profiles"]["default"]["mappings"],
            saved_mappings,
        )

    @patch("ui.backend.sys.platform", "win32")
    def test_generic_mouse_remaps_interactive_xbutton_hotspots(self):
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg["settings"]["generic_mouse_enabled"] = True
        backend = self._make_backend(cfg=cfg)
        physical_hotspots = [
            {"buttonKey": "xbutton1", "label": "Back"},
            {"buttonKey": "xbutton2", "label": "Forward"},
            {"buttonKey": "middle", "label": "Middle"},
        ]
        backend._device_layout = {"hotspots": physical_hotspots}

        self.assertEqual(
            [item["buttonKey"] for item in backend.deviceHotspots],
            ["generic_xbutton1", "generic_xbutton2", "middle"],
        )
        self.assertEqual(
            [item["buttonKey"] for item in physical_hotspots],
            ["xbutton1", "xbutton2", "middle"],
        )

    def test_device_status_no_logitech_generic_off(self):
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg["settings"]["generic_mouse_enabled"] = False

        with patch("ui.backend.sys.platform", "win32"):
            backend = self._make_backend(cfg=cfg)

        self.assertFalse(backend.mouseConnected)
        self.assertEqual(backend.deviceStatusKind, "no_supported_mouse")

    def test_device_status_no_logitech_generic_on(self):
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg["settings"]["generic_mouse_enabled"] = True

        with patch("ui.backend.sys.platform", "win32"):
            backend = self._make_backend(cfg=cfg)

            self.assertFalse(backend.mouseConnected)
            self.assertEqual(backend.deviceStatusKind, "generic_ready")

    def test_generic_mouse_toggle_updates_device_status_immediately(self):
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg["settings"]["generic_mouse_enabled"] = False

        with patch("ui.backend.sys.platform", "win32"):
            backend = self._make_backend(cfg=cfg)
            notifications = []
            backend.deviceStatusChanged.connect(lambda: notifications.append(backend.deviceStatusKind))

            backend.setGenericMouseEnabled(True)
            backend.setGenericMouseEnabled(False)

        self.assertEqual(notifications, ["generic_ready", "no_supported_mouse"])
        self.assertFalse(backend.mouseConnected)
        self.assertFalse(backend._mouse_connected)

    def test_logitech_connected_takes_precedence_over_generic_ready(self):
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg["settings"]["generic_mouse_enabled"] = True
        device = SimpleNamespace(
            key="mx_master_3",
            display_name="MX Master 3",
            dpi_min=200,
            dpi_max=8000,
            ui_layout="mx_master_3",
        )

        with patch("ui.backend.sys.platform", "win32"):
            backend = self._make_backend(
                engine=_FakeEngine(device_connected=True, connected_device=device),
                cfg=cfg,
            )

        self.assertTrue(backend.mouseConnected)
        self.assertEqual(backend.deviceStatusKind, "logitech_connected")
        self.assertEqual(backend.deviceDisplayName, "MX Master 3")

    def test_logitech_disconnect_falls_back_to_generic_ready_when_enabled(self):
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg["settings"]["generic_mouse_enabled"] = True
        device = SimpleNamespace(
            key="mx_master_3",
            display_name="MX Master 3",
            dpi_min=200,
            dpi_max=8000,
            ui_layout="mx_master_3",
        )

        with patch("ui.backend.sys.platform", "win32"):
            backend = self._make_backend(
                engine=_FakeEngine(device_connected=True, connected_device=device),
                cfg=cfg,
            )
            notifications = []
            backend.deviceStatusChanged.connect(lambda: notifications.append(backend.deviceStatusKind))
            backend._handleConnectionChange(False)

            self.assertFalse(backend.mouseConnected)
            self.assertEqual(backend.deviceStatusKind, "generic_ready")
            self.assertEqual(notifications, ["generic_ready"])

    def test_generic_mouse_mode_coexists_with_logitech_layout_without_duplicates(self):
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg["settings"]["generic_mouse_enabled"] = True
        device = SimpleNamespace(
            key="mx_master_3s",
            display_name="MX Master 3S",
            dpi_min=200,
            dpi_max=8000,
            ui_layout="mx_master_3s",
            supported_buttons=(
                "middle",
                "gesture",
                "xbutton1",
                "xbutton2",
                "hscroll_left",
                "hscroll_right",
                "mode_shift",
            ),
        )

        with (
            patch("ui.backend.load_config", return_value=cfg),
            patch("ui.backend.save_config"),
            patch("ui.backend.supports_login_startup", return_value=False),
            patch("ui.backend.sys.platform", "win32"),
        ):
            backend = Backend(
                engine=_FakeEngine(
                    device_connected=True,
                    connected_device=device,
                    cfg=cfg,
                )
            )

            button_keys = [button["key"] for button in backend.buttons]
            self.assertEqual(button_keys.count("middle"), 1)
            self.assertEqual(button_keys.count("generic_xbutton1"), 1)
            self.assertEqual(button_keys.count("generic_xbutton2"), 1)
            self.assertNotIn("xbutton1", button_keys)
            self.assertNotIn("xbutton2", button_keys)
            self.assertIn("gesture", button_keys)
            self.assertIn("hscroll_left", button_keys)
            self.assertIn("hscroll_right", button_keys)
            self.assertIn("mode_shift", button_keys)

    def test_set_generic_mouse_enabled_persists_and_reloads_mappings(self):
        engine = _FakeEngine()
        cfg = copy.deepcopy(DEFAULT_CONFIG)

        with (
            patch("ui.backend.load_config", return_value=cfg),
            patch("ui.backend.save_config") as save_config,
            patch("ui.backend.supports_login_startup", return_value=False),
            patch("ui.backend.sys.platform", "win32"),
        ):
            backend = Backend(engine=engine)
            backend.setGenericMouseEnabled(True)
            self.assertTrue(backend.genericMouseEnabled)

        self.assertTrue(backend._cfg["settings"]["generic_mouse_enabled"])
        self.assertEqual(engine.reload_count, 1)
        save_config.assert_called_once_with(backend._cfg)

    def test_localized_mapping_status_does_not_translate_mapping_data(self):
        engine = _FakeEngine()
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg["settings"]["language"] = "zh_CN"
        locale_manager = LocaleManager(cfg["settings"]["language"])
        backend = self._make_backend(
            engine=engine,
            cfg=cfg,
            locale_manager=locale_manager,
        )
        statuses = []
        backend.statusMessage.connect(statuses.append)

        backend.setMapping("middle", "copy")
        backend.setProfileMapping("default", "generic_xbutton1", "paste")

        mappings = backend._cfg["profiles"]["default"]["mappings"]
        self.assertEqual(statuses, ["\u5df2\u4fdd\u5b58", "\u5df2\u4fdd\u5b58"])
        self.assertEqual(mappings["middle"], "copy")
        self.assertEqual(mappings["generic_xbutton1"], "paste")
        self.assertEqual(mappings["xbutton1"], "alt_tab")
        self.assertIn("generic_xbutton1_long", mappings)
        self.assertEqual(engine.reload_count, 2)

    def test_mx_master_side_button_edits_persist_reload_and_stay_device_specific(self):
        from core.engine import Engine

        persisted = copy.deepcopy(DEFAULT_CONFIG)
        persisted["settings"]["generic_mouse_enabled"] = False
        persisted["settings"]["debug_mode"] = True
        persisted["profiles"]["work"] = copy.deepcopy(
            persisted["profiles"]["default"]
        )
        persisted["profiles"]["work"]["label"] = "Work"
        persisted["profiles"]["work"]["mappings"]["xbutton1"] = "cut"
        device = SimpleNamespace(
            key="mx_master_3",
            name="MX Master 3",
            transport="bluetooth",
            supported_buttons=("middle", "xbutton1", "xbutton2"),
            capabilities=SimpleNamespace(
                reprogrammable_buttons=("middle", "xbutton1", "xbutton2"),
            ),
            capability_inventory=SimpleNamespace(
                has_reprog_controls=True,
                control_cids=(0x0052, 0x0053, 0x0056),
            ),
        )

        def load_persisted(**_):
            return copy.deepcopy(persisted)

        def save_persisted(updated):
            nonlocal persisted
            persisted = copy.deepcopy(updated)

        with (
            patch("ui.backend.load_config", side_effect=load_persisted),
            patch("ui.backend.save_config", side_effect=save_persisted),
            patch("ui.backend.supports_login_startup", return_value=False),
            patch("ui.backend.sys.platform", "win32"),
            patch("core.config.save_config", side_effect=save_persisted),
            patch("core.engine.load_config", side_effect=load_persisted),
            patch("core.engine.MouseHook", _DisconnectedInspectableMouseHook),
            patch("core.engine.AppDetector", _FakeAppDetector),
            patch("core.engine.sys.platform", "win32"),
        ):
            engine = Engine()
            engine.hook.connected_device = device
            engine.hook.device_connected = True
            engine.reload_mappings()
            backend = Backend(engine=engine)
            initial_generation = engine.hook.capture_binding_snapshot().generation

            backend.setProfileMapping("default", "xbutton1", "copy")
            backend.setProfileMapping("default", "xbutton2", "paste")

            mappings = persisted["profiles"]["default"]["mappings"]
            self.assertEqual(mappings["xbutton1"], "copy")
            self.assertEqual(mappings["xbutton2"], "paste")
            self.assertEqual(mappings["generic_xbutton1"], "none")
            self.assertFalse(persisted["settings"]["generic_mouse_enabled"])
            self.assertGreater(
                engine.hook.capture_binding_snapshot().generation,
                initial_generation,
            )
            ui_mappings = {
                item["key"]: item["actionId"]
                for item in backend.getProfileMappings("default")
            }
            self.assertEqual(ui_mappings["xbutton1"], "copy")
            self.assertEqual(ui_mappings["xbutton2"], "paste")
            self.assertIn(
                "control=xbutton1 saved_key=xbutton1 action=copy",
                backend.debugLog,
            )
            self.assertIn("active_profile=default", backend.debugLog)
            self.assertIn("generation=", backend.debugLog)

            with patch("core.engine.execute_action") as execute_action_mock:
                debug_messages = []
                engine._debug_cb = debug_messages.append
                snapshot = engine.hook.capture_binding_snapshot()
                for event_type in (
                    MouseEvent.LOGI_XBUTTON1_DOWN,
                    MouseEvent.LOGI_XBUTTON2_DOWN,
                ):
                    route = snapshot.routes[event_type]
                    snapshot.callbacks[event_type][0](SimpleNamespace(
                        event_type=event_type,
                        binding_route=route,
                    ))
            self.assertEqual(
                [item.args for item in execute_action_mock.call_args_list],
                [("copy",), ("paste",)],
            )
            self.assertTrue(any(
                "logical=xbutton1" in message and "action=copy" in message
                for message in debug_messages
            ))

            restarted = Engine()
            restarted.hook.connected_device = device
            restarted.hook.device_connected = True
            restarted.reload_mappings()
            self.assertEqual(
                restarted.cfg["profiles"]["default"]["mappings"]["xbutton1"],
                "copy",
            )
            restarted._switch_profile("work")
            with patch("core.engine.execute_action") as execute_action_mock:
                snapshot = restarted.hook.capture_binding_snapshot()
                snapshot.callbacks[MouseEvent.LOGI_XBUTTON1_DOWN][0](
                    SimpleNamespace(
                        event_type=MouseEvent.LOGI_XBUTTON1_DOWN,
                        binding_route="xbutton1",
                    )
                )
            execute_action_mock.assert_called_once_with("cut")
            restarted._switch_profile("default")
            self.assertEqual(
                restarted.hook.capture_binding_snapshot().routes[
                    MouseEvent.LOGI_XBUTTON1_DOWN
                ],
                "xbutton1",
            )

    def test_generic_mouse_toggle_clears_live_xbutton_hook_state(self):
        from core.engine import Engine

        persisted = copy.deepcopy(DEFAULT_CONFIG)
        persisted["settings"]["generic_mouse_enabled"] = True
        persisted["profiles"]["default"]["mappings"]["generic_xbutton1"] = "browser_back"
        persisted["profiles"]["default"]["mappings"]["generic_xbutton1_long"] = "copy"

        def load_persisted(**_):
            return copy.deepcopy(persisted)

        def save_persisted(updated):
            nonlocal persisted
            persisted = copy.deepcopy(updated)

        with (
            patch("ui.backend.load_config", side_effect=load_persisted),
            patch("ui.backend.save_config", side_effect=save_persisted),
            patch("ui.backend.supports_login_startup", return_value=False),
            patch("ui.backend.sys.platform", "win32"),
            patch("core.engine.load_config", side_effect=load_persisted),
            patch("core.engine.MouseHook", _DisconnectedInspectableMouseHook),
            patch("core.engine.AppDetector", _FakeAppDetector),
            patch("core.engine.sys.platform", "win32"),
        ):
            engine = Engine()
            backend = Backend(engine=engine)

            self.assertTrue(engine.cfg["settings"]["generic_mouse_enabled"])
            self.assertIn(MouseEvent.XBUTTON1_DOWN, engine.hook._callbacks)
            self.assertIn(MouseEvent.XBUTTON1_UP, engine.hook._callbacks)
            self.assertIn(MouseEvent.XBUTTON1_DOWN, engine.hook._blocked_events)
            self.assertIn(MouseEvent.XBUTTON1_UP, engine.hook._blocked_events)

            backend.setGenericMouseEnabled(False)

            self.assertFalse(persisted["settings"]["generic_mouse_enabled"])
            self.assertFalse(engine.cfg["settings"]["generic_mouse_enabled"])
            self.assertEqual(engine.cfg["profiles"]["default"]["mappings"]["xbutton1"], "alt_tab")
            self.assertEqual(
                engine.cfg["profiles"]["default"]["mappings"]["generic_xbutton1"],
                "browser_back",
            )
            self.assertNotIn(MouseEvent.XBUTTON1_DOWN, engine.hook._callbacks)
            self.assertNotIn(MouseEvent.XBUTTON1_UP, engine.hook._callbacks)
            self.assertNotIn(MouseEvent.XBUTTON2_DOWN, engine.hook._callbacks)
            self.assertNotIn(MouseEvent.XBUTTON2_UP, engine.hook._callbacks)
            self.assertNotIn(MouseEvent.XBUTTON1_DOWN, engine.hook._blocked_events)
            self.assertNotIn(MouseEvent.XBUTTON1_UP, engine.hook._blocked_events)
            self.assertNotIn(MouseEvent.XBUTTON2_DOWN, engine.hook._blocked_events)
            self.assertNotIn(MouseEvent.XBUTTON2_UP, engine.hook._blocked_events)

            backend.setGenericMouseEnabled(True)

            self.assertTrue(persisted["settings"]["generic_mouse_enabled"])
            self.assertTrue(engine.cfg["settings"]["generic_mouse_enabled"])
            self.assertIn(MouseEvent.XBUTTON1_DOWN, engine.hook._callbacks)
            self.assertIn(MouseEvent.XBUTTON1_UP, engine.hook._callbacks)
            self.assertIn(MouseEvent.XBUTTON1_DOWN, engine.hook._blocked_events)
            self.assertIn(MouseEvent.XBUTTON1_UP, engine.hook._blocked_events)
            self.assertEqual(len(engine.hook._callbacks[MouseEvent.XBUTTON1_DOWN]), 1)
            self.assertEqual(len(engine.hook._callbacks[MouseEvent.XBUTTON1_UP]), 1)

    def test_disconnect_clears_stale_linux_device_identity_and_layout(self):
        device = SimpleNamespace(
            key="mx_master_3",
            display_name="MX Master 3S",
            dpi_min=200,
            dpi_max=8000,
            ui_layout="mx_master_3",
        )

        def fake_layout(key):
            return {"key": key, "interactive": key != "generic_mouse"}

        with (
            patch("ui.backend.load_config", return_value=copy.deepcopy(DEFAULT_CONFIG)),
            patch("ui.backend.save_config"),
            patch("ui.backend.supports_login_startup", return_value=False),
            patch("ui.backend.get_device_layout", side_effect=fake_layout),
        ):
            backend = Backend(engine=_FakeEngine(device_connected=True, connected_device=device))
            self.assertTrue(backend.mouseConnected)
            self.assertEqual(backend.connectedDeviceKey, "mx_master_3")
            self.assertEqual(backend.effectiveDeviceLayoutKey, "mx_master_3")
            backend._battery_level = 42

            backend._handleConnectionChange(False)

        self.assertFalse(backend.mouseConnected)
        self.assertEqual(backend.connectedDeviceKey, "")
        self.assertEqual(backend.effectiveDeviceLayoutKey, "generic_mouse")
        self.assertEqual(backend.batteryLevel, -1)

    def test_refresh_updates_hid_features_without_reemitting_connection_edge(self):
        device = SimpleNamespace(
            key="mx_master_3",
            display_name="MX Master 3S",
            dpi_min=200,
            dpi_max=8000,
            ui_layout="mx_master_3",
        )

        def fake_layout(key):
            return {"key": key, "interactive": key != "generic_mouse"}

        engine = _FakeEngine(
            device_connected=True,
            connected_device=None,
            hid_features_ready=False,
            smart_shift_supported=False,
        )

        with (
            patch("ui.backend.load_config", return_value=copy.deepcopy(DEFAULT_CONFIG)),
            patch("ui.backend.save_config"),
            patch("ui.backend.supports_login_startup", return_value=False),
            patch("ui.backend.get_device_layout", side_effect=fake_layout),
        ):
            backend = Backend(engine=engine)
            mouse_notifications = []
            hid_notifications = []
            backend.mouseConnectedChanged.connect(lambda: mouse_notifications.append(True))
            backend.hidFeaturesReadyChanged.connect(lambda: hid_notifications.append(True))

            engine.connected_device = device
            engine.hid_features_ready = True
            engine.smart_shift_supported = True
            backend._handleConnectionChange(True)

        self.assertTrue(backend.mouseConnected)
        self.assertTrue(backend.hidFeaturesReady)
        self.assertTrue(backend.smartShiftSupported)
        self.assertEqual(backend.connectedDeviceKey, "mx_master_3")
        self.assertEqual(mouse_notifications, [])
        self.assertEqual(hid_notifications, [True])

    def test_retry_refresh_promotes_late_hid_features_ready(self):
        device = SimpleNamespace(
            key="mx_master_3",
            display_name="MX Master 3S",
            dpi_min=200,
            dpi_max=8000,
            ui_layout="mx_master",
        )
        engine = _FakeEngine(
            device_connected=True,
            connected_device=None,
            hid_features_ready=False,
            smart_shift_supported=False,
        )
        backend = self._make_backend(engine=engine)
        backend._mouse_connected = True
        hid_notifications = []
        backend.hidFeaturesReadyChanged.connect(lambda: hid_notifications.append(True))

        engine.connected_device = device
        engine.hid_features_ready = True
        engine.smart_shift_supported = True
        backend._refresh_connected_device_info()

        self.assertTrue(backend.hidFeaturesReady)
        self.assertTrue(backend.smartShiftSupported)
        self.assertEqual(backend.connectedDeviceKey, "mx_master_3")
        self.assertEqual(hid_notifications, [True])

    def test_init_wires_engine_status_callback_into_backend(self):
        engine = _FakeEngine()

        backend = self._make_backend(engine=engine)

        self.assertIsNotNone(engine.status_callback)
        self.assertIs(engine.status_callback.__self__, backend)
        self.assertIs(engine.status_callback.__func__, Backend._onEngineStatusMessage)

    def test_screenshot_directory_defaults_to_system_behavior(self):
        backend = self._make_backend()

        self.assertEqual(backend.screenshotDirectory, "")
        self.assertEqual(backend.screenshotDirectoryLabel, "")
        self.assertFalse(backend.hasCustomScreenshotDirectory)

    def test_next_screenshot_file_path_uses_custom_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = copy.deepcopy(DEFAULT_CONFIG)
            cfg["settings"]["screenshot_directory"] = tmp
            with (
                patch("ui.backend.load_config", return_value=cfg),
                patch("ui.backend.save_config"),
                patch("ui.backend.supports_login_startup", return_value=False),
            ):
                backend = Backend(engine=None)

            path = backend.next_screenshot_file_path()

        self.assertEqual(path.parent, Path(tmp))
        self.assertTrue(path.name.startswith("Screenshot "))
        self.assertEqual(path.suffix, ".png")

    def test_next_screenshot_file_paths_reserves_multiple_custom_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = copy.deepcopy(DEFAULT_CONFIG)
            cfg["settings"]["screenshot_directory"] = tmp
            with (
                patch("ui.backend.load_config", return_value=cfg),
                patch("ui.backend.save_config"),
                patch("ui.backend.supports_login_startup", return_value=False),
            ):
                backend = Backend(engine=None)

            paths = backend.next_screenshot_file_paths(2)

        self.assertEqual([path.parent for path in paths], [Path(tmp), Path(tmp)])
        self.assertEqual(len({path.name for path in paths}), 2)

    def test_choose_screenshot_directory_persists_valid_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = copy.deepcopy(DEFAULT_CONFIG)
            with (
                patch("ui.backend.load_config", return_value=cfg),
                patch("ui.backend.save_config") as save_mock,
                patch("ui.backend.supports_login_startup", return_value=False),
                patch(
                    "PySide6.QtWidgets.QFileDialog.getExistingDirectory",
                    return_value=tmp,
                ),
            ):
                backend = Backend(engine=None)
                statuses = []
                backend.statusMessage.connect(statuses.append)
                backend.chooseScreenshotDirectory()

        self.assertEqual(backend.screenshotDirectory, str(Path(tmp)))
        self.assertTrue(backend.hasCustomScreenshotDirectory)
        save_mock.assert_called_once()
        self.assertEqual(statuses, ["Saved"])

    def test_choose_screenshot_directory_ignores_invalid_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            file_path = Path(tmp) / "not-a-folder"
            file_path.write_text("x", encoding="utf-8")
            cfg = copy.deepcopy(DEFAULT_CONFIG)
            with (
                patch("ui.backend.load_config", return_value=cfg),
                patch("ui.backend.save_config") as save_mock,
                patch("ui.backend.supports_login_startup", return_value=False),
                patch(
                    "PySide6.QtWidgets.QFileDialog.getExistingDirectory",
                    return_value=str(file_path),
                ),
            ):
                backend = Backend(engine=None)
                statuses = []
                backend.statusMessage.connect(statuses.append)
                backend.chooseScreenshotDirectory()

        self.assertEqual(backend.screenshotDirectory, "")
        save_mock.assert_not_called()
        self.assertEqual(statuses, ["Choose a valid screenshot folder"])

    def test_reset_screenshot_directory_clears_custom_folder(self):
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg["settings"]["screenshot_directory"] = "/tmp/screens"
        with (
            patch("ui.backend.load_config", return_value=cfg),
            patch("ui.backend.save_config") as save_mock,
            patch("ui.backend.supports_login_startup", return_value=False),
        ):
            backend = Backend(engine=None)
            statuses = []
            backend.statusMessage.connect(statuses.append)
            backend.resetScreenshotDirectory()

        self.assertEqual(backend.screenshotDirectory, "")
        self.assertFalse(backend.hasCustomScreenshotDirectory)
        save_mock.assert_called_once()
        self.assertEqual(statuses, ["Saved"])

    def test_replay_failure_status_becomes_backend_status_message(self):
        app = _ensure_qapp()
        engine = _FakeEngine()

        with (
            patch("ui.backend.load_config", return_value=copy.deepcopy(DEFAULT_CONFIG)),
            patch("ui.backend.save_config"),
            patch("ui.backend.supports_login_startup", return_value=False),
        ):
            backend = Backend(engine=engine)
            status_messages = []
            backend.statusMessage.connect(status_messages.append)

            engine.status_callback("Failed to replay HID++ settings after reconnect")
            app.processEvents()

        self.assertEqual(
            status_messages,
            ["Failed to replay HID++ settings after reconnect"],
        )

    def test_non_dict_smart_shift_payload_does_not_emit_change_signal(self):
        backend = self._make_backend()
        notifications = []
        backend.smartShiftChanged.connect(lambda: notifications.append(True))

        backend._pending_smart_shift_state = "freespin"
        backend._handleSmartShiftRead()

        self.assertEqual(notifications, [])

    def test_non_dict_smart_shift_payload_does_not_mutate_config(self):
        backend = self._make_backend()
        original = copy.deepcopy(backend._cfg["settings"])

        backend._pending_smart_shift_state = "freespin"
        backend._handleSmartShiftRead()

        self.assertEqual(backend._cfg["settings"], original)

    def test_linux_reports_gesture_direction_support(self):
        backend = self._make_backend()

        with patch("ui.backend.sys.platform", "linux"):
            self.assertTrue(backend.supportsGestureDirections)

    def test_known_apps_include_paths_and_refresh_signal(self):
        backend = self._make_backend()
        fake_catalog = [
            {
                "id": "code.desktop",
                "label": "Visual Studio Code",
                "path": "/usr/bin/code",
                "aliases": ["code.desktop", "Visual Studio Code"],
                "legacy_icon": "",
            }
        ]
        notifications = []
        backend.knownAppsChanged.connect(lambda: notifications.append(True))

        with (
            patch("ui.backend.app_catalog.get_app_catalog", return_value=fake_catalog),
            patch("ui.backend.get_icon_for_exe", return_value=""),
        ):
            apps = backend.knownApps
            backend.refreshKnownAppsSilently()

        self.assertEqual(apps[0]["path"], "/usr/bin/code")
        self.assertEqual(len(notifications), 1)

    def test_shortcut_capture_keeps_ctrl_and_super_distinct_on_macos(self):
        backend = self._make_backend()

        with patch("ui.backend.sys.platform", "darwin"):
            self.assertEqual(
                backend.shortcutComboFromQtEvent(
                    Qt.Key_W,
                    Qt.ControlModifier,
                    "w",
                ),
                "super+w",
            )
            self.assertEqual(
                backend.shortcutComboFromQtEvent(
                    Qt.Key_W,
                    Qt.MetaModifier,
                    "w",
                ),
                "ctrl+w",
            )

    def test_shortcut_capture_preserves_default_qt_modifier_names_off_macos(self):
        backend = self._make_backend()

        with patch("ui.backend.sys.platform", "linux"):
            self.assertEqual(
                backend.shortcutComboFromQtEvent(
                    Qt.Key_W,
                    Qt.ControlModifier,
                    "w",
                ),
                "ctrl+w",
            )
            self.assertEqual(
                backend.shortcutComboFromQtEvent(
                    Qt.Key_W,
                    Qt.MetaModifier,
                    "w",
                ),
                "super+w",
            )

    def test_shortcut_capture_accepts_qt_enum_objects(self):
        backend = self._make_backend()

        with patch("ui.backend.sys.platform", "darwin"):
            self.assertEqual(
                backend.shortcutComboFromQtEvent(
                    Qt.Key_W,
                    Qt.ControlModifier,
                    "w",
                ),
                "super+w",
            )

    def test_shortcut_capture_keeps_enter_and_escape_capturable(self):
        backend = self._make_backend()

        self.assertEqual(
            backend.shortcutComboFromQtEvent(
                Qt.Key_Return,
                Qt.NoModifier,
                "",
            ),
            "enter",
        )
        self.assertEqual(
            backend.shortcutComboFromQtEvent(
                Qt.Key_Enter,
                Qt.NoModifier,
                "",
            ),
            "enter",
        )
        self.assertEqual(
            backend.shortcutComboFromQtEvent(
                Qt.Key_Escape,
                Qt.NoModifier,
                "",
            ),
            "esc",
        )

    def test_shortcut_capture_accepts_extended_function_keys(self):
        backend = self._make_backend()

        with patch("ui.backend.sys.platform", "win32"):
            self.assertEqual(
                backend.shortcutComboFromQtEvent(
                    Qt.Key_F13,
                    Qt.NoModifier,
                    "",
                ),
                "f13",
            )
            self.assertEqual(
                backend.shortcutComboFromQtEvent(
                    Qt.Key_F24,
                    Qt.ControlModifier,
                    "",
                ),
                "ctrl+f24",
            )

    def test_shortcut_capture_accepts_shifted_symbol_text(self):
        backend = self._make_backend()

        with patch("ui.backend.sys.platform", "win32"):
            self.assertEqual(
                backend.shortcutComboFromQtEvent(
                    Qt.Key_Comma,
                    Qt.ControlModifier | Qt.ShiftModifier,
                    "<",
                ),
                "ctrl+shift+comma",
            )

    def test_reserved_custom_shortcut_warning_slot(self):
        backend = self._make_backend()

        self.assertTrue(backend.isReservedCustomShortcut("Win+Shift+S"))
        self.assertFalse(backend.isReservedCustomShortcut("Ctrl+Shift+P"))

    def test_custom_shortcut_validation_error_info_explains_parse_failure(self):
        backend = self._make_backend()

        self.assertEqual(backend.customShortcutValidationErrorInfo("Ctrl+Shift+P"), {})
        self.assertEqual(
            backend.customShortcutValidationErrorInfo("Ctrl+A+B"),
            {"code": "multiple_main_keys", "detail": ""},
        )
        self.assertEqual(
            backend.customShortcutValidationErrorInfo("Ctrl++"),
            {"code": "empty_segment", "detail": ""},
        )
        self.assertEqual(
            backend.customShortcutValidationErrorInfo("Ctrl+Hyperdrive"),
            {"code": "unknown_key", "detail": "Hyperdrive"},
        )

    def test_add_profile_stores_catalog_id_for_linux_app(self):
        backend = self._make_backend()
        fake_catalog = [
            {
                "id": "firefox.desktop",
                "label": "Firefox",
                "path": "/usr/bin/firefox",
                "aliases": ["firefox.desktop", "/usr/bin/firefox", "firefox"],
                "legacy_icon": "",
            }
        ]
        fake_entry = {
            "id": "firefox.desktop",
            "label": "Firefox",
            "path": "/usr/bin/firefox",
            "aliases": ["firefox.desktop", "/usr/bin/firefox", "firefox"],
            "legacy_icon": "",
        }

        with (
            patch("ui.backend.app_catalog.get_app_catalog", return_value=fake_catalog),
            patch("ui.backend.app_catalog.resolve_app_spec", return_value=fake_entry),
            patch("ui.backend.create_profile", side_effect=self._fake_create_profile),
        ):
            backend.addProfile("firefox.desktop")

        self.assertEqual(
            backend._cfg["profiles"]["firefox"]["apps"],
            ["firefox.desktop"],
        )

    def test_add_profile_rejects_linux_duplicate_when_existing_profile_uses_legacy_path(self):
        backend = self._make_backend()
        backend._cfg["profiles"]["firefox"] = {
            "label": "Firefox",
            "apps": ["/usr/bin/firefox"],
            "mappings": {},
        }
        fake_catalog = [
            {
                "id": "firefox.desktop",
                "label": "Firefox",
                "path": "/usr/bin/firefox",
                "aliases": ["firefox.desktop", "/usr/bin/firefox", "firefox"],
                "legacy_icon": "",
            }
        ]
        status_messages = []
        backend.statusMessage.connect(status_messages.append)

        def resolve_app(spec):
            if spec in ("firefox.desktop", "/usr/bin/firefox"):
                return {
                    "id": "firefox.desktop",
                    "label": "Firefox",
                    "path": "/usr/bin/firefox",
                    "aliases": ["firefox.desktop", "/usr/bin/firefox", "firefox"],
                    "legacy_icon": "",
                }
            return None

        with (
            patch("ui.backend.app_catalog.get_app_catalog", return_value=fake_catalog),
            patch("ui.backend.app_catalog.resolve_app_spec", side_effect=resolve_app),
            patch("ui.backend.create_profile") as create_profile,
        ):
            backend.addProfile("firefox.desktop")

        create_profile.assert_not_called()
        self.assertIn("Profile already exists", status_messages)


@unittest.skipIf(Backend is None, "PySide6 not installed in test environment")
class BackendLoginStartupTests(unittest.TestCase):
    def test_unverified_config_never_syncs_login_startup(self):
        from core import config

        _ensure_qapp()
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.json"
            malformed = "{not-valid-json"
            config_file.write_text(malformed, encoding="utf-8")
            with (
                patch.object(config, "CONFIG_DIR", temp_dir),
                patch.object(config, "CONFIG_FILE", str(config_file)),
                patch("ui.backend.supports_login_startup", return_value=True),
                patch("ui.backend.sync_login_startup_from_config") as sync_mock,
            ):
                backend = Backend(engine=None)
                try:
                    self.assertFalse(config.config_is_verified(backend._cfg))
                    sync_mock.assert_not_called()
                    self.assertEqual(
                        config_file.read_text(encoding="utf-8"),
                        malformed,
                    )
                finally:
                    config.mark_config_verified_writable(backend._cfg)

    def test_init_calls_sync_from_config_when_supported(self):
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg["settings"]["start_at_login"] = True
        with (
            patch("ui.backend.load_config", return_value=cfg),
            patch("ui.backend.save_config"),
            patch("ui.backend.supports_login_startup", return_value=True),
            patch("ui.backend.sync_login_startup_from_config") as sync_mock,
        ):
            Backend(engine=None)
        sync_mock.assert_called_once_with(True)

    def test_init_clears_start_at_login_when_sync_fails(self):
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg["settings"]["start_at_login"] = True
        with (
            patch("ui.backend.load_config", return_value=cfg),
            patch("ui.backend.save_config") as save_mock,
            patch("ui.backend.supports_login_startup", return_value=True),
            patch(
                "ui.backend.sync_login_startup_from_config",
                side_effect=RuntimeError("bootstrap failed"),
            ),
        ):
            backend = Backend(engine=None)

        self.assertFalse(backend.startAtLogin)
        save_mock.assert_called_once()

    def test_init_sync_failure_keeps_disabled_config_disabled(self):
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg["settings"]["start_at_login"] = False
        with (
            patch("ui.backend.load_config", return_value=cfg),
            patch("ui.backend.save_config") as save_mock,
            patch("ui.backend.supports_login_startup", return_value=True),
            patch(
                "ui.backend.sync_login_startup_from_config",
                side_effect=RuntimeError("bootout failed"),
            ),
        ):
            backend = Backend(engine=None)

        self.assertFalse(backend.startAtLogin)
        save_mock.assert_not_called()

    def test_init_clears_start_at_login_when_unsupported(self):
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg["settings"]["start_at_login"] = True
        with (
            patch("ui.backend.load_config", return_value=cfg),
            patch("ui.backend.save_config"),
            patch("ui.backend.supports_login_startup", return_value=False),
            patch("ui.backend.sync_login_startup_from_config") as sync_mock,
        ):
            backend = Backend(engine=None)
        sync_mock.assert_not_called()
        self.assertFalse(backend.startAtLogin)

    def test_set_start_at_login_calls_apply(self):
        with (
            patch("ui.backend.load_config", return_value=copy.deepcopy(DEFAULT_CONFIG)),
            patch("ui.backend.save_config"),
            patch("ui.backend.supports_login_startup", return_value=True),
            patch("ui.backend.sync_login_startup_from_config"),
            patch("ui.backend.apply_login_startup") as apply_mock,
        ):
            backend = Backend(engine=None)
            backend.setStartAtLogin(True)

        apply_mock.assert_called_once_with(True)
        self.assertTrue(backend.startAtLogin)

    def test_set_start_at_login_keeps_config_when_os_apply_fails(self):
        status_messages = []
        with (
            patch("ui.backend.load_config", return_value=copy.deepcopy(DEFAULT_CONFIG)),
            patch("ui.backend.save_config") as save_mock,
            patch("ui.backend.supports_login_startup", return_value=True),
            patch("ui.backend.sync_login_startup_from_config"),
            patch("ui.backend.apply_login_startup", side_effect=RuntimeError("denied")),
        ):
            backend = Backend(engine=None)
            backend.statusMessage.connect(status_messages.append)
            backend.setStartAtLogin(True)

        save_mock.assert_not_called()
        self.assertFalse(backend.startAtLogin)
        self.assertEqual(status_messages, ["Failed to update login item: denied"])

    def test_set_start_at_login_rolls_back_os_when_config_save_fails(self):
        status_messages = []
        with (
            patch("ui.backend.load_config", return_value=copy.deepcopy(DEFAULT_CONFIG)),
            patch("ui.backend.save_config", side_effect=RuntimeError("disk full")),
            patch("ui.backend.supports_login_startup", return_value=True),
            patch("ui.backend.sync_login_startup_from_config"),
            patch("ui.backend.apply_login_startup") as apply_mock,
        ):
            backend = Backend(engine=None)
            backend.statusMessage.connect(status_messages.append)
            backend.setStartAtLogin(True)

        self.assertEqual([c.args for c in apply_mock.call_args_list], [(True,), (False,)])
        self.assertFalse(backend.startAtLogin)
        self.assertEqual(status_messages, ["Failed to save login item setting: disk full"])

    def test_set_start_at_login_reports_inconsistent_state_when_rollback_fails(self):
        status_messages = []
        with (
            patch("ui.backend.load_config", return_value=copy.deepcopy(DEFAULT_CONFIG)),
            patch("ui.backend.save_config", side_effect=RuntimeError("disk full")),
            patch("ui.backend.supports_login_startup", return_value=True),
            patch("ui.backend.sync_login_startup_from_config"),
            patch(
                "ui.backend.apply_login_startup",
                side_effect=[None, RuntimeError("rollback failed")],
            ) as apply_mock,
        ):
            backend = Backend(engine=None)
            backend.statusMessage.connect(status_messages.append)
            backend.setStartAtLogin(True)

        self.assertEqual([c.args for c in apply_mock.call_args_list], [(True,), (False,)])
        self.assertFalse(backend.startAtLogin)
        self.assertEqual(
            status_messages,
            ["Start-at-login state is inconsistent; please restart MousePro to recover."],
        )

    def test_set_start_minimized_does_not_call_apply_login_startup(self):
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg["settings"]["start_at_login"] = True
        with (
            patch("ui.backend.load_config", return_value=cfg),
            patch("ui.backend.save_config"),
            patch("ui.backend.supports_login_startup", return_value=True),
            patch("ui.backend.sync_login_startup_from_config"),
            patch("ui.backend.apply_login_startup") as apply_mock,
        ):
            backend = Backend(engine=None)
            apply_mock.reset_mock()
            backend.setStartMinimized(False)

        apply_mock.assert_not_called()
        self.assertFalse(backend.startMinimized)


if __name__ == "__main__":
    unittest.main()
