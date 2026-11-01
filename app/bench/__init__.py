"""Objective quality benchmark suite (CI-only: `python -m app bench`).

Renders a deterministic golden reference episode through the REAL audio/render
stages into an isolated state root (production state/ is never touched),
computes objective metrics (sharpness, encode fidelity, pan motion, flicker,
loudness, speech prominence, WER, TTS RTF, render cost), and compares them
against the committed benchmarks/baseline.json gates.

Execution belongs to GitHub Actions — never run renders locally.
"""

from __future__ import annotations

__all__ = ["REFERENCE_ID"]

REFERENCE_ID = "bench001"
