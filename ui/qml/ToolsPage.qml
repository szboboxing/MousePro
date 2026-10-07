import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "Theme.js" as Theme

/*  MousePro V1.0 — System Tools page.
    A card grid of Windows quick actions. Each card calls
    backend.runQuickAction(id); the {ok,title,detail} result drives the
    bottom result line and successes are mirrored to the Main toast.    */

Item {
    id: toolsPage

    signal toastRequested(string msg)

    readonly property var theme: Theme.palette(uiState.darkMode)
    property var s: lm.strings

    // 0 = idle hint, 1 = last action succeeded, 2 = last action failed
    property int resultState: 0
    property string resultText: ""

    Component.onCompleted: resultText = s["mousepro.tools.result_idle"]

    function runAction(actionId) {
        var result = backend.runQuickAction(actionId)
        if (!result)
            return
        if (result.ok) {
            resultState = 1
            resultText = result.title
            toastRequested(result.title)
        } else {
            resultState = 2
            resultText = result.title
                         + (result.detail ? " — " + result.detail : "")
        }
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
                        text: s["mousepro.tools.title"]
                        font { family: uiState.fontFamily; pixelSize: 24; bold: true }
                        color: toolsPage.theme.textPrimary
                    }

                    Text {
                        text: s["mousepro.tools.subtitle"]
                        font { family: uiState.fontFamily; pixelSize: 13 }
                        color: toolsPage.theme.textSecondary
                    }
                }
            }

            Rectangle {
                width: parent.width - 64
                height: 1
                color: toolsPage.theme.border
                anchors.horizontalCenter: parent.horizontalCenter
            }

            Item { width: 1; height: Theme.space20 }

            // ── Tool cards ───────────────────────────────────────
            Flow {
                width: parent.width - 64
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: Theme.space16

                Repeater {
                    model: [
                        { titleKey: "mousepro.tools.calculator", descKey: "",
                          action: "calculator", dual: false },
                        { titleKey: "mousepro.tools.browser",
                          descKey: "mousepro.tools.browser_desc",
                          action: "browser", dual: false },
                        { titleKey: "mousepro.tools.media_player", descKey: "",
                          action: "media_player", dual: false },
                        { titleKey: "mousepro.tools.pointer_size",
                          descKey: "mousepro.tools.pointer_size_note",
                          action: "pointer_size", dual: false },
                        { titleKey: "mousepro.tools.enhanced_paste", descKey: "",
                          action: "enhanced_paste", dual: false },
                        { titleKey: "mousepro.tools.brightness", descKey: "",
                          action: "", dual: true,
                          downAction: "brightness_down", upAction: "brightness_up" },
                        { titleKey: "mousepro.tools.contrast", descKey: "",
                          action: "", dual: true,
                          downAction: "contrast_down", upAction: "contrast_up" }
                    ]

                    delegate: Rectangle {
                        required property var modelData
                        width: 270
                        height: toolCardContent.implicitHeight + 32
                        radius: Theme.radius
                        color: toolsPage.theme.bgCard
                        border.width: 1
                        border.color: toolsPage.theme.border

                        Column {
                            id: toolCardContent
                            anchors {
                                left: parent.left
                                right: parent.right
                                top: parent.top
                                margins: Theme.space16
                            }
                            spacing: 10

                            Text {
                                width: parent.width
                                text: s[modelData.titleKey] || modelData.titleKey
                                wrapMode: Text.WordWrap
                                font { family: uiState.fontFamily; pixelSize: 15; bold: true }
                                color: toolsPage.theme.textPrimary
                            }

                            Text {
                                width: parent.width
                                visible: modelData.descKey !== ""
                                text: modelData.descKey ? (s[modelData.descKey] || "") : ""
                                wrapMode: Text.WordWrap
                                font { family: uiState.fontFamily; pixelSize: 11 }
                                color: toolsPage.theme.textSecondary
                            }

                            // Single-action card: one primary button
                            Rectangle {
                                visible: !modelData.dual
                                width: parent.width
                                height: 38
                                radius: Theme.radiusControl
                                color: toolPrimaryMouse.containsMouse
                                       ? toolsPage.theme.accentHover
                                       : toolsPage.theme.accent

                                Behavior on color { ColorAnimation { duration: 120 } }

                                Accessible.role: Accessible.Button
                                Accessible.name: s[modelData.titleKey] || modelData.titleKey
                                Accessible.description: modelData.descKey
                                                         ? (s[modelData.descKey] || "") : ""

                                Text {
                                    anchors.centerIn: parent
                                    text: s[modelData.titleKey] || modelData.titleKey
                                    font { family: uiState.fontFamily; pixelSize: 13; bold: true }
                                    color: toolsPage.theme.bgSidebar
                                }

                                MouseArea {
                                    id: toolPrimaryMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: toolsPage.runAction(modelData.action)
                                }
                            }

                            // Dual-action card: decrease / increase
                            Row {
                                visible: modelData.dual
                                width: parent.width
                                spacing: 8

                                Rectangle {
                                    width: (parent.width - 8) / 2
                                    height: 38
                                    radius: Theme.radiusControl
                                    color: toolDownMouse.containsMouse
                                           ? toolsPage.theme.bgCardHover
                                           : toolsPage.theme.bgSubtle
                                    border.width: 1
                                    border.color: toolsPage.theme.border

                                    Behavior on color { ColorAnimation { duration: 120 } }

                                    Accessible.role: Accessible.Button
                                    Accessible.name: (s["mousepro.tools.decrease"] || "") + " "
                                                     + (s[modelData.titleKey] || modelData.titleKey)

                                    Text {
                                        anchors.centerIn: parent
                                        text: "−"
                                        font { family: uiState.fontFamily; pixelSize: 17; bold: true }
                                        color: toolsPage.theme.textPrimary
                                    }

                                    MouseArea {
                                        id: toolDownMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: toolsPage.runAction(modelData.downAction)
                                    }
                                }

                                Rectangle {
                                    width: (parent.width - 8) / 2
                                    height: 38
                                    radius: Theme.radiusControl
                                    color: toolUpMouse.containsMouse
                                           ? toolsPage.theme.bgCardHover
                                           : toolsPage.theme.bgSubtle
                                    border.width: 1
                                    border.color: toolsPage.theme.border

                                    Behavior on color { ColorAnimation { duration: 120 } }

                                    Accessible.role: Accessible.Button
                                    Accessible.name: (s["mousepro.tools.increase"] || "") + " "
                                                     + (s[modelData.titleKey] || modelData.titleKey)

                                    Text {
                                        anchors.centerIn: parent
                                        text: "+"
                                        font { family: uiState.fontFamily; pixelSize: 17; bold: true }
                                        color: toolsPage.theme.textPrimary
                                    }

                                    MouseArea {
                                        id: toolUpMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: toolsPage.runAction(modelData.upAction)
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Item { width: 1; height: Theme.space16 }

            // ── Result line ──────────────────────────────────────
            Rectangle {
                width: parent.width - 64
                anchors.horizontalCenter: parent.horizontalCenter
                height: toolResultRow.implicitHeight + 28
                radius: Theme.radius
                color: toolsPage.theme.bgCard
                border.width: 1
                border.color: toolsPage.theme.border

                Row {
                    id: toolResultRow
                    anchors {
                        left: parent.left
                        right: parent.right
                        top: parent.top
                        margins: 14
                    }
                    spacing: 10

                    AppIcon {
                        anchors.verticalCenter: parent.verticalCenter
                        width: 18
                        height: 18
                        name: toolsPage.resultState === 2 ? "warning" : "info"
                        iconColor: toolsPage.resultState === 2
                                   ? toolsPage.theme.danger
                                   : toolsPage.resultState === 1
                                     ? toolsPage.theme.success
                                     : toolsPage.theme.textDim
                    }

                    Text {
                        width: parent.width - 28
                        anchors.verticalCenter: parent.verticalCenter
                        text: toolsPage.resultText
                        wrapMode: Text.WordWrap
                        font { family: uiState.fontFamily; pixelSize: 12 }
                        color: toolsPage.resultState === 2
                               ? toolsPage.theme.danger
                               : toolsPage.resultState === 1
                                 ? toolsPage.theme.success
                                 : toolsPage.theme.textDim
                    }
                }
            }

            Item { width: 1; height: Theme.space24 }
        }
    }
}
