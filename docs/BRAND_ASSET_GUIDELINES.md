# Pour Brand Asset Guidelines

> **Scope:** The current MousePro identity is the implemented reference for MousePro. These rules separate production brand assets from functional UI iconography. See [`POUR_DESIGN_SYSTEM.md`](POUR_DESIGN_SYSTEM.md) for family principles.

## Contents

- [Identity inventory](#identity-inventory)
- [Usage rules](#usage-rules)
- [Platform requirements](#platform-requirements)
- [Placement guidance](#placement-guidance)
- [Naming and generation](#naming-and-generation)
- [Do and Don't](#do-and-dont)

## Identity inventory

| Asset | Current file | Dimensions/type | Authority and use |
|---|---|---|---|
| Symbol/app-icon master | [`images/logo_icon.png`](../images/logo_icon.png) | 1024 × 1024 RGBA | Canonical symbol master; mouse silhouette, integrated P, and leaf |
| Horizontal logo | [`images/logo.png`](../images/logo.png) | 1983 × 793 RGB | Complete uncropped MousePro wordmark for light/white presentation and README |
| Monochrome symbol template | [`images/logo_tray_template.png`](../images/logo_tray_template.png) | 1024 × 1024 RGBA | System-tinted macOS menu-bar/tray mark |
| Windows icon | [`images/logo.ico`](../images/logo.ico) | Multi-image ICO | Generated Windows executable/title/taskbar resource |
| macOS bundle icon | [`images/AppIcon.icns`](../images/AppIcon.icns) | Multi-resolution ICNS | Current macOS spec authority |
| Compatibility ICNS | [`images/logo.icns`](../images/logo.icns) | ICNS | Retained production asset; current specs reference `AppIcon.icns` instead |
| Linux icons | [`packaging/linux/icons/hicolor/`](../packaging/linux/icons/hicolor/) | 16–512 px PNG ladder | Desktop integration and taskbar/application menus |

The repository does **not** currently contain a separate full horizontal dark-background logo or a full horizontal monochrome logo. Do not invent, recolor, or synthesize one in ordinary product work. On dark UI, use the transparent symbol master, or place the existing horizontal RGB logo on an intentional white/light panel that preserves its full canvas.

## Usage rules

### Core identity

Preserve the mouse silhouette, integrated P, leaf, scroll-wheel accent, proportions, curves, and current blue-gray/soft-green palette. Do not redraw or substitute individual parts. The P is the focal point; the leaf and wheel remain supporting details.

### Aspect ratio and cropping

- Always use `PreserveAspectFit` or equivalent.
- Never crop, stretch, skew, rotate, condense, or expand the logo.
- Never trim the master symbol's transparent gutter or the horizontal logo's source canvas.
- Do not mask the logo into an unrelated shape.
- Keep the complete wordmark visible; `MousePro` must never be truncated to `MouseP` or another partial string.

### Clear space

The app-icon master includes its production clear area: an approximately 824 px symbol on a 1024 px canvas, leaving about 100 px transparent gutter per side. Preserve the full canvas. For the horizontal RGB logo, the complete 1983 × 793 canvas is the minimum exclusion area; no text, badge, edge, or overlay may intrude into it.

No additional family-wide clear-space ratio is encoded in the current implementation. If a new context needs one, record it as a recommendation and validate it against the master rather than trimming the existing built-in space.

### Minimum size and simplification

- The symbol is production-tested through the generated Windows/Linux 16, 24, 32, 48, 64, 128, 256, and (Linux) 512 px sizes.
- At 16–24 px, use the generated platform asset; do not manually sharpen, remove the leaf, thicken the P, or redraw the wheel.
- The current README implementation displays the horizontal logo at 420 CSS px. No smaller horizontal-wordmark threshold is encoded. If the complete wordmark becomes illegible, use the symbol-only mark rather than creating a cropped or altered wordmark.
- Small-size platform fitting is performed by [`scripts/build_app_icon.py`](../scripts/build_app_icon.py), not by editing the master.

### Color use

- Use the supplied artwork. Do not sample UI accent tokens to recolor the production logo.
- Do not replace blue-gray with pure black or increase green saturation.
- The monochrome tray template is the only current asset intended for system tinting.
- Do not add gradients, gloss, shadows, outlines, or effects. Any tonal variation already present in a supplied raster is part of that asset.
- On light backgrounds, use the horizontal logo or symbol master as supplied.
- On dark backgrounds, prefer the transparent symbol master. The horizontal RGB file retains its white/light source canvas and should not be made transparent ad hoc.

## Platform requirements

### Windows ICO

[`images/logo.ico`](../images/logo.ico) must contain 16, 24, 32, 48, 64, 128, and 256 px images. [`MousePro.spec`](../MousePro.spec) embeds it in the executable; [`main_qml.py`](../main_qml.py) loads it for the Windows runtime icon. Validate the embedded EXE independently of Explorer's icon cache.

### macOS ICNS and menu bar

[`images/AppIcon.icns`](../images/AppIcon.icns) is consumed by [`MousePro-mac.spec`](../MousePro-mac.spec). The build pipeline produces 16, 32, 128, 256, and 512 px plus Retina variants from the 1024 px master. The Dock uses the full-color symbol; the menu bar uses `logo_tray_template.png` as a system template. Do not use the generic functional mouse SVG as the product tray identity.

### Linux

The hicolor ladder uses the application ID `io.github.szboboxing.mousepro` at 16, 24, 32, 48, 64, 128, 256, and 512 px. Keep directory names and file names exact so desktop environments resolve them.

### High DPI

Use the master or multi-resolution platform container, not a screenshot. Verify the icon at 100%, 125%, 150%, and 200% OS scale. QML brand `Image` elements use explicit high-resolution `sourceSize`, smoothing, mipmaps, and aspect preservation.

## Placement guidance

### Window title bar and taskbar

Use the generated platform app icon. It must remain recognizable at 16–32 px and must not be replaced with the horizontal wordmark.

### Sidebar

The current global rail uses the symbol master in a 44 × 44 logical-pixel `Image` with a 128 × 128 source request. Preserve the full symbol and its internal clear area. Functional navigation items below it retain their own icons.

### About dialog

Use the symbol master at 36 × 36 logical px with a 96 × 96 source request. Keep it aligned with the product name and subtitle; do not enlarge it until it competes with the version information.

### README

Both [`README.md`](../README.md) and [`README_CN.md`](../README_CN.md) use the complete horizontal logo at 420 CSS px. Keep both language versions aligned. Do not substitute a preview mockup or a wordmark crop.

### GitHub and social surfaces

Use a production master, not an application screenshot containing the logo. For square avatar/icon contexts, use `logo_icon.png`. For wide contexts, use `logo.png` only when its full light canvas is appropriate. The repository has no separately approved social-preview composition; creating one is a distinct design task and must not be implied by these assets.

### Functional mouse icons are not brand marks

[`images/icons/mouse-simple.svg`](../images/icons/mouse-simple.svg), device art, button hotspots, and mouse-control glyphs communicate product function. They are **not** legacy MousePro logos. Keep them wherever the UI needs a mouse/device/action symbol. Replace them with the brand mark only when the surface explicitly represents the application identity, such as the application icon, global rail brand slot, or About header.

## Naming and generation

### Source/master names

- `images/logo_icon.png` — canonical square symbol master
- `images/logo.png` — complete horizontal light-canvas logo
- `images/logo_tray_template.png` — monochrome system-template symbol

### Generated/packaged names

- `images/logo.ico` — Windows container
- `images/AppIcon.icns` — macOS bundle container
- `images/logo.icns` — retained compatibility container, not the current spec authority
- `packaging/linux/icons/hicolor/<size>x<size>/apps/io.github.szboboxing.mousepro.png` — Linux ladder

Regenerate platform outputs with `python scripts/build_app_icon.py`. Do not hand-edit derived sizes. Keep review previews and temporary render outputs outside tracked production asset paths unless a separate request explicitly approves them as repository content.

## Do and Don't

| Do | Don't |
|---|---|
| Use the supplied master and generated platform assets | Redraw the P, leaf, wheel, or silhouette |
| Preserve the full canvas and aspect ratio | Crop, stretch, skew, or truncate |
| Use the symbol for small/system contexts | Force the horizontal wordmark into a title bar or taskbar |
| Keep functional mouse icons for functional meaning | Replace every mouse glyph with the brand mark |
| Use the tray template only where the OS tints it | Recolor the full-color master with UI tokens |
| Validate at every generated small size and DPI scale | Trust a single 256 px preview |
| Keep README language versions visually aligned | Commit temporary logo-review mockups as production assets |
