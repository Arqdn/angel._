// First-run problems (missing keys, no microphone) — quiet, clear, top of screen.

import QtQuick

Item {
    id: notice
    property var issues: []
    width: column.width + 60
    height: issues.length > 0 ? column.height + 30 : 0
    visible: issues.length > 0

    Rectangle {
        anchors.fill: parent
        radius: 3
        color: "#120e0a"
        opacity: 0.82
        border.color: "#3d3527"
        border.width: 1
    }

    Column {
        id: column
        anchors.centerIn: parent
        spacing: 5

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "S E T U P   N E E D E D"
            color: "#d9b571"
            font.family: "Palatino Linotype"
            font.pixelSize: 12
            font.letterSpacing: 3
        }
        Repeater {
            model: notice.issues
            Text {
                required property string modelData
                anchors.horizontalCenter: parent.horizontalCenter
                text: modelData
                color: "#c9bda2"
                font.family: "Segoe UI"
                font.pixelSize: 12
                font.letterSpacing: 1
            }
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "add keys to the .env file, then restart — see README"
            color: "#6d6353"
            font.family: "Segoe UI"
            font.pixelSize: 11
            font.italic: true
        }
    }
}
