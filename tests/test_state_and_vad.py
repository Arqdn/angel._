"""State machine transitions + VAD segmentation on synthetic audio."""

import numpy as np

from angel.audio.vad import SegmentDetector, VadConfig
from angel.state import AngelState, StateMachine


# ------------------------------------------------------------- state machine

def test_happy_path_transitions():
    sm = StateMachine(AngelState.SETUP)
    for target in (AngelState.IDLE, AngelState.LISTENING, AngelState.THINKING,
                   AngelState.SPEAKING, AngelState.IDLE):
        assert sm.transition(target), target
    assert sm.state == AngelState.IDLE


def test_illegal_transition_rejected():
    sm = StateMachine(AngelState.SETUP)
    assert not sm.transition(AngelState.SPEAKING)
    assert sm.state == AngelState.SETUP


def test_error_reachable_from_anywhere():
    sm = StateMachine(AngelState.SETUP)
    sm.transition(AngelState.IDLE)
    sm.transition(AngelState.THINKING)
    assert sm.transition(AngelState.ERROR)
    assert sm.transition(AngelState.IDLE)


def test_confirmation_flow():
    sm = StateMachine(AngelState.SETUP)
    sm.transition(AngelState.IDLE)
    sm.transition(AngelState.THINKING)
    assert sm.transition(AngelState.CONFIRMING)
    assert sm.transition(AngelState.SPEAKING)   # Angel asks aloud
    assert sm.transition(AngelState.CONFIRMING)  # back to waiting
    assert sm.transition(AngelState.THINKING)   # approved -> executes


def test_listeners_notified():
    sm = StateMachine(AngelState.SETUP)
    seen = []
    sm.add_listener(lambda s, info: seen.append((s, info)))
    sm.transition(AngelState.IDLE, "boot")
    assert seen == [(AngelState.IDLE, "boot")]


# ---------------------------------------------------------------------- VAD

def _cfg() -> VadConfig:
    return VadConfig(sample_rate=16000, frame_ms=30, sensitivity=0.5,
                     min_speech_ms=200, end_silence_ms=300, pre_roll_ms=120)


def _frames(signal: np.ndarray, frame_len: int):
    for start in range(0, len(signal) - frame_len + 1, frame_len):
        yield signal[start:start + frame_len].astype(np.float32)


def test_vad_detects_loud_burst_between_silence():
    cfg = _cfg()
    rng = np.random.default_rng(0)
    quiet = rng.normal(0, 0.002, 16000)               # 1s near-silence
    loud = rng.normal(0, 0.2, 16000)                  # 1s speech-like noise
    tail = rng.normal(0, 0.002, 16000)                # 1s silence to close it
    signal = np.concatenate([quiet, loud, tail])

    detector = SegmentDetector(cfg)
    utterances = [u for f in _frames(signal, cfg.frame_len)
                  if (u := detector.feed(f)) is not None]
    assert len(utterances) == 1
    # Captured roughly the loud second (+pre-roll +end-silence).
    assert 0.8 <= utterances[0].duration_s <= 2.0


def test_vad_ignores_short_click():
    cfg = _cfg()
    rng = np.random.default_rng(1)
    signal = np.concatenate([
        rng.normal(0, 0.002, 16000),
        rng.normal(0, 0.25, int(16000 * 0.08)),        # 80 ms click
        rng.normal(0, 0.002, 16000),
    ])
    detector = SegmentDetector(cfg)
    utterances = [u for f in _frames(signal, cfg.frame_len)
                  if (u := detector.feed(f)) is not None]
    assert utterances == []


def test_vad_reports_level_for_ui():
    cfg = _cfg()
    detector = SegmentDetector(cfg)
    detector.feed(np.zeros(cfg.frame_len, dtype=np.float32))
    assert detector.level == 0.0
    detector.feed(np.full(cfg.frame_len, 0.5, dtype=np.float32))
    assert detector.level > 0.5


def test_vad_max_utterance_forces_cut():
    cfg = _cfg()
    cfg.max_utterance_s = 1.0
    rng = np.random.default_rng(2)
    signal = rng.normal(0, 0.2, 16000 * 3)  # 3s continuous loudness
    detector = SegmentDetector(cfg)
    utterances = [u for f in _frames(signal, cfg.frame_len)
                  if (u := detector.feed(f)) is not None]
    assert utterances, "expected at least one forced segment"
    assert utterances[0].duration_s <= 1.2
