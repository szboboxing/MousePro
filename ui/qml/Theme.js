.pragma library

// Pour family tokens, translated from PourSend's shipped desktop UI.
// MousePro keeps its own information architecture and dark appearance while
// sharing the same calm blue-gray surfaces, restrained borders, and blue focus.
var radius = 12
var radiusSmall = 8
var radiusControl = 10
var radiusLarge = 16

var space4 = 4
var space8 = 8
var space12 = 12
var space16 = 16
var space20 = 20
var space24 = 24
var space32 = 32

function palette(isDark) {
    if (isDark) {
        return {
            bg: "#111a2a",
            bgElevated: "#172236",
            bgCard: "#19253a",
            bgCardHover: "#223149",
            bgSidebar: "#141f31",
            bgInput: "#111b2d",
            bgSubtle: "#1d2a40",
            accent: "#7da6ff",
            accentHover: "#9ab9ff",
            accentDim: "#243958",
            textPrimary: "#f2f6fc",
            textSecondary: "#b2bfd0",
            textDim: "#8797ae",
            border: "#2b3a51",
            danger: "#ff8585",
            dangerBg: "#4b2730",
            success: "#55c684",
            warning: "#e9b95e",
            tooltipBg: "#263650",
            tooltipText: "#f8fafc"
        }
    }

    return {
        bg: "#f3f7fc",
        bgElevated: "#ffffff",
        bgCard: "#ffffff",
        bgCardHover: "#f1f6ff",
        bgSidebar: "#f1f7ff",
        bgInput: "#ffffff",
        bgSubtle: "#f8fbff",
        accent: "#5d8ff3",
        accentHover: "#4779df",
        accentDim: "#e7f0ff",
        textPrimary: "#17233a",
        textSecondary: "#5e718c",
        textDim: "#74819a",
        border: "#dce6f2",
        danger: "#d92d20",
        dangerBg: "#fdecec",
        success: "#1f8a4c",
        warning: "#b7791f",
        tooltipBg: "#202938",
        tooltipText: "#f8fafc"
    }
}
