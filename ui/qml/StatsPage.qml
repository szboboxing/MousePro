import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "Theme.js" as Theme

/*  MousePro V1.0 — Usage statistics page (current session only).
    Clicks / wheel / feature cards read flat keys from backend.usageStats;
    distance is formatted as 万 px / k px depending on the active locale. */

Item {
    id: statsPage

    signal toastRequested(string msg)

    readonly property var theme: Theme.palette(uiState.darkMode)
    property var s: lm.strings

    // Bumped on usageStatsChanged so formatter bindings re-evaluate.
    property int statsTick: 0

    function statValue(key) {
        var snap = backend.usageStats
        var v = snap ? snap[key] : 0
        return v === undefined || v === null ? 0 : v
    }

    function formatDistance(px) {
        var value = Number(px) || 0
        statsTick // track refresh signal
        if (value >= 10000 && lm.language === "zh_CN")
            return (value / 10000).toFixed(1) + s["mousepro.stats.unit_wan"]
        if (value >= 10000)
            return Math.round(value / 1000) + s["mousepro.stats.unit_wan"]
        return Math.round(value) + " px"
    }

    ScrollView {
        id: pageScroll
        anchors.fill: parent
        clip: true
        contentWidth: availableWidth

        Column {
            width: pageScroll.availableWidth
            spacing: 0

            // ── Header ───────────────────────────────────────────
            Item {
                width: parent.width
                height: 88

                Column {
                    anchors {
                        left: parent.left
                        leftMargin: Theme.space32
                        verticalCenter: parent.verticalCenter
                    }
                    spacing: 4

                    Text {
                        text: s["mousepro.stats.page_title"]
                        font { family: uiState.fontFamily; pixelSize: 24; bold: true }
                        color: statsPage.theme.textPrimary
                    }

                    Text {
                        text: s["mousepro.stats.page_subtitle"]
                        font { family: uiState.fontFamily; pixelSize: 13 }
                        color: statsPage.theme.textSecondary
                    }
                }
            }

            Rectangle {
                width: parent.width - 64
                height: 1
                color: statsPage.theme.border
                anchors.horizontalCenter: parent.horizontalCenter
            }

            Item { width: 1; height: Theme.space20 }

            // ── Clicks ───────────────────────────────────────────
            Rectangle {
                width: parent.width - 64
                anchors.horizontalCenter: parent.horizontalCenter
                height: clicksCard.implicitHeight + 32
                radius: Theme.radius
                color: statsPage.theme.bgCard
                border.width: 1
                border.color: statsPage.theme.border

                Column {
                    id: clicksCard
                    anchors {
                        left: parent.left
                        right: parent.right
                        top: parent.top
                        margins: Theme.space16
                    }
                    spacing: 12

                    RowLayout {
                        width: parent.width

                        AppIcon {
                            width: 18
                            height: 18
                            name: "mouse-simple"
                            iconColor: statsPage.theme.accent
                        }

                        Text {
                            text: s["mousepro.stats.clicks_section"]
                            font { family: uiState.fontFamily; pixelSize: 16; bold: true }
                            color: statsPage.theme.textPrimary
                            Layout.fillWidth: true
                            Layout.leftMargin: 4
                        }

                        Rectangle {
                            Layout.preferredWidth: Math.max(
                                118, statsResetText.implicitWidth + 24)
                            Layout.preferredHeight: 34
                            radius: Theme.radiusSmall
                            color: statsResetMouse.containsMouse
                                   ? statsPage.theme.bgCardHover
                                   : statsPage.theme.bgSubtle
                            border.width: 1
                            border.color: statsPage.theme.border

                            Behavior on color { ColorAnimation { duration: 120 } }

                            Accessible.role: Accessible.Button
                            Accessible.name: s["mousepro.usage_stats.reset"]

                            Row {
                                anchors.centerIn: parent
                                spacing: 6

                                AppIcon {
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: 14
                                    height: 14
                                    name: "trash"
                                    iconColor: statsPage.theme.textSecondary
                                }

                                Text {
                                    id: statsResetText
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: s["mousepro.usage_stats.reset"]
                                    font { family: uiState.fontFamily; pixelSize: 12 }
                                    color: statsPage.theme.textPrimary
                                }
                            }

                            MouseArea {
                                id: statsResetMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: backend.resetUsageStats()
                            }
                        }
                    }

                    GridLayout {
                        width: parent.width
                        columns: 2
                        rowSpacing: 10
                        columnSpacing: 12

                        Repeater {
                            model: [
                                "mousepro.stats.left_clicks",
                                "mousepro.stats.right_clicks",
                                "mousepro.stats.middle_clicks",
                                "mousepro.stats.xbutton1_clicks",
                                "mousepro.stats.xbutton2_clicks"
                            ]

                            delegate: Rectangle {
                                required property var modelData
                                Layout.fillWidth: true
                                Layout.preferredHeight: 44
                                radius: Theme.radiusControl
                                color: statsPage.theme.bgSubtle

                                RowLayout {
                                    anchors {
                                        left: parent.left
                                        right: parent.right
                                        top: parent.top
                                        bottom: parent.bottom
                                        leftMargin: 12
                                        rightMargin: 12
                                    }

                                    Text {
                                        text: s[modelData] || modelData
                                        font { family: uiState.fontFamily; pixelSize: 12 }
                                        color: statsPage.theme.textSecondary
                                        Layout.fillWidth: true
                                    }

                                    Text {
                                        text: "" + statsPage.statValue(
                                                   modelData.replace("mousepro.stats.", ""))
                                        font { family: uiState.fontFamily; pixelSize: 15; bold: true }
                                        color: statsPage.theme.textPrimary
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Item { width: 1; height: Theme.space16 }

            // ── Wheel ────────────────────────────────────────────
            Rectangle {
                width: parent.width - 64
                anchors.horizontalCenter: parent.horizontalCenter
                height: wheelCard.implicitHeight + 32
                radius: Theme.radius
                color: statsPage.theme.bgCard
                border.width: 1
                border.color: statsPage.theme.border

                Column {
                    id: wheelCard
                    anchors {
                        left: parent.left
                        right: parent.right
                        top: parent.top
                        margins: Theme.space16
                    }
                    spacing: 12

                    Row {
                        spacing: 4

                        AppIcon {
                            width: 18
                            height: 18
                            name: "sliders-horizontal"
                            iconColor: statsPage.theme.accent
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: s["mousepro.stats.wheel_section"]
                            font { family: uiState.fontFamily; pixelSize: 16; bold: true }
                            color: statsPage.theme.textPrimary
                        }
                    }

                    GridLayout {
                        width: parent.width
                        columns: 2
                        rowSpacing: 10
                        columnSpacing: 12

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 44
                            radius: Theme.radiusControl
                            color: statsPage.theme.bgSubtle

                            RowLayout {
                                anchors {
                                    left: parent.left
                                    right: parent.right
                                    top: parent.top
                                    bottom: parent.bottom
                                    leftMargin: 12
                                    rightMargin: 12
                                }

                                Text {
                                    text: s["mousepro.stats.wheel_up"]
                                    font { family: uiState.fontFamily; pixelSize: 12 }
                                    color: statsPage.theme.textSecondary
                                    Layout.fillWidth: true
                                }

                                Text {
                                    text: "" + statsPage.statValue("wheel_up")
                                    font { family: uiState.fontFamily; pixelSize: 15; bold: true }
                                    color: statsPage.theme.textPrimary
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 44
                            radius: Theme.radiusControl
                            color: statsPage.theme.bgSubtle

                            RowLayout {
                                anchors {
                                    left: parent.left
                                    right: parent.right
                                    top: parent.top
                                    bottom: parent.bottom
                                    leftMargin: 12
                                    rightMargin: 12
                                }

                                Text {
                                    text: s["mousepro.stats.wheel_down"]
                                    font { family: uiState.fontFamily; pixelSize: 12 }
                                    color: statsPage.theme.textSecondary
                                    Layout.fillWidth: true
                                }

                                Text {
                                    text: "" + statsPage.statValue("wheel_down")
                                    font { family: uiState.fontFamily; pixelSize: 15; bold: true }
                                    color: statsPage.theme.textPrimary
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 44
                            radius: Theme.radiusControl
                            color: statsPage.theme.bgSubtle

                            RowLayout {
                                anchors {
                                    left: parent.left
                                    right: parent.right
                                    top: parent.top
                                    bottom: parent.bottom
                                    leftMargin: 12
                                    rightMargin: 12
                                }

                                Text {
                                    text: s["mousepro.stats.distance"]
                                    font { family: uiState.fontFamily; pixelSize: 12 }
                                    color: statsPage.theme.textSecondary
                                    Layout.fillWidth: true
                                }

                                Text {
                                    text: statsPage.formatDistance(
                                             statsPage.statValue("distance_pixels"))
                                    font { family: uiState.fontFamily; pixelSize: 15; bold: true }
                                    color: statsPage.theme.textPrimary
                                }
                            }
                        }
                    }
                }
            }

            Item { width: 1; height: Theme.space16 }

            // ── Features ─────────────────────────────────────────
            Rectangle {
                width: parent.width - 64
                anchors.horizontalCenter: parent.horizontalCenter
                height: featuresCard.implicitHeight + 32
                radius: Theme.radius
                color: statsPage.theme.bgCard
                border.width: 1
                border.color: statsPage.theme.border

                Column {
                    id: featuresCard
                    anchors {
                        left: parent.left
                        right: parent.right
                        top: parent.top
                        margins: Theme.space16
                    }
                    spacing: 12

                    Row {
                        spacing: 4

                        AppIcon {
                            width: 18
                            height: 18
                            name: "stats"
                            iconColor: statsPage.theme.accent
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: s["mousepro.stats.features_section"]
                            font { family: uiState.fontFamily; pixelSize: 16; bold: true }
                            color: statsPage.theme.textPrimary
                        }
                    }

                    Repeater {
                        model: [
                            "mousepro.stats.feature_copy",
                            "mousepro.stats.feature_enhanced_paste",
                            "mousepro.stats.feature_screenshot"
                        ]

                        delegate: Rectangle {
                            required property var modelData
                            width: parent.width
                            height: 44
                            radius: Theme.radiusControl
                            color: statsPage.theme.bgSubtle

                            RowLayout {
                                anchors {
                                    left: parent.left
                                    right: parent.right
                                    top: parent.top
                                    bottom: parent.bottom
                                    leftMargin: 12
                                    rightMargin: 12
                                }

                                Text {
                                    text: s[modelData] || modelData
                                    font { family: uiState.fontFamily; pixelSize: 12 }
                                    color: statsPage.theme.textSecondary
                                    Layout.fillWidth: true
                                }

                                Text {
                                    text: "" + statsPage.statValue(
                                                   modelData.replace("mousepro.stats.", ""))
                                    font { family: uiState.fontFamily; pixelSize: 15; bold: true }
                                    color: statsPage.theme.textPrimary
                                }
                            }
                        }
                    }
                }
            }

            Item { width: 1; height: Theme.space16 }

            // ── Session note ─────────────────────────────────────
            Row {
                width: parent.width - 64
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 8

                AppIcon {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 16
                    height: 16
                    name: "info"
                    iconColor: statsPage.theme.textDim
                }

                Text {
                    width: parent.width - 24
                    anchors.verticalCenter: parent.verticalCenter
                    text: s["mousepro.stats.session_note"]
                    wrapMode: Text.WordWrap
                    font { family: uiState.fontFamily; pixelSize: 11 }
                    color: statsPage.theme.textDim
                }
            }

            Item { width: 1; height: Theme.space24 }
        }
    }

    Connections {
        target: backend
        function onUsageStatsChanged() {
            statsPage.statsTick += 1
        }
    }
}
