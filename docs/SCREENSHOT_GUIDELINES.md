# Pour Screenshot Guidelines

> **Purpose:** A repeatable desktop screenshot standard for Pour repositories. These are production/review guidelines, not changes to application behavior. Brand rules are in [`BRAND_ASSET_GUIDELINES.md`](BRAND_ASSET_GUIDELINES.md).

## Contents

- [Capture baseline](#capture-baseline)
- [Content and privacy](#content-and-privacy)
- [Framing and visual state](#framing-and-visual-state)
- [Pages and variants](#pages-and-variants)
- [Files and repository handling](#files-and-repository-handling)
- [README and social previews](#readme-and-social-previews)
- [Standard checklist](#standard-checklist)

## Capture baseline

### Window size and framing

- Capture the current default MousePro window at **1060 × 700 logical px** unless the screenshot's purpose is minimum-window validation.
- Capture the small-window case at the implemented **920 × 620 logical px** minimum.
- Keep the same logical dimensions across DPI scales. Do not resize by eye after changing OS scale.
- Preserve the complete application window, including native title bar and visible window edges, for release evidence.
- For README crops, crop only surrounding desktop space; never crop application content, window controls, or branding.
- Record the logical size and OS scale with the capture set.

The existing checked-in `images/Screenshot*.png` files are approximately 1919 × 1145–1150 and predate this standard. They are implementation history, not the sizing authority for new captures.

### DPI matrix

Release verification must inspect 100%, 125%, 150%, and 200% scale. The primary documentation set may use one consistent scale, but the release evidence must include all four scales or a written record that each was visually checked.

At each scale inspect:

- title-bar, taskbar, rail, and About icons;
- one-pixel borders and dividers;
- text baselines, clipping, and wrapping;
- QML raster/device art sharpness;
- dialog fit and shadow/chrome boundaries;
- minimum-window overflow and scrolling.

## Content and privacy

- Use a clean test profile and non-sensitive sample app names.
- Remove personal paths, usernames, device serials, HID dumps, commit credentials, notifications, chat windows, and unrelated desktop content.
- Do not expose API keys, email addresses, private repository names, or user-specific recent files.
- Use stable data that will not look stale immediately after release.
- Do not edit a screenshot to conceal incorrect UI. Fix the test state or document the limitation.
- If a system-level surface such as taskbar or File Explorer is required, close unrelated applications and use a neutral desktop background.

## Framing and visual state

### Clean state

- Launch the actual build being reviewed, not an older installed copy.
- Wait for loading/transient blank states to finish.
- Dismiss incidental toasts, menus, tooltips, and cursor hover unless they are the subject of the screenshot.
- Use a consistent window position and capture bounds throughout one set.
- Avoid focus rings in hero screenshots unless keyboard focus is being demonstrated.
- Hide the pointer for static documentation captures; include it only when it explains hover, drag, hotspot, or tooltip behavior.

### Light and dark

- Capture the same page, data, window size, and language in light and dark mode.
- Do not change device/profile state between theme captures.
- Confirm the system/title-bar treatment matches the application mode where the platform supports it.
- Use the same background/chrome framing so palette differences are comparable.

### Language

- The required current language set is English (`en`) and Simplified Chinese (`zh_CN`).
- Capture at least one complete primary page in each language for release validation.
- Include a mixed-script state containing product names, app names, numbers/units, or shortcuts beside Chinese text.
- Do not use machine-translated screenshot overlays.

### Tooltips, menus, and dialogs

- Capture a tooltip only for a tooltip-specific review; keep the cursor positioned consistently.
- Capture one dialog as a standalone evidence image with the entire scrim and underlying window visible.
- Do not leave another modal, toast, or OS notification behind the dialog.
- For hover/pressed/disabled evidence, use a dedicated review sheet rather than the primary README hero.

## Pages and variants

Recommended MousePro production/release set:

1. Main Mouse & Profiles page with the primary workspace visible.
2. Generic Mouse Mode state on Windows.
3. Profile selection/add-profile workflow.
4. General/settings page.
5. About dialog.
6. Matched light-mode primary page.
7. Matched dark-mode primary page.
8. Minimum-window state.

Capture feature-dependent cards only when the build/device supports them. Do not fabricate unsupported battery, DPI, or SmartShift data.

## Files and repository handling

### Production screenshots

The current repository stores referenced screenshots in `images/`. Continue using that location until a separately approved repository migration establishes another production path. Use descriptive names for new files:

`mousepro_<page>_<mode>_<language>_<scale>.png`

Examples:

- `mousepro_mouse_light_en_100.png`
- `mousepro_settings_dark_zh-cn_150.png`
- `mousepro_about_light_en_100.png`

The README homepage uses explicit language-specific names for its matched English and Simplified Chinese screenshot sets:

- `Screenshot_mouse_en.png` and `Screenshot_mouse_zh-CN.png`
- `Screenshot_settings_en.png` and `Screenshot_settings_zh-CN.png`
- `Screenshot_generic_en.png` and `Screenshot_generic_zh-CN.png`

### Review and before/after screenshots

- Put temporary review captures in `review_screenshots/` and `review_screenshots_after/`, or another clearly temporary folder named in the task.
- Do not reference temporary review folders from README or release documentation.
- Delete them before commit, or leave them untracked only when the user explicitly wants local evidence retained.
- Never stage review screenshots, DPI proof sheets, File Explorer previews, taskbar mockups, or image-generation workspaces unless the user explicitly approves those exact files as production assets.
- Build outputs (`build/`, `dist/`, release archives), caches, and screenshot-tool intermediates are never production screenshot sources.

### Format

- Use lossless PNG for application UI.
- Preserve native pixel dimensions and color profile; do not upscale.
- Avoid JPEG for text-heavy UI.
- Do not add decorative shadows, device frames, captions, or gradients to evidence screenshots.

## README and social previews

README ordering should lead with the clearest product state, then the primary workflow, then settings/secondary workflow. Keep light/dark comparison images adjacent when both are included. Avoid long galleries above installation/download information.

README screenshots must:

- match the current released UI and branding;
- use consistent width and framing;
- avoid duplicate views that add no new information;
- have useful alt text in both README language versions;
- preserve the complete logo and window chrome where shown.

GitHub social previews are separate compositions, not cropped README screenshots. Use only approved brand assets, safe margins, and no private UI data. This repository has no approved social-preview master; creating one requires an explicit design task.

## Standard checklist

### Main page

- [ ] Built application and correct version launched
- [ ] 1060 × 700 logical window
- [ ] Main title and primary workspace visible
- [ ] Rail, profile sidebar, device state, and status content are intentional
- [ ] No transient toast, tooltip, or unrelated cursor
- [ ] No private device/app/path data

### Secondary workflow

- [ ] Generic Mouse Mode or profile workflow is in a valid supported state
- [ ] Action controls are visible without clipped labels
- [ ] Status/empty state is truthful; no fabricated device capabilities
- [ ] Navigation context remains visible

### Settings

- [ ] Page title and first complete cards are visible
- [ ] Feature-gated cards do not leave accidental gaps
- [ ] Switches, segmented choices, and sliders are in intentional states
- [ ] Vertical scroll position is reproducible

### Dialog

- [ ] Entire dialog, scrim, and underlying window are visible
- [ ] Title, close action, primary/secondary actions, and branding are uncropped
- [ ] Focus/validation state is intentional
- [ ] Long localized text and paths fit or wrap correctly

### Light mode

- [ ] Correct light palette and title-bar treatment
- [ ] Borders remain restrained but visible
- [ ] Brand art and semantic statuses retain contrast

### Dark mode

- [ ] Same page/data/framing as light mode
- [ ] No pure-black accidental surfaces or heavy border stacking
- [ ] Secondary text and disabled states remain readable

### Small-window state

- [ ] Exactly 920 × 620 logical px
- [ ] No horizontal clipping in shell, rail, sidebar, or dialog
- [ ] Scrollable content remains reachable
- [ ] Tooltips and modals remain inside the window
- [ ] Long English, Chinese, and mixed-script strings remain usable
