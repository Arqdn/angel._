// Typed fallback (Ctrl+T): a hairline of a text field, nearly invisible
// until focused. Keeps Angel usable with no microphone at all.

import QtQuick

Item {
    id: typed
    signal submitted(string text)
    readonly property bool hasFocus: input.activeFocus
    height: 30

    function focusInput() { input.forceActiveFocus() }

    Rectangle {
        anchors.fill: parent
        radius: 4
        color: input.activeFocus ? "#14100c" : "transparent"
        border.color: input.activeFocus ? "#3d3527" : "#1d1913"
        border.width: 1
        opacity: input.activeFocus ? 0.95 : 0.35
        Behavior on opacity { NumberAnimation { duration: 250 } }
    }

    TextInput {
        id: input
        anchors.fill: parent
        anchors.leftMargin: 12
        anchors.rightMargin: 12
        verticalAlignment: TextInput.AlignVCenter
        color: "#e8dfcc"
        font.family: "Segoe UI"
        font.pixelSize: 13
        clip: true
        selectByMouse: true
        onAccepted: {
            var t = text.trim()
            if (t.length > 0) {
                typed.submitted(t)
                text = ""
            }
            focus = false
        }
        Keys.onEscapePressed: { text = ""; focus = false }
    }

    Text {
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.leftMargin: 12
        text: "whisper in writing…"
        color: "#4a4336"
        font.family: "Segoe UI"
        font.italic: true
        font.pixelSize: 12
        visible: input.text.length === 0 && !input.activeFocus
        opacity: 0.6
    }

    MouseArea {
        anchors.fill: parent
        visible: !input.activeFocus
        cursorShape: Qt.IBeamCursor
        onClicked: input.forceActiveFocus()
    }
}
