import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "Theme.js" as Theme

/*  MousePro V1.0 — Right-button hold gesture page.
    Master switch, three gesture explanation cards, screenshot side-button
    picker. All state lives on backend; this page is presentation only.    */

Item {
    id: gesturePage

    signal toastRequested(string msg)

    readonly property var theme: Theme.palette(uiState.darkMode)
    property var s: lm.strings

    function sideSelected(name) {
        var buttons = backend.screenshotSideButtons
        for (var i = 0; i < buttons.length; i++) {
            if (buttons[i] === name)
                return true
        }
        return false
    }

    function toggleSideButton(name) {
        var buttons = backend.screenshotSideButtons
        var next = []
        var found = false
        for (var i = 0; i < buttons.length; i++) {
            if (buttons[i] === name) {
                found = true
                continue
            }
            next.push(buttons[i])
        }
        if (!found)
            next.push(name)
        backend.setScreenshotSideButtons(next)
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
                        text: s["mousepro.gesture.title"]
                        font {
                            family: uiState.fontFamily
                            pixelSize: 24
                            bold: true
                        }
                        color: gesturePage.theme.textPrimary
                    }

                    Text {
                        text: s["mousepro.gesture.subtitle"]
                        font {
                            family: uiState.fontFamily
                            pixelSize: 13
                        }
                        color: gesturePage.theme.textSecondary
                    }
                }
            }

            Rectangle {
                width: parent.width - 64
                height: 1
                color: gesturePage.theme.border
                anchors.horizontalCenter: parent.horizontalCenter
            }

            Item { width: 1; height: Theme.space20 }

            // ── Master switch ────────────────────────────────────
            Rectangle {
                width: parent.width - 64
                anchors.horizontalCenter: parent.horizontalCenter
                height: masterContent.implicitHeight + 32
                radius: Theme.radius
                color: gesturePage.theme.bgCard
                border.width: 1
                border.color: gesturePage.theme.border

                RowLayout {
                    id: masterContent
                    anchors {
                        left: parent.left
                        right: parent.right
                        top: parent.top
                        margins: Theme.space16
                    }
                    spacing: 12

                    Column {
                        Layout.fillWidth: true
                        spacing: 4

                        Text {
                            text: s["mousepro.gesture.master_switch"]
                            font {
                                family: uiState.fontFamily
                                pixelSize: 16
                                bold: true
                            }
                            color: gesturePage.theme.textPrimary
                        }

                        Text {
                            width: parent.width
                            text: s["mousepro.gesture.master_switch_desc"]
                            wrapMode: Text.WordWrap
                            font {
                                family: uiState.fontFamily
                                pixelSize: 12
                            }
                            color: gesturePage.theme.textSecondary
                        }
                    }

                    Switch {
                        id: gestureToggle
                        checked: backend.rightHoldGestureEnabled
                        focusPolicy: Qt.StrongFocus
                        Material.accent: gesturePage.theme.accent
                        Accessible.name: s["mousepro.gesture.master_switch"]
                        onClicked: backend.setRightHoldGestureEnabled(checked)
                    }
                }
            }

            Item { width: 1; height: Theme.space16 }

            // ── Gesture cards ────────────────────────────────────
            Rectangle {
                width: parent.width - 64
                anchors.horizontalCenter: parent.horizontalCenter
                height: gestureCopyCard.implicitHeight + 28
                radius: Theme.radius
                color: gesturePage.theme.bgCard
                border.width: 1
                border.color: gesturePage.theme.border

                Row {
                    id: gestureCopyCard
                    anchors {
                        left: parent.left
                        right: parent.right
                        top: parent.top
                        margins: 14
                    }
                    spacing: 12

                    Rectangle {
                        width: 40
                        height: 40
                        radius: Theme.radiusControl
                        color: gesturePage.theme.accentDim

                        AppIcon {
                            anchors.centerIn: parent
                            width: 20
                            height: 20
                            name: "gesture"
                            iconColor: gesturePage.theme.accent
                        }
                    }

                    Column {
                        width: parent.width - 52
                        spacing: 4

                        Text {
                            width: parent.width
                            text: s["mousepro.gesture.copy_title"]
                            wrapMode: Text.WordWrap
                            font { family: uiState.fontFamily; pixelSize: 14; bold: true }
                            color: gesturePage.theme.textPrimary
                        }

                        Text {
                            width: parent.width
                            text: s["mousepro.gesture.copy_detail"]
                            wrapMode: Text.WordWrap
                            font { family: uiState.fontFamily; pixelSize: 12 }
                            color: gesturePage.theme.textSecondary
                        }
                    }
                }
            }

            Item { width: 1; height: Theme.space12 }

            Rectangle {
                width: parent.width - 64
                anchors.horizontalCenter: parent.horizontalCenter
                height: gesturePasteCard.implicitHeight + 28
                radius: Theme.radius
                color: gesturePage.theme.bgCard
                border.width: 1
                border.color: gesturePage.theme.border

                Row {
                    id: gesturePasteCard
                    anchors {
                        left: parent.left
                        right: parent.right
                        top: parent.top
                        margins: 14
                    }
                    spacing: 12

                    Rectangle {
                        width: 40
                        height: 40
                        radius: Theme.radiusControl
                        color: gesturePage.theme.accentDim

                        AppIcon {
                            anchors.centerIn: parent
                            width: 20
                            height: 20
                            name: "plus"
                            iconColor: gesturePage.theme.accent
                        }
                    }

                    Column {
                        width: parent.width - 52
                        spacing: 4

                        Text {
                            width: parent.width
                            text: s["mousepro.gesture.paste_title"]
                            wrapMode: Text.WordWrap
                            font { family: uiState.fontFamily; pixelSize: 14; bold: true }
                            color: gesturePage.theme.textPrimary
                        }

                        Text {
                            width: parent.width
                            text: s["mousepro.gesture.paste_detail"]
                            wrapMode: Text.WordWrap
                            font { family: uiState.fontFamily; pixelSize: 12 }
                            color: gesturePage.theme.textSecondary
                        }
                    }
                }
            }

            Item { width: 1; height: Theme.space12 }

            Rectangle {
                width: parent.width - 64
                anchors.horizontalCenter: parent.horizontalCenter
                height: gestureShotCard.implicitHeight + 28
                radius: Theme.radius
                color: gesturePage.theme.bgCard
                border.width: 1
                border.color: gesturePage.theme.border

                Row {
                    id: gestureShotCard
                    anchors {
                        left: parent.left
                        right: parent.right
                        top: parent.top
                        margins: 14
                    }
                    spacing: 12

                    Rectangle {
                        width: 40
                        height: 40
                        radius: Theme.radiusControl
                        color: gesturePage.theme.accentDim

                        AppIcon {
                            anchors.centerIn: parent
                            width: 20
                            height: 20
                            name: "test"
                            iconColor: gesturePage.theme.accent
                        }
                    }

                    Column {
                        width: parent.width - 52
                        spacing: 4

                        Text {
                            width: parent.width
                            text: s["mousepro.gesture.shot_title"]
                            wrapMode: Text.WordWrap
                            font { family: uiState.fontFamily; pixelSize: 14; bold: true }
                            color: gesturePage.theme.textPrimary
                        }

                        Text {
                            width: parent.width
                            text: s["mousepro.gesture.shot_detail"]
                            wrapMode: Text.WordWrap
                            font { family: uiState.fontFamily; pixelSize: 12 }
                            color: gesturePage.theme.textSecondary
                        }
                    }
                }
            }

            Item { id: gestureRuleSpacer; width: 1; height: Theme.space12 }

            // ── Rules ────────────────────────────────────────────
            Column {
                width: parent.width - 64
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 6

                Repeater {
                    model: [
                        "mousepro.gesture.rule_single",
                        "mousepro.gesture.rule_menu"
                    ]

                    delegate: Text {
                        required property var modelData
                        width: parent.width
                        text: "• " + (s[modelData] || modelData)
                        wrapMode: Text.WordWrap
                        font {
                            family: uiState.fontFamily
                            pixelSize: 12
                        }
                        color: gesturePage.theme.textDim
                    }
                }
            }

            Item { width: 1; height: Theme.space16 }

            // ── Screenshot side buttons ──────────────────────────
            Rectangle {
                width: parent.width - 64
                anchors.horizontalCenter: parent.horizontalCenter
                height: sideContent.implicitHeight + 32
                radius: Theme.radius
                color: gesturePage.theme.bgCard
                border.width: 1
                border.color: gesturePage.theme.border

                Column {
                    id: sideContent
                    anchors {
                        left: parent.left
                        right: parent.right
                        top: parent.top
                        margins: Theme.space16
                    }
                    spacing: 12

                    Text {
                        text: s["mousepro.gesture.side_title"]
                        font {
                            family: uiState.fontFamily
                            pixelSize: 16
                            bold: true
                        }
                        color: gesturePage.theme.textPrimary
                    }

                    Text {
                        width: parent.width
                        text: s["mousepro.screenshot_side_buttons.desc"]
                        wrapMode: Text.WordWrap
                        font {
                            family: uiState.fontFamily
                            pixelSize: 12
                        }
                        color: gesturePage.theme.textSecondary
                    }

                    Row {
                        spacing: 10

                        Repeater {
                            model: [
                                { name: "xbutton1", labelKey: "mousepro.gesture.side_x1" },
                                { name: "xbutton2", labelKey: "mousepro.gesture.side_x2" }
                            ]

                            delegate: Rectangle {
                                required property var modelData
                                width: sideChipText.implicitWidth + 44
                                height: 38
                                radius: Theme.radiusControl
                                color: gesturePage.sideSelected(modelData.name)
                                       ? gesturePage.theme.accent
                                       : sideChipMouse.containsMouse
                                         ? gesturePage.theme.bgCardHover
                                         : gesturePage.theme.bgSubtle
                                border.width: 1
                                border.color: gesturePage.sideSelected(modelData.name)
                                              ? gesturePage.theme.accent
                                              : gesturePage.theme.border

                                Behavior on color { ColorAnimation { duration: 120 } }

                                Accessible.role: Accessible.CheckBox
                                Accessible.name: s[modelData.labelKey] || modelData.labelKey
                                Accessible.checkable: true
                                Accessible.checked: gesturePage.sideSelected(modelData.name)

                                Row {
                                    anchors.centerIn: parent
                                    spacing: 6

                                    Text {
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: "✓"
                                        font {
                                            family: uiState.fontFamily
                                            pixelSize: 13
                                            bold: true
                                        }
                                        color: gesturePage.theme.bgSidebar
                                        opacity: gesturePage.sideSelected(modelData.name) ? 1 : 0
                                    }

                                    Text {
                                        id: sideChipText
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: s[modelData.labelKey] || modelData.labelKey
                                        font {
                                            family: uiState.fontFamily
                                            pixelSize: 12
                                            bold: gesturePage.sideSelected(modelData.name)
                                        }
                                        color: gesturePage.sideSelected(modelData.name)
                                               ? gesturePage.theme.bgSidebar
                                               : gesturePage.theme.textPrimary
                                    }
                                }

                                MouseArea {
                                    id: sideChipMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: gesturePage.toggleSideButton(modelData.name)
                                }
                            }
                        }
                    }

                    Text {
                        width: parent.width
                        text: s["mousepro.gesture.side_hint"]
                        wrapMode: Text.WordWrap
                        font {
                            family: uiState.fontFamily
                            pixelSize: 11
                        }
                        color: gesturePage.theme.textDim
                    }
                }
            }

            Item { width: 1; height: Theme.space24 }
        }
    }
}
