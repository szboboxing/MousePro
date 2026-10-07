# MousePro Component Vocabulary

> **Scope:** This document records the approved current MousePro UI. It does not imply that every inline pattern is a reusable QML component. Family tokens and authority rules are in [`POUR_DESIGN_SYSTEM.md`](POUR_DESIGN_SYSTEM.md).

## Contents

- [Shared state contract](#shared-state-contract)
- [Shell and navigation](#shell-and-navigation)
- [Content and feedback](#content-and-feedback)
- [Controls](#controls)
- [Dialogs and product-specific controls](#dialogs-and-product-specific-controls)
- [Implementation gaps](#implementation-gaps)

## Shared state contract

Unless a section states otherwise, components use the palette from [`Theme.js`](../ui/qml/Theme.js): `bgCard`/`bgSubtle` for normal surfaces, `bgCardHover` for hover, `accentDim` for selected backgrounds, `accent` for focus/active borders, `textPrimary` for main labels, and `textSecondary` or `textDim` for supporting copy. Light and dark mode use the same anatomy and hierarchy with their corresponding palette values.

State expectations:

| State | Treatment |
|---|---|
| Normal | Neutral surface; 1 px `border` where containment is needed |
| Hover | `bgCardHover` or a documented subtle RGBA; 120–150 ms color transition where implemented |
| Pressed | Immediate activation; many inline controls do not yet expose a visually separate pressed treatment |
| Focused | Accent border and visible keyboard focus; required for new custom controls |
| Selected | `accentDim` background and/or `accent` border/text; checked semantics where applicable |
| Disabled | Interaction suppressed; current patterns use approximately 0.45–0.5 opacity |

Localization rules are common: use `lm.strings`/translation helpers, allow dynamic width, wrap explanatory text, and elide intentionally single-line app/path labels. Do not embed English labels in a reusable visual component.

## Shell and navigation

### Application shell

- **Purpose/anatomy/source:** Top-level desktop window with navigation rail and stacked workspace; inline in [`Main.qml`](../ui/qml/Main.qml), not reusable.
- **Geometry:** 1060 × 700 logical px default; 920 × 620 minimum; 76 px rail; content fills the remainder.
- **Typography/icons/style:** System font; title bar includes product/version/device; `bg` canvas and `bgSidebar` rail; no gap between rail and content.
- **States/themes:** `system`, `light`, and `dark`; hierarchy must remain identical. Window close hides to tray.
- **Accessibility/localization:** Reading order starts at rail then workspace; global shortcuts are blocked by modal workflows. Title text may include localized device/status data.
- **Use / avoid:** Use as the sole application frame. Do not add a second nested shell or mobile-style top navigation.

### Global navigation rail

- **Purpose/anatomy/source:** Product mark, two primary navigation destinations, and About action; inline in `Main.qml`.
- **Geometry:** 76 px wide; 20 px top and 16 px bottom inset; 44 px brand mark; 48 px item rows containing 44 × 40 surfaces; 20 px navigation icons (About 18 px); 10 px control radius.
- **States/style:** Transparent normal, `bgCardHover` hover/focus, `accentDim` selected, 1 px accent focus border; 150 ms color transition. Selected state is surface-based; the old left indicator exists but is hidden.
- **Accessibility/localization:** `FocusScope`, `Accessible.Button`, localized tooltip/name, and Enter/Return/Space activation.
- **Use / avoid:** Keep global destinations few and iconically distinct. Do not replace functional navigation icons with the brand mark or add text labels inside the narrow rail.

### Profile sidebar and profile rows

- **Purpose/anatomy/source:** Selects the profile being edited and offers Add App Profile; inline in [`MousePage.qml`](../ui/qml/MousePage.qml).
- **Geometry:** 240 px wide; 60 px heading; 52 px rows; row insets 10/12 px; 24 px app icons; 76 px add-profile region; 28 px add icon.
- **Typography/style:** 15 px bold heading; 12 px demi-bold row label; 10 px subtitle; `bgElevated` surface with a 1 px right divider; selected row uses `accentDim`; 2 × 24 px active indicator.
- **States:** Hover uses subtle neutral surface, selected uses `accentDim`, active profile adds the vertical accent indicator. No separate pressed treatment is encoded.
- **Accessibility/localization:** Row labels and app lists elide; active/selected meaning must remain understandable beyond color. The current row is pointer-driven and should gain explicit keyboard semantics before becoming a family component.
- **Use / avoid:** Use for profile context only. Do not place global settings or unrelated navigation here.

### Page header and page title

- **Purpose/anatomy/source:** Establishes the page focal point and supports subtitle/status actions; inline in `MousePage.qml` and [`ScrollPage.qml`](../ui/qml/ScrollPage.qml).
- **Geometry:** 88 px tall; 32 px left/right content origin; separator spans `parent.width - 64`.
- **Typography:** 24 px bold title, 13 px supporting text. Mouse header may include profile, battery, connection, delete, and layout badges on the right.
- **States/themes:** Static hierarchy; status badges carry their own states. Same geometry and emphasis in both themes.
- **Accessibility/localization:** Allow title/subtitle expansion and keep right-side status content from competing with the title. Long device names require elision or available width.
- **Use / avoid:** One title per page. Do not style a status badge at equal visual weight to the title.

## Content and feedback

### Cards

- **Purpose/source:** Group related settings, empty-state guidance, action selection, or diagnostics; mostly inline in `MousePage.qml` and `ScrollPage.qml`.
- **Geometry:** Standard settings card is `parent.width - 64`, 12 px radius, 1 px border, and 16 px padding; internal spacing is usually 12 px; cards are usually separated by 16 px.
- **Typography/style:** 16 px bold section title, 12 px description, 13 px row values; `bgCard` surface, `border` outline, `bgSubtle` nested rows.
- **States:** Cards are normally static. Clickable nested rows provide hover/focus/selected feedback; do not make the whole card appear interactive unless it is.
- **Accessibility/localization:** Reading order follows visible hierarchy; descriptions wrap. Feature-gated cards may be absent, so surrounding spacing must collapse.
- **Use / avoid:** One concept per card. Avoid nested borders and arbitrary radii outside documented exceptions.

### Status badges

- **Purpose/source:** Compact profile, battery, connection, layout, count, waiting, and build-state indicators; inline across `Main.qml` and `MousePage.qml`.
- **Geometry:** Usually 22–24 px high with half-height radius; destructive profile action is 28 px; About build chip is 30 px. Horizontal padding is generally 8–11 px per side; icons are 7–14 px.
- **Typography/style:** 10–11 px, often demi-bold/bold. Neutral/selected use `accentDim`; semantic states use danger/warning/success treatments.
- **States:** Status badges are static unless explicitly implemented as buttons. Interactive pills must add hover, focus, pressed, accessible role, and pointer cursor.
- **Accessibility/localization:** Always include text or a readable accessible name; do not encode connection or error using only a colored dot. Width must follow localized text.
- **Use / avoid:** Use for concise state. Do not turn explanatory sentences into badges.

### Empty states

- **Purpose/source:** Explain unavailable device layouts, disconnected devices, or empty search results; inline in `MousePage.qml`.
- **Geometry:** Primary disconnected card max 640 px wide, content height + 40 px, 16 px radius, 20 px padding, 32 px top offset; fallback layout card max 480 px. Search empty state occupies the results surface.
- **Typography/style:** 24 px bold primary title (fallback 15 px), 13/12 px explanation, compact 11 px hints; `bgCard` with 1 px border.
- **States/themes:** Status badge reflects waiting/error; cards preserve hierarchy in both themes. Empty states are not disabled controls.
- **Accessibility/localization:** State and next step must be readable in text; wrap copy; ensure any offered choices are separately focusable.
- **Use / avoid:** Explain why content is absent and what the user can do now. Do not add promotional or decorative content.

### Tooltips

- **Purpose/source:** Label icon-only rail actions; one inline tooltip in `Main.qml`.
- **Geometry:** 8 px radius; 10 px horizontal offset from the rail; text width + 20 px and text height + 12 px.
- **Typography/style:** 12 px; `tooltipBg`/`tooltipText`; 1 px low-contrast light border; 120 ms opacity transition.
- **States:** Visible on pointer hover. Current implementation does not add a separate focus-triggered tooltip even though the focused item has an accessible name.
- **Accessibility/localization:** Tooltip text is localized and not the sole accessible label. Keep on screen with an 8 px edge clamp.
- **Use / avoid:** Use for short labels. Do not put instructions or critical state only in a tooltip.

### Toast notifications

- **Purpose/source:** Brief backend status feedback; inline in `Main.qml`.
- **Geometry:** Text width + 32 px, 38 px high, 19 px radius, centered 24 px above the window bottom.
- **Typography/style:** 12 px bold; `accent` surface with `bgSidebar` text; 200 ms opacity transition; visible for 2000 ms.
- **States/themes:** Single informational treatment; no separate success/error variants in current source.
- **Accessibility/localization:** Messages may be localized, but the current toast has no explicit live-region accessibility behavior. Do not use it as the only channel for critical or persistent errors.
- **Use / avoid:** Use for reversible, short confirmation. Do not place actions in this toast pattern.

### List rows

- **Purpose/source:** Present apps, settings, metadata, and selectable results; inline variants.
- **Geometry:** Common heights are 52 px; screenshot destination row is 58 px; descriptive platform row is 62 px; About metadata rows are 64 px. Standard horizontal inset is 14–18 px; app icons are 24 px.
- **Typography/style:** 12–13 px primary, 10–11 px secondary; `bgSubtle` for settings rows; selected app results use `accentDim` and an accent border.
- **States:** Neutral, hover, selected, disabled as applicable. Pressed is generally not visually distinct.
- **Accessibility/localization:** Selectable rows require role/name/checked semantics and keyboard support. Use elision only for intentionally single-line values.
- **Use / avoid:** Keep row anatomy consistent within one list. Do not mix several row heights without a content reason.

## Controls

### Buttons

- **Purpose/source:** Confirm, cancel, browse, choose/reset, delete, and secondary actions. Most are inline rectangles; update actions also use Qt Quick Controls `Button`.
- **Geometry:** Compact buttons are 34 px high; segmented/choice buttons 38 px; primary dialog actions 40 px. Radius is usually 8 or 10 px. Width follows label with 20–28 px total horizontal padding or a documented minimum.
- **Typography/icons/style:** 12 px, bold for primary actions; 14–16 px icons where present; primary uses `accent`, secondary uses `bgSubtle`/`bgCard` with 1 px border.
- **States:** Hover uses `accentHover` or `bgCardHover`; disabled commonly uses 0.45–0.5 opacity. Many inline buttons lack explicit pressed/focused visuals—do not propagate that limitation.
- **Accessibility/localization:** New custom buttons require `Accessible.Button`, localized name, Tab focus, and Enter/Return/Space. Let width grow for translated labels.
- **Use / avoid:** One visually primary action per dialog/section. Do not use accent fill for every action.

### Icon buttons

- **Purpose/source:** Close, delete, and compact utility actions; inline in `Main.qml`/`MousePage.qml` using [`AppIcon.qml`](../ui/qml/AppIcon.qml).
- **Geometry:** About close 34 × 34 with 14 px icon; Add App close 34 × 34 with 16 px icon; other icons are generally 14–18 px; 8–12 px radius.
- **States/style:** Transparent normal, subtle hover, accent focus where implemented. Destructive icon buttons may use danger semantics.
- **Accessibility/localization:** Accessible name is mandatory because no visible label exists. Target size must remain larger than the glyph.
- **Use / avoid:** Use only for universally recognized actions. Do not use an unlabeled icon for product-specific workflow.

### Inputs and search fields

- **Purpose/source:** Capture shortcuts, choose actions through `ComboBox`, and search apps. `TextField`/`ComboBox` use Qt Quick Controls; Add App search is inline.
- **Geometry:** Add App search is 40 px high, 10 px radius, 20 px dialog-side inset, and 16 px internal horizontal inset. Key capture dialog is 380 px wide with 24 px content margins.
- **Typography/style:** 12 px search text; 13 px key input; `bgSubtle`/`bgInput` surface, 1 px border, accent border on active focus.
- **States:** Normal, active focus, invalid/valid preview, and disabled where applicable. ComboBox popup delegates use 11 px text and accent-tinted highlight.
- **Accessibility/localization:** Placeholders are hints, not labels. Support keyboard navigation and translated options; shortcut notation remains plain text.
- **Use / avoid:** Use search for filtering a visible collection. Do not place persistent instructions only in placeholder text.

### Switches

- **Purpose/source:** Binary settings such as Generic Mouse Mode, SmartShift, startup, updates, and scroll inversion; Qt Quick Controls `Switch` inline in both pages.
- **Geometry:** Native Material control dimensions are style-derived, not fixed by this repository; switches sit in 52–62 px rows with 16 px horizontal inset.
- **Typography/style:** 13 px row label, optional 11 px description; `Material.accent` is the theme accent.
- **States:** Checked/unchecked, hover/pressed/focus/disabled are provided by Qt Quick Controls; focus policy is usually `Qt.StrongFocus`.
- **Accessibility/localization:** Each switch supplies an accessible localized name. Keep the label adjacent and do not invert the meaning between languages.
- **Use / avoid:** Use only for immediate binary state. Do not use for mutually exclusive choices or actions that merely start a task.

### Segmented and choice controls

- **Purpose/source:** Select appearance, language, scroll mode, DPI preset, or another mutually exclusive option; inline repeater patterns in `ScrollPage.qml`.
- **Geometry:** Main choices are 38 px high, 10 px radius, minimum 96 px (language minimum 108 px), label width + 28 px; DPI chips are 30 px high with 8 px radius.
- **Typography/style:** 12 px; selected uses `accentDim`, accent text, and sometimes a 2 px accent border; normal uses `bgSubtle` with 1 px border.
- **States:** Normal, hover, focus/selected/checked; selected semantics are exposed for scroll/language choices. Pressed treatment is not separately defined.
- **Accessibility/localization:** Use `Accessible.Button`, `checkable`, and `checked` for mutually exclusive choices. Width grows with translations.
- **Use / avoid:** Use for a small visible option set. Use a ComboBox when the set is long or changes dynamically.

### Sliders

- **Purpose/anatomy/source:** DPI, SmartShift threshold, gesture threshold, and DPI presets; reusable [`WheelSafeSlider.qml`](../ui/qml/WheelSafeSlider.qml).
- **Geometry:** 240 × 28 px implicit size; 6 px track with 3 px radius; 18 px handle with 9 px radius and 2 px accent border.
- **States/style:** Track uses `border`; filled track uses `accent`; handle uses `accentDim`, changing to `accent` while pressed. Cursor is pointing hand or closed hand during drag.
- **Behavior:** Snaps to `stepSize`, emits `moved`, and deliberately passes wheel events through to avoid changing values during page scrolling.
- **Accessibility/localization:** Current custom slider lacks explicit `Accessible.Slider` semantics and keyboard increments. Surrounding numeric labels expose range/value visually. Add these before treating it as a complete family control.
- **Use / avoid:** Use for bounded numeric choice where relative position matters. Do not use when exact keyboard entry is required.

### Action chips

- **Purpose/source:** Compact action selection; reusable [`ActionChip.qml`](../ui/qml/ActionChip.qml).
- **Geometry:** Label width + 24 px, 34 px high, 9 px radius; 12 px text.
- **States/style:** `bgCard` normal, `bgCardHover` hover, `accent` selected; 1 px border, 2 px on focus; 120 ms color transition.
- **Accessibility/localization:** `Accessible.Button`, Tab focus, and Enter/Return/Space; label and width are dynamic.
- **Use / avoid:** Use for short action labels in a flowing group. Do not use for long descriptions or unrelated navigation.

## Dialogs and product-specific controls

### General dialogs

- **Purpose/source:** Block a focused decision or short workflow. Implementations are inline Qt `Dialog` plus [`KeyCaptureDialog.qml`](../ui/qml/KeyCaptureDialog.qml).
- **Geometry:** Add App is 680 × 460, 16 px radius, 20 px outer inset, 40 px controls; delete confirmation is 380 px wide; key capture content is 380 px wide, content height + 48, 16 px radius, and 24 px margins.
- **Typography/style:** 18 px Add App title, 16 px key-capture title, 12–13 px body; `bgElevated`/`bgCard` with 1 px border; modal scrim is `#80000000` for key capture.
- **States:** Modal focus, validation, disabled confirmation, hover/focus/pressed controls, and Escape/close handling as implemented. Underlying global shortcuts are blocked.
- **Accessibility/localization:** Focus should enter the dialog, remain within its workflow, and return predictably. Titles, descriptions, actions, validation, and dynamic result counts must localize.
- **Use / avoid:** Use for a bounded decision. Do not move ordinary settings into a dialog.

### Functional mouse controls

- **Purpose/anatomy/source:** Select physical controls on device art and connect them to action configuration; reusable [`HotspotDot.qml`](../ui/qml/HotspotDot.qml) plus inline fallback rows.
- **Geometry:** 16 px dot, 30 px glow, 36 × 36 hit target; 6 px line endpoint; labels add 20 px width and 14 px height with 8 px radius; connector uses a 1 px dashed `[4,3]` line.
- **Typography/icons/style:** 12 px bold translated button label, 10 px action subtitle; accent dot/glow and selected label; label is clamped 8 px from its container edges.
- **States/motion:** Hover scales dot to 1.2 over 150 ms; selected glow pulses 1.0–1.25 over 800 ms each way; focus strengthens glow border; selected state changes label/surface.
- **Accessibility/localization:** `Accessible.Button`, Tab focus, Enter/Return/Space, translated button/action helpers, clickable label and dot. Long subtitles elide at 220 px.
- **Use / avoid:** Use only on correctly normalized device coordinates. These functional mouse symbols are not branding and must not be replaced by the logo.

### About dialog

- **Purpose/anatomy/source:** Presents product identity, version/build data, provenance, maintainer, and launch path; inline in `Main.qml`.
- **Geometry:** 500 × 560; outer radius 24; 24 px side inset; 36 px product mark; 44 px header; version hero radius 20 with 18 px inner padding; metadata surface radius 18 with 64 px rows.
- **Typography/style:** 17 px bold product name, 11 px subtitle/labels, 28 px bold version, 12–13 px platform-aware monospace metadata; `bgElevated`, `accentDim`, and `bgSubtle` layers.
- **States:** Modal; close button has hover and accessible press action; content treatment is identical in light/dark palettes.
- **Accessibility/localization:** Localized labels/subtitle, wrap-anywhere launch path, accessible close action, and full uncropped brand symbol.
- **Use / avoid:** Keep factual product/build information concise. Do not use About as a settings or release-notes workflow.

## Implementation gaps

These are documented limitations, not requests to change code in this task:

- Most component styling remains inline; only `ActionChip`, `AppIcon`, `HotspotDot`, `KeyCaptureDialog`, and `WheelSafeSlider` are reusable QML files.
- Button, row, and dialog dimensions are coherent but not fully tokenized.
- Custom pointer controls do not all expose focused, pressed, disabled, and keyboard states.
- `WheelSafeSlider` lacks keyboard and accessibility slider semantics.
- Toasts do not expose an assistive-technology live region.
- The selected hotspot label retains one earlier green-tinted light-mode RGBA.
- Icon sources mix filled and stroked construction.
