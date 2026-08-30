// Dust motes. Idle: slow rising drift. Listening: drawn gently toward the
// angel's heart. Speaking: the heart breathes them outward with the voice.

import QtQuick
import QtQuick.Particles

Item {
    id: field
    property real energy: 0.12
    property string angelState: "idle"
    property real density: 1.0
    property bool reduceMotion: false
    property real centerX: width / 2
    property real centerY: height / 2

    ParticleSystem {
        id: system
        running: !field.reduceMotion && field.density > 0.01
    }

    ImageParticle {
        system: system
        source: assetsUrl + "/angel/particle.png"
        alpha: 0.0
        alphaVariation: 0.35
        color: "#f0e0c2"
        colorVariation: 0.12
        entryEffect: ImageParticle.Fade
    }

    // Ambient dust across the whole scene.
    Emitter {
        system: system
        anchors.fill: parent
        emitRate: (14 + 26 * field.energy) * field.density
        lifeSpan: 14000
        lifeSpanVariation: 5000
        size: 5
        sizeVariation: 4
        velocity: AngleDirection {
            angle: 270            // upward
            angleVariation: 40
            magnitude: 5 + 14 * field.energy
            magnitudeVariation: 5
        }
    }

    // Breath of sparks from the chest-light while speaking.
    Emitter {
        system: system
        x: field.centerX - 20; y: field.centerY - 20
        width: 40; height: 40
        enabled: field.angelState === "speaking"
        emitRate: 70 * field.energy * field.density
        lifeSpan: 2600
        lifeSpanVariation: 900
        size: 7
        sizeVariation: 5
        velocity: AngleDirection {
            angleVariation: 180
            magnitude: 24 + 70 * field.energy
            magnitudeVariation: 18
        }
    }

    // While listening, dust leans toward the heart.
    Attractor {
        system: system
        enabled: field.angelState === "listening" || field.angelState === "thinking"
        pointX: field.centerX
        pointY: field.centerY
        strength: field.angelState === "thinking" ? 90 : 55
        affectedParameter: Attractor.Velocity
        proportionalToDistance: Attractor.InverseLinear
        anchors.fill: parent
    }

    Wander {
        system: system
        anchors.fill: parent
        xVariance: 16
        yVariance: 10
        pace: 60
    }
}
