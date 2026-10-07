import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "Theme.js" as Theme

/*  Unified Mouse + Profiles page.
    Left panel  — profile list with add/delete.
    Right panel — interactive mouse image with hotspot overlay & action picker.
    Selecting a profile switches which mappings are shown / edited.            */

Item {
    id: mousePage
    readonly property var theme: Theme.palette(uiState.darkMode)
    readonly property bool hasBlockingDialog: addAppDialog.visible
                                             || deleteDialog.visible
                                             || keyCaptureDialog.visible
    readonly property bool canConfigureMouse: backend.mouseConnected || backend.genericMouseEnabled
    property string pendingDeleteProfile: ""
    // Reactive i18n shortcut — all s["key"] bindings update on lm.languageChanged
    property var s: lm.strings

    // Shared delegate for action-picker ComboBoxes: translates every list item.
    Component {
        id: actionComboDelegate
        ItemDelegate {
            width: parent ? parent.width : implicitWidth
            highlighted: ListView.isCurrentItem
            font { family: uiState.fontFamily; pixelSize: 11 }
            contentItem: Text {
                leftPadding: 10; rightPadding: 10
                text: (lm.strings, lm.trAction(modelData ? modelData.label : ""))
                font { family: uiState.fontFamily; pixelSize: 11; bold: modelData && modelData.category === "MousePro" }
                color: highlighted
                       ? mousePage.theme.accent
                       : (modelData && modelData.category === "MousePro")
                         ? mousePage.theme.accent
                         : mousePage.theme.textPrimary
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle {
                color: highlighted
                         ? Qt.rgba(0.36, 0.56, 0.95, 0.1)
                         : (modelData && modelData.category === "MousePro")
                           ? Qt.rgba(0.36, 0.56, 0.95, 0.05)
                           : "transparent"
            }
        }
    }

    // Shared delegate for the device-layout override ComboBox (translates "Auto-detect").
    Component {
        id: layoutComboDelegate
        ItemDelegate {
            width: parent ? parent.width : implicitWidth
            highlighted: ListView.isCurrentItem
            font { family: uiState.fontFamily; pixelSize: 11 }
            contentItem: Text {
                leftPadding: 10; rightPadding: 10
                text: {
                    if (!modelData) return ""
                    var lbl = modelData.label || ""
                    return lbl === "Auto-detect"
                           ? (s["mouse.auto_detect"] || lbl)
                           : lbl
                }
                font { family: uiState.fontFamily; pixelSize: 11 }
                color: highlighted ? mousePage.theme.accent : mousePage.theme.textPrimary
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle {
                color: highlighted ? Qt.rgba(0.36, 0.56, 0.95, 0.1) : "transparent"
            }
        }
    }

    // ── Profile state ─────────────────────────────────────────
    property string selectedProfile: backend.activeProfile
    readonly property string selectedProfileLabel: {
        var localeStrings = s
        var profs = backend.profiles
        for (var i = 0; i < profs.length; i++) {
            if (profs[i].name === selectedProfile)
                return profileDisplayLabel(profs[i])
        }
        return ""
    }
    readonly property string displayDeviceName: {
        var localeStrings = s
        var name = backend.deviceDisplayName
        return name === "Mouse device"
               ? (localeStrings["mouse.device_fallback_name"] || name)
               : name
    }
    property var selectedProfileMappingState: ({})
    property string appSearchText: ""
    property var filteredKnownApps: []
    property var suggestedKnownApps: []
    property var selectedKnownApp: null

    Component.onCompleted: {
        selectProfile(backend.activeProfile)
        refreshSuggestedApps()
        refreshAppSearch()
    }

    function refreshSelectedProfileMappings() {
        var mappings = backend.getProfileMappings(selectedProfile)
        var mappingState = ({})
        for (var i = 0; i < mappings.length; i++) {
            var mapping = mappings[i]
            mappingState[mapping.key] = mapping
        }
        selectedProfileMappingState = mappingState
    }

    function mappingFor(key) {
        return selectedProfileMappingState[key] || null
    }

    function supportsMultiActionButton(key) {
        var mapping = mappingFor(key)
        return mapping ? mapping.supportsMultiAction === true : false
    }

    function longMappingKey(key) {
        return key + "_long"
    }

    function longActionIdFor(key) {
        var mapping = mappingFor(key)
        return mapping && mapping.longActionId ? mapping.longActionId : "none"
    }

    function selectProfile(name) {
        selectedProfile = name
        refreshSelectedProfileMappings()
        // Clear hotspot selection when switching profiles
        selectedButton = ""
        selectedActionId = ""
        selectedLongActionId = "none"
    }

    function profileDisplayLabel(profile) {
        if (!profile)
            return ""
        if (profile.name === "default")
            return s["mouse.default_profile"] || profile.label
        return profile.label || ""
    }

    function appMatchesSearch(app, query) {
        if (!query)
            return false
        var lowered = query.toLowerCase()
        if ((app.label || "").toLowerCase().indexOf(lowered) !== -1)
            return true
        if ((app.id || "").toLowerCase().indexOf(lowered) !== -1)
            return true
        var aliases = app.aliases || []
        for (var i = 0; i < aliases.length; i++) {
            if ((aliases[i] || "").toLowerCase().indexOf(lowered) !== -1)
                return true
        }
        return false
    }

    function appIsSystem(app) {
        var path = (app && app.path) ? app.path : ""
        return path.indexOf("/System/") === 0
    }

    function appLocationLabel(app) {
        if (!app || !app.path)
            return s["mouse.installed_app"] || "Installed app"
        if (app.path.indexOf("/Applications/") === 0)
            return s["mouse.applications"] || "Applications"
        if (app.path.indexOf("/System/Applications/") === 0)
            return s["mouse.system_applications"] || "System Applications"
        if (app.path.indexOf("/System/Library/CoreServices/") === 0)
            return s["mouse.macos_coreservices"] || "macOS CoreServices"
        if (app.path.indexOf("/Users/") === 0)
            return app.path
        return app.path
    }

    function isPreferredAppLabel(label) {
        var preferred = [
            "Google Chrome", "Safari", "Arc", "Firefox", "Visual Studio Code",
            "Cursor", "Terminal", "iTerm2", "Warp", "Finder", "Figma",
            "Slack", "Discord", "Spotify", "Notion", "Preview", "Calendar",
            "Messages", "Music", "App Store", "System Settings"
        ]
        return preferred.indexOf(label || "") !== -1
    }

    function preferredAppRank(label) {
        var preferred = [
            "Google Chrome", "Safari", "Arc", "Firefox", "Visual Studio Code",
            "Cursor", "Terminal", "iTerm2", "Warp", "Finder", "Figma",
            "Slack", "Discord", "Spotify", "Notion", "Preview", "Calendar",
            "Messages", "Music", "App Store", "System Settings"
        ]
        var idx = preferred.indexOf(label || "")
        return idx === -1 ? 999 : idx
    }

    function suggestedAppScore(app) {
        var score = preferredAppRank(app.label)
        if (score === 999) {
            if (app.path && app.path.indexOf("/Applications/") === 0)
                score = 200
            else if (app.path && app.path.indexOf("/Users/") === 0)
                score = 260
            else if (appIsSystem(app))
                score = 500
            else
                score = 350
        }

        if (app.path && app.path.indexOf("/System/Library/CoreServices/") === 0)
            score += 100
        return score
    }

    function shouldSuggestApp(app) {
        if (!app || !app.label)
            return false
        if (isPreferredAppLabel(app.label))
            return true
        if (app.path && app.path.indexOf("/Applications/") === 0)
            return true
        if (app.path && app.path.indexOf("/Users/") === 0)
            return true
        return false
    }

    function refreshSuggestedApps() {
        var apps = backend.knownApps || []
        var matches = []
        for (var i = 0; i < apps.length; i++) {
            if (!shouldSuggestApp(apps[i]))
                continue
            matches.push({
                app: apps[i],
                score: suggestedAppScore(apps[i])
            })
        }

        matches.sort(function(a, b) {
            if (a.score !== b.score)
                return a.score - b.score
            return (a.app.label || "").localeCompare(b.app.label || "")
        })

        var results = []
        for (var j = 0; j < matches.length && j < 14; j++)
            results.push(matches[j].app)
        suggestedKnownApps = results
    }

    function appResultScore(app, query) {
        var lowered = query.toLowerCase()
        var label = (app.label || "").toLowerCase()
        var score = 50

        if (label === lowered)
            score = 0
        else if (label.indexOf(lowered) === 0)
            score = 1
        else if (label.indexOf(lowered) !== -1)
            score = 2

        var aliases = app.aliases || []
        for (var i = 0; i < aliases.length; i++) {
            var alias = (aliases[i] || "").toLowerCase()
            if (alias === lowered)
                score = Math.min(score, 3)
            else if (alias.indexOf(lowered) === 0)
                score = Math.min(score, 4)
            else if (alias.indexOf(lowered) !== -1)
                score = Math.min(score, 5)
        }

        if (appIsSystem(app))
            score += 10
        return score
    }

    function refreshAppSearch() {
        var query = (appSearchText || "").trim()
        var apps = backend.knownApps || []
        var matches = []

        if (query.length === 0) {
            filteredKnownApps = []
            return
        }

        for (var i = 0; i < apps.length; i++) {
            if (appMatchesSearch(apps[i], query)) {
                matches.push({
                    app: apps[i],
                    score: appResultScore(apps[i], query)
                })
            }
        }

        matches.sort(function(a, b) {
            if (a.score !== b.score)
                return a.score - b.score
            return (a.app.label || "").localeCompare(b.app.label || "")
        })

        var results = []
        for (var j = 0; j < matches.length && j < 12; j++)
            results.push(matches[j].app)

        filteredKnownApps = results
    }

    function selectKnownApp(app) {
        selectedKnownApp = app
    }

    function syncSelectedKnownApp() {
        if (!selectedKnownApp || !selectedKnownApp.id)
            return
        var apps = backend.knownApps || []
        for (var i = 0; i < apps.length; i++) {
            if (apps[i].id === selectedKnownApp.id) {
                selectedKnownApp = apps[i]
                return
            }
        }
        selectedKnownApp = null
    }

    function openAddProfileDialog() {
        selectedKnownApp = null
        appSearchText = ""
        filteredKnownApps = []
        refreshSuggestedApps()
        if (appSearchInput)
            appSearchInput.text = ""
        addAppDialog.open()
    }

    Connections {
        target: backend
        function onProfilesChanged() {
            // Keep the current profile selected if it still exists.
            var profs = backend.profiles
            for (var i = 0; i < profs.length; i++) {
                if (profs[i].name === selectedProfile)
                    return
            }
            // Profile deleted — fall back to active
            selectProfile(backend.activeProfile)
        }
        function onActiveProfileChanged() {
            // Auto-select when engine switches profile
            selectProfile(backend.activeProfile)
        }
    }

    // ── Button / hotspot state ────────────────────────────────
    property string selectedButton: ""
    readonly property string selectedButtonName: {
        if (selectedButton === "")
            return ""
        if (selectedButton === "hscroll_left")
            return s["mouse.horizontal_scroll"] || "Horizontal Scroll"
        var mapping = mappingFor(selectedButton)
        return mapping ? (lm.strings, lm.trButton(mapping.name)) : ""
    }
    property string selectedActionId: ""
    property string selectedLongActionId: "none"
    readonly property string hscrollLeftActionId: selectedProfileMappingState.hscroll_left
                                             ? selectedProfileMappingState.hscroll_left.actionId
                                             : "none"
    readonly property string hscrollLeftActionLabel: selectedProfileMappingState.hscroll_left
                                                ? selectedProfileMappingState.hscroll_left.actionLabel
                                                : (s["mouse.do_nothing"] || "Do Nothing")
    readonly property string hscrollRightActionId: selectedProfileMappingState.hscroll_right
                                              ? selectedProfileMappingState.hscroll_right.actionId
                                              : "none"
    readonly property string hscrollRightActionLabel: selectedProfileMappingState.hscroll_right
                                                 ? selectedProfileMappingState.hscroll_right.actionLabel
                                                 : (s["mouse.do_nothing"] || "Do Nothing")
    readonly property string gestureTapActionId: selectedProfileMappingState.gesture
                                            ? selectedProfileMappingState.gesture.actionId
                                            : "none"
    readonly property string gestureTapActionLabel: selectedProfileMappingState.gesture
                                               ? selectedProfileMappingState.gesture.actionLabel
                                               : (s["mouse.do_nothing"] || "Do Nothing")
    readonly property string gestureLeftActionId: selectedProfileMappingState.gesture_left
                                             ? selectedProfileMappingState.gesture_left.actionId
                                             : "none"
    readonly property string gestureRightActionId: selectedProfileMappingState.gesture_right
                                              ? selectedProfileMappingState.gesture_right.actionId
                                              : "none"
    readonly property string gestureUpActionId: selectedProfileMappingState.gesture_up
                                           ? selectedProfileMappingState.gesture_up.actionId
                                           : "none"
    readonly property string gestureDownActionId: selectedProfileMappingState.gesture_down
                                             ? selectedProfileMappingState.gesture_down.actionId
                                             : "none"
    readonly property bool hasGestureSwipeAction: gestureLeftActionId !== "none"
                                             || gestureRightActionId !== "none"
                                             || gestureUpActionId !== "none"
                                             || gestureDownActionId !== "none"

    function selectButton(key) {
        if (selectedButton === key) {
            selectedButton = ""
            selectedActionId = ""
            selectedLongActionId = "none"
            return
        }
        var mapping = mappingFor(key)
        if (mapping) {
            selectedButton = key
            selectedActionId = mapping.actionId
            selectedLongActionId = longActionIdFor(key)
        }
    }

    function selectHScroll() {
        if (selectedButton === "hscroll_left") {
            selectedButton = ""
            selectedActionId = ""
            selectedLongActionId = "none"
            return
        }
        selectedButton = "hscroll_left"
        var mapping = mappingFor("hscroll_left")
        selectedActionId = mapping ? mapping.actionId : "none"
        selectedLongActionId = "none"
    }

    Connections {
        id: mappingsConn
        target: backend
        function onMappingsChanged() {
            refreshSelectedProfileMappings()
            if (selectedButton === "") return
            var mapping = mappingFor(selectedButton)
            if (mapping) {
                selectedActionId = mapping.actionId
                selectedLongActionId = longActionIdFor(selectedButton)
            }
        }
    }

    function actionFor(key) {
        var mapping = mappingFor(key)
        if (mapping)
            return (lm.strings, lm.trAction(mapping.actionLabel))
        return s["mouse.do_nothing"] || "Do Nothing"
    }

    function actionFor_id(key) {
        var mapping = mappingFor(key)
        if (mapping)
            return mapping.actionId
        return "none"
    }

    function actionIndexForId(actionId) {
        var actions = backend.allActions
        for (var i = 0; i < actions.length; i++)
            if (actions[i].id === actionId) return i
        // Custom shortcut: point to the __custom__ sentinel at the end
        if (actionId.startsWith("custom:")) return actions.length - 1
        return 0
    }

    function customLabel(actionId) {
        if (!actionId.startsWith("custom:")) return ""
        return backend.actionLabelFor(actionId)
    }

    function isCustomAction(actionId) {
        return actionId.startsWith("custom:")
    }

    function gestureSummary() {
        if (!backend.supportsGestureDirections)
            return actionFor("gesture")
        if (!hasGestureSwipeAction)
            return (s["mouse.tap"] || "Tap: ")
                   + (lm.strings, lm.trAction(gestureTapActionLabel))
        return (s["mouse.tap"] || "Tap: ")
               + (lm.strings, lm.trAction(gestureTapActionLabel))
               + " | " + (s["mouse.swipes_configured"] || "Swipes configured")
    }

    function hotspotSublabel(hotspot) {
        if (!hotspot)
            return ""
        if (hotspot.summaryType === "gesture")
            return gestureSummary()
        if (hotspot.summaryType === "hscroll")
            return (s["mouse.left_short"] || "L") + ": "
                   + (lm.strings, lm.trAction(hscrollLeftActionLabel))
                   + " | " + (s["mouse.right_short"] || "R") + ": "
                   + (lm.strings, lm.trAction(hscrollRightActionLabel))
        return actionFor(hotspot.buttonKey)
    }

    function layoutHasButton(buttonKey) {
        var hotspots = backend.deviceHotspots
        for (var i = 0; i < hotspots.length; i++) {
            if (hotspots[i].buttonKey === buttonKey)
                return true
        }
        return false
    }

    function manualLayoutChoiceIndex(layoutKey) {
        var choices = backend.manualLayoutChoices
        for (var i = 0; i < choices.length; i++) {
            if (choices[i].key === layoutKey)
                return i
        }
        return 0
    }

    function currentLayoutChoiceLabel() {
        var idx = manualLayoutChoiceIndex(backend.deviceLayoutOverrideKey)
        var choices = backend.manualLayoutChoices
        if (idx >= 0 && idx < choices.length)
            return choices[idx].label
        return s["mouse.auto_detect"] || "Auto-detect"
    }

    Connections {
        target: backend
        function onDeviceLayoutChanged() {
            if (selectedButton !== "" && !layoutHasButton(selectedButton)) {
                selectedButton = ""
                selectedActionId = ""
                selectedLongActionId = "none"
            }
        }
    }

    // ── Main two-column layout ────────────────────────────────
    Row {
        anchors.fill: parent
        spacing: 0

        // ══════════════════════════════════════════════════════
        // ── Left panel: profile list ─────────────────────────
        // ══════════════════════════════════════════════════════
        Rectangle {
            id: leftPanel
            width: 240
            height: parent.height
            color: theme.bgElevated
            border.width: 0

            Column {
                anchors.fill: parent
                spacing: 0

                // Title bar
                Item {
                    width: parent.width; height: 60

                    Text {
                        anchors {
                            left: parent.left; leftMargin: Theme.space16
                            verticalCenter: parent.verticalCenter
                        }
                                text: s["mouse.profiles"]
                                font { family: uiState.fontFamily; pixelSize: 15; bold: true }
                                color: theme.textPrimary
                    }
                }

                Rectangle { width: parent.width; height: 1; color: theme.border }

                // Profile items
                ListView {
                    id: profileList
                    width: parent.width
                    height: parent.height - 62 - addProfileSection.height
                    model: backend.profiles
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds

                    delegate: Rectangle {
                        width: profileList.width
                        height: 52
                        color: selectedProfile === modelData.name
                               ? theme.accentDim
                               : profItemMa.containsMouse
                                 ? Qt.rgba(1, 1, 1, 0.03)
                                 : "transparent"
                        Behavior on color { ColorAnimation { duration: 120 } }

                        Row {
                            anchors {
                                fill: parent
                                leftMargin: 10; rightMargin: 12
                            }
                            spacing: 8

                            // Active indicator
                            Rectangle {
                                width: 2; height: 24; radius: 1
                                color: modelData.isActive
                                       ? theme.accent : "transparent"
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            // App icons
                            Row {
                                spacing: -4
                                anchors.verticalCenter: parent.verticalCenter
                                visible: modelData.appIcons !== undefined
                                         && modelData.appIcons.length > 0

                                Repeater {
                                    model: modelData.appIcons
                                    delegate: Image {
                                        source: modelData || ""
                                        width: 24; height: 24
                                        sourceSize { width: 24; height: 24 }
                                        fillMode: Image.PreserveAspectFit
                                        visible: source !== ""
                                        smooth: true; mipmap: true
                                        asynchronous: true
                                        cache: true
                                    }
                                }
                            }

                            Column {
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 2

                                Text {
                                    text: profileDisplayLabel(modelData)
                                    font {
                                        family: uiState.fontFamily
                                        pixelSize: 12; weight: Font.DemiBold
                                    }
                                    color: theme.textPrimary
                                    elide: Text.ElideRight
                                    width: leftPanel.width - 70
                                }
                                Text {
                                    text: modelData.displayApps.length
                                          ? modelData.displayApps.join(", ")
                                          : (s["mouse.all_applications"] || "All applications")
                                    font { family: uiState.fontFamily; pixelSize: 10 }
                                    color: theme.textSecondary
                                    elide: Text.ElideRight
                                    width: leftPanel.width - 70
                                }
                            }
                        }

                        MouseArea {
                            id: profItemMa
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: selectProfile(modelData.name)
                        }
                    }
                }

                Rectangle { width: parent.width; height: 1; color: theme.border }

                // Add profile controls
                Item {
                    id: addProfileSection
                    width: parent.width
                    height: 76

                    Rectangle {
                        anchors {
                            fill: parent
                            leftMargin: 8
                            rightMargin: 8
                            topMargin: 8
                            bottomMargin: 8
                        }
                        radius: Theme.radiusControl
                        color: theme.bgSubtle
                        border.width: 1
                        border.color: theme.border

                        Row {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            spacing: 8

                            Rectangle {
                                width: 28
                                height: 28
                                radius: 8
                                anchors.verticalCenter: parent.verticalCenter
                                color: Qt.rgba(0.36, 0.56, 0.95, uiState.darkMode ? 0.16 : 0.14)

                                Text {
                                    anchors.centerIn: parent
                                    text: "+"
                                    font { family: uiState.fontFamily; pixelSize: 16; bold: true }
                                    color: theme.accent
                                }
                            }

                            Column {
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 2

                                Text {
                                    text: s["mouse.add_app_profile"]
                                    font { family: uiState.fontFamily; pixelSize: 11; bold: true }
                                    color: theme.textPrimary
                                }

                                Text {
                                    text: s["mouse.search_installed_apps"]
                                    font { family: uiState.fontFamily; pixelSize: 10 }
                                    color: theme.textSecondary
                                    elide: Text.ElideRight
                                    width: leftPanel.width - 110
                                }
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: openAddProfileDialog()
                        }
                    }
                }
            }

            Rectangle {
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.right: parent.right
                width: 1
                color: theme.border
            }
        }

        // ══════════════════════════════════════════════════════
        // ── Right panel: mouse image + hotspots + picker ─────
        // ══════════════════════════════════════════════════════
        ScrollView {
            width: parent.width - leftPanel.width
            height: parent.height
            contentWidth: availableWidth
            clip: true

            Flickable {
                contentHeight: rightCol.implicitHeight + Theme.space24
                boundsBehavior: Flickable.StopAtBounds

                Column {
                    id: rightCol
                    width: parent.width
                    spacing: 0

                    // ── Header ────────────────────────────────
                    Item {
                        width: parent.width; height: 88

                        Row {
                            anchors {
                                left: parent.left; leftMargin: Theme.space32
                                verticalCenter: parent.verticalCenter
                            }
                            spacing: Theme.space12

                            Column {
                                spacing: 3
                                anchors.verticalCenter: parent.verticalCenter

                                Row {
                                    spacing: 8

                                    Text {
                                        text: displayDeviceName
                                        font { family: uiState.fontFamily; pixelSize: 24; bold: true }
                                        color: theme.textPrimary
                                    }

                                    // Profile badge
                                    Rectangle {
                                        visible: selectedProfileLabel !== ""
                                        width: profBadgeText.implicitWidth + 16
                                        height: 22; radius: 11
                                        color: Qt.rgba(0.36, 0.56, 0.95, 0.12)
                                        anchors.verticalCenter: parent.verticalCenter

                                        Text {
                                            id: profBadgeText
                                            anchors.centerIn: parent
                                            text: selectedProfileLabel
                                            font { family: uiState.fontFamily; pixelSize: 11 }
                                            color: theme.accent
                                        }
                                    }
                                }

                                Text {
                                    text: !canConfigureMouse
                                          ? s["mouse.turn_on_mouse"]
                                          : backend.hasInteractiveDeviceLayout
                                            ? s["mouse.click_dot"]
                                            : s["mouse.choose_layout"]
                                    font { family: uiState.fontFamily; pixelSize: 13 }
                                    color: theme.textSecondary
                                }
                            }
                        }

                        // Right-side status row: delete button + battery + connection
                        Row {
                            anchors {
                                right: parent.right; rightMargin: Theme.space32
                                verticalCenter: parent.verticalCenter
                            }
                            spacing: Theme.space8

                            // Delete profile button (not for default)
                            Rectangle {
                                visible: selectedProfile !== ""
                                         && selectedProfile !== "default"
                                width: delRow.implicitWidth + 18
                                height: 28
                                radius: 10
                                color: delMa.containsMouse ? theme.danger : theme.dangerBg
                                Behavior on color { ColorAnimation { duration: 120 } }
                                anchors.verticalCenter: parent.verticalCenter

                                Row {
                                    id: delRow
                                    anchors.centerIn: parent
                                    spacing: 6

                                    AppIcon {
                                        anchors.verticalCenter: parent.verticalCenter
                                        width: 14
                                        height: 14
                                        name: "trash"
                                        iconColor: uiState.darkMode ? theme.textPrimary : theme.danger
                                    }

                                    Text {
                                        text: s["mouse.delete_profile"]
                                        font { family: uiState.fontFamily; pixelSize: 10; bold: true }
                                        color: uiState.darkMode ? theme.textPrimary : theme.danger
                                    }
                                }

                                MouseArea {
                                    id: delMa
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        pendingDeleteProfile = selectedProfile
                                        deleteDialog.open()
                                    }
                                }
                            }

                            // Battery badge
                            Rectangle {
                                visible: backend.batteryLevel >= 0
                                width: battRow.implicitWidth + 16
                                height: 22; radius: 11
                                anchors.verticalCenter: parent.verticalCenter
                                color: {
                                    var lvl = backend.batteryLevel
                                    if (lvl <= 20) return Qt.rgba(0.88, 0.2, 0.2, 0.18)
                                    if (lvl <= 40) return Qt.rgba(0.9, 0.56, 0.1, 0.18)
                                    return Qt.rgba(0.36, 0.56, 0.95, uiState.darkMode ? 0.12 : 0.16)
                                }

                                Row {
                                    id: battRow
                                    anchors.centerIn: parent
                                    spacing: 6

                                    AppIcon {
                                        anchors.verticalCenter: parent.verticalCenter
                                        width: 14
                                        height: 14
                                        name: "battery-high"
                                        iconColor: {
                                            var lvl = backend.batteryLevel
                                            if (lvl <= 20) return "#e05555"
                                            if (lvl <= 40) return "#e09045"
                                            return theme.accent
                                        }
                                    }

                                    Text {
                                        text: backend.batteryLevel + "%"
                                        font { family: uiState.fontFamily; pixelSize: 11; bold: true }
                                        color: {
                                            var lvl = backend.batteryLevel
                                            if (lvl <= 20) return "#e05555"
                                            if (lvl <= 40) return "#e09045"
                                            return theme.accent
                                        }
                                    }
                                }
                            }

                            // Connection status badge
                            Rectangle {
                                width: statusRow.implicitWidth + 16
                                height: 24; radius: 12
                                anchors.verticalCenter: parent.verticalCenter
                                color: backend.mouseConnected
                                       ? Qt.rgba(0.36, 0.56, 0.95, 0.12)
                                       : (backend.deviceStatusKind === "generic_ready"
                                          ? Qt.rgba(0.36, 0.56, 0.95, 0.12)
                                          : Qt.rgba(0.9, 0.3, 0.3, 0.15))

                                Row {
                                    id: statusRow
                                    anchors.centerIn: parent
                                    spacing: 5

                                    Rectangle {
                                        width: 7; height: 7; radius: 4
                                        color: backend.deviceStatusKind === "no_supported_mouse"
                                               ? "#e05555" : theme.accent
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                    Text {
                                        text: backend.deviceStatusKind === "logitech_connected"
                                              ? ((s["mouse.connected"] || "Connected")
                                                 + (backend.deviceDisplayName !== ""
                                                    ? " \u2014 " + backend.deviceDisplayName : ""))
                                              : (backend.deviceStatusKind === "generic_ready"
                                                 ? (s["mouse.generic_ready"] || "Generic Mouse Mode Ready")
                                                 : (s["mouse.no_supported_mouse_detected"] || "No supported mouse detected"))
                                        font { family: uiState.fontFamily; pixelSize: 10; weight: Font.DemiBold }
                                        color: backend.deviceStatusKind === "no_supported_mouse"
                                               ? "#e05555" : theme.accent
                                    }
                                }
                            }

                            // Layout picker pill
                            Rectangle {
                                visible: backend.mouseConnected
                                width: layoutPillRow.implicitWidth + 16
                                height: 24; radius: 12
                                anchors.verticalCenter: parent.verticalCenter
                                color: layoutPillMa.containsMouse
                                       ? Qt.rgba(0.5, 0.5, 0.5, 0.18)
                                       : (backend.deviceLayoutOverrideKey !== ""
                                          ? Qt.rgba(0.95, 0.7, 0.2, 0.18)
                                          : Qt.rgba(0.5, 0.5, 0.5, 0.10))

                                Row {
                                    id: layoutPillRow
                                    anchors.centerIn: parent
                                    spacing: 4

                                    Text {
                                        text: {
                                            if (backend.deviceLayoutOverrideKey !== "")
                                                return currentLayoutChoiceLabel()
                                            return backend.deviceDisplayName || (s["mouse.auto_detect"] || "Auto-detect")
                                        }
                                        font { family: uiState.fontFamily; pixelSize: 10 }
                                        color: backend.deviceLayoutOverrideKey !== ""
                                               ? "#d4a017" : theme.textSecondary
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                    Text {
                                        text: "\u25BE"
                                        font.pixelSize: 9
                                        color: theme.textSecondary
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                }

                                MouseArea {
                                    id: layoutPillMa
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: layoutMenu.open()
                                }

                                Menu {
                                    id: layoutMenu
                                    y: parent.height + 4

                                    Repeater {
                                        model: backend.manualLayoutChoices
                                        MenuItem {
                                            text: {
                                                var lbl = modelData.label || ""
                                                return lbl === "Auto-detect"
                                                       ? (s["mouse.auto_detect"] || lbl)
                                                       : lbl
                                            }
                                            font { family: uiState.fontFamily; pixelSize: 11 }
                                            highlighted: modelData.key === backend.deviceLayoutOverrideKey
                                                         || (modelData.key === "" && backend.deviceLayoutOverrideKey === "")
                                            onTriggered: backend.setDeviceLayoutOverride(modelData.key)
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        width: parent.width - 64; height: 1
                        color: theme.border
                        anchors.horizontalCenter: parent.horizontalCenter
                    }

                    // ── Mouse image with hotspots ─────────────
                    Item { width: 1; height: Theme.space16 }

                    Rectangle {
                        visible: backend.isWindows
                        width: parent.width - 64
                        anchors.horizontalCenter: parent.horizontalCenter
                        height: 52
                        radius: Theme.radius
                        color: theme.bgCard
                        border.width: 1
                        border.color: theme.border

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.space16
                            anchors.rightMargin: Theme.space16
                            spacing: Theme.space12

                            Column {
                                Layout.fillWidth: true
                                spacing: 3

                                Text {
                                    text: s["mouse.generic_mouse_mode"] || "Generic Mouse Mode"
                                    font { family: uiState.fontFamily; pixelSize: 13; bold: true }
                                    color: theme.textPrimary
                                }

                                Text {
                                    text: s["mouse.generic_mouse_side_buttons"] || "Middle / Side Buttons"
                                    font { family: uiState.fontFamily; pixelSize: 11 }
                                    color: theme.textSecondary
                                }
                            }

                            Switch {
                                checked: backend.genericMouseEnabled
                                text: checked ? s["mouse.on"] : s["mouse.off"]
                                Material.accent: theme.accent
                                Accessible.name: s["mouse.generic_mouse_mode"] || "Generic Mouse Mode"
                                onClicked: backend.setGenericMouseEnabled(checked)
                            }
                        }
                    }

                    Item { width: 1; height: Theme.space12; visible: backend.isWindows }

                    Item {
                        id: mouseImageArea
                        width: parent.width
                        height: canConfigureMouse ? 420 : 340

                        Rectangle {
                            anchors.fill: parent
                            color: theme.bg
                        }

                        Image {
                            id: mouseImg
                            source: backend.deviceImageSource
                            fillMode: Image.PreserveAspectFit
                            width: backend.deviceImageWidth
                            height: backend.deviceImageHeight
                            anchors.centerIn: parent
                            visible: canConfigureMouse
                            smooth: true
                            mipmap: true
                            asynchronous: true
                            cache: true

                            property real offX: (width - paintedWidth) / 2
                            property real offY: (height - paintedHeight) / 2
                        }

                        Rectangle {
                            visible: !canConfigureMouse
                            width: Math.min(parent.width - 64, 640)
                            height: emptyStateCol.implicitHeight + 40
                            radius: Theme.radiusLarge
                            anchors.top: parent.top
                            anchors.topMargin: Theme.space32
                            anchors.horizontalCenter: parent.horizontalCenter
                            color: theme.bgCard
                            border.width: 1
                            border.color: theme.border

                            Column {
                                id: emptyStateCol
                                anchors.fill: parent
                                anchors.margins: Theme.space20
                                spacing: Theme.space12

                                Rectangle {
                                    width: waitingRow.implicitWidth + 16
                                    height: 24
                                    radius: 12
                                    color: Qt.rgba(0.9, 0.3, 0.3, uiState.darkMode ? 0.18 : 0.10)

                                    Row {
                                        id: waitingRow
                                        anchors.centerIn: parent
                                        spacing: 6

                                        Rectangle {
                                            width: 8
                                            height: 8
                                            radius: 4
                                            color: "#e05555"
                                            anchors.verticalCenter: parent.verticalCenter
                                        }

                                        Text {
                                            text: s["mouse.waiting_for_connection"]
                                            font { family: uiState.fontFamily; pixelSize: 11; bold: true }
                                            color: "#e05555"
                                        }
                                    }
                                }

                                Text {
                                    width: parent.width
                                    text: s["mouse.connect_mouse"]
                                    wrapMode: Text.WordWrap
                                    font { family: uiState.fontFamily; pixelSize: 24; bold: true }
                                    color: theme.textPrimary
                                }

                                Text {
                                    width: Math.min(parent.width, 680)
                                    text: s["mouse.connect_mouse_desc"]
                                    wrapMode: Text.WordWrap
                                    font { family: uiState.fontFamily; pixelSize: 13 }
                                    color: theme.textSecondary
                                }

                                Flow {
                                    width: parent.width
                                    spacing: 10

                                    Rectangle {
                                        width: firstHint.implicitWidth + 20
                                        height: 28
                                        radius: Theme.radiusSmall
                                        color: theme.bgSubtle
                                        border.width: 1
                                        border.color: theme.border

                                        Text {
                                            id: firstHint
                                            anchors.centerIn: parent
                                            text: s["mouse.layout_appears_auto"]
                                            font { family: uiState.fontFamily; pixelSize: 11 }
                                            color: theme.textSecondary
                                        }
                                    }

                                    Rectangle {
                                        width: secondHint.implicitWidth + 20
                                        height: 28
                                        radius: Theme.radiusSmall
                                        color: theme.bgSubtle
                                        border.width: 1
                                        border.color: theme.border

                                        Text {
                                            id: secondHint
                                            anchors.centerIn: parent
                                            text: s["mouse.per_device_settings"]
                                            font { family: uiState.fontFamily; pixelSize: 11 }
                                            color: theme.textSecondary
                                        }
                                    }
                                }
                            }
                        }

                        Repeater {
                            model: backend.deviceHotspots

                            delegate: HotspotDot {
                                required property int index
                                readonly property var hotspot: backend.deviceHotspots[index]
                                anchors.fill: mouseImageArea
                                imgItem: mouseImg
                                normX: Number(hotspot["normX"] || 0)
                                normY: Number(hotspot["normY"] || 0)
                                buttonKey: String(hotspot["buttonKey"] || "")
                                isHScroll: hotspot["isHScroll"] === true
                                label: String(hotspot["label"] || hotspot["buttonKey"] || "")
                                sublabel: hotspotSublabel(hotspot)
                                labelSide: String(hotspot["labelSide"] || "right")
                                labelOffX: hotspot["labelOffX"] === undefined ? 120 : Number(hotspot["labelOffX"])
                                labelOffY: hotspot["labelOffY"] === undefined ? -30 : Number(hotspot["labelOffY"])
                            }
                        }

                        Rectangle {
                            visible: canConfigureMouse && !backend.hasInteractiveDeviceLayout
                            width: Math.min(480, parent.width - 64)
                            height: fallbackCol.implicitHeight + 40
                            radius: Theme.radiusLarge
                            color: theme.bgCard
                            border.width: 1
                            border.color: theme.border
                            anchors.top: parent.top
                            anchors.topMargin: Theme.space32
                            anchors.horizontalCenter: parent.horizontalCenter

                            Column {
                                id: fallbackCol
                                anchors.fill: parent
                                anchors.margins: Theme.space20
                                spacing: Theme.space12

                                Text {
                                    text: s["mouse.interactive_layout_coming"]
                                    width: parent.width
                                    font { family: uiState.fontFamily; pixelSize: 15; bold: true }
                                    color: theme.textPrimary
                                }

                                Text {
                                    text: backend.effectiveDeviceLayoutKey === "generic_mouse"
                                          ? (s["mouse.generic_layout_note"] || backend.deviceLayoutNote)
                                          : backend.deviceLayoutNote
                                    width: parent.width
                                    wrapMode: Text.WordWrap
                                    font { family: uiState.fontFamily; pixelSize: 12 }
                                    color: theme.textSecondary
                                    visible: text !== ""
                                }

                                // Clickable button list for devices without an interactive overlay
                                Repeater {
                                    model: backend.buttons
                                    delegate: Rectangle {
                                        required property var modelData
                                        width: fallbackCol.width
                                        height: 40
                                        radius: 10
                                        color: selectedButton === modelData.key
                                               ? Qt.rgba(theme.accent.r, theme.accent.g, theme.accent.b, 0.12)
                                               : fbBtnArea.containsMouse
                                                 ? Qt.rgba(theme.textPrimary.r, theme.textPrimary.g, theme.textPrimary.b, 0.06)
                                                 : "transparent"
                                        border.width: selectedButton === modelData.key ? 1 : 0
                                        border.color: theme.accent

                                        Row {
                                            anchors.fill: parent
                                            anchors.leftMargin: 12
                                            anchors.rightMargin: 12
                                            spacing: 8

                                            Text {
                                                text: (lm.strings, lm.trButton(modelData.name))
                                                width: parent.width * 0.45
                                                anchors.verticalCenter: parent.verticalCenter
                                                font { family: uiState.fontFamily; pixelSize: 13; bold: true }
                                                color: selectedButton === modelData.key
                                                       ? theme.accent : theme.textPrimary
                                                elide: Text.ElideRight
                                            }

                                            Text {
                                                text: (lm.strings, lm.trAction(modelData.actionLabel))
                                                width: parent.width * 0.55 - 8
                                                anchors.verticalCenter: parent.verticalCenter
                                                horizontalAlignment: Text.AlignRight
                                                font { family: uiState.fontFamily; pixelSize: 12 }
                                                color: theme.textSecondary
                                                elide: Text.ElideRight
                                            }
                                        }

                                        MouseArea {
                                            id: fbBtnArea
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: selectButton(modelData.key)
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // ── Separator ─────────────────────────────
                    Rectangle {
                        width: parent.width - 64; height: 1
                        color: theme.border
                        anchors.horizontalCenter: parent.horizontalCenter
                        visible: selectedButton !== ""
                    }

                    // ── Action picker ─────────────────────────
                    Rectangle {
                        id: actionPicker
                        width: parent.width - 64
                        anchors.horizontalCenter: parent.horizontalCenter
                        height: selectedButton !== ""
                                ? pickerCol.implicitHeight + 32 : 0
                        clip: true
                        color: "transparent"
                        visible: height > 0

                        Behavior on height {
                            NumberAnimation { duration: 250; easing.type: Easing.OutQuad }
                        }

                        Column {
                            id: pickerCol
                            anchors {
                                left: parent.left; right: parent.right
                                top: parent.top; topMargin: 16
                            }
                            spacing: 16

                            Row {
                                spacing: 12

                                Rectangle {
                                    width: 6; height: pickerTitleCol.height
                                    radius: 3; color: theme.accent
                                    anchors.verticalCenter: parent.verticalCenter
                                }

                                Column {
                                    id: pickerTitleCol
                                    spacing: 2

                                    Text {
                                        text: selectedButtonName
                                              ? selectedButtonName + (s["mouse.choose_action_suffix"] || " — Choose Action")
                                              : ""
                                        font { family: uiState.fontFamily; pixelSize: 15; bold: true }
                                        color: theme.textPrimary
                                    }
                                    Text {
                                        text: selectedButton === "hscroll_left"
                                              ? s["mouse.configure_scroll_actions"]
                                              : selectedButton === "gesture"
                                                && backend.supportsGestureDirections
                                                ? s["mouse.configure_gesture"]
                                              : s["mouse.select_button_action"]
                                        font { family: uiState.fontFamily; pixelSize: 12 }
                                        color: theme.textSecondary
                                        visible: selectedButton !== ""
                                    }
                                }
                            }

                            // Horizontal scroll: left + right rows
                            Column {
                                width: parent.width
                                spacing: 14
                                visible: selectedButton === "hscroll_left"

                                Text {
                                    text: s["mouse.scroll_left"]
                                    font { family: uiState.fontFamily; pixelSize: 11;
                                           capitalization: Font.AllUppercase; letterSpacing: 1 }
                                    color: theme.textDim
                                }

                                Flow {
                                    width: parent.width; spacing: 8
                                    Repeater {
                                        model: backend.allActions
                                        delegate: ActionChip {
                                            actionId: modelData.id
                                            actionLabel: modelData.id === "__custom__" && isCustomAction(hscrollLeftActionId)
                                                         ? customLabel(hscrollLeftActionId)
                                                         : (lm.strings, lm.trAction(modelData.label))
                                            isCurrent: modelData.id === "__custom__"
                                                       ? isCustomAction(hscrollLeftActionId)
                                                       : modelData.id === hscrollLeftActionId
                                            onPicked: function(aid) {
                                                if (aid === "__custom__") {
                                                    keyCaptureDialog.open(selectedProfile, "hscroll_left")
                                                    return
                                                }
                                                backend.setProfileMapping(
                                                    selectedProfile, "hscroll_left", aid)
                                            }
                                        }
                                    }
                                }

                                Item { width: 1; height: 4 }

                                Text {
                                    text: s["mouse.scroll_right"]
                                    font { family: uiState.fontFamily; pixelSize: 11;
                                           capitalization: Font.AllUppercase; letterSpacing: 1 }
                                    color: theme.textDim
                                }

                                Flow {
                                    width: parent.width; spacing: 8
                                    Repeater {
                                        model: backend.allActions
                                        delegate: ActionChip {
                                            actionId: modelData.id
                                            actionLabel: modelData.id === "__custom__" && isCustomAction(hscrollRightActionId)
                                                         ? customLabel(hscrollRightActionId)
                                                         : (lm.strings, lm.trAction(modelData.label))
                                            isCurrent: modelData.id === "__custom__"
                                                       ? isCustomAction(hscrollRightActionId)
                                                       : modelData.id === hscrollRightActionId
                                            onPicked: function(aid) {
                                                if (aid === "__custom__") {
                                                    keyCaptureDialog.open(selectedProfile, "hscroll_right")
                                                    return
                                                }
                                                backend.setProfileMapping(
                                                    selectedProfile, "hscroll_right", aid)
                                            }
                                        }
                                    }
                                }
                            }

                            Column {
                                width: parent.width
                                spacing: 14
                                visible: selectedButton === "gesture"
                                         && backend.supportsGestureDirections

                                Text {
                                    text: s["mouse.tap_action"]
                                    font { family: uiState.fontFamily; pixelSize: 11;
                                           capitalization: Font.AllUppercase; letterSpacing: 1 }
                                    color: theme.textDim
                                }

                                ComboBox {
                                    width: parent.width
                                    model: backend.allActions
                                    textRole: "label"
                                    delegate: actionComboDelegate
                                    Material.accent: theme.accent
                                    font { family: uiState.fontFamily; pixelSize: 11 }
                                    currentIndex: actionIndexForId(gestureTapActionId)
                                    displayText: isCustomAction(gestureTapActionId)
                                                 ? customLabel(gestureTapActionId)
                                                 : (lm.strings, lm.trAction(currentText))
                                    onActivated: function(index) {
                                        var aid = backend.allActions[index].id
                                        if (aid === "__custom__") {
                                            keyCaptureDialog.open(selectedProfile, "gesture")
                                            return
                                        }
                                        backend.setProfileMapping(selectedProfile, "gesture", aid)
                                        selectedActionId = aid
                                    }
                                }

                                Rectangle {
                                    width: parent.width
                                    height: 1
                                    color: theme.border
                                }

                                Row {
                                    width: parent.width
                                    spacing: 12

                                Text {
                                    text: s["mouse.threshold"]
                                    font { family: uiState.fontFamily; pixelSize: 12; bold: true }
                                    color: theme.textPrimary
                                }

                                    Text {
                                        text: (
                                            gestureThresholdSlider.pressed
                                            ? Math.round(gestureThresholdSlider.value / 5.0) * 5
                                            : backend.gestureThreshold
                                        ) + " px"
                                        font { family: uiState.fontFamily; pixelSize: 12 }
                                        color: theme.textSecondary
                                    }
                                }

                                WheelSafeSlider {
                                    id: gestureThresholdSlider
                                    width: parent.width
                                    from: 20
                                    to: 400
                                    stepSize: 5
                                    value: backend.gestureThreshold
                                    accentColor: theme.accent
                                    accentDimColor: theme.accentDim
                                    trackColor: theme.border
                                    onMoved: gestureThresholdSave.restart()
                                    onPressedChanged: {
                                        if (!pressed) {
                                            gestureThresholdSave.stop()
                                            backend.setGestureThreshold(
                                                Math.round(value / 5.0) * 5)
                                        }
                                    }
                                }

                                Timer {
                                    id: gestureThresholdSave
                                    interval: 250
                                    repeat: false
                                    onTriggered: backend.setGestureThreshold(
                                        Math.round(gestureThresholdSlider.value / 5.0) * 5)
                                }

                                Text {
                                    text: s["mouse.swipe_actions"]
                                    font { family: uiState.fontFamily; pixelSize: 11;
                                           capitalization: Font.AllUppercase; letterSpacing: 1 }
                                    color: theme.textDim
                                }

                                RowLayout {
                                    width: parent.width
                                    spacing: 12

                                    Text {
                                        text: s["mouse.swipe_left"]
                                        Layout.preferredWidth: 100
                                        font { family: uiState.fontFamily; pixelSize: 12 }
                                        color: theme.textPrimary
                                    }

                                    ComboBox {
                                        Layout.fillWidth: true
                                        model: backend.allActions
                                        textRole: "label"
                                        delegate: actionComboDelegate
                                        Material.accent: theme.accent
                                        font { family: uiState.fontFamily; pixelSize: 11 }
                                        currentIndex: actionIndexForId(gestureLeftActionId)
                                        displayText: isCustomAction(gestureLeftActionId)
                                                     ? customLabel(gestureLeftActionId)
                                                     : (lm.strings, lm.trAction(currentText))
                                        onActivated: function(index) {
                                            var aid = backend.allActions[index].id
                                            if (aid === "__custom__") {
                                                keyCaptureDialog.open(selectedProfile, "gesture_left")
                                                return
                                            }
                                            backend.setProfileMapping(
                                                selectedProfile, "gesture_left", aid)
                                        }
                                    }
                                }

                                RowLayout {
                                    width: parent.width
                                    spacing: 12

                                    Text {
                                        text: s["mouse.swipe_right"]
                                        Layout.preferredWidth: 100
                                        font { family: uiState.fontFamily; pixelSize: 12 }
                                        color: theme.textPrimary
                                    }

                                    ComboBox {
                                        Layout.fillWidth: true
                                        model: backend.allActions
                                        textRole: "label"
                                        delegate: actionComboDelegate
                                        Material.accent: theme.accent
                                        font { family: uiState.fontFamily; pixelSize: 11 }
                                        currentIndex: actionIndexForId(gestureRightActionId)
                                        displayText: isCustomAction(gestureRightActionId)
                                                     ? customLabel(gestureRightActionId)
                                                     : (lm.strings, lm.trAction(currentText))
                                        onActivated: function(index) {
                                            var aid = backend.allActions[index].id
                                            if (aid === "__custom__") {
                                                keyCaptureDialog.open(selectedProfile, "gesture_right")
                                                return
                                            }
                                            backend.setProfileMapping(
                                                selectedProfile, "gesture_right", aid)
                                        }
                                    }
                                }

                                RowLayout {
                                    width: parent.width
                                    spacing: 12

                                    Text {
                                        text: s["mouse.swipe_up"]
                                        Layout.preferredWidth: 100
                                        font { family: uiState.fontFamily; pixelSize: 12 }
                                        color: theme.textPrimary
                                    }

                                    ComboBox {
                                        Layout.fillWidth: true
                                        model: backend.allActions
                                        textRole: "label"
                                        delegate: actionComboDelegate
                                        Material.accent: theme.accent
                                        font { family: uiState.fontFamily; pixelSize: 11 }
                                        currentIndex: actionIndexForId(gestureUpActionId)
                                        displayText: isCustomAction(gestureUpActionId)
                                                     ? customLabel(gestureUpActionId)
                                                     : (lm.strings, lm.trAction(currentText))
                                        onActivated: function(index) {
                                            var aid = backend.allActions[index].id
                                            if (aid === "__custom__") {
                                                keyCaptureDialog.open(selectedProfile, "gesture_up")
                                                return
                                            }
                                            backend.setProfileMapping(
                                                selectedProfile, "gesture_up", aid)
                                        }
                                    }
                                }

                                RowLayout {
                                    width: parent.width
                                    spacing: 12

                                    Text {
                                        text: s["mouse.swipe_down"]
                                        Layout.preferredWidth: 100
                                        font { family: uiState.fontFamily; pixelSize: 12 }
                                        color: theme.textPrimary
                                    }

                                    ComboBox {
                                        Layout.fillWidth: true
                                        model: backend.allActions
                                        textRole: "label"
                                        delegate: actionComboDelegate
                                        Material.accent: theme.accent
                                        font { family: uiState.fontFamily; pixelSize: 11 }
                                        currentIndex: actionIndexForId(gestureDownActionId)
                                        displayText: isCustomAction(gestureDownActionId)
                                                     ? customLabel(gestureDownActionId)
                                                     : (lm.strings, lm.trAction(currentText))
                                        onActivated: function(index) {
                                            var aid = backend.allActions[index].id
                                            if (aid === "__custom__") {
                                                keyCaptureDialog.open(selectedProfile, "gesture_down")
                                                return
                                            }
                                            backend.setProfileMapping(
                                                selectedProfile, "gesture_down", aid)
                                        }
                                    }
                                }
                            }

                            // Single button: categorized chips
                            Column {
                                width: parent.width
                                spacing: 14
                                visible: selectedButton !== ""
                                         && selectedButton !== "hscroll_left"
                                         && !(selectedButton === "gesture"
                                              && backend.supportsGestureDirections)

                                Text {
                                    visible: supportsMultiActionButton(selectedButton)
                                    text: s["mouse.click_action"] || "Click Action"
                                    font { family: uiState.fontFamily; pixelSize: 11;
                                           capitalization: Font.AllUppercase;
                                           letterSpacing: 1 }
                                    color: theme.textDim
                                }

                                Repeater {
                                    model: backend.actionCategories

                                    delegate: Column {
                                        width: parent.width
                                        spacing: 8

                                        Rectangle {
                                            width: parent.width
                                            height: modelData.category === "MousePro" ? 36 : 28
                                            radius: Theme.radiusSmall
                                            color: modelData.category === "MousePro"
                                                   ? theme.accentDim
                                                   : "transparent"
                                            border.width: modelData.category === "MousePro" ? 1 : 0
                                            border.color: theme.accent

                                            Text {
                                                anchors.centerIn: parent
                                                text: { var _lang = lm.strings; return lm.trCategory(modelData.category) }
                                                font { family: uiState.fontFamily; pixelSize: modelData.category === "MousePro" ? 12 : 11;
                                                       capitalization: Font.AllUppercase;
                                                       letterSpacing: 1;
                                                       bold: modelData.category === "MousePro" }
                                                color: modelData.category === "MousePro" ? theme.accent : theme.textDim
                                            }
                                        }

                                        Flow {
                                            width: parent.width; spacing: 8
                                            Repeater {
                                                model: modelData.actions
                                                delegate: ActionChip {
                                                    actionId: modelData.id
                                                    actionLabel: modelData.id === "__custom__" && isCustomAction(selectedActionId)
                                                                 ? customLabel(selectedActionId)
                                                                 : (lm.strings, lm.trAction(modelData.label))
                                                    isCurrent: modelData.id === "__custom__"
                                                               ? isCustomAction(selectedActionId)
                                                               : modelData.id === selectedActionId
                                                    isMousePro: modelData.category === "MousePro"
                                                    onPicked: function(aid) {
                                                        if (aid === "__custom__") {
                                                            keyCaptureDialog.open(selectedProfile, selectedButton)
                                                            return
                                                        }
                                                        backend.setProfileMapping(
                                                            selectedProfile,
                                                            selectedButton, aid)
                                                        selectedActionId = aid
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }

                                Column {
                                    width: parent.width
                                    spacing: 8
                                    visible: supportsMultiActionButton(selectedButton)

                                    Text {
                                        text: s["mouse.long_press_action"] || "Long Press Action"
                                        font { family: uiState.fontFamily; pixelSize: 11;
                                               capitalization: Font.AllUppercase;
                                               letterSpacing: 1 }
                                        color: theme.textDim
                                    }

                                    ComboBox {
                                        width: parent.width
                                        model: backend.allActions
                                        textRole: "label"
                                        delegate: actionComboDelegate
                                        currentIndex: actionIndexForId(selectedLongActionId)
                                        displayText: isCustomAction(selectedLongActionId)
                                                     ? customLabel(selectedLongActionId)
                                                     : (lm.strings, lm.trAction(currentText))
                                        onActivated: function(index) {
                                            var aid = backend.allActions[index].id
                                            var targetButton = longMappingKey(selectedButton)
                                            if (aid === "__custom__") {
                                                keyCaptureDialog.open(selectedProfile, targetButton)
                                                return
                                            }
                                            backend.setProfileMapping(
                                                selectedProfile,
                                                targetButton, aid)
                                            selectedLongActionId = aid
                                        }
                                    }
                                }
                            }

                            // ── DPI Presets editor (when cycle_dpi is selected)
                            Rectangle {
                                id: dpiPresetsCard
                                property int activeSlot: 0
                                readonly property var slotColors: ["#e8d44d", "#5da5e8", "#e8943a", "#e05daa"]
                                visible: selectedActionId === "cycle_dpi"
                                width: parent.width
                                height: dpiPresetsCol.implicitHeight + 28
                                radius: 12
                                color: Qt.rgba(0.5, 0.5, 0.5, 0.06)
                                border.width: 1
                                border.color: theme.border

                                Column {
                                    id: dpiPresetsCol
                                    anchors {
                                        left: parent.left; right: parent.right
                                        top: parent.top; margins: 14
                                    }
                                    spacing: 14

                                    Text {
                                        text: s["mouse.dpi_presets"] || "DPI Presets"
                                        font { family: uiState.fontFamily; pixelSize: 11;
                                               capitalization: Font.AllUppercase; letterSpacing: 1 }
                                        color: theme.textDim
                                    }

                                    // Slot pills row
                                    Row {
                                        spacing: 10
                                        Repeater {
                                            model: 4
                                            Rectangle {
                                                width: slotVal.implicitWidth + 24
                                                height: 32; radius: 8
                                                color: dpiPresetsCard.activeSlot === index
                                                       ? Qt.rgba(0.5, 0.5, 0.5, 0.14)
                                                       : "transparent"
                                                border.width: dpiPresetsCard.activeSlot === index ? 2 : 1
                                                border.color: dpiPresetsCard.slotColors[index]

                                                Text {
                                                    id: slotVal
                                                    anchors.centerIn: parent
                                                    text: {
                                                        var presets = backend.dpiPresets
                                                        return presets[index] !== undefined ? presets[index] : "---"
                                                    }
                                                    font { family: uiState.fontFamily; pixelSize: 13; bold: true }
                                                    color: dpiPresetsCard.slotColors[index]
                                                }

                                                // Active indicator dot
                                                Rectangle {
                                                    width: 5; height: 5; radius: 3
                                                    anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom; bottomMargin: 2 }
                                                    color: dpiPresetsCard.slotColors[index]
                                                    visible: {
                                                        var presets = backend.dpiPresets
                                                        return presets[index] !== undefined && presets[index] === backend.dpi
                                                    }
                                                }

                                                MouseArea {
                                                    anchors.fill: parent
                                                    cursorShape: Qt.PointingHandCursor
                                                    onClicked: {
                                                        dpiPresetsCard.activeSlot = index
                                                        var presets = backend.dpiPresets
                                                        if (presets[index] !== undefined)
                                                            dpiPresetSlider.value = presets[index]
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    // Slider for active slot
                                    Column {
                                        width: parent.width
                                        spacing: 6

                                        Row {
                                            spacing: 8
                                            Rectangle {
                                                width: 10; height: 10; radius: 5
                                                color: dpiPresetsCard.slotColors[dpiPresetsCard.activeSlot]
                                                anchors.verticalCenter: parent.verticalCenter
                                            }
                                            Text {
                                                text: (s["mouse.dpi_slot"] || "Slot %1: %2 DPI")
                                                      .replace("%1", dpiPresetsCard.activeSlot + 1)
                                                      .replace("%2", Math.round(dpiPresetSlider.value))
                                                font { family: uiState.fontFamily; pixelSize: 12; bold: true }
                                                color: dpiPresetsCard.slotColors[dpiPresetsCard.activeSlot]
                                            }
                                        }

                                        WheelSafeSlider {
                                            id: dpiPresetSlider
                                            width: parent.width
                                            from: backend.deviceDpiMin
                                            to: backend.deviceDpiMax
                                            stepSize: 50
                                            value: {
                                                var presets = backend.dpiPresets
                                                var idx = dpiPresetsCard.activeSlot
                                                return presets[idx] !== undefined ? presets[idx] : 1000
                                            }
                                            accentColor: dpiPresetsCard.slotColors[dpiPresetsCard.activeSlot]
                                            accentDimColor: Qt.rgba(0.5, 0.5, 0.5, 0.12)
                                            trackColor: theme.border
                                            onMoved: {
                                                backend.setDpiPreset(dpiPresetsCard.activeSlot, Math.round(value))
                                            }
                                        }

                                        Row {
                                            width: parent.width
                                            Text {
                                                text: backend.deviceDpiMin
                                                font { family: uiState.fontFamily; pixelSize: 10 }
                                                color: theme.textDim
                                            }
                                            Item { width: parent.width - minDpiLabel.implicitWidth - maxDpiLabel.implicitWidth; height: 1 }
                                            Text {
                                                id: maxDpiLabel
                                                text: backend.deviceDpiMax
                                                font { family: uiState.fontFamily; pixelSize: 10 }
                                                color: theme.textDim
                                            }
                                            Text {
                                                id: minDpiLabel
                                                visible: false
                                                text: backend.deviceDpiMin
                                            }
                                        }
                                    }

                                    Text {
                                        width: parent.width
                                        wrapMode: Text.WordWrap
                                        text: (s["mouse.press_button_to_cycle"] || "Press the button to cycle: %1")
                                              .replace("%1", (function() {
                                                  var p = backend.dpiPresets
                                                  var parts = []
                                                  for (var i = 0; i < p.length; i++)
                                                      parts.push(p[i])
                                                  return parts.join(" \u2192 ")
                                              })())
                                        font { family: uiState.fontFamily; pixelSize: 11 }
                                        color: theme.textSecondary
                                    }
                                }
                            }

                            Item { width: 1; height: 8 }
                        }
                    }

                    // ── Device info share card (always visible when connected)
                    Rectangle {
                        visible: backend.mouseConnected
                        width: parent.width - 64
                        anchors.horizontalCenter: parent.horizontalCenter
                        height: shareDevRow.implicitHeight + 24
                        radius: 14
                        color: theme.bgCard
                        border.width: 1
                        border.color: theme.border

                        Row {
                            id: shareDevRow
                            anchors.centerIn: parent
                            spacing: 10

                            Text {
                                text: s["mouse.share_device_details"] || "Help us support your mouse"
                                font { family: uiState.fontFamily; pixelSize: 12 }
                                color: theme.textSecondary
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            Rectangle {
                                width: shareDevBtnRow.implicitWidth + 20
                                height: 30; radius: 10
                                color: shareDevBtnMa.containsMouse
                                       ? Qt.rgba(0.36, 0.56, 0.95, 0.22)
                                       : Qt.rgba(0.36, 0.56, 0.95, 0.12)
                                anchors.verticalCenter: parent.verticalCenter

                                Row {
                                    id: shareDevBtnRow
                                    anchors.centerIn: parent
                                    spacing: 6

                                    Text {
                                        text: "\uD83D\uDCCB"
                                        font.pixelSize: 13
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                    Text {
                                        text: s["mouse.copy_device_info"] || "Copy device info"
                                        font { family: uiState.fontFamily; pixelSize: 11; bold: true }
                                        color: theme.accent
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                }

                                MouseArea {
                                    id: shareDevBtnMa
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        var info = backend.dumpDeviceInfo()
                                        if (info) {
                                            backend.copyToClipboard(info)
                                            backend.statusMessage(
                                                s["mouse.device_info_copied"] || "Device info copied to clipboard -- paste it into a GitHub issue!")
                                        } else {
                                            backend.statusMessage(
                                                s["mouse.no_device_connected"] || "No device connected")
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        width: parent.width - 64
                        anchors.horizontalCenter: parent.horizontalCenter
                        height: debugCol.implicitHeight + 24
                        radius: 14
                        color: theme.bgCard
                        border.width: 1
                        border.color: theme.border
                        visible: backend.debugMode

                        Column {
                            id: debugCol
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 12

                            RowLayout {
                                width: parent.width
                                spacing: 12

                                Column {
                                    Layout.fillWidth: true
                                    spacing: 3

                                    Text {
                                        text: s["mouse.debug_events"]
                                        font { family: uiState.fontFamily; pixelSize: 14; bold: true }
                                        color: theme.textPrimary
                                    }

                                    Text {
                                        text: s["mouse.debug_events_desc"]
                                        font { family: uiState.fontFamily; pixelSize: 11 }
                                        color: theme.textSecondary
                                    }
                                }

                                Switch {
                                    checked: backend.debugEventsEnabled
                                    text: checked ? s["mouse.on"] : s["mouse.off"]
                                    Material.accent: theme.accent
                                    onToggled: backend.setDebugEventsEnabled(checked)
                                }

                                Switch {
                                    checked: backend.recordMode
                                    text: checked ? s["mouse.rec"] : s["mouse.record"]
                                    Material.accent: "#e46f4e"
                                    onToggled: backend.setRecordMode(checked)
                                }

                                Rectangle {
                                    Layout.preferredWidth: clearText.implicitWidth + 20
                                    Layout.preferredHeight: 28
                                    radius: 8
                                    color: clearMa.containsMouse
                                           ? Qt.rgba(1, 1, 1, 0.08)
                                           : Qt.rgba(1, 1, 1, 0.04)

                                    Text {
                                        id: clearText
                                        anchors.centerIn: parent
                                        text: s["mouse.clear"]
                                        font { family: uiState.fontFamily; pixelSize: 11; bold: true }
                                        color: theme.textPrimary
                                    }

                                    MouseArea {
                                        id: clearMa
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: backend.clearDebugLog()
                                    }
                                }

                                Rectangle {
                                    Layout.preferredWidth: clearRecText.implicitWidth + 20
                                    Layout.preferredHeight: 28
                                    radius: 8
                                    color: clearRecMa.containsMouse
                                           ? Qt.rgba(1, 1, 1, 0.08)
                                           : Qt.rgba(1, 1, 1, 0.04)

                                    Text {
                                        id: clearRecText
                                        anchors.centerIn: parent
                                        text: s["mouse.clear_rec"]
                                        font { family: uiState.fontFamily; pixelSize: 11; bold: true }
                                        color: theme.textPrimary
                                    }

                                    MouseArea {
                                        id: clearRecMa
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: backend.clearGestureRecords()
                                    }
                                }

                                Rectangle {
                                    Layout.preferredWidth: copyDevInfoText.implicitWidth + 20
                                    Layout.preferredHeight: 28
                                    radius: 8
                                    color: copyDevInfoMa.containsMouse
                                           ? Qt.rgba(1, 1, 1, 0.08)
                                           : Qt.rgba(1, 1, 1, 0.04)

                                    Text {
                                        id: copyDevInfoText
                                        anchors.centerIn: parent
                                        text: s["mouse.copy_device_info"] || "Copy device info"
                                        font { family: uiState.fontFamily; pixelSize: 11; bold: true }
                                        color: theme.textPrimary
                                    }

                                    MouseArea {
                                        id: copyDevInfoMa
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            var info = backend.dumpDeviceInfo()
                                            if (info) {
                                                backend.copyToClipboard(info)
                                                backend.statusMessage(s["mouse.device_info_copied"] || "Device info copied to clipboard")
                                            } else {
                                                backend.statusMessage(s["mouse.no_device_connected"] || "No device connected")
                                            }
                                        }
                                    }
                                }
                            }

                            Rectangle {
                                width: parent.width
                                radius: 10
                                color: Qt.rgba(1, 1, 1, 0.03)
                                border.width: 1
                                border.color: theme.border
                                height: monitorCol.implicitHeight + 20

                                Column {
                                    id: monitorCol
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 8

                                    Text {
                                        text: s["mouse.live_gesture_monitor"]
                                        font { family: uiState.fontFamily; pixelSize: 11; bold: true }
                                        color: theme.textPrimary
                                    }

                                    Row {
                                        spacing: 8

                                        Rectangle {
                                            width: activeText.implicitWidth + 16
                                            height: 24
                                            radius: 12
                                            color: backend.gestureActive
                                                   ? Qt.rgba(0.89, 0.45, 0.25, 0.18)
                                                   : Qt.rgba(1, 1, 1, 0.05)

                                            Text {
                                                id: activeText
                                                anchors.centerIn: parent
                                                text: backend.gestureActive ? s["mouse.held"] : s["mouse.idle"]
                                                font { family: uiState.fontFamily; pixelSize: 11; bold: true }
                                                color: backend.gestureActive ? "#f39c6b" : theme.textSecondary
                                            }
                                        }

                                        Rectangle {
                                            width: moveText.implicitWidth + 16
                                            height: 24
                                            radius: 12
                                            color: backend.gestureMoveSeen
                                                   ? Qt.rgba(0.36, 0.56, 0.95, 0.12)
                                                   : Qt.rgba(1, 1, 1, 0.05)

                                            Text {
                                                id: moveText
                                                anchors.centerIn: parent
                                                text: backend.gestureMoveSeen ? s["mouse.move_seen"] : s["mouse.no_move"]
                                                font { family: uiState.fontFamily; pixelSize: 11; bold: true }
                                                color: backend.gestureMoveSeen ? theme.accent : theme.textSecondary
                                            }
                                        }
                                    }

                                    Text {
                                        text: (s["mouse.source"] || "Source") + ": "
                                              + (backend.gestureMoveSource ? backend.gestureMoveSource : (s["mouse.not_available"] || "n/a"))
                                              + " | dx: " + backend.gestureMoveDx
                                              + " | dy: " + backend.gestureMoveDy
                                        font { family: uiState.monospaceFontFamily; pixelSize: 11 }
                                        color: theme.textSecondary
                                    }

                                    Text {
                                        text: backend.gestureStatus
                                        font { family: uiState.fontFamily; pixelSize: 11 }
                                        color: theme.textPrimary
                                        wrapMode: Text.Wrap
                                    }
                                }
                            }

                            Rectangle {
                                width: parent.width
                                height: 160
                                radius: 10
                                color: Qt.rgba(0, 0, 0, 0.18)
                                border.width: 1
                                border.color: theme.border

                                ScrollView {
                                    anchors.fill: parent
                                    anchors.margins: 1
                                    clip: true

                                    TextArea {
                                        id: debugLogArea
                                        text: backend.debugLog.length
                                              ? backend.debugLog
                                              : s["mouse.debug_placeholder"]
                                        readOnly: true
                                        wrapMode: TextEdit.NoWrap
                                        selectByMouse: true
                                        color: backend.debugLog.length
                                               ? theme.textPrimary
                                               : theme.textSecondary
                                        font.pixelSize: 11
                                        font.family: uiState.monospaceFontFamily
                                        background: null
                                        padding: 10

                                        onTextChanged: {
                                            cursorPosition = length
                                        }
                                    }
                                }
                            }

                            Rectangle {
                                width: parent.width
                                height: 180
                                radius: 10
                                color: Qt.rgba(0, 0, 0, 0.18)
                                border.width: 1
                                border.color: theme.border

                                ScrollView {
                                    anchors.fill: parent
                                    anchors.margins: 1
                                    clip: true

                                    TextArea {
                                        text: backend.gestureRecords.length
                                              ? backend.gestureRecords
                                              : s["mouse.gesture_placeholder"]
                                        readOnly: true
                                        wrapMode: TextEdit.Wrap
                                        selectByMouse: true
                                        color: backend.gestureRecords.length
                                               ? theme.textPrimary
                                               : theme.textSecondary
                                        font.pixelSize: 11
                                        font.family: uiState.monospaceFontFamily
                                        background: null
                                        padding: 10
                                    }
                                }
                            }
                        }
                    }

                    Item { width: 1; height: 24 }
                }
            }
        }
    }

    Dialog {
        id: addAppDialog
        parent: Overlay.overlay
        modal: true
        focus: true
        title: ""
        width: 680
        height: 460
        x: Math.round((parent.width - width) / 2)
        y: Math.round((parent.height - height) / 2)
        padding: 0
        property bool searching: appSearchText.trim().length > 0
        property var visibleApps: searching ? filteredKnownApps : suggestedKnownApps

        function ensureSelection() {
            var apps = visibleApps || []
            if (!apps.length) {
                selectedKnownApp = null
                return
            }

            if (!selectedKnownApp || !selectedKnownApp.id) {
                selectedKnownApp = apps[0]
                return
            }

            for (var i = 0; i < apps.length; i++) {
                if (apps[i].id === selectedKnownApp.id)
                    return
            }

            selectedKnownApp = apps[0]
        }

        function selectedIndex() {
            var apps = visibleApps || []
            if (!selectedKnownApp || !selectedKnownApp.id)
                return -1
            for (var i = 0; i < apps.length; i++) {
                if (apps[i].id === selectedKnownApp.id)
                    return i
            }
            return -1
        }

        function moveSelection(delta) {
            var apps = visibleApps || []
            if (!apps.length)
                return

            var current = selectedIndex()
            if (current === -1)
                current = 0

            var next = current + delta
            if (next < 0)
                next = 0
            if (next >= apps.length)
                next = apps.length - 1

            selectedKnownApp = apps[next]
            if (appResultsList)
                appResultsList.positionViewAtIndex(next, ListView.Contain)
        }

        onOpened: {
            if (appSearchInput) {
                appSearchInput.text = ""
                appSearchInput.forceActiveFocus()
            }
            refreshSuggestedApps()
            refreshAppSearch()
            ensureSelection()
            backend.refreshKnownAppsSilently()
        }
        onVisibleAppsChanged: ensureSelection()

        background: Rectangle {
            radius: Theme.radiusLarge
            color: theme.bgElevated
            border.width: 1
            border.color: theme.border
        }

        contentItem: Item {
            width: addAppDialog.width
            height: addAppDialog.height

            Item {
                id: addDialogHeader
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.topMargin: Theme.space16
                anchors.leftMargin: Theme.space20
                anchors.rightMargin: Theme.space20
                height: 42

                Column {
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 3

                    Text {
                        text: s["mouse.add_app_dialog.title"]
                        font { family: uiState.fontFamily; pixelSize: 18; bold: true }
                        color: theme.textPrimary
                    }

                    Text {
                        text: s["mouse.add_app_dialog.desc"]
                        font { family: uiState.fontFamily; pixelSize: 12 }
                        color: theme.textSecondary
                    }
                }

                Rectangle {
                    width: 34
                    height: 34
                    radius: Theme.radiusControl
                    anchors.right: parent.right
                    anchors.rightMargin: 0
                    anchors.verticalCenter: parent.verticalCenter
                    color: closeAddDialogMa.containsMouse
                           ? Qt.rgba(1, 1, 1, uiState.darkMode ? 0.08 : 0.65)
                           : "transparent"

                    AppIcon {
                        anchors.centerIn: parent
                        width: 16
                        height: 16
                        name: "x"
                        iconColor: theme.textSecondary
                    }

                    MouseArea {
                        id: closeAddDialogMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: addAppDialog.close()
                    }
                }
            }

            Rectangle {
                id: searchField
                anchors.top: addDialogHeader.bottom
                anchors.topMargin: 12
                anchors.left: parent.left
                anchors.leftMargin: Theme.space20
                anchors.right: browseButton.left
                anchors.rightMargin: 12
                height: 40
                radius: Theme.radiusControl
                color: theme.bgSubtle
                border.width: 1
                border.color: appSearchInput.activeFocus ? theme.accent : theme.border

                TextInput {
                    id: appSearchInput
                    anchors.fill: parent
                    anchors.leftMargin: 16
                    anchors.rightMargin: 16
                    color: theme.textPrimary
                    font { family: uiState.fontFamily; pixelSize: 12 }
                    verticalAlignment: TextInput.AlignVCenter
                    selectByMouse: true
                    clip: true

                    onTextChanged: {
                        appSearchText = text
                        refreshAppSearch()
                        addAppDialog.ensureSelection()
                    }

                    Keys.onPressed: function(event) {
                        if (event.key === Qt.Key_Down) {
                            addAppDialog.moveSelection(1)
                            event.accepted = true
                        } else if (event.key === Qt.Key_Up) {
                            addAppDialog.moveSelection(-1)
                            event.accepted = true
                        } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                            if (selectedKnownApp) {
                                backend.addProfile(selectedKnownApp.id)
                                addAppDialog.close()
                            }
                            event.accepted = true
                        }
                    }
                }

                    Text {
                        anchors.left: parent.left
                        anchors.leftMargin: 16
                        anchors.verticalCenter: parent.verticalCenter
                        text: s["mouse.search_placeholder"]
                        font { family: uiState.fontFamily; pixelSize: 12 }
                        color: theme.textDim
                        visible: !appSearchInput.text.length
                    }
            }

            Rectangle {
                id: browseButton
                anchors.top: searchField.top
                anchors.right: parent.right
                anchors.rightMargin: Theme.space20
                width: 104
                height: 40
                radius: Theme.radiusControl
                color: browseDialogMa.containsMouse
                       ? Qt.rgba(1, 1, 1, uiState.darkMode ? 0.08 : 0.55)
                       : theme.bgSubtle
                border.width: 1
                border.color: theme.border

                    Text {
                        anchors.centerIn: parent
                        text: s["mouse.browse"]
                        font { family: uiState.fontFamily; pixelSize: 12; bold: true }
                        color: theme.textPrimary
                    }

                MouseArea {
                    id: browseDialogMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        addAppDialog.close()
                        backend.browseForAppProfile()
                    }
                }
            }

            Item {
                id: resultsBlock
                anchors.top: searchField.bottom
                anchors.topMargin: Theme.space16
                anchors.left: parent.left
                anchors.leftMargin: Theme.space20
                anchors.right: parent.right
                anchors.rightMargin: Theme.space20
                anchors.bottom: footerRow.top
                anchors.bottomMargin: Theme.space16

                Row {
                    id: resultsHeader
                    anchors.top: parent.top
                    anchors.left: parent.left
                    height: 22
                    spacing: Theme.space8

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: addAppDialog.searching ? s["mouse.search_results"] : s["mouse.suggested_apps"]
                        font { family: uiState.fontFamily; pixelSize: 11; bold: true }
                        color: theme.textPrimary
                    }

                    Rectangle {
                        width: resultCountText.implicitWidth + 16
                        height: 22
                        radius: 11
                        color: Qt.rgba(0.36, 0.56, 0.95, uiState.darkMode ? 0.12 : 0.14)

                        Text {
                            id: resultCountText
                            anchors.centerIn: parent
                            text: addAppDialog.visibleApps.length
                            font { family: uiState.fontFamily; pixelSize: 10; bold: true }
                            color: theme.accent
                        }
                    }
                }

                Rectangle {
                    anchors.top: resultsHeader.bottom
                    anchors.topMargin: Theme.space8
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    radius: Theme.radius
                    color: theme.bg
                    border.width: 1
                    border.color: theme.border

                    ListView {
                        id: appResultsList
                        anchors.fill: parent
                        anchors.margins: Theme.space8
                        clip: true
                        model: addAppDialog.visibleApps
                        spacing: Theme.space4
                        visible: addAppDialog.visibleApps.length > 0
                        boundsBehavior: Flickable.StopAtBounds

                        delegate: Rectangle {
                            width: ListView.view.width
                            height: 52
                            radius: Theme.radiusControl
                            color: selectedKnownApp && selectedKnownApp.id === modelData.id
                                   ? Qt.rgba(0.36, 0.56, 0.95, uiState.darkMode ? 0.16 : 0.12)
                                   : appRowMa.containsMouse
                                     ? Qt.rgba(1, 1, 1, uiState.darkMode ? 0.06 : 0.6)
                                     : "transparent"
                            border.width: selectedKnownApp && selectedKnownApp.id === modelData.id ? 1 : 0
                            border.color: theme.accent

                            Row {
                                anchors.fill: parent
                                anchors.leftMargin: 14
                                anchors.rightMargin: 14
                                spacing: 12

                                Image {
                                    anchors.verticalCenter: parent.verticalCenter
                                    source: modelData.iconSource || ""
                                    width: 24
                                    height: 24
                                    sourceSize.width: 24
                                    sourceSize.height: 24
                                    fillMode: Image.PreserveAspectFit
                                    smooth: true
                                    visible: source !== ""
                                }

                                Column {
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 2

                                    Text {
                                        text: modelData.label || ""
                                        font { family: uiState.fontFamily; pixelSize: 13; bold: true }
                                        color: theme.textPrimary
                                        elide: Text.ElideRight
                                        width: 470
                                    }

                                    Text {
                                        text: appLocationLabel(modelData)
                                        font { family: uiState.fontFamily; pixelSize: 10 }
                                        color: theme.textSecondary
                                        elide: Text.ElideRight
                                        width: 470
                                    }
                                }

                                Item {
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: 1
                                    height: 1
                                }
                            }

                            MouseArea {
                                id: appRowMa
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: selectedKnownApp = modelData
                                onDoubleClicked: {
                                    selectedKnownApp = modelData
                                    backend.addProfile(modelData.id)
                                    addAppDialog.close()
                                }
                            }
                        }
                    }

                    Column {
                        width: parent.width - 48
                        anchors.centerIn: parent
                        spacing: 8
                        visible: addAppDialog.visibleApps.length === 0

                        Text {
                            width: parent.width
                            horizontalAlignment: Text.AlignHCenter
                            text: addAppDialog.searching
                                  ? s["mouse.no_matched"]
                                  : s["mouse.no_suggested"]
                            font { family: uiState.fontFamily; pixelSize: 13; bold: true }
                            color: theme.textPrimary
                            wrapMode: Text.WordWrap
                        }

                        Text {
                            width: parent.width
                            horizontalAlignment: Text.AlignHCenter
                            text: addAppDialog.searching
                                  ? s["mouse.try_different"]
                                  : s["mouse.use_search"]
                            font { family: uiState.fontFamily; pixelSize: 11 }
                            color: theme.textSecondary
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }

            Item {
                id: footerRow
                anchors.left: parent.left
                anchors.leftMargin: Theme.space20
                anchors.right: parent.right
                anchors.rightMargin: Theme.space20
                anchors.bottom: parent.bottom
                anchors.bottomMargin: Theme.space20
                height: 40

                Rectangle {
                    id: createButton
                    anchors.right: parent.right
                    width: 144
                    height: parent.height
                    radius: Theme.radiusControl
                    color: selectedKnownApp
                           ? (createDialogMa.containsMouse ? theme.accentHover : theme.accent)
                           : Qt.rgba(0.36, 0.56, 0.95, 0.22)

                    Text {
                        anchors.centerIn: parent
                        text: s["mouse.create_profile"]
                        font { family: uiState.fontFamily; pixelSize: 12; bold: true }
                        color: selectedKnownApp ? theme.bgSidebar : theme.textSecondary
                    }

                    MouseArea {
                        id: createDialogMa
                        anchors.fill: parent
                        enabled: !!selectedKnownApp
                        hoverEnabled: enabled
                        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: {
                            if (selectedKnownApp) {
                                backend.addProfile(selectedKnownApp.id)
                                addAppDialog.close()
                            }
                        }
                    }
                }

                Rectangle {
                    anchors.right: createButton.left
                    anchors.rightMargin: Theme.space8
                    width: 100
                    height: parent.height
                    radius: Theme.radiusControl
                    color: cancelDialogMa.containsMouse
                           ? Qt.rgba(1, 1, 1, uiState.darkMode ? 0.08 : 0.55)
                           : theme.bgSubtle
                    border.width: 1
                    border.color: theme.border

                    Text {
                        anchors.centerIn: parent
                        text: s["mouse.cancel"]
                        font { family: uiState.fontFamily; pixelSize: 12; bold: true }
                        color: theme.textPrimary
                    }

                    MouseArea {
                        id: cancelDialogMa
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: addAppDialog.close()
                    }
                }
            }
        }
    }

    Dialog {
        id: deleteDialog
        parent: Overlay.overlay
        modal: true
        focus: true
        title: s["mouse.delete_dialog.title"]
        width: 380
        x: Math.round((parent.width - width) / 2)
        y: Math.round((parent.height - height) / 2)
        standardButtons: Dialog.Ok | Dialog.Cancel

        function confirmDelete() {
            if (pendingDeleteProfile && pendingDeleteProfile !== "default") {
                backend.deleteProfile(pendingDeleteProfile)
                selectProfile(backend.activeProfile)
            }
            pendingDeleteProfile = ""
        }

        function cancelDelete() {
            pendingDeleteProfile = ""
        }

        onAccepted: confirmDelete()
        onRejected: cancelDelete()

        contentItem: Column {
            width: deleteDialog.availableWidth
            spacing: 10

            Text {
                width: parent.width
                text: pendingDeleteProfile
                      ? (s["mouse.delete_dialog.confirm_prefix"] || "Delete the profile for ")
                        + selectedProfileLabel
                        + (s["mouse.delete_dialog.confirm_suffix"] || "?")
                      : ""
                font { family: uiState.fontFamily; pixelSize: 13; bold: true }
                color: theme.textPrimary
                wrapMode: Text.WordWrap
            }

            Text {
                width: parent.width
                text: s["mouse.delete_dialog.desc"]
                font { family: uiState.fontFamily; pixelSize: 12 }
                color: theme.textSecondary
                wrapMode: Text.WordWrap
            }
        }
    }

    // ── Key capture dialog for custom shortcuts ──────────────
    KeyCaptureDialog {
        id: keyCaptureDialog
        onCaptured: function(comboString) {
            backend.setProfileMapping(
                keyCaptureDialog.targetProfile,
                keyCaptureDialog.targetButton,
                "custom:" + comboString)
            refreshSelectedProfileMappings()
            if (keyCaptureDialog.targetButton.indexOf("_long") === keyCaptureDialog.targetButton.length - 5)
                selectedLongActionId = "custom:" + comboString
            else
                selectedActionId = "custom:" + comboString
        }
    }
}
