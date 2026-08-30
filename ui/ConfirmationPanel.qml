// Dangerous-action confirmation. Clearly readable, impossible to miss,
// answerable by voice ("yes" / "no") or by these two quiet controls.

import QtQuick

Item {
    id: panel
    property string action: ""
    signal confirmed()
    signal denied()

    visible: action.length > 0
    width: Math.max(360, body.width + 80)
    height: visible ? body.height + 56 : 0
    opacity: visible ? 1 : 0
    Behavior on opacity { NumberAnimation { duration: 250 } }

    Rectangle {
        anchors.fill: parent
        radius: 4
        color: "#100c08"
        opacity: 0.94
        border.color: "#8a744d"
        border.width: 1
    }
    // Warm top hairline.
    Rectangle {
        anchors.top: parent.top
        anchors.horizontalCenter: parent.horizontalCenter
        width: parent.width - 2
        height: 1
        color: "#d9b571"
        opacity: 0.6
    }

    Column {
        id: body
        anchors.centerIn: parent
        spacing: 14

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "A N G E L   A S K S"
            color: "#d9b571"
            font.family: "Palatino Linotype"
            font.pixelSize: 12
            font.letterSpacing: 3
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.min(460, panel.parent ? panel.parent.width * 0.5 : 460)
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.Wrap
            text: "May I " + panel.action + "?"
            color: "#efe6d5"
            font.family: "Palatino Linotype"
            font.pixelSize: 17
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "say “yes” or “no” — or choose below"
            color: "#6d6353"
            font.family: "Segoe UI"
            font.pixelSize: 11
            font.italic: true
        }

        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 18

            Rectangle {
                width: 120; height: 34; radius: 3
                color: yesMouse.containsMouse ? "#2a2318" : "#1a1610"
                border.color: "#8a744d"; border.width: 1
                Text {
                    anchors.centerIn: parent
                    text: "C O N F I R M"
                    color: "#d9b571"
                    font.family: "Segoe UI"; font.pixelSize: 11; font.letterSpacing: 2
                }
                MouseArea {
                    id: yesMouse
                    anchors.fill: parent; hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: panel.confirmed()
                }
            }
            Rectangle {
                width: 120; height: 34; radius: 3
                color: noMouse.containsMouse ? "#231412" : "#160f0d"
                border.color: "#5a3d33"; border.width: 1
                Text {
                    anchors.centerIn: parent
                    text: "D E N Y"
                    color: "#c98263"
                    font.family: "Segoe UI"; font.pixelSize: 11; font.letterSpacing: 2
                }
                MouseArea {
                    id: noMouse
                    anchors.fill: parent; hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: panel.denied()
                }
            }
        }
    }
}
