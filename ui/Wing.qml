// One wing, drawn once as layered engraved plumes (no repaints during
// animation — intensity is animated via opacity on the glow pass).
// Painted for the RIGHT side; mirror with scale.x: -1 for the left.

import QtQuick

Canvas {
    id: wing
    // "line" = fine ivory engraving strokes; "glow" = soft wide golden pass
    property string pass: "line"
    renderStrategy: Canvas.Cooperative

    onPaint: {
        var ctx = getContext("2d")
        ctx.reset()
        var w = width, h = height
        // Shoulder anchor: lower-left of this canvas.
        var bx = w * 0.04, by = h * 0.62
        var feathers = 20

        for (var i = 0; i < feathers; i++) {
            var t = i / (feathers - 1)
            // Sweep from steep-up (-72°) to gently-down (+38°)
            var theta = (-72 + 110 * t) * Math.PI / 180
            // Long primaries in the middle of the fan, shorter at extremes
            var span = 0.42 + 0.58 * Math.sin(Math.PI * (0.18 + 0.82 * t))
            var len = w * 0.92 * span
            var tipX = bx + Math.cos(theta) * len
            var tipY = by + Math.sin(theta) * len * 0.92
            // Bow each plume upward
            var midX = bx + Math.cos(theta) * len * 0.5
            var midY = by + Math.sin(theta) * len * 0.5
            var normX = -Math.sin(theta), normY = Math.cos(theta)
            var bow = len * 0.18
            var cpX = midX - normX * bow
            var cpY = midY - normY * bow

            ctx.beginPath()
            ctx.moveTo(bx + Math.cos(theta) * w * 0.03,
                       by + Math.sin(theta) * w * 0.03)
            ctx.quadraticCurveTo(cpX, cpY, tipX, tipY)

            if (pass === "glow") {
                ctx.strokeStyle = "rgba(217,181,113," + (0.05 + 0.05 * Math.sin(Math.PI * t)) + ")"
                ctx.lineWidth = 7
            } else {
                var alpha = 0.10 + 0.16 * Math.sin(Math.PI * (0.15 + 0.85 * t))
                ctx.strokeStyle = "rgba(240,230,210," + alpha + ")"
                ctx.lineWidth = 1.4
            }
            ctx.lineCap = "round"
            ctx.stroke()

            // Secondary barb: a shorter echo stroke under each plume (engraving feel)
            if (pass === "line" && i % 2 === 0) {
                ctx.beginPath()
                ctx.moveTo(bx + Math.cos(theta) * w * 0.05,
                           by + Math.sin(theta) * w * 0.05)
                ctx.quadraticCurveTo(
                    cpX + normX * len * 0.05, cpY + normY * len * 0.05,
                    bx + (tipX - bx) * 0.86 + normX * len * 0.055,
                    by + (tipY - by) * 0.86 + normY * len * 0.055)
                ctx.strokeStyle = "rgba(240,230,210,0.06)"
                ctx.lineWidth = 1
                ctx.stroke()
            }
        }

        // Leading-edge contour: shoulder rising over the top of the fan.
        ctx.beginPath()
        ctx.moveTo(bx, by + h * 0.02)
        ctx.bezierCurveTo(bx - w * 0.02, by - h * 0.42,
                          w * 0.28, h * 0.02,
                          w * 0.78, h * 0.10)
        if (pass === "glow") {
            ctx.strokeStyle = "rgba(217,181,113,0.10)"
            ctx.lineWidth = 8
        } else {
            ctx.strokeStyle = "rgba(244,234,216,0.20)"
            ctx.lineWidth = 1.8
        }
        ctx.stroke()
    }
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
}
