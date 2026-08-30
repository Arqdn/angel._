// The angel: column of light, enormous engraved wings, dark robed silhouette,
// burning chest-light, halo, and slowly turning celestial rings.
// All animation is transform/opacity-based — canvases paint once.

import QtQuick

Item {
    id: visual
    property real energy: 0.12          // 0..1 from Main (audio-reactive)
    property string angelState: "idle"
    property bool reduceMotion: false

    // Slow breathing 0..1 — the idle life of the figure.
    property real breath: 0
    SequentialAnimation on breath {
        running: !visual.reduceMotion
        loops: Animation.Infinite
        NumberAnimation { to: 1; duration: 4200; easing.type: Easing.InOutSine }
        NumberAnimation { to: 0; duration: 4600; easing.type: Easing.InOutSine }
    }

    readonly property real cx: width / 2
    readonly property real headY: height * 0.215
    readonly property real chestY: height * 0.42

    // ------------------------------------------------------- column of light
    Image {
        source: assetsUrl + "/angel/glow.png"
        anchors.horizontalCenter: parent.horizontalCenter
        y: -parent.height * 0.10
        width: parent.width * 0.34
        height: parent.height * 1.15
        opacity: 0.10 + 0.16 * visual.energy + 0.03 * visual.breath
        fillMode: Image.Stretch
    }
    // Narrow bright core of the column.
    Image {
        source: assetsUrl + "/angel/glow.png"
        anchors.horizontalCenter: parent.horizontalCenter
        y: -parent.height * 0.05
        width: parent.width * 0.13
        height: parent.height * 1.05
        opacity: 0.10 + 0.22 * visual.energy
        fillMode: Image.Stretch
    }

    // ------------------------------------------------------- celestial rings
    Item {
        id: rings
        anchors.horizontalCenter: parent.horizontalCenter
        y: visual.chestY - width / 2
        width: parent.height * 0.78
        height: width
        opacity: 0.5 + 0.5 * visual.energy
        RotationAnimation on rotation {
            running: !visual.reduceMotion
            loops: Animation.Infinite
            from: 0; to: 360; duration: 240000
        }
        Canvas {
            anchors.fill: parent
            onPaint: {
                var ctx = getContext("2d")
                ctx.reset()
                var c = width / 2
                var radii = [0.30, 0.40, 0.485]
                var dashes = [[1, 9], [4, 14], [1, 5]]
                var alphas = [0.10, 0.075, 0.12]
                for (var i = 0; i < radii.length; i++) {
                    ctx.beginPath()
                    ctx.setLineDash(dashes[i])
                    ctx.arc(c, c, width * radii[i], 0, Math.PI * 2)
                    ctx.strokeStyle = "rgba(217,181,113," + alphas[i] + ")"
                    ctx.lineWidth = i === 2 ? 0.8 : 1.2
                    ctx.stroke()
                }
                // Tiny engraved tick marks on the outer ring.
                ctx.setLineDash([])
                for (var k = 0; k < 36; k++) {
                    var a = k / 36 * Math.PI * 2
                    var r0 = width * 0.485, r1 = width * (k % 3 === 0 ? 0.505 : 0.495)
                    ctx.beginPath()
                    ctx.moveTo(c + Math.cos(a) * r0, c + Math.sin(a) * r0)
                    ctx.lineTo(c + Math.cos(a) * r1, c + Math.sin(a) * r1)
                    ctx.strokeStyle = "rgba(217,181,113,0.10)"
                    ctx.lineWidth = 1
                    ctx.stroke()
                }
            }
            onWidthChanged: requestPaint()
        }
    }

    // ---------------------------------------------------------------- wings
    Item {
        id: wings
        anchors.fill: parent
        // Breathing + audio: wings swell with the voice.
        scale: 1.0 + 0.008 * visual.breath + 0.018 * visual.energy
        transformOrigin: Item.Center

        // Right wing
        Item {
            x: visual.cx - parent.width * 0.015
            y: parent.height * 0.02
            width: parent.width * 0.52
            height: parent.height * 0.72
            rotation: 1.2 * visual.breath + 2.0 * visual.energy
            transformOrigin: Item.BottomLeft
            Wing { anchors.fill: parent; pass: "line" }
            Wing {
                anchors.fill: parent; pass: "glow"
                opacity: 0.35 + 0.65 * visual.energy
            }
        }
        // Left wing (mirror)
        Item {
            x: visual.cx - parent.width * 0.52 + parent.width * 0.015
            y: parent.height * 0.02
            width: parent.width * 0.52
            height: parent.height * 0.72
            rotation: -(1.2 * visual.breath + 2.0 * visual.energy)
            transformOrigin: Item.BottomRight
            transform: Scale { xScale: -1; origin.x: width / 2 }
            Wing { anchors.fill: parent; pass: "line" }
            Wing {
                anchors.fill: parent; pass: "glow"
                opacity: 0.35 + 0.65 * visual.energy
            }
        }
    }

    // ----------------------------------------------------------------- halo
    Item {
        anchors.horizontalCenter: parent.horizontalCenter
        y: visual.headY - height * 1.9 - visual.breath * 3
        width: parent.height * 0.16
        height: width * 0.30
        opacity: 0.35 + 0.55 * visual.energy
        Canvas {
            anchors.fill: parent
            onPaint: {
                var ctx = getContext("2d")
                ctx.reset()
                ctx.beginPath()
                ctx.ellipse(2, 2, width - 4, height - 4)
                ctx.strokeStyle = "rgba(244,234,216,0.75)"
                ctx.lineWidth = 1.6
                ctx.stroke()
                ctx.beginPath()
                ctx.ellipse(0, 0, width, height)
                ctx.strokeStyle = "rgba(217,181,113,0.30)"
                ctx.lineWidth = 4
                ctx.stroke()
            }
            onWidthChanged: requestPaint()
        }
    }

    // ------------------------------------------------------------ silhouette
    Canvas {
        id: figureCanvas
        anchors.fill: parent
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var w = width, h = height, cx = w / 2
            var headR = h * 0.052
            var headCY = h * 0.215 + headR

            // Robed body: shoulders sloping into a long flared robe.
            ctx.beginPath()
            ctx.moveTo(cx - headR * 0.62, headCY + headR * 0.75)   // neck L
            ctx.bezierCurveTo(cx - headR * 2.6, headCY + headR * 1.7,
                              cx - w * 0.085, h * 0.40,
                              cx - w * 0.105, h * 0.52)            // torso L
            ctx.bezierCurveTo(cx - w * 0.135, h * 0.70,
                              cx - w * 0.165, h * 0.86,
                              cx - w * 0.155, h * 0.995)           // robe hem L
            ctx.lineTo(cx + w * 0.155, h * 0.995)                  // hem
            ctx.bezierCurveTo(cx + w * 0.165, h * 0.86,
                              cx + w * 0.135, h * 0.70,
                              cx + w * 0.105, h * 0.52)            // robe R
            ctx.bezierCurveTo(cx + w * 0.085, h * 0.40,
                              cx + headR * 2.6, headCY + headR * 1.7,
                              cx + headR * 0.62, headCY + headR * 0.75) // neck R
            ctx.closePath()

            var bodyGrad = ctx.createLinearGradient(0, headCY, 0, h)
            bodyGrad.addColorStop(0.0, "rgba(9,8,7,0.96)")
            bodyGrad.addColorStop(0.55, "rgba(7,6,5,0.90)")
            bodyGrad.addColorStop(1.0, "rgba(5,4,3,0.35)")
            ctx.fillStyle = bodyGrad
            ctx.fill()
            // Ivory rim light on the robe edges.
            ctx.strokeStyle = "rgba(240,230,210,0.10)"
            ctx.lineWidth = 1.5
            ctx.stroke()

            // Head — featureless, bowed very slightly.
            ctx.beginPath()
            ctx.arc(cx, headCY, headR, 0, Math.PI * 2)
            ctx.fillStyle = "rgba(8,7,6,0.97)"
            ctx.fill()
            ctx.beginPath()
            ctx.arc(cx, headCY, headR, -Math.PI * 0.85, -Math.PI * 0.15)
            ctx.strokeStyle = "rgba(244,234,216,0.22)"
            ctx.lineWidth = 1.2
            ctx.stroke()
        }
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
    }

    // ------------------------------------------------------ chest light (core)
    Image {
        id: coreOuter
        source: assetsUrl + "/angel/glow.png"
        anchors.horizontalCenter: parent.horizontalCenter
        y: visual.chestY - height / 2
        width: parent.height * (0.34 + 0.10 * visual.energy)
        height: width
        opacity: 0.28 + 0.45 * visual.energy + 0.05 * visual.breath
    }
    Image {
        id: coreInner
        source: assetsUrl + "/angel/glow.png"
        anchors.horizontalCenter: parent.horizontalCenter
        y: visual.chestY - height / 2
        width: parent.height * (0.13 + 0.05 * visual.energy + 0.008 * visual.breath)
        height: width
        opacity: 0.55 + 0.45 * visual.energy
    }
    // Thinking: the light contracts and slowly rotates a faint inner ring.
    Item {
        anchors.horizontalCenter: parent.horizontalCenter
        y: visual.chestY - width / 2
        width: parent.height * 0.20
        height: width
        visible: visual.angelState === "thinking"
        opacity: visible ? 0.8 : 0
        Behavior on opacity { NumberAnimation { duration: 400 } }
        RotationAnimation on rotation {
            running: visual.angelState === "thinking" && !visual.reduceMotion
            loops: Animation.Infinite
            from: 360; to: 0; duration: 9000
        }
        Canvas {
            anchors.fill: parent
            onPaint: {
                var ctx = getContext("2d")
                ctx.reset()
                ctx.beginPath()
                ctx.setLineDash([3, 16])
                ctx.arc(width / 2, width / 2, width * 0.46, 0, Math.PI * 2)
                ctx.strokeStyle = "rgba(244,234,216,0.5)"
                ctx.lineWidth = 1.2
                ctx.stroke()
            }
            onWidthChanged: requestPaint()
        }
    }

    // Error: the light gutters — brief desaturated dimming veil.
    Rectangle {
        anchors.fill: parent
        color: "#30160c08"
        opacity: visual.angelState === "error" ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: 500 } }
    }
}
