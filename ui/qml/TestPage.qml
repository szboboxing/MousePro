import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "Theme.js" as Theme

/*  MousePro V1.0 — Mouse button test page.
    Big start/stop switch, 7 live control indicators with per-control
    event counts, and the side-button re-confirmation flow.              */

Item {
    id: testPage

    signal toastRequested(string msg)

    readonly property var theme: Theme.palette(uiState.darkMode)
    property var s: lm.strings

    // Transient press highlights for the seven tracked controls.
    property bool litLeft: false
    property bool litRight: false
    property bool litMiddle: false
    property bool litX1: false
    property bool litX2: false
    property bool litWheelUp: false
    property bool litWheelDown: false

    // Candidate side buttons during the confirm flow.
    property var chosenButtons: []

    function chosenContains(name) {
        for (var i = 0; i < chosenButtons.length; i++) {
            if (chosenButtons[i] === name)
                return true
        }
        return false
    }

    function toggleChosen(name) {
        var next = []
        var found = false
        for (var i = 0; i < chosenButtons.length; i++) {
            if (chosenButtons[i] === name) {
                found = true
                continue
            }
            next.push(chosenButtons[i])
        }
        if (!found)
            next.push(name)
        chosenButtons = next
    }

    function startConfirm() {
        backend.startSideButtonConfirm()
        chosenButtons = backend.screenshotSideButtons.slice(0)
    }

    function saveConfirm() {
        backend.saveConfirmedSideButtons(testPage.chosenButtons)
        toastRequested(s["mousepro.test.side_saved"])
    }

    function cancelConfirm() {
        backend.cancelSideButtonConfirm()
    }

    function clearLights() {
        litLeft = false
        litRight = false
        litMiddle = false
        litX1 = false
        litX2 = false
        litWheelUp = false
        litWheelDown = false
    }

    function handleTestEvent(ev) {
        if (!ev || !ev.control) {
            // Empty payload = reset / clear.
            clearLights()
            return
        }
        var pressed = ev.pressed
        switch (ev.control) {
        case "left":
            litLeft = pressed === true
            break
        case "right":
            litRight = pressed === true
            break
        case "middle":
            litMiddle = pressed === true
            break
        case "xbutton1":
            litX1 = pressed === true
            break
        case "xbutton2":
            litX2 = pressed === true
            break
        case "wheel_up":
            litWheelUp = true
            wheelLightTimer.restart()
            break
        case "wheel_down":
            litWheelDown = true
            wheelLightTimer.restart()
            break
        }
        if (backend.sideButtonConfirmActive
                && pressed === true
                && (ev.control === "xbutton1" || ev.control === "xbutton2")) {
            toggleChosen(ev.control)
        }
    }

    Timer {
        id: wheelLightTimer
        interval: 280
        onTriggered: {
            litWheelUp = false
            litWheelDown = false
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
                        text: s["mousepro.test.title"]
                        font { family: uiState.fontFamily; pixelSize: 24; bold: true }
                        color: testPage.theme.textPrimary
                    }

                    Text {
                        text: s["mousepro.test.subtitle"]
                        font { family: uiState.fontFamily; pixelSize: 13 }
                        color: testPage.theme.textSecondary
                    }
                }
            }

            Rectangle {
                width: parent.width - 64
                height: 1
                color: testPage.theme.border
                anchors.horizontalCenter: parent.horizontalCenter
            }

            Item { width: 1; height: Theme.space20 }

            // ── Test switch ──────────────────────────────────────
            Rectangle {
                width: parent.width - 64
                anchors.horizontalCenter: parent.horizontalCenter
                height: testSwitchContent.implicitHeight + 32
                radius: Theme.radius
                color: testPage.theme.bgCard
                border.width: 1
                border.color: testPage.theme.border

                Column {
                    id: testSwitchContent
                    anchors {
                        left: parent.left
                        right: parent.right
                        top: parent.top
                        margins: Theme.space16
                    }
                    spacing: 12

                    RowLayout {
                        width: parent.width
                        spacing: 12

                        Column {
                            Layout.fillWidth: true
                            spacing: 4

                            Text {
                                text: backend.buttonTestActive
                                      ? s["mousepro.button_test.stop"]
                                      : s["mousepro.button_test.start"]
                                font { family: uiState.fontFamily; pixelSize: 16; bold: true }
                                color: testPage.theme.textPrimary
                            }

                            Text {
                                width: parent.width
                                text: s["mousepro.test.passthrough_hint"]
                                wrapMode: Text.WordWrap
                                font { family: uiState.fontFamily; pixelSize: 12 }
                                color: testPage.theme.textSecondary
                            }
                        }

                        Switch {
                            id: testToggle
                            checked: backend.buttonTestActive
                            focusPolicy: Qt.StrongFocus
                            Material.accent: testPage.theme.accent
                            Accessible.name: backend.buttonTestActive
                                            ? s["mousepro.button_test.stop"]
                                            : s["mousepro.button_test.start"]
                            onClicked: backend.setButtonTestActive(checked)
                        }
                    }

                    Row {
                        spacing: 8
                        visible: backend.buttonTestActive

                        Rectangle {
                            width: 8
                            height: 8
                            radius: 4
                            color: testPage.theme.success
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Text {
                            text: s["mousepro.button_test.waiting"]
                            font { family: uiState.fontFamily; pixelSize: 12 }
                            color: testPage.theme.success
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                }
            }

            Item { width: 1; height: Theme.space16 }

            // ── Control indicators + counts ──────────────────────
            Rectangle {
                width: parent.width - 64
                anchors.horizontalCenter: parent.horizontalCenter
                height: testCountsContent.implicitHeight + 32
                radius: Theme.radius
                color: testPage.theme.bgCard
                border.width: 1
                border.color: testPage.theme.border

                Column {
                    id: testCountsContent
                    anchors {
                        left: parent.left
                        right: parent.right
                        top: parent.top
                        margins: Theme.space16
                    }
                    spacing: 12

                    RowLayout {
                        width: parent.width

                        Text {
                            text: s["mousepro.test.counts_title"]
                            font { family: uiState.fontFamily; pixelSize: 16; bold: true }
                            color: testPage.theme.textPrimary
                            Layout.fillWidth: true
                        }

                        Rectangle {
                            Layout.preferredWidth: Math.max(
                                104, testResetText.implicitWidth + 24)
                            Layout.preferredHeight: 34
                            radius: Theme.radiusSmall
                            color: testResetMouse.containsMouse
                                   ? testPage.theme.bgCardHover
                                   : testPage.theme.bgSubtle
                            border.width: 1
                            border.color: testPage.theme.border

                            Behavior on color { ColorAnimation { duration: 120 } }

                            Accessible.role: Accessible.Button
                            Accessible.name: s["mousepro.test.counts_reset"]

                            Text {
                                id: testResetText
                                anchors.centerIn: parent
                                text: s["mousepro.test.counts_reset"]
                                font { family: uiState.fontFamily; pixelSize: 12 }
                                color: testPage.theme.textPrimary
                            }

                            MouseArea {
                                id: testResetMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: backend.resetTestCounts()
                            }
                        }
                    }

                    GridLayout {
                        width: parent.width
                        columns: 4
                        rowSpacing: 10
                        columnSpacing: 10

                        // Reusable-looking tile, repeated per control.
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 64
                            radius: Theme.radiusControl
                            color: testPage.litLeft
                                   ? testPage.theme.accentDim
                                   : testPage.theme.bgSubtle
                            border.width: testPage.litLeft ? 2 : 1
                            border.color: testPage.litLeft
                                          ? testPage.theme.accent
                                          : testPage.theme.border

                            Behavior on color { ColorAnimation { duration: 120 } }
                            Behavior on border.color { ColorAnimation { duration: 120 } }

                            Column {
                                anchors.centerIn: parent
                                spacing: 2

                                Text {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: s["mousepro.test.left"]
                                    font { family: uiState.fontFamily; pixelSize: 11 }
                                    color: testPage.theme.textDim
                                }

                                Text {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: "" + (backend.testCounts["left"] || 0)
                                    font { family: uiState.fontFamily; pixelSize: 20; bold: true }
                                    color: testPage.litLeft
                                           ? testPage.theme.accent
                                           : testPage.theme.textPrimary
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 64
                            radius: Theme.radiusControl
                            color: testPage.litRight
                                   ? testPage.theme.accentDim
                                   : testPage.theme.bgSubtle
                            border.width: testPage.litRight ? 2 : 1
                            border.color: testPage.litRight
                                          ? testPage.theme.accent
                                          : testPage.theme.border

                            Behavior on color { ColorAnimation { duration: 120 } }
                            Behavior on border.color { ColorAnimation { duration: 120 } }

                            Column {
                                anchors.centerIn: parent
                                spacing: 2

                                Text {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: s["mousepro.test.right"]
                                    font { family: uiState.fontFamily; pixelSize: 11 }
                                    color: testPage.theme.textDim
                                }

                                Text {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: "" + (backend.testCounts["right"] || 0)
                                    font { family: uiState.fontFamily; pixelSize: 20; bold: true }
                                    color: testPage.litRight
                                           ? testPage.theme.accent
                                           : testPage.theme.textPrimary
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 64
                            radius: Theme.radiusControl
                            color: testPage.litMiddle
                                   ? testPage.theme.accentDim
                                   : testPage.theme.bgSubtle
                            border.width: testPage.litMiddle ? 2 : 1
                            border.color: testPage.litMiddle
                                          ? testPage.theme.accent
                                          : testPage.theme.border

                            Behavior on color { ColorAnimation { duration: 120 } }
                            Behavior on border.color { ColorAnimation { duration: 120 } }

                            Column {
                                anchors.centerIn: parent
                                spacing: 2

                                Text {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: s["mousepro.test.middle"]
                                    font { family: uiState.fontFamily; pixelSize: 11 }
                                    color: testPage.theme.textDim
                                }

                                Text {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: "" + (backend.testCounts["middle"] || 0)
                                    font { family: uiState.fontFamily; pixelSize: 20; bold: true }
                                    color: testPage.litMiddle
                                           ? testPage.theme.accent
                                           : testPage.theme.textPrimary
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 64
                            radius: Theme.radiusControl
                            color: testPage.litX1
                                   ? testPage.theme.accentDim
                                   : testPage.theme.bgSubtle
                            border.width: testPage.litX1 ? 2 : 1
                            border.color: testPage.litX1
                                          ? testPage.theme.accent
                                          : testPage.theme.border

                            Behavior on color { ColorAnimation { duration: 120 } }
                            Behavior on border.color { ColorAnimation { duration: 120 } }

                            Column {
                                anchors.centerIn: parent
                                spacing: 2

                                Text {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: s["mousepro.test.x1"]
                                    font { family: uiState.fontFamily; pixelSize: 11 }
                                    color: testPage.theme.textDim
                                }

                                Text {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: "" + (backend.testCounts["xbutton1"] || 0)
                                    font { family: uiState.fontFamily; pixelSize: 20; bold: true }
                                    color: testPage.litX1
                                           ? testPage.theme.accent
                                           : testPage.theme.textPrimary
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 64
                            radius: Theme.radiusControl
                            color: testPage.litX2
                                   ? testPage.theme.accentDim
                                   : testPage.theme.bgSubtle
                            border.width: testPage.litX2 ? 2 : 1
                            border.color: testPage.litX2
                                          ? testPage.theme.accent
                                          : testPage.theme.border

                            Behavior on color { ColorAnimation { duration: 120 } }
                            Behavior on border.color { ColorAnimation { duration: 120 } }

                            Column {
                                anchors.centerIn: parent
                                spacing: 2

                                Text {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: s["mousepro.test.x2"]
                                    font { family: uiState.fontFamily; pixelSize: 11 }
                                    color: testPage.theme.textDim
                                }

                                Text {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: "" + (backend.testCounts["xbutton2"] || 0)
                                    font { family: uiState.fontFamily; pixelSize: 20; bold: true }
                                    color: testPage.litX2
                                           ? testPage.theme.accent
                                           : testPage.theme.textPrimary
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 64
                            radius: Theme.radiusControl
                            color: testPage.litWheelUp
                                   ? testPage.theme.accentDim
                                   : testPage.theme.bgSubtle
                            border.width: testPage.litWheelUp ? 2 : 1
                            border.color: testPage.litWheelUp
                                          ? testPage.theme.accent
                                          : testPage.theme.border

                            Behavior on color { ColorAnimation { duration: 120 } }
                            Behavior on border.color { ColorAnimation { duration: 120 } }

                            Column {
                                anchors.centerIn: parent
                                spacing: 2

                                Text {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: s["mousepro.test.wheel_up"]
                                    font { family: uiState.fontFamily; pixelSize: 11 }
                                    color: testPage.theme.textDim
                                }

                                Text {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: "" + (backend.testCounts["wheel_up"] || 0)
                                    font { family: uiState.fontFamily; pixelSize: 20; bold: true }
                                    color: testPage.litWheelUp
                                           ? testPage.theme.accent
                                           : testPage.theme.textPrimary
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 64
                            radius: Theme.radiusControl
                            color: testPage.litWheelDown
                                   ? testPage.theme.accentDim
                                   : testPage.theme.bgSubtle
                            border.width: testPage.litWheelDown ? 2 : 1
                            border.color: testPage.litWheelDown
                                          ? testPage.theme.accent
                                          : testPage.theme.border

                            Behavior on color { ColorAnimation { duration: 120 } }
                            Behavior on border.color { ColorAnimation { duration: 120 } }

                            Column {
                                anchors.centerIn: parent
                                spacing: 2

                                Text {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: s["mousepro.test.wheel_down"]
                                    font { family: uiState.fontFamily; pixelSize: 11 }
                                    color: testPage.theme.textDim
                                }

                                Text {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: "" + (backend.testCounts["wheel_down"] || 0)
                                    font { family: uiState.fontFamily; pixelSize: 20; bold: true }
                                    color: testPage.litWheelDown
                                           ? testPage.theme.accent
                                           : testPage.theme.textPrimary
                                }
                            }
                        }
                    }
                }
            }

            Item { width: 1; height: Theme.space16 }

            // ── Side button re-confirmation ──────────────────────
            Rectangle {
                width: parent.width - 64
                anchors.horizontalCenter: parent.horizontalCenter
                height: sideConfirmContent.implicitHeight + 32
                radius: Theme.radius
                color: testPage.theme.bgCard
                border.width: 1
                border.color: testPage.theme.border

                Column {
                    id: sideConfirmContent
                    anchors {
                        left: parent.left
                        right: parent.right
                        top: parent.top
                        margins: Theme.space16
                    }
                    spacing: 12

                    Text {
                        text: s["mousepro.test.side_section"]
                        font { family: uiState.fontFamily; pixelSize: 16; bold: true }
                        color: testPage.theme.textPrimary
                    }

                    Text {
                        width: parent.width
                        text: s["mousepro.test.side_desc"]
                        wrapMode: Text.WordWrap
                        font { family: uiState.fontFamily; pixelSize: 12 }
                        color: testPage.theme.textSecondary
                    }

                    // Idle: launch the confirm flow
                    Rectangle {
                        visible: !backend.sideButtonConfirmActive
                        width: Math.max(150, sideStartText.implicitWidth + 32)
                        height: 38
                        radius: Theme.radiusControl
                        color: sideStartMouse.containsMouse
                               ? testPage.theme.accentHover
                               : testPage.theme.accent

                        Behavior on color { ColorAnimation { duration: 120 } }

                        Accessible.role: Accessible.Button
                        Accessible.name: s["mousepro.test.side_start"]

                        Text {
                            id: sideStartText
                            anchors.centerIn: parent
                            text: s["mousepro.test.side_start"]
                            font { family: uiState.fontFamily; pixelSize: 13; bold: true }
                            color: testPage.theme.bgSidebar
                        }

                        MouseArea {
                            id: sideStartMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: testPage.startConfirm()
                        }
                    }

                    // Active: live candidates + save/cancel
                    Column {
                        width: parent.width
                        visible: backend.sideButtonConfirmActive
                        spacing: 12

                        Rectangle {
                            width: parent.width
                            height: 44
                            radius: Theme.radiusControl
                            color: testPage.theme.accentDim

                            Row {
                                anchors {
                                    left: parent.left
                                    right: parent.right
                                    top: parent.top
                                    bottom: parent.bottom
                                    leftMargin: 12
                                    rightMargin: 12
                                }
                                spacing: 8

                                Rectangle {
                                    width: 8
                                    height: 8
                                    radius: 4
                                    color: testPage.theme.accent
                                    anchors.verticalCenter: parent.verticalCenter
                                }

                                Text {
                                    width: parent.width - 16
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: s["mousepro.test.side_instruction"]
                                    wrapMode: Text.WordWrap
                                    font { family: uiState.fontFamily; pixelSize: 12 }
                                    color: testPage.theme.textPrimary
                                }
                            }
                        }

                        Row {
                            spacing: 10

                            Repeater {
                                model: [
                                    { name: "xbutton1", labelKey: "mousepro.test.x1" },
                                    { name: "xbutton2", labelKey: "mousepro.test.x2" }
                                ]

                                delegate: Rectangle {
                                    required property var modelData
                                    width: confirmChipText.implicitWidth + 44
                                    height: 38
                                    radius: Theme.radiusControl
                                    color: testPage.chosenContains(modelData.name)
                                           ? testPage.theme.accent
                                           : confirmChipMouse.containsMouse
                                             ? testPage.theme.bgCardHover
                                             : testPage.theme.bgSubtle
                                    border.width: 1
                                    border.color: testPage.chosenContains(modelData.name)
                                              ? testPage.theme.accent
                                              : testPage.theme.border

                                    Behavior on color { ColorAnimation { duration: 120 } }

                                    Accessible.role: Accessible.CheckBox
                                    Accessible.name: s[modelData.labelKey] || modelData.labelKey
                                    Accessible.checkable: true
                                    Accessible.checked: testPage.chosenContains(modelData.name)

                                    Row {
                                        anchors.centerIn: parent
                                        spacing: 6

                                        Text {
                                            anchors.verticalCenter: parent.verticalCenter
                                            text: "✓"
                                            font { family: uiState.fontFamily; pixelSize: 13; bold: true }
                                            color: testPage.theme.bgSidebar
                                            opacity: testPage.chosenContains(modelData.name) ? 1 : 0
                                        }

                                        Text {
                                            id: confirmChipText
                                            anchors.verticalCenter: parent.verticalCenter
                                            text: s[modelData.labelKey] || modelData.labelKey
                                            font {
                                                family: uiState.fontFamily
                                                pixelSize: 12
                                                bold: testPage.chosenContains(modelData.name)
                                            }
                                            color: testPage.chosenContains(modelData.name)
                                                   ? testPage.theme.bgSidebar
                                                   : testPage.theme.textPrimary
                                        }
                                    }

                                    MouseArea {
                                        id: confirmChipMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: testPage.toggleChosen(modelData.name)
                                    }
                                }
                            }
                        }

                        Row {
                            spacing: 10

                            Rectangle {
                                width: Math.max(96, sideSaveText.implicitWidth + 28)
                                height: 38
                                radius: Theme.radiusControl
                                color: sideSaveMouse.containsMouse
                                       ? testPage.theme.accentHover
                                       : testPage.theme.accent

                                Behavior on color { ColorAnimation { duration: 120 } }

                                Accessible.role: Accessible.Button
                                Accessible.name: s["mousepro.test.save"]

                                Text {
                                    id: sideSaveText
                                    anchors.centerIn: parent
                                    text: s["mousepro.test.save"]
                                    font { family: uiState.fontFamily; pixelSize: 13; bold: true }
                                    color: testPage.theme.bgSidebar
                                }

                                MouseArea {
                                    id: sideSaveMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: testPage.saveConfirm()
                                }
                            }

                            Rectangle {
                                width: Math.max(96, sideCancelText.implicitWidth + 28)
                                height: 38
                                radius: Theme.radiusControl
                                color: sideCancelMouse.containsMouse
                                       ? testPage.theme.bgCardHover
                                       : testPage.theme.bgSubtle
                                border.width: 1
                                border.color: testPage.theme.border

                                Behavior on color { ColorAnimation { duration: 120 } }

                                Accessible.role: Accessible.Button
                                Accessible.name: s["mousepro.test.cancel"]

                                Text {
                                    id: sideCancelText
                                    anchors.centerIn: parent
                                    text: s["mousepro.test.cancel"]
                                    font { family: uiState.fontFamily; pixelSize: 13 }
                                    color: testPage.theme.textPrimary
                                }

                                MouseArea {
                                    id: sideCancelMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: testPage.cancelConfirm()
                                }
                            }
                        }
                    }
                }
            }

            Item { width: 1; height: Theme.space24 }
        }
    }

    Connections {
        target: backend
        function onTestEventOccurred(event) {
            testPage.handleTestEvent(event)
        }
        function onSideButtonConfirmChanged() {
            if (!backend.sideButtonConfirmActive)
                testPage.chosenButtons = []
        }
    }
}
