// Slow drifting fog: large soft glow sprites wandering at very low opacity.

import QtQuick

Item {
    id: fog
    property real energy: 0.12
    property bool reduceMotion: false

    Repeater {
        model: 4
        Image {
            id: wisp
            required property int index
            source: assetsUrl + "/angel/glow.png"
            width: fog.width * (0.55 + 0.2 * index)
            height: fog.height * 0.5
            opacity: 0.020 + 0.012 * (index % 2) + 0.015 * fog.energy
            x: fog.width * (index * 0.23 - 0.15)
            y: fog.height * (0.15 + 0.22 * index)
            fillMode: Image.Stretch

            SequentialAnimation on x {
                running: !fog.reduceMotion
                loops: Animation.Infinite
                NumberAnimation {
                    to: fog.width * (wisp.index * 0.23 - 0.05)
                    duration: 26000 + wisp.index * 7000
                    easing.type: Easing.InOutSine
                }
                NumberAnimation {
                    to: fog.width * (wisp.index * 0.23 - 0.25)
                    duration: 30000 + wisp.index * 6000
                    easing.type: Easing.InOutSine
                }
            }
            SequentialAnimation on y {
                running: !fog.reduceMotion
                loops: Animation.Infinite
                NumberAnimation {
                    to: fog.height * (0.10 + 0.22 * wisp.index)
                    duration: 21000 + wisp.index * 5000
                    easing.type: Easing.InOutSine
                }
                NumberAnimation {
                    to: fog.height * (0.20 + 0.22 * wisp.index)
                    duration: 24000 + wisp.index * 5500
                    easing.type: Easing.InOutSine
                }
            }
        }
    }
}
