import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "Theme.js" as Theme

ApplicationWindow {
    id: root
    visible: !launchHidden
    width: 1060
    height: 700
    minimumWidth: 920
    minimumHeight: 620
    readonly property string versionLabel: "v" + appVersion
    title: backend.mouseConnected
           ? appName + " " + versionLabel + " - " + backend.deviceDisplayName
           : appName + " " + versionLabel

    property string appearanceMode: uiState.appearanceMode
    readonly property bool darkMode: appearanceMode === "dark"
                                    || (appearanceMode === "system"
                                        && uiState.systemDarkMode)
    readonly property var theme: Theme.palette(darkMode)
    property var s: lm.strings
    readonly property string displayBuildMode: appBuildMode === "Packaged app"
                                                ? (s["about.build_mode.packaged"] || appBuildMode)
                                                : (appBuildMode === "Source checkout"
                                                   ? (s["about.build_mode.source"] || appBuildMode)
                                                   : appBuildMode)
    property int currentPage: 0
    property Item hoveredNavItem: null
    property string hoveredNavText: ""
    property string hoveredNavTipKey: ""
    property real hoveredNavCenterX: 0
    property real hoveredNavCenterY: 0
    readonly property bool shortcutsBlocked: aboutDialog.visible
                                            || mousePageView.hasBlockingDialog

    function openPage(page) {
        if (root.currentPage === page)
            return
        root.currentPage = page
        root.contentItem.forceActiveFocus(Qt.OtherFocusReason)
    }

    function showToast(msg) {
        toast.show(msg)
    }

    color: theme.bg

    Material.theme: darkMode ? Material.Dark : Material.Light
    Material.accent: theme.accent
    Material.background: theme.bg
    Material.foreground: theme.textPrimary

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            id: sidebar
            Layout.preferredWidth: 76
            Layout.fillHeight: true
            color: root.theme.bgSidebar

            Item {
                anchors {
                    fill: parent
                    topMargin: 20
                    bottomMargin: 16
                }

                Column {
                    anchors {
                        top: parent.top
                        left: parent.left
                        right: parent.right
                    }
                    spacing: Theme.space8

                    Item {
                        width: 44
                        height: 44
                        anchors.horizontalCenter: parent.horizontalCenter

                        Accessible.role: Accessible.StaticText
                        Accessible.name: appName
                        Accessible.description: root.versionLabel

                        Image {
                            anchors.fill: parent
                            source: "../../images/logo_icon.png"
                            sourceSize.width: 128
                            sourceSize.height: 128
                            fillMode: Image.PreserveAspectFit
                            smooth: true
                            mipmap: true
                        }
                    }

                    Item { width: 1; height: 16 }

                    Repeater {
                        model: {
                            var pages = [
                                { icon: "mouse-simple", tipKey: "nav.mouse_profiles", page: 0 },
                                { icon: "sliders-horizontal", tipKey: "nav.point_scroll", page: 1 },
                                { icon: "book-open", tipKey: "nav.reading", page: 2 }
                            ]
                            if (backend.enhancementsSupported) {
                                pages.push({ icon: "gesture", tipKey: "nav.mousepro_gesture", page: 3 })
                                pages.push({ icon: "tools", tipKey: "nav.mousepro_tools", page: 4 })
                                pages.push({ icon: "test", tipKey: "nav.mousepro_test", page: 5 })
                                pages.push({ icon: "stats", tipKey: "nav.mousepro_stats", page: 6 })
                            }
                            return pages
                        }

                        delegate: FocusScope {
                            id: navItem
                            width: sidebar.width
                            height: 48
                            activeFocusOnTab: true

                            Accessible.role: Accessible.Button
                            Accessible.name: lm.strings[modelData.tipKey] || modelData.tipKey
                            Accessible.description: (lm.strings["nav.open_page"] || "Open %1")
                                                    .replace("%1", lm.strings[modelData.tipKey] || modelData.tipKey)

                            Keys.onReturnPressed: root.openPage(modelData.page)
                            Keys.onEnterPressed: root.openPage(modelData.page)
                            Keys.onSpacePressed: root.openPage(modelData.page)

                            Rectangle {
                                anchors.centerIn: parent
                                width: 44
                                height: 40
                                radius: Theme.radiusControl
                                color: root.currentPage === modelData.page
                                       ? root.theme.accentDim
                                       : navMouse.containsMouse || navItem.activeFocus
                                         ? root.theme.bgCardHover
                                         : "transparent"

                                border.width: navItem.activeFocus ? 1 : 0
                                border.color: root.theme.accent

                                Behavior on color { ColorAnimation { duration: 150 } }

                                AppIcon {
                                    anchors.centerIn: parent
                                    width: 20
                                    height: 20
                                    name: modelData.icon
                                    iconColor: root.currentPage === modelData.page
                                               ? root.theme.accent
                                               : navMouse.containsMouse || navItem.activeFocus
                                                 ? root.theme.textPrimary
                                                 : root.theme.textSecondary
                                }
                            }

                            Rectangle {
                                width: 3
                                height: 22
                                radius: 2
                                color: root.theme.accent
                                anchors {
                                    left: parent.left
                                    verticalCenter: parent.verticalCenter
                                }
                                visible: false
                            }

                            MouseArea {
                                id: navMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.openPage(modelData.page)
                                onContainsMouseChanged: {
                                    if (containsMouse) {
                                        var p = navItem.mapToItem(overlayLayer, navItem.width, navItem.height / 2)
                                        root.hoveredNavItem = navItem
                                        root.hoveredNavTipKey = modelData.tipKey
                                        root.hoveredNavText = lm.strings[modelData.tipKey] || modelData.tipKey
                                        root.hoveredNavCenterX = p.x
                                        root.hoveredNavCenterY = p.y
                                    } else if (root.hoveredNavItem === navItem) {
                                        root.hoveredNavItem = null
                                        root.hoveredNavTipKey = ""
                                        root.hoveredNavText = ""
                                    }
                                }
                            }
                        }
                    }
                }

                FocusScope {
                    id: aboutButton
                    anchors {
                        bottom: parent.bottom
                        horizontalCenter: parent.horizontalCenter
                    }
                    width: sidebar.width
                    height: 48
                    activeFocusOnTab: true

                    Accessible.role: Accessible.Button
                    Accessible.name: lm.strings["nav.about"] || "About"
                    Accessible.description: (lm.strings["nav.open_page"] || "Open %1")
                                            .replace("%1", lm.strings["nav.about"] || "About")

                    Keys.onReturnPressed: aboutDialog.open()
                    Keys.onEnterPressed: aboutDialog.open()
                    Keys.onSpacePressed: aboutDialog.open()

                    Rectangle {
                        anchors.centerIn: parent
                        width: 44
                        height: 40
                        radius: Theme.radiusControl
                        color: aboutMouse.containsMouse || aboutButton.activeFocus || aboutDialog.visible
                               ? root.theme.bgCardHover
                               : "transparent"

                        border.width: aboutButton.activeFocus ? 1 : 0
                        border.color: root.theme.accent

                        Behavior on color { ColorAnimation { duration: 150 } }

                        AppIcon {
                            anchors.centerIn: parent
                            width: 18
                            height: 18
                            name: "info"
                            iconColor: aboutMouse.containsMouse || aboutButton.activeFocus || aboutDialog.visible
                                       ? root.theme.textPrimary
                                       : root.theme.textSecondary
                        }
                    }

                    MouseArea {
                        id: aboutMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: aboutDialog.open()
                        onContainsMouseChanged: {
                            if (containsMouse) {
                                var p = aboutButton.mapToItem(overlayLayer, aboutButton.width, aboutButton.height / 2)
                                root.hoveredNavItem = aboutButton
                                root.hoveredNavTipKey = "nav.about"
                                root.hoveredNavText = lm.strings["nav.about"] || "About"
                                root.hoveredNavCenterX = p.x
                                root.hoveredNavCenterY = p.y
                            } else if (root.hoveredNavItem === aboutButton) {
                                root.hoveredNavItem = null
                                root.hoveredNavTipKey = ""
                                root.hoveredNavText = ""
                            }
                        }
                    }
                }
            }
        }

        StackLayout {
            id: contentStack
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: root.currentPage

            MousePage {
                id: mousePageView
            }
            Loader {
                active: root.currentPage === 1 || item
                source: "ScrollPage.qml"
            }
            ReadingPage {
                controller: reader
                theme: root.theme
            }
            Loader {
                id: gesturePageLoader
                active: backend.enhancementsSupported
                        && (root.currentPage === 3 || item)
                source: "GesturePage.qml"
                onItemChanged: if (item) item.toastRequested.connect(root.showToast)
            }
            Loader {
                id: toolsPageLoader
                active: backend.enhancementsSupported
                        && (root.currentPage === 4 || item)
                source: "ToolsPage.qml"
                onItemChanged: if (item) item.toastRequested.connect(root.showToast)
            }
            Loader {
                id: testPageLoader
                active: backend.enhancementsSupported
                        && (root.currentPage === 5 || item)
                source: "TestPage.qml"
                onItemChanged: if (item) item.toastRequested.connect(root.showToast)
            }
            Loader {
                id: statsPageLoader
                active: backend.enhancementsSupported
                        && (root.currentPage === 6 || item)
                source: "StatsPage.qml"
                onItemChanged: if (item) item.toastRequested.connect(root.showToast)
            }
        }
    }

    ReadingPanel { controller: reader }

    Item {
        id: overlayLayer
        anchors.fill: parent
        z: 999

        Rectangle {
            id: navTooltip
            x: root.hoveredNavCenterX + 10
            y: Math.max(8, Math.min(root.height - height - 8, root.hoveredNavCenterY - height / 2))
            visible: root.hoveredNavItem !== null
            opacity: visible ? 1 : 0
            radius: Theme.radiusSmall
            color: root.theme.tooltipBg
            border.width: 1
            border.color: Qt.rgba(1, 1, 1, root.darkMode ? 0.06 : 0.12)
            width: navTooltipText.implicitWidth + 20
            height: navTooltipText.implicitHeight + 12

            Behavior on opacity { NumberAnimation { duration: 120 } }

            Text {
                id: navTooltipText
                anchors.centerIn: parent
                text: root.hoveredNavTipKey
                      ? (lm.strings[root.hoveredNavTipKey] || root.hoveredNavTipKey)
                      : root.hoveredNavText
                font {
                    family: uiState.fontFamily
                    pixelSize: 12
                }
                color: root.theme.tooltipText
            }
        }
    }

    Dialog {
        id: aboutDialog
        parent: Overlay.overlay
        modal: true
        focus: true
        title: ""
        width: 500
        height: 560
        x: Math.round((parent.width - width) / 2)
        y: Math.round((parent.height - height) / 2)
        padding: 0

        background: Rectangle {
            radius: 24
            color: theme.bgElevated
            border.width: 1
            border.color: theme.border
        }

        contentItem: Item {
            width: aboutDialog.width
            height: aboutDialog.height

            Item {
                id: aboutHeader
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.topMargin: 16
                anchors.leftMargin: 24
                anchors.rightMargin: 24
                height: 44

                Row {
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 12

                    Item {
                        width: 36
                        height: 36

                        Image {
                            anchors.fill: parent
                            source: "../../images/logo_icon.png"
                            sourceSize.width: 96
                            sourceSize.height: 96
                            fillMode: Image.PreserveAspectFit
                            smooth: true
                            mipmap: true
                        }
                    }

                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 3

                        Text {
                            text: appName
                            font { family: uiState.fontFamily; pixelSize: 17; bold: true }
                            color: theme.textPrimary
                        }

                        Text {
                            text: lm.strings["about.subtitle"] || ""
                            font { family: uiState.fontFamily; pixelSize: 11 }
                            color: theme.textSecondary
                        }
                    }
                }

                Rectangle {
                    width: 34
                    height: 34
                    radius: 12
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    color: closeAboutMouse.containsMouse
                           ? Qt.rgba(1, 1, 1, uiState.darkMode ? 0.08 : 0.65)
                           : "transparent"

                    Accessible.role: Accessible.Button
                    Accessible.name: s["dialog.close"]
                    Accessible.onPressAction: aboutDialog.close()

                    AppIcon {
                        anchors.centerIn: parent
                        width: 14
                        height: 14
                        name: "x"
                        iconColor: theme.textSecondary
                    }

                    MouseArea {
                        id: closeAboutMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: aboutDialog.close()
                    }
                }
            }

            Column {
                anchors {
                    top: aboutHeader.bottom
                    topMargin: 20
                    left: parent.left
                    right: parent.right
                    leftMargin: 24
                    rightMargin: 24
                }
                spacing: 14

                Rectangle {
                    width: parent.width
                    height: versionHero.implicitHeight + 24
                    radius: 20
                    color: root.theme.accentDim
                    border.width: 1
                    border.color: Qt.rgba(0, 0, 0, root.darkMode ? 0.0 : 0.04)

                    Column {
                        id: versionHero
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 10

                        Text {
                            text: lm.strings["about.version"] || "Version:"
                            font { family: uiState.fontFamily; pixelSize: 11; bold: true }
                            color: root.theme.textSecondary
                        }

                        Row {
                            spacing: 10

                            Text {
                                text: root.versionLabel
                                font { family: uiState.fontFamily; pixelSize: 28; bold: true }
                                color: root.theme.textPrimary
                            }

                            Rectangle {
                                anchors.verticalCenter: parent.verticalCenter
                                radius: 999
                                color: Qt.rgba(1, 1, 1, root.darkMode ? 0.08 : 0.6)
                                border.width: 1
                                border.color: Qt.rgba(1, 1, 1, root.darkMode ? 0.05 : 0.18)
                                width: buildModeChipLabel.implicitWidth + 22
                                height: 30

                                Text {
                                    id: buildModeChipLabel
                                    anchors.centerIn: parent
                                    text: displayBuildMode
                                    font { family: uiState.fontFamily; pixelSize: 11; bold: true }
                                    color: root.theme.textPrimary
                                }
                            }
                        }

                        Text {
                            text: (lm.strings["about.commit"] || "Commit") + ": " + appCommit
                            font { family: uiState.monospaceFontFamily; pixelSize: 12 }
                            color: root.theme.textSecondary
                        }
                    }
                }

                Rectangle {
                    width: parent.width
                    height: metadataColumn.implicitHeight + 2
                    radius: 18
                    color: theme.bgSubtle
                    border.width: 1
                    border.color: theme.border

                    Column {
                        id: metadataColumn
                        anchors.fill: parent
                        spacing: 0

                        Item {
                            width: parent.width
                            height: 64

                            Text {
                                anchors.left: parent.left
                                anchors.leftMargin: 18
                                anchors.verticalCenter: parent.verticalCenter
                                width: 92
                                text: lm.strings["about.build_mode"] || "Build mode"
                                font { family: uiState.fontFamily; pixelSize: 11; bold: true }
                                color: theme.textSecondary
                            }

                            Text {
                                anchors.left: parent.left
                                anchors.leftMargin: 126
                                anchors.right: parent.right
                                anchors.rightMargin: 18
                                anchors.verticalCenter: parent.verticalCenter
                                text: displayBuildMode
                                font { family: uiState.fontFamily; pixelSize: 14 }
                                color: theme.textPrimary
                            }
                        }

                        Rectangle {
                            width: parent.width - 36
                            height: 1
                            x: 18
                            color: theme.border
                            opacity: 0.9
                        }

                        Item {
                            width: parent.width
                            height: 64

                            Text {
                                anchors.left: parent.left
                                anchors.leftMargin: 18
                                anchors.verticalCenter: parent.verticalCenter
                                width: 92
                                text: lm.strings["about.commit"] || "Commit"
                                font { family: uiState.fontFamily; pixelSize: 11; bold: true }
                                color: theme.textSecondary
                            }

                            Text {
                                anchors.left: parent.left
                                anchors.leftMargin: 126
                                anchors.right: parent.right
                                anchors.rightMargin: 18
                                anchors.verticalCenter: parent.verticalCenter
                                text: appCommit
                                font { family: uiState.monospaceFontFamily; pixelSize: 13 }
                                color: theme.textPrimary
                            }
                        }

                        Rectangle {
                            width: parent.width - 36
                            height: 1
                            x: 18
                            color: theme.border
                            opacity: 0.9
                        }

                        Item {
                            width: parent.width
                            height: 64

                            Text {
                                anchors.left: parent.left
                                anchors.leftMargin: 18
                                anchors.verticalCenter: parent.verticalCenter
                                width: 92
                                text: lm.strings["about.maintainer"] || "Maintainer:"
                                font { family: uiState.fontFamily; pixelSize: 11; bold: true }
                                color: theme.textSecondary
                            }

                            Text {
                                anchors.left: parent.left
                                anchors.leftMargin: 126
                                anchors.right: parent.right
                                anchors.rightMargin: 18
                                anchors.verticalCenter: parent.verticalCenter
                                text: appMaintainer
                                font { family: uiState.monospaceFontFamily; pixelSize: 13 }
                                color: theme.textPrimary
                            }
                        }

                        Rectangle {
                            width: parent.width - 36
                            height: 1
                            x: 18
                            color: theme.border
                            opacity: 0.9
                        }

                        Item {
                            width: parent.width
                            height: launchPathValue.implicitHeight + 34

                            Text {
                                anchors.left: parent.left
                                anchors.leftMargin: 18
                                anchors.top: parent.top
                                anchors.topMargin: 18
                                width: 92
                                text: lm.strings["about.launch_path"] || "Launch path"
                                font { family: uiState.fontFamily; pixelSize: 11; bold: true }
                                color: theme.textSecondary
                            }

                            Text {
                                id: launchPathValue
                                anchors.left: parent.left
                                anchors.leftMargin: 126
                                anchors.right: parent.right
                                anchors.rightMargin: 18
                                anchors.top: parent.top
                                anchors.topMargin: 18
                                text: appLaunchPath
                                wrapMode: Text.WrapAnywhere
                                font { family: uiState.monospaceFontFamily; pixelSize: 12 }
                                color: theme.textPrimary
                            }
                        }
                    }
                }
            }

        }
    }

    Rectangle {
        id: toast
        anchors {
            bottom: parent.bottom
            horizontalCenter: parent.horizontalCenter
            bottomMargin: 24
        }
        width: toastText.implicitWidth + 32
        height: 38
        radius: 19
        color: root.theme.accent
        opacity: 0
        visible: opacity > 0

        Text {
            id: toastText
            anchors.centerIn: parent
            font {
                family: uiState.fontFamily
                pixelSize: 12
                bold: true
            }
            color: root.theme.bgSidebar
        }

        Behavior on opacity { NumberAnimation { duration: 200 } }

        function show(msg) {
            toastText.text = msg
            toast.opacity = 1
            toastTimer.restart()
        }

        Timer {
            id: toastTimer
            interval: 2000
            onTriggered: toast.opacity = 0
        }
    }

    // Hide-to-tray: every "close window" idiom on every supported platform routes through
    // dismiss() so the engine and tray icon keep running. macOS LSUIElement bundles depend
    // on this because the Dock close button never terminates the process; Linux and Windows
    // tray builds inherit the same behavior for consistency.
    function dismiss() {
        if (!root.visible) {
            return
        }
        root.hide()
    }

    onClosing: function(close) {
        close.accepted = false
        root.dismiss()
    }

    // LSUIElement apps have no platform menu bar binding StandardKey.Close to Cmd-W, and
    // Ctrl/Cmd+M mirrors the OS "minimize" idiom. Keep these scoped to the main window
    // and disable them while any blocking dialog / shortcut-capture overlay is open so
    // typing flows cannot get swallowed by a global hide-to-tray shortcut.
    Shortcut {
        sequence: StandardKey.Close
        context: Qt.WindowShortcut
        enabled: root.visible && !root.shortcutsBlocked
        onActivated: root.dismiss()
    }

    Shortcut {
        sequence: "Ctrl+M"
        context: Qt.WindowShortcut
        enabled: root.visible && !root.shortcutsBlocked
        onActivated: root.dismiss()
    }

    // Keep Esc on the same main-window path; blocking dialogs and the key-capture overlay
    // own Escape while open, so dismiss() only runs when the real shell is frontmost.
    Shortcut {
        sequence: "Escape"
        context: Qt.WindowShortcut
        enabled: root.visible && !root.shortcutsBlocked
        onActivated: root.dismiss()
    }

    Connections {
        target: backend
        function onStatusMessage(msg) { toast.show(msg) }
    }
}
