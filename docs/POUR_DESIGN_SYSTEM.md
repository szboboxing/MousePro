# Pour Product-Family Design System

> **Authority:** This document defines the shared Pour-family foundation. For the current MousePro implementation, [`ui/qml/Theme.js`](../ui/qml/Theme.js) and the shipped QML remain the source of truth. [`POUR_COMPONENTS.md`](POUR_COMPONENTS.md) records current component details and product-specific exceptions. When guidance conflicts, current source wins for MousePro; this document governs new family work unless an explicitly documented product exception applies.

## Contents

- [Documentation map](#documentation-map)
- [Brand philosophy](#brand-philosophy)
- [Family and product relationship](#family-and-product-relationship)
- [Foundation tokens](#foundation-tokens)
- [Typography](#typography)
- [Layout and spacing](#layout-and-spacing)
- [Surfaces, borders, and radii](#surfaces-borders-and-radii)
- [Light and dark modes](#light-and-dark-modes)
- [Iconography and motion](#iconography-and-motion)
- [Accessibility and localization](#accessibility-and-localization)
- [High DPI and desktop interaction](#high-dpi-and-desktop-interaction)
- [Rules for future Pour applications](#rules-for-future-pour-applications)
- [Known implementation exceptions](#known-implementation-exceptions)

## Documentation map

- Current component vocabulary: [`POUR_COMPONENTS.md`](POUR_COMPONENTS.md)
- Identity assets: [`BRAND_ASSET_GUIDELINES.md`](BRAND_ASSET_GUIDELINES.md)
- Screenshot production: [`SCREENSHOT_GUIDELINES.md`](SCREENSHOT_GUIDELINES.md)
- Release gate: [`RELEASE_VISUAL_CHECKLIST.md`](RELEASE_VISUAL_CHECKLIST.md)

There is no `docs/DESIGN_SYSTEM.md` in the current repository. If one is introduced later as a MousePro-specific authority, it must link here, state its narrower scope, and identify every deliberate exception instead of silently redefining family rules.

## Brand philosophy

**Transform complexity into clarity.**

Pour products should make technically capable workflows feel calm, understandable, and deliberate. The interface should reveal the current state, make the next action obvious, and keep advanced detail available without letting it dominate the first visual read.

Product-family principles:

1. **One focal point per page.** The page title and primary workspace lead; badges and secondary controls support them.
2. **Dense, not crowded.** Use desktop-scale controls and compact vertical rhythm without sacrificing readable grouping.
3. **State is visible.** Selected, connected, disabled, pending, and error states must not depend on color alone.
4. **Shared structure, product-specific workflow.** Family resemblance comes from tokens, typography, surfaces, icon treatment, and craftsmanship—not copied layouts.
5. **Quiet confidence.** Neutral surfaces and restrained borders carry the interface; accent color is reserved for action, focus, and selection.

## Family and product relationship

MousePro and PourSend are companion shipped products in the Pour family. This repository establishes MousePro's implementation and records only one direct PourSend relationship: the current tokens were translated from PourSend's shipped desktop UI. This documentation does not infer PourSend behavior or undocumented tokens.

### Shared decisions

- calm blue-gray neutral hierarchy;
- restrained borders and elevated white/dark surfaces;
- blue focus and selection language;
- compact desktop spacing and radii;
- system-font typography;
- aspect-preserving, high-DPI brand assets;
- consistent light/dark information hierarchy.

### Product-specific decisions

- MousePro's mouse diagram, profile sidebar, device status, DPI controls, and functional mouse icons;
- MousePro's current blue accent values;
- platform-specific input, tray, and device workflows;
- any layout required by a product's own information architecture.

Future products may choose a distinct accent, but must retain the neutral philosophy and define complete normal, hover, focus, selected, disabled, light, and dark treatments. No future product name, logo, or accent is established here.

## Foundation tokens

All implemented color tokens below come from [`ui/qml/Theme.js`](../ui/qml/Theme.js).

### Light palette

| Token | Value | Purpose |
|---|---:|---|
| `bg` | `#f3f7fc` | Primary application canvas |
| `bgElevated` | `#ffffff` | Dialogs and elevated panels |
| `bgCard` | `#ffffff` | Standard cards |
| `bgCardHover` | `#f1f6ff` | Hovered neutral controls and rows |
| `bgSidebar` | `#f1f7ff` | Global navigation rail |
| `bgInput` | `#ffffff` | Input surfaces |
| `bgSubtle` | `#f8fbff` | Nested rows and secondary surfaces |
| `accent` | `#5d8ff3` | Focus, active action, selection |
| `accentHover` | `#4779df` | Stronger interactive accent |
| `accentDim` | `#e7f0ff` | Selected/active background |
| `textPrimary` | `#17233a` | Titles and primary content |
| `textSecondary` | `#5e718c` | Supporting copy |
| `textDim` | `#74819a` | Metadata and low-emphasis labels |
| `border` | `#dce6f2` | Dividers and card boundaries |
| `danger` | `#d92d20` | Destructive/error foreground |
| `dangerBg` | `#fdecec` | Destructive/error background |
| `success` | `#1f8a4c` | Success state |
| `warning` | `#b7791f` | Warning state |
| `tooltipBg` | `#202938` | Tooltip surface |
| `tooltipText` | `#f8fafc` | Tooltip text |

### Dark palette

| Token | Value | Purpose |
|---|---:|---|
| `bg` | `#111a2a` | Primary application canvas |
| `bgElevated` | `#172236` | Dialogs and elevated panels |
| `bgCard` | `#19253a` | Standard cards |
| `bgCardHover` | `#223149` | Hovered neutral controls and rows |
| `bgSidebar` | `#141f31` | Global navigation rail |
| `bgInput` | `#111b2d` | Input surfaces |
| `bgSubtle` | `#1d2a40` | Nested rows and secondary surfaces |
| `accent` | `#7da6ff` | Focus, active action, selection |
| `accentHover` | `#9ab9ff` | Stronger interactive accent |
| `accentDim` | `#243958` | Selected/active background |
| `textPrimary` | `#f2f6fc` | Titles and primary content |
| `textSecondary` | `#b2bfd0` | Supporting copy |
| `textDim` | `#8797ae` | Metadata and low-emphasis labels |
| `border` | `#2b3a51` | Dividers and card boundaries |
| `danger` | `#ff8585` | Destructive/error foreground |
| `dangerBg` | `#4b2730` | Destructive/error background |
| `success` | `#55c684` | Success state |
| `warning` | `#e9b95e` | Warning state |
| `tooltipBg` | `#263650` | Tooltip surface |
| `tooltipText` | `#f8fafc` | Tooltip text |

### Product accent strategy

The blue pairs above are the **implemented MousePro standard**, including the Material accent set in [`main_qml.py`](../main_qml.py). They are not automatically the accent of every Pour product. A future product accent must be documented as product-specific and must not replace semantic danger, success, or warning colors.

The neutral palette is the family anchor. New products should first reuse or deliberately adapt the neutral roles, then add one restrained product accent. Avoid large accent-colored surfaces and avoid using the accent as a substitute for hierarchy.

## Typography

MousePro uses the current Qt application font. [`main_qml.py`](../main_qml.py) falls back to `.AppleSystemUIFont` on macOS, `Segoe UI` on Windows, and `Noto Sans` on Linux when Qt returns no useful family. Monospace metadata uses Menlo, Consolas, or generic `monospace` according to platform.

The following is the **implemented hierarchy**, not a perfectly normalized type scale:

| Role | Current size/weight | Current implementation |
|---|---|---|
| Version display | 28 px bold | About dialog, [`Main.qml`](../ui/qml/Main.qml) |
| Page title / empty-state title | 24 px bold | [`MousePage.qml`](../ui/qml/MousePage.qml), [`ScrollPage.qml`](../ui/qml/ScrollPage.qml) |
| Dialog title | 18 px bold; About uses 17 px | Inline dialogs in `MousePage.qml` and `Main.qml` |
| Section title | 16 px bold | Settings cards; key-capture title |
| Profile/sidebar heading | 15 px bold | Profile sidebar |
| Strong row/value | 13–14 px, regular or bold | Settings rows and values |
| Body | 12–13 px regular | Descriptions and primary supporting copy |
| Metadata/labels | 11 px, sometimes bold | Badges, field labels, captions |
| Compact metadata | 10 px | Profile subtitles and compact status |
| Exceptional microcopy | 9 px | A small number of layout/status labels |

Rules:

- Use `uiState.fontFamily`; do not hardcode a platform font in ordinary UI.
- Use bold or `Font.DemiBold` for hierarchy, not arbitrary color changes alone.
- Keep body copy at 12–13 px in current-density desktop layouts.
- Wrap explanatory copy and elide path/app labels where their container is intentionally single-line.
- Future components should use the closest existing role before introducing another size.

## Layout and spacing

### Implemented shell grid

| Element | Value | Source |
|---|---:|---|
| Default window | `1060 × 700` logical px | [`Main.qml`](../ui/qml/Main.qml) |
| Minimum window | `920 × 620` logical px | `Main.qml` |
| Navigation rail | `76` px | `Main.qml` |
| Profile sidebar | `240` px | [`MousePage.qml`](../ui/qml/MousePage.qml) |
| Standard page header | `88` px | `MousePage.qml`, [`ScrollPage.qml`](../ui/qml/ScrollPage.qml) |
| Main content inset | `32` px per side | Cards are `parent.width - 64` |
| Standard card padding | `16` px | `Theme.space16` |
| Typical card gap | `16` px | Inline gaps between settings cards |

### Implemented spacing tokens

| Token | Value | Intended use |
|---|---:|---|
| `space4` | 4 px | Tight internal grouping |
| `space8` | 8 px | Icon/label and compact row gaps |
| `space12` | 12 px | Standard control grouping |
| `space16` | 16 px | Card padding and section gaps |
| `space20` | 20 px | Dialog padding and major internal separation |
| `space24` | 24 px | Large section/footer separation |
| `space32` | 32 px | Page-level content origin |

Use these tokens for new work. Current inline values such as 3, 6, 10, 14, and 18 px are implementation-specific optical adjustments, not new family tokens.

## Surfaces, borders, and radii

### Implemented radius tokens

| Token | Value | Purpose |
|---|---:|---|
| `radiusSmall` | 8 px | Tooltips, compact pills, small controls |
| `radiusControl` | 10 px | Buttons, rows, search fields |
| `radius` | 12 px | Standard cards |
| `radiusLarge` | 16 px | Empty states and principal dialogs |

Use a 1 px `border` token around cards, inputs, and neutral buttons when separation is needed. Prefer surface contrast over multiple nested borders. Dividers are 1 px and usually inset to the content grid. Selected controls may strengthen to a 2 px accent border. Fully rounded badges use half their height; the About build chip uses an intentionally pill-like radius of `999`.

Current exceptions include About-dialog radii of 18, 20, and 24 px and several inline 14 px cards. These are product-specific implemented values, not additions to the family scale.

## Light and dark modes

Light mode uses cool off-white canvas/sidebar surfaces, white cards, navy text, and restrained blue-gray borders. Dark mode uses layered navy surfaces rather than pure black. Both modes must preserve the same order of title, content, secondary copy, selection, and status.

- Do not add extra borders in dark mode merely to compensate for low contrast; choose the correct adjacent surface roles.
- Do not use pure black for family UI or brand text.
- Keep semantic colors readable in both palettes.
- Use `appearanceMode` values `system`, `light`, and `dark`; system mode follows Qt's platform color scheme.
- Validate every component in both modes. A light-mode-only custom RGBA is not automatically safe in dark mode.

## Iconography and motion

### Iconography

Functional icons are served through [`AppIcon.qml`](../ui/qml/AppIcon.qml) and `AppIconProvider`, normally at 18–20 px with aspect preservation, smoothing, mipmaps, caching, and caller-supplied theme color. Use one optical family per surface, center by eye, and keep adjacent icons at a consistent perceived—not merely numeric—size.

The current icon folder contains mostly filled 256-unit SVG paths, while `info.svg` is a 24-unit stroked icon. This is a known inconsistency. Future additions should match the dominant filled family or deliberately normalize an entire set; do not mix construction styles casually.

Functional mouse icons describe navigation, device type, or controls. They are not legacy brand marks and must not be replaced by the MousePro logo. See [`BRAND_ASSET_GUIDELINES.md`](BRAND_ASSET_GUIDELINES.md).

### Motion

| Pattern | Current duration |
|---|---:|
| Chip/tooltip hover transition | 120 ms |
| Navigation/scale/color transition | 150 ms |
| Toast/hotspot opacity transition | 200 ms |
| Selected-hotspot pulse | 800 ms out + 800 ms in |

Motion should explain state change, not decorate idle UI. Use short color/opacity transitions for hover and selection. Avoid layout movement for routine hover. The current implementation has no reduced-motion branch; future animation work should add one before expanding ambient or looping motion.

## Accessibility and localization

### Accessibility requirements

- Every actionable custom item must expose an appropriate `Accessible.role`, name, checked/selected state where relevant, and keyboard activation.
- Support Tab focus and Enter/Return/Space activation for custom buttons.
- Use a visible accent focus treatment; do not rely on hover.
- Preserve at least the implemented 36 × 36 px hotspot hit area and 48 px navigation row height for equivalent controls.
- Communicate error, warning, connection, and selection with text/icon/shape in addition to color.
- Maintain readable contrast in both theme palettes. This repository does not contain a recorded contrast audit, so do not claim formal compliance without measuring it.
- Disabled controls must suppress interaction and retain a readable label; current implementations commonly use 0.45–0.5 opacity.

Custom-control accessibility coverage is not yet uniform. `ActionChip`, navigation, hotspot controls, segmented choices, and switches expose accessibility data; several inline rectangle buttons are pointer-driven only. Treat that as an implementation limitation, not a model for future components.

### Localization and mixed scripts

The current selectable languages are English (`en`) and Simplified Chinese (`zh_CN`) in [`ui/locale_manager.py`](../ui/locale_manager.py). UI strings are reactive to language changes. Future work must:

- test English, Chinese, and mixed Latin/Chinese labels;
- avoid fixed text widths unless elision or wrapping is intentional;
- use `Text.WordWrap` for explanatory copy and middle/right elision for paths and single-line app labels;
- keep numbers, DPI units, shortcut notation, and product names legible beside CJK text;
- verify baseline alignment and avoid relying on letter spacing for CJK hierarchy;
- keep both README language versions structurally aligned when shared presentation changes.

## High DPI and desktop interaction

QML dimensions are logical pixels. Brand images and functional icons use `PreserveAspectFit`, explicit `sourceSize`, smoothing, and mipmaps. Runtime tray rendering reads `devicePixelRatio`; the Windows ICO includes 16, 24, 32, 48, 64, 128, and 256 px; Linux includes 16 through 512 px; macOS ICNS contains standard and Retina representations.

Validate at 100%, 125%, 150%, and 200% scale. Check raster sharpness, one-pixel borders, centered icons, text clipping, dialog fit, and the `920 × 620` minimum-window state. Never compensate for DPI problems by hardcoding physical-pixel offsets.

Desktop-first interaction means:

- compact controls sized for pointer and keyboard use, not mobile touch patterns;
- hover, focus, pressed, selected, and disabled states where applicable;
- visible window chrome and platform-consistent title/taskbar icons;
- scrollable content when vertical space is constrained;
- keyboard focus that follows visual and reading order;
- no workflow changes solely to imitate another platform.

## Rules for future Pour applications

1. Start with the family neutral roles, spacing tokens, radius hierarchy, system typography, and state model.
2. Define product-specific accent and workflow exceptions in writing; do not silently fork shared tokens.
3. Keep the product's own information architecture. Do not copy MousePro or PourSend page layouts verbatim.
4. Use the standard shell grid as a reference, then document any deliberate window, rail, or content-inset difference.
5. Add a reusable component only when the same anatomy and behavior recur; accurately document inline styling until then.
6. Provide light, dark, localized, high-DPI, keyboard, empty, error, and minimum-window evidence before release.
7. Keep brand identity separate from functional iconography.
8. Update this package and the product-specific authority in the same change when a shared standard changes.

## Known implementation exceptions

- Typography uses a coherent hierarchy but not a single tokenized scale; 9–28 px values remain inline.
- About and several secondary cards use radii outside the four shared radius tokens.
- SVG construction mixes filled and stroked icon sources.
- Several inline rectangle buttons lack the complete keyboard/focus behavior of reusable components.
- Pressed states are not consistently distinct from hover states.
- `HotspotDot.qml` uses a light-mode selected-label RGBA derived from the earlier green direction; the main family accent is now blue.
- One debug text area hardcodes `Menlo`, while the shell otherwise supplies a platform-aware monospace family.
- Existing checked-in screenshots predate this screenshot standard and use approximately 1919 × 1150 output rather than the default 1060 × 700 logical window framing.

Do not change application code merely to make these notes disappear. Resolve them only through a separately scoped, tested implementation change.
