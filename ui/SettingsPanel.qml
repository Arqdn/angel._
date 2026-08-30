// Settings: a dark pane that slides in from the right. Custom minimal
// controls (no stock widget styling). Every change is saved immediately
// through angel.saveSettings — secrets never appear here, only status.

import QtQuick
import QtQuick.Window

Item {
    id: panel
    property bool open: false
    width: 380
    visible: x < parent.width
    x: open ? parent.width - width : parent.width
    Behavior on x { NumberAnimation { duration: 320; easing.type: Easing.OutCubic } }

    property var cfg: ({})
    function reload() {
        try { cfg = JSON.parse(angel.settingsJson) } catch (e) { cfg = {} }
    }
    Component.onCompleted: reload()
    Connections {
        target: angel
        function onSettingsJsonChanged() { panel.reload() }
    }
    function save(key, value) {
        var change = {}
        change[key] = value
        angel.saveSettings(JSON.stringify(change))
    }

    // ------------------------------------------------------ custom controls
    component SectionLabel: Text {
        color: "#8a744d"
        font.family: "Palatino Linotype"
        font.pixelSize: 12
        font.letterSpacing: 3
        topPadding: 14
    }

    component RowLabel: Text {
        color: "#c9bda2"
        font.family: "Segoe UI"
        font.pixelSize: 12
        elide: Text.ElideRight
    }

    component Toggle: Item {
        id: toggle
        property bool checked: false
        signal toggled(bool value)
        width: 34; height: 18
        Rectangle {
            anchors.fill: parent
            radius: height / 2
            color: toggle.checked ? "#4a3d26" : "#1a1712"
            border.color: toggle.checked ? "#d9b571" : "#3d3527"
            border.width: 1
            Behavior on color { ColorAnimation { duration: 180 } }
        }
        Rectangle {
            width: 12; height: 12; radius: 6
            y: 3
            x: toggle.checked ? parent.width - width - 3 : 3
            color: toggle.checked ? "#efe6d5" : "#6d6353"
            Behavior on x { NumberAnimation { duration: 180; easing.type: Easing.OutQuad } }
        }
        MouseArea {
            anchors.fill: parent
            anchors.margins: -6
            cursorShape: Qt.PointingHandCursor
            onClicked: { toggle.checked = !toggle.checked; toggle.toggled(toggle.checked) }
        }
    }

    component ThinSlider: Item {
        id: slider
        property real value: 0.5
        property real from: 0
        property real to: 1
        signal moved(real value)
        width: 150; height: 18
        readonly property real ratio: (value - from) / (to - from)
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width; height: 2; radius: 1
            color: "#2a2419"
        }
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width * Math.max(0, Math.min(1, slider.ratio))
            height: 2; radius: 1
            color: "#d9b571"
        }
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            x: parent.width * Math.max(0, Math.min(1, slider.ratio)) - 5
            width: 10; height: 10; radius: 5
            color: "#efe6d5"
        }
        MouseArea {
            anchors.fill: parent
            anchors.margins: -6
            cursorShape: Qt.PointingHandCursor
            function apply(mx) {
                var r = Math.max(0, Math.min(1, mx / slider.width))
                slider.value = slider.from + r * (slider.to - slider.from)
                slider.moved(slider.value)
            }
            onPressed: function(mouse) { apply(mouse.x) }
            onPositionChanged: function(mouse) { if (pressed) apply(mouse.x) }
        }
    }

    component ChoiceRow: Row {
        id: choice
        property var options: []
        property string current: ""
        signal chosen(string value)
        spacing: 10
        Repeater {
            model: choice.options
            Text {
                required property string modelData
                text: modelData
                color: modelData === choice.current ? "#efe6d5" : "#5a4f3d"
                font.family: "Segoe UI"
                font.pixelSize: 12
                font.underline: modelData === choice.current
                MouseArea {
                    anchors.fill: parent
                    anchors.margins: -4
                    cursorShape: Qt.PointingHandCursor
                    onClicked: { choice.current = modelData; choice.chosen(modelData) }
                }
            }
        }
    }

    // ------------------------------------------------------------- the pane
    Rectangle {
        anchors.fill: parent
        color: "#0b0907"
        opacity: 0.97
        border.color: "#2a2419"
        border.width: 1
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: 26
        contentHeight: content.height + 40
        clip: true

        Column {
            id: content
            width: parent.width
            spacing: 12

            Text {
                text: "S E T T I N G S"
                color: "#efe6d5"
                font.family: "Palatino Linotype"
                font.pixelSize: 15
                font.letterSpacing: 4
            }

            // ------------------------------------------------------- keys
            SectionLabel { text: "K E Y S" }
            RowLabel {
                text: (panel.cfg["keys.openrouter"] ? "◆" : "◇") +
                      "  OpenRouter key " +
                      (panel.cfg["keys.openrouter"] ? "present" : "missing — add to .env")
                color: panel.cfg["keys.openrouter"] ? "#c9bda2" : "#c98263"
            }
            RowLabel {
                text: (panel.cfg["keys.fish"] ? "◆" : "◇") +
                      "  Fish Audio key " +
                      (panel.cfg["keys.fish"] ? "present" : "missing — add to .env")
                color: panel.cfg["keys.fish"] ? "#c9bda2" : "#c98263"
            }

            // ------------------------------------------------------ voice
            SectionLabel { text: "V O I C E" }
            Row {
                spacing: 12
                RowLabel { text: "voice enabled"; width: 150 }
                Toggle {
                    checked: panel.cfg["tts.enabled"] !== false
                    onToggled: function(v) { panel.save("tts.enabled", v) }
                }
            }
            Column {
                spacing: 4
                RowLabel { text: "Fish voice reference ID (male voice)" }
                Rectangle {
                    width: content.width; height: 28; radius: 3
                    color: "#14100c"; border.color: "#2a2419"; border.width: 1
                    TextInput {
                        id: refInput
                        anchors.fill: parent
                        anchors.margins: 7
                        color: "#e8dfcc"
                        font.family: "Consolas"
                        font.pixelSize: 12
                        clip: true
                        selectByMouse: true
                        text: panel.cfg["tts.reference_id"] || ""
                        onEditingFinished: panel.save("tts.reference_id", text.trim())
                    }
                }
                RowLabel {
                    text: "leave empty for the default male voice"
                    color: "#5a4f3d"; font.pixelSize: 10; font.italic: true
                }
            }
            Row {
                spacing: 12
                RowLabel { text: "voice volume"; width: 150 }
                ThinSlider {
                    value: panel.cfg["tts.volume"] !== undefined ? panel.cfg["tts.volume"] : 0.9
                    onMoved: function(v) { panel.save("tts.volume", Math.round(v * 100) / 100) }
                }
            }

            // ---------------------------------------------------- hearing
            SectionLabel { text: "H E A R I N G" }
            Row {
                spacing: 12
                RowLabel { text: "wake word  “Angel”"; width: 150 }
                Toggle {
                    checked: panel.cfg["wake.enabled"] !== false
                    onToggled: function(v) { panel.save("wake.enabled", v) }
                }
            }
            Row {
                spacing: 12
                RowLabel { text: "push-to-talk (Space)"; width: 150 }
                Toggle {
                    checked: panel.cfg["wake.push_to_talk_enabled"] !== false
                    onToggled: function(v) { panel.save("wake.push_to_talk_enabled", v) }
                }
            }
            Row {
                spacing: 12
                RowLabel { text: "speech sensitivity"; width: 150 }
                ThinSlider {
                    value: panel.cfg["audio.vad_sensitivity"] !== undefined
                           ? panel.cfg["audio.vad_sensitivity"] : 0.5
                    onMoved: function(v) { panel.save("audio.vad_sensitivity", Math.round(v * 100) / 100) }
                }
            }
            Column {
                spacing: 4
                RowLabel { text: "microphone" }
                Column {
                    spacing: 2
                    Repeater {
                        model: angel ? angel.micDevices : []
                        Text {
                            required property var modelData
                            readonly property bool selected:
                                panel.cfg["audio.input_device"] === modelData.index ||
                                (panel.cfg["audio.input_device"] === null && modelData.default)
                            text: (selected ? "◆ " : "◇ ") + modelData.name
                            color: selected ? "#efe6d5" : "#6d6353"
                            font.family: "Segoe UI"
                            font.pixelSize: 11
                            width: content.width
                            elide: Text.ElideRight
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: panel.save("audio.input_device", modelData.index)
                            }
                        }
                    }
                    RowLabel {
                        visible: !angel || angel.micDevices.length === 0
                        text: "no input devices found"
                        color: "#c98263"; font.pixelSize: 11
                    }
                }
                RowLabel {
                    text: "device changes apply after restart"
                    color: "#5a4f3d"; font.pixelSize: 10; font.italic: true
                }
            }

            // ------------------------------------------------ personality
            SectionLabel { text: "P E R S O N A L I T Y" }
            Row {
                spacing: 12
                RowLabel { text: "celestial intensity"; width: 150 }
                ThinSlider {
                    value: panel.cfg["personality.intensity"] !== undefined
                           ? panel.cfg["personality.intensity"] : 0.7
                    onMoved: function(v) { panel.save("personality.intensity", Math.round(v * 100) / 100) }
                }
            }
            Row {
                spacing: 12
                RowLabel { text: "verbosity"; width: 150 }
                ChoiceRow {
                    options: ["terse", "balanced", "detailed"]
                    current: panel.cfg["personality.verbosity"] || "balanced"
                    onChosen: function(v) { panel.save("personality.verbosity", v) }
                }
            }

            // ----------------------------------------------------- safety
            SectionLabel { text: "S A F E T Y" }
            Row {
                spacing: 12
                RowLabel { text: "confirm dangerous acts"; width: 150 }
                Toggle {
                    checked: panel.cfg["safety.require_confirmation"] !== false
                    onToggled: function(v) { panel.save("safety.require_confirmation", v) }
                }
            }

            // ------------------------------------------------- appearance
            SectionLabel { text: "A P P E A R A N C E" }
            Row {
                spacing: 12
                RowLabel { text: "fullscreen"; width: 150 }
                Toggle {
                    checked: panel.cfg["ui.fullscreen"] !== false
                    onToggled: function(v) {
                        panel.save("ui.fullscreen", v)
                        panel.Window.window.visibility =
                            v ? Window.FullScreen : Window.Maximized
                    }
                }
            }
            Row {
                spacing: 12
                RowLabel { text: "particle density"; width: 150 }
                ThinSlider {
                    from: 0; to: 1.5
                    value: panel.cfg["ui.particle_density"] !== undefined
                           ? panel.cfg["ui.particle_density"] : 1.0
                    onMoved: function(v) { panel.save("ui.particle_density", Math.round(v * 100) / 100) }
                }
            }
            Row {
                spacing: 12
                RowLabel { text: "reduce motion"; width: 150 }
                Toggle {
                    checked: panel.cfg["ui.reduce_motion"] === true
                    onToggled: function(v) { panel.save("ui.reduce_motion", v) }
                }
            }

            // ----------------------------------------------------- system
            SectionLabel { text: "S Y S T E M" }
            Row {
                spacing: 12
                RowLabel { text: "start with Windows"; width: 150 }
                Toggle {
                    checked: panel.cfg["app.auto_start"] === true
                    onToggled: function(v) { panel.save("app.auto_start", v) }
                }
            }

            Item { width: 1; height: 12 }
            Rectangle {
                width: 130; height: 32; radius: 3
                color: quitMouse.containsMouse ? "#231412" : "#160f0d"
                border.color: "#5a3d33"; border.width: 1
                Text {
                    anchors.centerIn: parent
                    text: "Q U I T   A N G E L"
                    color: "#c98263"
                    font.family: "Segoe UI"; font.pixelSize: 10; font.letterSpacing: 2
                }
                MouseArea {
                    id: quitMouse
                    anchors.fill: parent; hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: angel.quitAngel()
                }
            }
        }
    }
}
