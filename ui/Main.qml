// Angel — main scene.
// An ancient celestial being living inside the computer: near-black ground,
// ivory light, warm gold, enormous wings. The angel IS the interface.

import QtQuick
import QtQuick.Window

Window {
    id: root
    visible: true
    title: "Angel"
    color: "#050403"

    // ---------------------------------------------------------------- state
    // angel.state: setup | idle | listening | thinking | speaking | confirming | error
    readonly property string angelState: angel ? angel.state : "setup"
    readonly property real micLevel: angel ? angel.micLevel : 0
    readonly property real voiceLevel: angel ? angel.voiceLevel : 0

    property var cfg: ({})
    function reloadCfg() {
        try { cfg = JSON.parse(angel.settingsJson) } catch (e) { cfg = {} }
    }
    Component.onCompleted: {
        reloadCfg()
        root.visibility = (cfg["ui.fullscreen"] === false)
            ? Window.Maximized : Window.FullScreen
    }
    Connections {
        target: angel
        function onSettingsJsonChanged() { root.reloadCfg() }
    }
    readonly property bool reduceMotion: cfg["ui.reduce_motion"] === true
    readonly property real particleDensity:
        cfg["ui.particle_density"] !== undefined ? cfg["ui.particle_density"] : 1.0

    // One smoothed "energy" value 0..1 drives the whole scene.
    // Audio-reactive: voice amplitude while speaking, mic level while listening.
    readonly property real targetEnergy: {
        switch (angelState) {
        case "speaking":   return 0.35 + 0.65 * Math.min(1, voiceLevel * 1.6)
        case "listening":  return 0.30 + 0.50 * Math.min(1, micLevel * 1.3)
        case "thinking":   return 0.55
        case "confirming": return 0.45
        case "error":      return 0.25
        default:           return 0.12
        }
    }
    property real energy: 0.12
    Behavior on energy {
        NumberAnimation { duration: 140; easing.type: Easing.OutQuad }
    }
    onTargetEnergyChanged: energy = targetEnergy

    // ------------------------------------------------------------ background
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0a0806" }
            GradientStop { position: 0.45; color: "#060504" }
            GradientStop { position: 1.0; color: "#030202" }
        }
    }

    // Faint warm ground haze behind the angel.
    Image {
        source: assetsUrl + "/angel/glow.png"
        anchors.centerIn: parent
        anchors.verticalCenterOffset: root.height * 0.06
        width: root.width * 1.25
        height: root.height * 1.1
        opacity: 0.05 + 0.06 * root.energy
        fillMode: Image.Stretch
    }

    FogLayer {
        anchors.fill: parent
        energy: root.energy
        reduceMotion: root.reduceMotion
    }

    LightRays {
        anchors.fill: parent
        energy: root.energy
        angelState: root.angelState
        reduceMotion: root.reduceMotion
    }

    // ------------------------------------------------------------- the angel
    AngelVisual {
        id: figure
        anchors.centerIn: parent
        anchors.verticalCenterOffset: -root.height * 0.03
        width: Math.min(root.width * 0.95, root.height * 1.35)
        height: root.height * 0.86
        energy: root.energy
        angelState: root.angelState
        reduceMotion: root.reduceMotion
    }

    ParticleField {
        anchors.fill: parent
        energy: root.energy
        angelState: root.angelState
        density: root.particleDensity
        reduceMotion: root.reduceMotion
        centerX: figure.x + figure.width / 2
        centerY: figure.y + figure.height * 0.42
    }

    // ------------------------------------------------------- film grain, vignette
    Image {
        anchors.fill: parent
        source: assetsUrl + "/angel/noise.png"
        fillMode: Image.Tile
        opacity: 0.05
    }
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0.0; color: "#66000000" }
            GradientStop { position: 0.25; color: "#00000000" }
            GradientStop { position: 0.75; color: "#00000000" }
            GradientStop { position: 1.0; color: "#88000000" }
        }
    }

    // -------------------------------------------------------------- overlays
    StatusText {
        id: statusText
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: waveform.top
        anchors.bottomMargin: 26
        angelState: root.angelState
        errorText: angel ? angel.errorText : ""
        statusLine: angel ? angel.status : ""
    }

    Waveform {
        id: waveform
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: conversation.top
        anchors.bottomMargin: 18
        width: Math.min(420, root.width * 0.4)
        height: 26
        level: root.angelState === "speaking" ? root.voiceLevel
             : (root.angelState === "listening" ? root.micLevel : 0)
        active: root.angelState === "speaking" || root.angelState === "listening"
        reduceMotion: root.reduceMotion
    }

    // Microphone indicator — a small breathing point of light while listening.
    Rectangle {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: waveform.top
        anchors.bottomMargin: 8
        width: 5; height: 5; radius: 2.5
        color: "#efe6d5"
        opacity: root.angelState === "listening" ? 0.55 + 0.4 * root.micLevel : 0
        Behavior on opacity { NumberAnimation { duration: 300 } }
    }

    // ------------------------------------------------------ conversation text
    Column {
        id: conversation
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: typedInput.top
        anchors.bottomMargin: 14
        width: Math.min(760, root.width * 0.7)
        spacing: 8
        visible: cfg["ui.show_conversation"] !== false

        Text {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.Wrap
            text: angel ? angel.userText : ""
            visible: text.length > 0
            color: "#8f8574"
            font.family: "Segoe UI"
            font.pixelSize: 13
            font.letterSpacing: 0.5
            opacity: 0.75
        }
        Text {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.Wrap
            maximumLineCount: 5
            elide: Text.ElideRight
            text: angel ? angel.angelText : ""
            visible: text.length > 0
            color: "#e8dfcc"
            font.family: "Palatino Linotype"
            font.pixelSize: 16
            font.letterSpacing: 0.4
            opacity: 0.92
        }
    }

    // Typed fallback input — nearly invisible until focused.
    TypedInput {
        id: typedInput
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 22
        width: Math.min(520, root.width * 0.5)
        onSubmitted: function(text) { angel.submitTypedRequest(text) }
    }

    // ----------------------------------------------------- setup issues panel
    SetupNotice {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: root.height * 0.055
        issues: angel ? angel.setupIssues : []
    }

    // --------------------------------------------------------- confirmation
    ConfirmationPanel {
        id: confirmPanel
        anchors.centerIn: parent
        anchors.verticalCenterOffset: root.height * 0.28
        action: angel ? angel.confirmAction : ""
        onConfirmed: angel.resolveConfirmation(true)
        onDenied: angel.resolveConfirmation(false)
    }

    // ------------------------------------------------------------- settings
    Text {
        id: settingsGlyph
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: 22
        text: "✦"
        color: settingsMouse.containsMouse ? "#d9b571" : "#5a4f3d"
        font.pixelSize: 18
        opacity: 0.9
        Behavior on color { ColorAnimation { duration: 200 } }
        MouseArea {
            id: settingsMouse
            anchors.fill: parent
            anchors.margins: -10
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: settingsPanel.open = !settingsPanel.open
        }
    }

    SettingsPanel {
        id: settingsPanel
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.right: parent.right
    }

    // ------------------------------------------------------------ shortcuts
    Item {
        id: keyCatcher
        anchors.fill: parent
        focus: !typedInput.hasFocus
        Keys.onPressed: function(event) {
            if (event.key === Qt.Key_Space && !event.isAutoRepeat) {
                angel.pushToTalk()
                event.accepted = true
            } else if (event.key === Qt.Key_Escape) {
                if (settingsPanel.open) { settingsPanel.open = false }
                else if (root.angelState === "confirming") { angel.resolveConfirmation(false) }
                event.accepted = true
            } else if (event.key === Qt.Key_F11) {
                root.visibility = root.visibility === Window.FullScreen
                    ? Window.Maximized : Window.FullScreen
                event.accepted = true
            } else if (event.key === Qt.Key_Q && (event.modifiers & Qt.ControlModifier)) {
                angel.quitAngel()
                event.accepted = true
            } else if (event.key === Qt.Key_T && (event.modifiers & Qt.ControlModifier)) {
                typedInput.focusInput()
                event.accepted = true
            }
        }
    }

    // Idle hint, fades away.
    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: 18
        text: "say  “Angel”      ·      Space to talk      ·      Ctrl+T to type      ·      F11 windowed"
        color: "#4a4336"
        font.family: "Segoe UI"
        font.pixelSize: 11
        font.letterSpacing: 1.5
        opacity: hintFade.running || root.angelState !== "idle" ? 0 : 0.55
        Behavior on opacity { NumberAnimation { duration: 800 } }
        Timer { id: hintFade; interval: 14000; running: true }
    }
}
