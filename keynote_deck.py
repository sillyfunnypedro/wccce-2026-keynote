#!/usr/bin/env python3
"""
Canonical deck format: ``keynote.json``.

Each slide has a stable ``id`` (UUID), ``kind``, ``markdown`` (source for PPTX),
``title`` / ``body`` (for LLM suggest), and ``image_prompt``. Images are stored as
``slide_images/{id}.png`` so reordering the ``slides[]`` array does not break assets.

``generator.py --deck`` and ``slide_editor.py --deck`` edit the same JSON.
"""

from __future__ import annotations

import json
from pathlib import Path

from generator import DEFAULT_MODEL, SCRIPT_DIR

DECK_VERSION = 1

CREDITS_DELAY_DEFAULT = 1.0
CREDITS_SPEED_DEFAULT = 60.0
CREDITS_DELAY_MIN, CREDITS_DELAY_MAX = 0.0, 60.0
CREDITS_SPEED_MIN, CREDITS_SPEED_MAX = 5.0, 500.0

TEXT_FIELDS = ("markdown", "body", "title")


def _normalize_text_field(value: object) -> str:
    """Convert a text field from on-disk format to in-memory string.

    Accepts:
      - list[str]: joined with newlines
      - str: returned as-is
      - None/missing: returns empty string
    """
    if isinstance(value, list):
        return "\n".join(str(item) for item in value)
    if isinstance(value, str):
        return value
    return ""


def _serialize_text_field(value: str) -> list[str]:
    """Convert an in-memory string to on-disk array format.

    Splits on newline characters. Empty string becomes [].
    """
    if not value:
        return []
    return value.split("\n")


def _coerce_float(value: object, default: float, lo: float, hi: float) -> float:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return default
    if f != f:  # NaN
        return default
    return max(lo, min(hi, f))


def ensure_deck_defaults(deck: dict) -> bool:
    """Materialize credits-related fields on the deck and on every slide.

    Returns True if anything was added or normalized (so callers can decide
    whether to persist the deck back to disk). Idempotent: a fully-normalized
    deck returns False.
    """
    changed = False

    delay_raw = deck.get("credits_start_delay_seconds", CREDITS_DELAY_DEFAULT)
    delay = _coerce_float(delay_raw, CREDITS_DELAY_DEFAULT, CREDITS_DELAY_MIN, CREDITS_DELAY_MAX)
    if delay_raw != delay or "credits_start_delay_seconds" not in deck:
        deck["credits_start_delay_seconds"] = delay
        changed = True

    speed_raw = deck.get("credits_scroll_pixels_per_second", CREDITS_SPEED_DEFAULT)
    speed = _coerce_float(speed_raw, CREDITS_SPEED_DEFAULT, CREDITS_SPEED_MIN, CREDITS_SPEED_MAX)
    if speed_raw != speed or "credits_scroll_pixels_per_second" not in deck:
        deck["credits_scroll_pixels_per_second"] = speed
        changed = True

    slides = deck.get("slides")
    if isinstance(slides, list):
        for spec in slides:
            if not isinstance(spec, dict):
                continue
            if "credits" not in spec or not isinstance(spec.get("credits"), bool):
                spec["credits"] = bool(spec.get("credits", False))
                changed = True
    return changed


def default_deck_shell(frontmatter: dict, slides: list[dict]) -> dict:
    return {
        "version": DECK_VERSION,
        "frontmatter": frontmatter,
        "slides": slides,
        "text_model": "anthropic/claude-haiku-4.5",
        "model": DEFAULT_MODEL,
        "output_directory": "slide_images",
        "global_style_file": "global_style.md",
        "width": 1024,
        "height": 1024,
    }


def load_deck(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data.get("slides"), list):
        raise ValueError("Deck must contain a slides[] array")
    # Normalize text fields from array or string to plain string
    for spec in data["slides"]:
        if not isinstance(spec, dict):
            continue
        for field in TEXT_FIELDS:
            if field in spec:
                spec[field] = _normalize_text_field(spec[field])
    ensure_deck_defaults(data)
    return data


def save_deck(path: Path, deck: dict) -> None:
    # Shallow-copy deck and slides to avoid mutating the in-memory deck
    out = dict(deck)
    if isinstance(out.get("slides"), list):
        out["slides"] = []
        for spec in deck["slides"]:
            if not isinstance(spec, dict):
                out["slides"].append(spec)
                continue
            slide_copy = dict(spec)
            for field in TEXT_FIELDS:
                if field in slide_copy and isinstance(slide_copy[field], str):
                    slide_copy[field] = _serialize_text_field(slide_copy[field])
            out["slides"].append(slide_copy)
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
