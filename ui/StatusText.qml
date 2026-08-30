// Minimal state text: "L I S T E N I N G", "T H I N K I N G"…
// Errors surface here too — elegant, but unmissable.

import QtQuick

Item {
    id: status
    property string angelState: "idle"
    property string errorText: ""
    property string statusLine: ""

    width: column.width
    height: column.height

    function spaced(s) { return s.split("").join(" ") }

    readonly property string label: {
        if (errorText.length > 0) return spaced(errorText)
        switch (angelState) {
        case "listening":  return spaced("LISTENING")
        case "thinking":   return spaced("THINKING")
        case "speaking":   return spaced("SPEAKING")
        case "confirming": return spaced("CONFIRM")
        case "setup":      return spaced("AWAKENING")
        default:           return ""
        }
    }
    readonly property bool isError: errorText.length > 0

    Column {
        id: column
        spacing: 6

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: status.label
            color: status.isError ? "#c98263" : "#cfc3a8"
            font.family: "Palatino Linotype"
            font.pixelSize: 13
            font.letterSpacing: 4
            opacity: text.length > 0 ? 0.9 : 0
            Behavior on opacity { NumberAnimation { duration: 350 } }

            SequentialAnimation on opacity {
                running: status.angelState === "thinking" && !status.isError
                loops: Animation.Infinite
                alwaysRunToEnd: true
                NumberAnimation { to: 0.45; duration: 900; easing.type: Easing.InOutSine }
                NumberAnimation { to: 0.9; duration: 900; easing.type: Easing.InOutSine }
            }
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: status.statusLine
            visible: text.length > 0 && !status.isError
            color: "#6d6353"
            font.family: "Segoe UI"
            font.pixelSize: 11
            font.letterSpacing: 1.2
            opacity: 0.8
        }
    }
}
