// Volumetric-feeling light: soft rays falling from above the angel's head.
// Each ray is a tall thin gradient, slowly swaying; brightness follows energy.

import QtQuick

Item {
    id: rays
    property real energy: 0.12
    property string angelState: "idle"
    property bool reduceMotion: false

    Item {
        id: fan
        anchors.horizontalCenter: parent.horizontalCenter
        y: -rays.height * 0.25
        width: rays.width
        height: rays.height * 1.3

        Repeater {
            model: 7
            Item {
                id: rayHolder
                required property int index
                readonly property real baseAngle: (index - 3) * 7.5
                anchors.horizontalCenter: parent.horizontalCenter
                width: rays.width * (index % 2 === 0 ? 0.055 : 0.030)
                height: fan.height
                rotation: baseAngle
                transformOrigin: Item.Top

                SequentialAnimation on rotation {
                    running: !rays.reduceMotion
                    loops: Animation.Infinite
                    NumberAnimation {
                        to: rayHolder.baseAngle + 1.6
                        duration: 14000 + rayHolder.index * 2100
                        easing.type: Easing.InOutSine
                    }
                    NumberAnimation {
                        to: rayHolder.baseAngle - 1.6
                        duration: 15000 + rayHolder.index * 1900
                        easing.type: Easing.InOutSine
                    }
                }

                Rectangle {
                    anchors.fill: parent
                    opacity: (0.026 + 0.016 * (rayHolder.index % 3 === 0 ? 1 : 0))
                             * (0.5 + 1.8 * rays.energy)
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "#00f4ead8" }
                        GradientStop { position: 0.22; color: "#f4ead8" }
                        GradientStop { position: 0.8; color: "#40d9b571" }
                        GradientStop { position: 1.0; color: "#00d9b571" }
                    }
                }
            }
        }
    }
}
