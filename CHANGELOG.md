# Changelog

All notable changes to MousePro are documented here.

This project uses Semantic Versioning.

## Unreleased

## v1.0.1 - 2026-10-08

### Added
- **单文件便携版**（Windows）：新增 `MousePro-v1.0.1-Windows-OneFile.exe`（PyInstaller one-file），单 exe 免安装、无 `_internal` 依赖文件夹，拷贝即用，适配内网电脑与 U 盘分发；首次启动需解压到临时目录，比目录版慢几秒属正常。
- 新增 `MousePro-onefile.spec`，与目录版 `MousePro.spec` 共用同一套模块裁剪规则。

### Fixed
- 改善目录版分发误用导致的启动失败：`MousePro.exe` 必须与 `_internal` 文件夹一起拷贝（单文件版无此限制）；README/发布说明补充内网使用提示（未签名程序需在杀毒软件中加白，系统要求 Windows 10+）。

## 鼠标pro V1.0 - 2026-10-06

### Added
- Fork 自 PourInput v1.4.3，产品品牌独立为鼠标Pro MousePro（维护者 szboboxing）；版本号重置为 1.0.0。
- **右键组合手势**（Windows）：按住右键 + 滚轮上 = 复制；按住右键 + 滚轮下 = 增强粘贴；按住右键 + 已配置侧键 = 系统截图；每次按住右键最多触发一个动作，未触发则原样弹出右键菜单。
- **增强粘贴**（Windows）：在当前激活的资源管理器或桌面新建文件夹并以剪贴板内容命名。
- **系统工具页**（Windows）：计算器、默认浏览器、媒体播放器、鼠标指针大小设置（Win11 辅助功能-鼠标指针与触控 / Win10 调整鼠标和光标大小）、亮度降/升（WMI→DDC/CI）、对比度降/升（DDC/CI）。
- **鼠标按键测试页**：7 类输入（左/右/中/滚轮上/下/X1/X2）高亮与计数，只读透传；支持侧键重新确认并保存为截图侧键。
- **使用统计页**：本次运行的按键次数、滚轮次数、移动像素距离与复制/增强粘贴/截图成功次数，可清零。
- 上述增强功能仅在 Windows 显示与启用，macOS/Linux 自动隐藏导航与页面。
- 新增单元测试 56 项，全量套件 953 项。

## v1.4.3 - 2026-09-26

### Added
- Chapter selection using EPUB contents, TXT headings, or clearly labeled layout suggestions requiring confirmation.
- Save chapter anchors with reader documents; preserve old imported books and explain reimport limitations.

### Changed
- Press the hide key once to hide, release keeps the panel hidden, and press again to show. Auto-reading remains paused while hidden.

### Fixed
- Start chapter jumps at the title on its own line, without the preceding chapter's tail; preserve position across resizing and restart.
- Prevent automatic reading from moving backward near the end of a book after a chapter jump.

## v1.4.2 - 2026-09-20

### Added
- Continuous automatic reading with adjustable speed, pause/resume, and fixed panel/font size.
- Preserve the text anchor and fractional scroll position in the independent reader store; restart paused.
- Pause automatic motion while the panel is temporarily hidden, resume on release, and stop at the end or when Reading Mode is disabled.
- English and Simplified Chinese controls, usage notes, and screenshots.

## v1.4.1 - 2026-09-20

### Fixed
- Give the mouse hold-to-hide button exclusive ownership while Reading Mode is enabled, suppressing conflicting Generic, MX HID, and native actions.
- Restore normal button actions when Reading Mode is disabled without modifying saved mappings or reading state.
- Consume the matching release when Reading Mode is disabled during a hold.

## v1.4.0 - 2026-09-20

### Added
- Local TXT/EPUB Reading Mode with independent persistence and wheel navigation.
- Fixed-font continuous pagination, direct panel movement/resizing, transparent background, custom text style, and hold-to-hide.
- English and Simplified Chinese reading UI and homepage screenshots.

### Fixed
- Avoid forced HID reconnects for unrelated Windows device-change notifications.
- Correct HID-only hold-button release handling while preserving standard-input ownership.
- Preserve all v1.3.5 configuration-loss protections.


## v1.3.5 - 2026-09-05

### Fixed

- Preserve user mouse mappings when the existing configuration cannot be safely read or validated at startup.
- Block unverified or fallback configuration from being saved by unrelated settings and update operations.
- Isolate automated tests from the user's real configuration.
- Improve configuration validation and safe startup behavior.
- Improve input backend startup, shutdown, and recovery reliability.

## v1.3.4 - 2026-07-19

### Fixed

- Fixed MX Master 3 Back and Forward mappings still allowing native browser navigation.
- Added targeted suppression of matching Windows XBUTTON events while preserving Generic Mouse Mode separation.
- Fixed transient HID++ empty-state reports splitting one physical hold into multiple logical presses.
- Physical release is now confirmed using the matching Windows XBUTTON UP event.
- Fixed full-screen screenshot-to-clipboard delivery in packaged Windows builds using durable native `CF_DIB`.
- Prevented duplicate screenshot actions during a continuous side-button hold.
- Improved persistent diagnostics for HID++, suppression, action execution, screenshot capture, and clipboard delivery.

### Validation

- Verified with a real Logitech MX Master 3 connected over Bluetooth and Generic Mouse Mode disabled.
- Confirmed native Back/Forward suppression, immediate mapping execution, durable screenshot clipboard delivery, and correlated physical release in a packaged Windows build.

## v1.3.3 - 2026-07-19

### Fixed

- Fixed MX Master 3 Back and Forward shortcut changes not taking effect.
- Added dedicated Logitech HID++ routes for Back CID `0x0053` and Forward CID `0x0056`.
- Fixed a reconnect loop caused by adding and removing side-button HID++ diverts during connection refresh.
- Kept MX Master 3 device-specific mappings separate from Generic Mouse Mode.
- Side-button mappings now apply immediately, remain profile-specific, and persist after restart.

### Validation

- Verified with a real Logitech MX Master 3 connected over Bluetooth.
- Confirmed stable HID++ diversion and independent Back and Forward action execution with Generic Mouse Mode disabled.

## v1.3.2 - 2026-07-17

### Fixed

- Fixed MX Master 3 side-button mappings in Generic Mouse Mode.
- Fixed the UI/runtime XBUTTON namespace mismatch that could save a mapping outside the active Generic Mouse Mode route.
- Fixed QML focus restoration when reopening the main window from the system tray.
- Fixed a missing Qt `Slot` import that prevented the application from starting.

### Improved

- Hardened Windows XBUTTON routing around immutable binding generations, dispatch leases, and retirement synchronization.
- Improved queue-overflow lifecycle handling and isolated multi-action press state across route and generation changes.
- Improved shutdown behavior for hook workers and retired callbacks.
- Improved locale-aware font fallback while preserving platform-appropriate system fonts.

### Validation

- Verified with a real Logitech MX Master 3 connected over Bluetooth.
- Logitech receiver transport remains to be validated.
- Logitech Options and Options+ coexistence remains to be validated.

## v1.3.1 - 2026-07-15

### Fixed

- Fixed Generic Mouse localization refresh after language switching.
- Corrected Side Button 1 (Back) and Side Button 2 (Forward) presentation labels.
- Fixed several remaining localized presentation labels.
- Improved localization consistency across the interface.

### Documentation

- Improved GitHub repository homepage.
- Added dedicated English and Simplified Chinese screenshots.
- Updated screenshot documentation and packaging references.

## v1.3.0 - 2026-07-14

### Changed

- Redesigned the desktop interface around a consistent PourInput visual system while preserving existing input and mapping behavior.
- Replaced legacy application identity artwork with finalized PourInput branding across Windows, macOS, Linux, the tray, and repository presentation.
- Refined navigation, profiles, settings, controls, spacing, typography, light/dark themes, and high-DPI presentation.

### Documentation

- Added the Pour product-family design system, component reference, brand asset guidelines, screenshot standards, and release visual checklist.
- Added architecture, event flow, profile, mapping, settings, state-management, QML, and project-structure references.
- Simplified and aligned the English and Simplified Chinese README homepages and download instructions.

## v1.2.1 — 2026-07-09

### Fixed

- Corrected the device status shown when Generic Mouse Mode is active without a supported Logitech mouse.
- Added distinct status states for Logitech connection, Generic Mouse Mode readiness, and no supported mouse detected.
- Kept Logitech connection state separate from Generic Mouse Mode readiness.

## v1.2.0 — 2026-07-09

### Added

- Generic Mouse Mode for standard Windows mouse buttons.
- Middle Button support.
- Side Button 1 and Side Button 2 support.
- Click + Long Press Multi-Action for all three generic buttons.
- Generic Mouse Mode operation without a supported Logitech mouse.
- English / Simplified Chinese application language switching.
- Persistent saved language preference.
- Complete Simplified Chinese application UI.
- Complete Simplified Chinese GitHub documentation.
- Added a Windows single-instance guard so duplicate PourInput processes cannot create competing low-level mouse hooks.

### Fixed

- Corrected Generic Mouse Mode button visibility without a Logitech connection.
- Restored correct runtime Generic Mouse Mode OFF behavior: disabling the mode removes generic mouse callbacks and blocking, returning buttons to native middle-click and Back / Forward behavior.
- Prevented stale XBUTTON interception after Generic Mouse Mode is disabled.
- Corrected Generic Mouse Mode CI regression coverage across platforms.

## v1.1.0 - 2026-07-08

### Changed

- Added the capability-based device support architecture so runtime HID++ evidence can enable or limit device features more safely.
- Documented the capability-based device support architecture, including HID++-detected feature enablement and the distinction between tested and experimental devices.

### Documentation

- Polished the README for the first official PourInput release.
- Added clearer screenshots, supported devices, roadmap, and credits sections.
- Replaced the corrupted Chinese README text with a readable PourInput overview.
- Refined repository presentation with logo placement, release badges, screenshot captions, support tables, and clearer known limitations.

## v1.0.0 - 2026-07-08

### Added

- Published the first official PourInput release.
- Promoted the Windows release package to `PourInput-v1.0.0-Windows.zip`.
- Updated application, updater, installer, package, and executable metadata to version 1.0.0.

### Documentation

- Reworked the README for a public open-source release.
- Added clearer project positioning, installation, usage, build, packaging, roadmap, known issue, and contribution guidance.
- Added repository community documents and GitHub pull request guidance.
- Updated issue templates to use PourInput naming consistently.
- Replaced stale upstream release links in the Chinese README.

## Initial Development Release - 2026-07-06

### Added

- Added generic Multi-Action Button framework.
- Added Click and Long Press support.
- Added Mode Shift Click and Long Press support.
- Added Back Button Click and Long Press support.
- Added Forward Button Click and Long Press support.
- Added generic dispatcher shared by supported multi-action buttons.
- Added config migration for long-press mappings and default 300 ms threshold.
- Added UI sections for Click Action and Long Press Action.
- Added versioned Windows release packaging.
- Added release notes and open-source release documentation.
- Standardized project metadata as PourInput.
- Set release repository metadata to pour-soi/PourInput.

### Fixed

- Improved HID diversion synchronization for Mode Shift remapping.
- Ensured Mode Shift diversion also applies when only the long-press slot is configured.
- Replaced placeholder maintainer metadata with pour-soi.

### Known Limitations

- Double Click is not implemented yet.
- Long-press timeout is global and not editable in the UI yet.
- Per-button timeout is not implemented yet.
- Macro and sequential actions are not implemented yet.
