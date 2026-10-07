"""
Configuration manager — loads/saves button mappings to a JSON file.
Supports per-application profiles (for future use).
"""

import json
import os
import stat
import sys
import tempfile
import threading
import traceback
from urllib.parse import quote
from core import app_catalog

if sys.platform == "darwin":
    CONFIG_DIR = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "MousePro")
elif sys.platform == "linux":
    CONFIG_DIR = os.path.join(
        os.environ.get("XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config")),
        "MousePro",
    )
else:
    CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "MousePro")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
_CONFIG_IO_LOCK = threading.RLock()
_READ_ONLY_FALLBACK_CONFIGS = {}


class ConfigLoadError(RuntimeError):
    pass


class ConfigWriteBlockedError(RuntimeError):
    pass


def _mark_config_read_only(cfg):
    # Keep a strong reference so a later object cannot inherit the guard through
    # Python object-id reuse.
    _READ_ONLY_FALLBACK_CONFIGS[id(cfg)] = cfg


def mark_config_verified_writable(cfg):
    """Unlock a shared fallback document after a successful strict reload."""
    with _CONFIG_IO_LOCK:
        guarded = _READ_ONLY_FALLBACK_CONFIGS.get(id(cfg))
        if guarded is cfg:
            del _READ_ONLY_FALLBACK_CONFIGS[id(cfg)]


def _config_write_is_blocked(cfg):
    return _READ_ONLY_FALLBACK_CONFIGS.get(id(cfg)) is cfg


def config_is_verified(cfg):
    """Return whether a config may safely drive runtime or OS side effects."""
    with _CONFIG_IO_LOCK:
        return not _config_write_is_blocked(cfg)

# Which mouse events map to which friendly button names
# Stable MousePro display order (top controls, then side controls).
BUTTON_NAMES = {
    "middle":        "Middle Button",
    "gesture":       "Gesture button",
    "xbutton1":      "Back button",
    "xbutton2":      "Forward button",
    "hscroll_left":  "Horizontal scroll left",
    "hscroll_right": "Horizontal scroll right",
    "mode_shift":    "Mode shift button",
    "dpi_switch":    "DPI switch button",
}

GESTURE_DIRECTION_BUTTONS = (
    "gesture_left",
    "gesture_right",
    "gesture_up",
    "gesture_down",
)

MULTI_ACTION_BUTTONS = (
    "middle",
    "mode_shift",
    "xbutton1",
    "xbutton2",
    "generic_xbutton1",
    "generic_xbutton2",
)
LONG_PRESS_SUFFIX = "_long"
DEFAULT_LONG_PRESS_THRESHOLD_MS = 300
GENERIC_MOUSE_BUTTON_NAMES = {
    "generic_xbutton1": "Side Button 1 — Back",
    "generic_xbutton2": "Side Button 2 — Forward",
}
GENERIC_MOUSE_BUTTONS = tuple(GENERIC_MOUSE_BUTTON_NAMES)
WINDOWS_XBUTTON_KEYS = frozenset(("xbutton1", "xbutton2"))

PROFILE_BUTTON_NAMES = {
    **BUTTON_NAMES,
    **GENERIC_MOUSE_BUTTON_NAMES,
    "gesture_left":  "Gesture swipe left",
    "gesture_right": "Gesture swipe right",
    "gesture_up":    "Gesture swipe up",
    "gesture_down":  "Gesture swipe down",
}

# Maps config button keys to the MouseEvent types they correspond to
BUTTON_TO_EVENTS = {
    "middle":        ("middle_down", "middle_up"),
    "gesture":       ("gesture_click",),
    "gesture_left":  ("gesture_swipe_left",),
    "gesture_right": ("gesture_swipe_right",),
    "gesture_up":    ("gesture_swipe_up",),
    "gesture_down":  ("gesture_swipe_down",),
    "xbutton1":      ("xbutton1_down", "xbutton1_up"),
    "xbutton2":      ("xbutton2_down", "xbutton2_up"),
    "generic_xbutton1": ("xbutton1_down", "xbutton1_up"),
    "generic_xbutton2": ("xbutton2_down", "xbutton2_up"),
    "hscroll_left":  ("hscroll_left",),
    "hscroll_right": ("hscroll_right",),
    "mode_shift":    ("mode_shift_down", "mode_shift_up"),
    "dpi_switch":    ("dpi_switch_down", "dpi_switch_up"),
}


def long_press_mapping_key(button):
    return f"{button}{LONG_PRESS_SUFFIX}"


def supports_multi_action(button):
    return button in MULTI_ACTION_BUTTONS


def resolve_windows_xbutton_mapping_key(
    button,
    *,
    generic_mouse_enabled,
    platform_name=None,
):
    """Resolve a standard XBUTTON event to one active configuration key.

    ``WH_MOUSE_LL`` does not expose per-device identity, so neither live device
    presence nor catalog capabilities can prove which mouse emitted an event.
    Generic Mouse Mode is therefore the only safe Windows route. Returning
    ``None`` leaves the native event untouched.
    """
    if button not in WINDOWS_XBUTTON_KEYS:
        return None
    platform_name = sys.platform if platform_name is None else platform_name
    if platform_name != "win32":
        return button
    if generic_mouse_enabled:
        return f"generic_{button}"
    return None

DEFAULT_CONFIG = {
    "version": 12,
    "active_profile": "default",
    "mousepro": {
        # Right-button-hold gesture chord (wheel = copy / enhanced paste,
        # side button while held = system screenshot).
        "right_hold_gesture_enabled": True,
        # Subset of {"xbutton1", "xbutton2"}; empty/invalid falls back to both.
        "screenshot_side_buttons": ["xbutton1", "xbutton2"],
    },
    "profiles": {
        "default": {
            "label": "Default (All Apps)",
            "apps": [],          # empty = all apps (fallback profile)
            "mappings": {
                "middle": "none",
                "gesture": "none",
                "gesture_left": "none",
                "gesture_right": "none",
                "gesture_up": "none",
                "gesture_down": "none",
                "xbutton1": "alt_tab",
                "xbutton2": "alt_tab",
                "hscroll_left": "browser_back",
                "hscroll_right": "browser_forward",
                "mode_shift": "switch_scroll_mode",
                "mode_shift_long": "switch_scroll_mode",
                "middle_long": "none",
                "xbutton1_long": "none",
                "xbutton2_long": "none",
                "generic_xbutton1": "none",
                "generic_xbutton2": "none",
                "generic_xbutton1_long": "none",
                "generic_xbutton2_long": "none",
            },
        }
    },
    "settings": {
        "start_minimized": True,
        "start_at_login": False,
        "hscroll_threshold": 1,
        "invert_hscroll": False,  # swap horizontal scroll directions
        "invert_vscroll": False,  # swap vertical scroll directions
        "dpi": 1000,              # pointer speed / DPI setting
        "smart_shift_mode": "ratchet",
        "smart_shift_enabled": False,
        "smart_shift_threshold": 25,
        "gesture_threshold": 50,
        "gesture_deadzone": 40,
        "gesture_timeout_ms": 3000,
        "gesture_cooldown_ms": 500,
        "multi_action_long_press_threshold_ms": DEFAULT_LONG_PRESS_THRESHOLD_MS,
        "generic_mouse_enabled": False,
        "appearance_mode": "system",
        "debug_mode": False,
        "device_layout_overrides": {},
        "language": "zh_CN",
        "ignore_trackpad": True,
        "screenshot_directory": "",
        "check_for_updates": True,
        "update_check_state": {},
    },
}

# Known applications for per-app profiles
# Note: Modern UWP apps appear as their package exe (e.g. Microsoft.Media.Player.exe)
# thanks to ApplicationFrameHost child-window resolution in app_detector.py.
# icon values must match filenames in images/ (without extension for png,
# or with extension for non-png like .webp)
KNOWN_APPS = {
    # Windows apps
    "msedge.exe":                {"label": "Microsoft Edge",       "icon": ""},
    "chrome.exe":                {"label": "Google Chrome",        "icon": "chrom"},
    "Microsoft.Media.Player.exe":{"label": "Windows Media Player", "icon": "media.webp"},
    "wmplayer.exe":              {"label": "Windows Media Player (Classic)", "icon": "media.webp"},
    "vlc.exe":                   {"label": "VLC Media Player",     "icon": "VLC"},
    "Code.exe":                  {"label": "Visual Studio Code",   "icon": "VSCODE"},
    # macOS apps (executable names from NSWorkspace)
    "Safari":                    {"label": "Safari",               "icon": ""},
    "Google Chrome":             {"label": "Google Chrome",        "icon": "chrom"},
    "VLC":                       {"label": "VLC Media Player",     "icon": "VLC"},
    "Code":                      {"label": "Visual Studio Code",   "icon": "VSCODE"},
    "Finder":                    {"label": "Finder",               "icon": ""},
}


def get_icon_for_exe(exe_name: str) -> str:
    """Return an image:// URL for the app icon, or '' if unavailable."""
    if not exe_name:
        return ""
    # Full path on disk → extract icon via SystemIconProvider
    if os.path.isabs(exe_name) and os.path.exists(exe_name):
        encoded = quote(exe_name.replace("\\", "/"), safe="/:")
        return f"image://systemicons/{encoded}"
    # Exe name / label → look up installed path via app catalog
    entry = app_catalog.resolve_app_spec(exe_name)
    if entry:
        path = entry.get("path", "")
        if path and os.path.exists(path):
            encoded = quote(path.replace("\\", "/"), safe="/:")
            return f"image://systemicons/{encoded}"
    return ""


def ensure_config_dir():
    os.makedirs(CONFIG_DIR, mode=0o700, exist_ok=True)


def _configured_mapping_count(cfg):
    return sum(
        action != "none"
        for profile in cfg.get("profiles", {}).values()
        for action in profile.get("mappings", {}).values()
    )


def load_config(*, strict=False):
    with _CONFIG_IO_LOCK:
        return _load_config_unlocked(strict=strict)


def _load_config_unlocked(*, strict=False):
    """Load config from disk, or return defaults if none exists."""
    ensure_config_dir()
    config_exists = os.path.lexists(CONFIG_FILE)
    if config_exists:
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            # Merge any missing keys from default
            cfg = _migrate(cfg)
            cfg = _merge_defaults(cfg, DEFAULT_CONFIG)
            _validate_mapping_value_types(cfg)
            cfg = _validate_types(cfg, DEFAULT_CONFIG)
            cfg = sanitize_mousepro_section(cfg)
            print(
                "[Config] CONFIG_LOAD status=ok source=disk "
                f"profiles={len(cfg.get('profiles', {}))} "
                f"configured={_configured_mapping_count(cfg)}"
            )
            return cfg
        except Exception as e:
            print(
                "[Config] CONFIG_LOAD "
                f"status={'failed' if strict else 'fallback'} "
                f"source={'disk' if strict else 'defaults'} "
                f"error={e!r} traceback={traceback.format_exc().strip()}"
            )
            if strict:
                raise ConfigLoadError("existing config could not be loaded") from e
    elif strict:
        print("[Config] CONFIG_LOAD status=failed error=config-file-missing")
        raise ConfigLoadError("config file is missing")
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    if config_exists:
        _mark_config_read_only(cfg)
    print(
        "[Config] CONFIG_LOAD status=ok source=defaults "
        f"profiles={len(cfg.get('profiles', {}))} "
        f"configured={_configured_mapping_count(cfg)}"
    )
    return cfg


def save_config(cfg):
    with _CONFIG_IO_LOCK:
        return _save_config_unlocked(cfg)


def _save_config_unlocked(cfg):
    """Persist config to disk via atomic write with restrictive permissions."""
    if _config_write_is_blocked(cfg):
        print(
            "[Config] CONFIG_SAVE status=blocked "
            "reason=unverified-fallback"
        )
        raise ConfigWriteBlockedError(
            "config loaded from fallback defaults is read-only until a strict reload succeeds"
        )
    ensure_config_dir()
    sanitize_mousepro_section(cfg)
    fd, tmp_path = tempfile.mkstemp(suffix=".tmp", dir=CONFIG_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        if sys.platform != "win32":
            os.chmod(tmp_path, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(tmp_path, CONFIG_FILE)
        print(
            "[Config] CONFIG_SAVE status=ok "
            f"profiles={len(cfg.get('profiles', {}))} "
            f"configured={_configured_mapping_count(cfg)}"
        )
    except BaseException as exc:
        print(
            "[Config] CONFIG_SAVE status=failed "
            f"error={exc!r} traceback={traceback.format_exc().strip()}"
        )
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def get_active_mappings(cfg):
    """Return the mappings dict for the currently active profile."""
    profile_name = cfg.get("active_profile", "default")
    profiles = cfg.get("profiles", {})
    profile = profiles.get(profile_name, profiles.get("default", {}))
    return profile.get("mappings", DEFAULT_CONFIG["profiles"]["default"]["mappings"])


def set_mapping(cfg, button, action_id, profile=None):
    """Set a mapping for a button in the given profile (or active profile)."""
    if profile is None:
        profile = cfg.get("active_profile", "default")
    cfg["profiles"].setdefault(profile, {
        "label": profile,
        "mappings": dict(DEFAULT_CONFIG["profiles"]["default"]["mappings"]),
    })
    cfg["profiles"][profile]["mappings"][button] = action_id
    save_config(cfg)
    return cfg


def create_profile(cfg, name, label=None, copy_from="default", apps=None):
    """Create a new profile, optionally copying from an existing one."""
    if label is None:
        label = name
    source = cfg["profiles"].get(copy_from, cfg["profiles"].get("default", {}))
    cfg["profiles"][name] = {
        "label": label,
        "apps": apps if apps is not None else [],
        "mappings": dict(source.get("mappings", {})),
    }
    save_config(cfg)
    return cfg


def delete_profile(cfg, name):
    """Delete a profile (cannot delete 'default')."""
    if name == "default":
        return cfg
    cfg["profiles"].pop(name, None)
    if cfg["active_profile"] == name:
        cfg["active_profile"] = "default"
    save_config(cfg)
    return cfg


def resolve_app_for_config(spec: str):
    """Resolve an app identifier/path into a catalog entry with aliases."""
    return app_catalog.resolve_app_spec(spec)


def get_profile_for_app(cfg, exe_name):
    """Return the profile name that matches the given executable, or 'default'."""
    if not exe_name:
        return "default"
    entry = resolve_app_for_config(exe_name)
    aliases = {a.lower() for a in ([entry["id"]] + entry.get("aliases", []))} if entry else {exe_name.lower()}
    for pname, pdata in cfg.get("profiles", {}).items():
        for app in pdata.get("apps", []):
            if app.lower() in aliases:
                return pname
    return "default"


def _migrate(cfg):
    """Migrate config from older versions to current."""
    version = cfg.get("version", 1)
    if version < 2:
        # v1 → v2:  add 'apps' list to each profile, new settings keys
        for pdata in cfg.get("profiles", {}).values():
            pdata.setdefault("apps", [])
        cfg.setdefault("settings", {})
        cfg["settings"].setdefault("invert_hscroll", False)
        cfg["settings"].setdefault("invert_vscroll", False)
        cfg["settings"].setdefault("dpi", 1000)
        cfg["version"] = 2

    if version < 3:
        settings = cfg.setdefault("settings", {})
        settings.setdefault("gesture_threshold", 50)
        settings.setdefault("gesture_deadzone", 40)
        settings.setdefault("gesture_timeout_ms", 3000)
        settings.setdefault("gesture_cooldown_ms", 500)
        for pdata in cfg.get("profiles", {}).values():
            mappings = pdata.setdefault("mappings", {})
            mappings.setdefault("gesture", "none")
            for key in GESTURE_DIRECTION_BUTTONS:
                mappings.setdefault(key, "none")
        cfg["version"] = 3

    if version < 4:
        settings = cfg.setdefault("settings", {})
        settings.setdefault("device_layout_overrides", {})
        cfg["version"] = 4

    if version < 5:
        settings = cfg.setdefault("settings", {})
        if "start_at_login" not in settings and "start_with_windows" in settings:
            settings["start_at_login"] = bool(settings["start_with_windows"])
        else:
            settings.setdefault("start_at_login", False)
        settings.pop("start_with_windows", None)
        cfg["version"] = 5

    if version < 6:
        for pdata in cfg.get("profiles", {}).values():
            mappings = pdata.setdefault("mappings", {})
            mappings.setdefault("mode_shift", "none")
        cfg["version"] = 6

    if version < 7:
        # v6 defaulted mode_shift to "none"; remap to "toggle_smart_shift" so the
        # physical SmartShift button behind the scroll wheel works out of the box.
        # Users who explicitly want no action can set it back to "none" in the UI.
        for pdata in cfg.get("profiles", {}).values():
            mappings = pdata.setdefault("mappings", {})
            if mappings.get("mode_shift") == "none":
                mappings["mode_shift"] = "toggle_smart_shift"
        cfg["version"] = 7

    if version < 8:
        # v7 defaulted mode_shift to "toggle_smart_shift" (SmartShift on/off toggle).
        # Default to switching between ratchet and free-spin modes.
        # Upgrade "toggle_smart_shift" → "switch_scroll_mode" for all profiles.
        # Users who prefer the old toggle can reassign it in the UI.
        for pdata in cfg.get("profiles", {}).values():
            mappings = pdata.setdefault("mappings", {})
            if mappings.get("mode_shift") == "toggle_smart_shift":
                mappings["mode_shift"] = "switch_scroll_mode"
        cfg["version"] = 8

    if version < 9:
        settings = cfg.setdefault("settings", {})
        settings.setdefault("ignore_trackpad", True)
        cfg["version"] = 9

    if version < 10:
        settings = cfg.setdefault("settings", {})
        settings.setdefault(
            "multi_action_long_press_threshold_ms",
            DEFAULT_LONG_PRESS_THRESHOLD_MS,
        )
        for pdata in cfg.get("profiles", {}).values():
            mappings = pdata.setdefault("mappings", {})
            mappings.setdefault("mode_shift_long", "switch_scroll_mode")
            mappings.setdefault("xbutton1_long", "none")
            mappings.setdefault("xbutton2_long", "none")
        cfg["version"] = 10

    if version < 11:
        settings = cfg.setdefault("settings", {})
        settings.setdefault("generic_mouse_enabled", False)
        for pdata in cfg.get("profiles", {}).values():
            mappings = pdata.setdefault("mappings", {})
            for button in GENERIC_MOUSE_BUTTONS:
                mappings.setdefault(button, "none")
                mappings.setdefault(long_press_mapping_key(button), "none")
        cfg["version"] = 11

    if version < 12:
        # MousePro right-hold gesture + screenshot side-button selection.
        mousepro = cfg.setdefault("mousepro", {})
        mousepro.setdefault("right_hold_gesture_enabled", True)
        mousepro.setdefault(
            "screenshot_side_buttons", ["xbutton1", "xbutton2"]
        )
        cfg["version"] = 12

    cfg.setdefault("settings", {})
    cfg["settings"].setdefault("appearance_mode", "system")
    cfg["settings"].setdefault("debug_mode", False)
    cfg["settings"].setdefault("device_layout_overrides", {})
    cfg["settings"].setdefault("language", "zh_CN")
    cfg["settings"].setdefault("ignore_trackpad", True)
    cfg["settings"].setdefault("screenshot_directory", "")
    cfg["settings"].setdefault("check_for_updates", True)
    cfg["settings"].setdefault("update_check_state", {})
    cfg["settings"].setdefault("generic_mouse_enabled", False)
    cfg["settings"].setdefault(
        "multi_action_long_press_threshold_ms",
        DEFAULT_LONG_PRESS_THRESHOLD_MS,
    )

    for pdata in cfg.get("profiles", {}).values():
        mappings = pdata.setdefault("mappings", {})
        for button in MULTI_ACTION_BUTTONS:
            long_key = long_press_mapping_key(button)
            mappings.setdefault(
                button,
                DEFAULT_CONFIG["profiles"]["default"]["mappings"].get(button, "none"),
            )
            mappings.setdefault(
                long_key,
                DEFAULT_CONFIG["profiles"]["default"]["mappings"].get(long_key, "none"),
            )

    # Always migrate old wmplayer.exe → Microsoft.Media.Player.exe in profile apps
    for pdata in cfg.get("profiles", {}).values():
        apps = pdata.get("apps", [])
        for i, a in enumerate(apps):
            if a.lower() == "wmplayer.exe":
                apps[i] = "Microsoft.Media.Player.exe"

    return cfg


def _merge_defaults(cfg, defaults):
    """Recursively merge missing keys from defaults into cfg."""
    for key, val in defaults.items():
        if key not in cfg:
            cfg[key] = json.loads(json.dumps(val))
        elif isinstance(val, dict) and isinstance(cfg.get(key), dict):
            _merge_defaults(cfg[key], val)
    return cfg


def _validate_types(cfg, defaults, path=""):
    """Reset values whose type doesn't match the defaults template."""
    for key, default_val in defaults.items():
        if key not in cfg:
            continue
        if isinstance(default_val, dict):
            if isinstance(cfg[key], dict):
                _validate_types(cfg[key], default_val, f"{path}.{key}")
            else:
                print(f"[Config] Type mismatch at {path}.{key}: "
                      f"expected dict, got {type(cfg[key]).__name__}")
                cfg[key] = json.loads(json.dumps(default_val))
        elif not isinstance(cfg[key], type(default_val)):
            print(f"[Config] Type mismatch at {path}.{key}: "
                  f"expected {type(default_val).__name__}, "
                  f"got {type(cfg[key]).__name__}")
            cfg[key] = default_val
    return cfg


MOUSEPRO_ALLOWED_SIDE_BUTTONS = ("xbutton1", "xbutton2")


def sanitize_mousepro_section(cfg):
    """Validate/repair the top-level ``mousepro`` section in place.

    Unknown button names are filtered to the xbutton1/xbutton2 subset,
    duplicates removed and order preserved.  An empty or non-list value
    falls back to the default (both buttons).  Non-bool enabled flags
    fall back to the default (True).
    """
    defaults = DEFAULT_CONFIG["mousepro"]
    section = cfg.get("mousepro")
    if not isinstance(section, dict):
        section = {}
        cfg["mousepro"] = section

    enabled = section.get("right_hold_gesture_enabled", defaults["right_hold_gesture_enabled"])
    section["right_hold_gesture_enabled"] = (
        enabled if isinstance(enabled, bool) else defaults["right_hold_gesture_enabled"]
    )

    raw_buttons = section.get("screenshot_side_buttons")
    buttons: list = []
    if isinstance(raw_buttons, list):
        for name in raw_buttons:
            if (
                name in MOUSEPRO_ALLOWED_SIDE_BUTTONS
                and name not in buttons
            ):
                buttons.append(name)
    if not buttons:
        buttons = list(defaults["screenshot_side_buttons"])
    section["screenshot_side_buttons"] = buttons
    return cfg


def _validate_mapping_value_types(cfg):
    """Reject mappings that cannot be interpreted without losing user intent."""
    profiles = cfg.get("profiles", {})
    if not isinstance(profiles, dict):
        return cfg
    for profile_name, profile in profiles.items():
        if not isinstance(profile_name, str) or not isinstance(profile, dict):
            raise TypeError("profile names and definitions must be objects keyed by strings")
        mappings = profile.get("mappings", {})
        if not isinstance(mappings, dict):
            raise TypeError(f"profile {profile_name!r} mappings must be an object")
        for button, action in mappings.items():
            if not isinstance(button, str) or not isinstance(action, str):
                raise TypeError(
                    f"profile {profile_name!r} mapping keys and actions must be strings"
                )
    return cfg
