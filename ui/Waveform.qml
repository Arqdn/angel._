// A thin breath of bars. Heights are driven by the REAL audio level
// (mic while listening, TTS RMS while speaking); the per-bar phase only
// shapes the curve, it never invents motion when the level is zero.

import QtQuick

Item {
    id: wf
    property real level: 0      // 0..1 live audio level
    property bool active: false
    property bool reduceMotion: false

    property real smoothed: 0
    Behavior on smoothed { NumberAnimation { duration: 90 } }
    onLevelChanged: smoothed = level

    property real phase: 0
    NumberAnimation on phase {
        running: wf.active && !wf.reduceMotion
        loops: Animation.Infinite
        from: 0; to: Math.PI * 2; duration: 1400
    }

    opacity: active ? 0.85 : 0
    Behavior on opacity { NumberAnimation { duration: 350 } }

    Row {
        anchors.centerIn: parent
        spacing: 3
        Repeater {
            model: 44
            Rectangle {
                required property int index
                readonly property real envelope:
                    Math.sin(Math.PI * (index + 0.5) / 44)   // taller mid, short ends
                readonly property real ripple:
                    0.65 + 0.35 * Math.sin(wf.phase + index * 0.55)
                width: 2
                height: Math.max(1.5, wf.height * wf.smoothed * envelope * ripple)
                anchors.verticalCenter: parent.verticalCenter
                radius: 1
                color: "#e8dcc2"
                opacity: 0.35 + 0.5 * envelope
            }
        }
    }
}
