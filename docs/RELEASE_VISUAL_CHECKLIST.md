# Pour Release Visual Checklist

> **Release gate:** Complete every applicable item against the actual candidate build. Mark non-applicable items with a reason; do not silently skip them. Related standards: [`POUR_DESIGN_SYSTEM.md`](POUR_DESIGN_SYSTEM.md), [`POUR_COMPONENTS.md`](POUR_COMPONENTS.md), [`BRAND_ASSET_GUIDELINES.md`](BRAND_ASSET_GUIDELINES.md), and [`SCREENSHOT_GUIDELINES.md`](SCREENSHOT_GUIDELINES.md).

## Candidate and scope

- [ ] Record candidate commit, version, platform, architecture, and build path.
- [ ] Launch the candidate build rather than a previously installed copy.
- [ ] Confirm the review contains no functionality, layout, or branding change outside the approved release scope.
- [ ] Confirm version text is consistent in the title, About dialog, README, manifests, and release documentation.

## Brand assets

- [ ] `images/logo_icon.png` is the approved 1024 × 1024 RGBA master.
- [ ] `images/logo.png` shows the complete `MousePro` wordmark without crop or distortion.
- [ ] Sidebar and About marks use aspect-preserving rendering and the full symbol canvas.
- [ ] Functional mouse/navigation/device icons remain functional icons; they have not been replaced by the brand mark.
- [ ] No legacy placeholder appears in application-identity surfaces.
- [ ] No preview mockup, screenshot, or temporary generated image is used as a production master.

## Windows identity

- [ ] Window title-bar icon is correct and sharp.
- [ ] Taskbar icon is correct in normal, active, and pinned contexts.
- [ ] Executable icon is embedded in the candidate `.exe`.
- [ ] ICO contains 16, 24, 32, 48, 64, 128, and 256 px images.
- [ ] File Explorer displays the current icon after testing with a cache-independent copy or refreshed icon cache.
- [ ] Any applicable installer/shortcut uses the same approved icon; mark N/A if no installer exists.

## macOS identity (when shipped)

- [ ] `AppIcon.icns` is present and selected by the macOS build specification.
- [ ] Dock, Cmd+Tab, Mission Control, Finder, and bundle icons show the full-color symbol.
- [ ] Menu-bar icon uses `logo_tray_template.png`, responds to system tint, and remains legible in light/dark menu bars.
- [ ] Retina and non-Retina sizes are sharp and uncropped.

## Linux identity (when shipped)

- [ ] Hicolor icons exist at 16, 24, 32, 48, 64, 128, 256, and 512 px.
- [ ] File name remains `io.github.szboboxing.mousepro.png` in each expected directory.
- [ ] Desktop entry, launcher, taskbar, and application switcher resolve the current icon.

## Shell and layout

- [ ] Default 1060 × 700 logical window has the approved rail, profile sidebar, page header, and content origins.
- [ ] Minimum 920 × 620 logical window has no inaccessible or clipped content.
- [ ] Title bar, rail, profile sidebar, page headers, cards, and dialogs align to the current grid.
- [ ] One clear focal point leads each major page.
- [ ] Whitespace is intentional; feature-gated content does not leave unexplained gaps.
- [ ] Buttons, inputs, switches, segmented controls, sliders, rows, and dialogs retain consistent proportions.

## Theme review

- [ ] Light mode matches the implemented `Theme.js` palette.
- [ ] Dark mode matches the implemented `Theme.js` palette and preserves the same hierarchy.
- [ ] System mode follows the platform color scheme.
- [ ] Theme changes do not alter layout, information order, or component size.
- [ ] Borders are visible but restrained; dark mode does not become border-heavy.
- [ ] Primary, secondary, dim, disabled, semantic, and tooltip text remain readable.

## DPI matrix

### 100%

- [ ] Brand and functional icons are sharp.
- [ ] One-pixel borders, text, and controls align cleanly.

### 125%

- [ ] No fractional-scale blur, clipping, or off-center icons.
- [ ] Title bar, taskbar, dialog, and rail marks remain recognizable.

### 150%

- [ ] Text wrapping and card heights remain correct.
- [ ] Device art, hotspots, and raster images remain sharp and aligned.

### 200%

- [ ] High-resolution assets are selected; no upscaled low-resolution source is visible.
- [ ] Minimum-window and dialog content remain reachable.

## Localization

- [ ] English (`en`) primary and settings pages reviewed.
- [ ] Simplified Chinese (`zh_CN`) primary and settings pages reviewed.
- [ ] Mixed Chinese/English product names, app names, shortcut notation, numbers, and DPI units reviewed.
- [ ] No raw translation key, mojibake, truncated word, or unintended fallback appears.
- [ ] Long labels wrap or elide intentionally; controls do not overlap.
- [ ] README English and Chinese branding/presentation remain structurally aligned.

## Interaction states

- [ ] Tab order follows visual/reading order.
- [ ] Every applicable custom control has visible keyboard focus.
- [ ] Enter, Return, and Space activate custom buttons where documented.
- [ ] Hover feedback is consistent and does not move layout.
- [ ] Pressed feedback is visible where implemented and not confused with selected state.
- [ ] Selected/checked state uses more than color alone where needed.
- [ ] Disabled controls cannot activate and retain readable labels.
- [ ] Sliders drag correctly and page scrolling does not change values accidentally.
- [ ] Tooltips stay within the window and are not the only accessible label.

## Content states

- [ ] Connected/supported device state reviewed where hardware is available.
- [ ] Disconnected/no-supported-device empty state reviewed.
- [ ] Generic Mouse Mode ready/off states reviewed on Windows.
- [ ] Feature-gated DPI/SmartShift/battery content is truthful and collapses cleanly when unavailable.
- [ ] Search with results and no-results states reviewed.
- [ ] Error and warning states include text and remain readable in both themes.
- [ ] Toasts do not obscure primary controls and are not the only critical error channel.

## Dialogs

- [ ] About dialog shows current brand, version, build mode, commit, provenance, maintainer, and launch path without crop.
- [ ] Add App dialog fits at default and minimum window sizes.
- [ ] Delete confirmation has clear destructive and cancel actions.
- [ ] Shortcut capture shows valid, invalid, reserved, focused, and disabled-confirm states.
- [ ] Modal focus and Escape/close behavior are correct; underlying shortcuts are blocked.
- [ ] English and Chinese dialog strings fit or wrap correctly.

## Screenshots and documentation

- [ ] Required screenshot set follows [`SCREENSHOT_GUIDELINES.md`](SCREENSHOT_GUIDELINES.md).
- [ ] Primary, secondary workflow, settings, dialog, light, dark, and small-window evidence exists.
- [ ] Screenshots contain no private data, unrelated windows, notifications, or accidental cursor/tooltips.
- [ ] README references current production images with useful alt text.
- [ ] README logo is full-width, uncropped, and current in both language files.
- [ ] Temporary before/after or review screenshots are not staged unless explicitly approved.
- [ ] Social-preview assets, if any, are separately approved rather than improvised from screenshots.

## Repository and validation gate

- [ ] Review `git status -sb` before staging.
- [ ] Review the complete textual and binary-file diff.
- [ ] Confirm only intended source, documentation, production assets, and required configuration are tracked.
- [ ] Confirm `build/`, `dist/`, release archives, caches, temporary files, generated previews, and review screenshots are absent from the commit.
- [ ] Run focused UI tests and record the command/result.
- [ ] Run QML validation and distinguish new failures from existing warnings.
- [ ] Run `git diff --check` successfully.
- [ ] Confirm every relative documentation link resolves.
- [ ] Confirm final staged diff matches the approved scope.
- [ ] Confirm the final working tree is clean after commit/push when publication is requested.
- [ ] Confirm no release or version tag was created unless separately authorized.

## Sign-off

- [ ] Design reviewer: ____________________  Date: __________
- [ ] Engineering reviewer: _______________  Date: __________
- [ ] Release owner: ______________________  Date: __________
- [ ] Exceptions/N/A reasons are recorded below.

Notes:

```text

```
