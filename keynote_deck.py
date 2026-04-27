#!/usr/bin/env python3
"""
Canonical deck format: ``keynote.json``.

Each slide has a stable ``id`` (UUID), ``kind``, ``markdown`` (source for PPTX),
``title`` / ``body`` (for LLM suggest), and ``image_prompt``. Images are stored as
``slide_images/{id}.png`` so reordering the ``slides[]`` array does not break assets.

  python keynote_deck.py import keynote.md keynote.json
  python keynote_deck.py migrate-images keynote.json slide_images/

``generator.py --deck`` and ``slide_editor.py --deck`` edit the same JSON.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import uuid
from pathlib import Path

from generator import (
    DEFAULT_MODEL,
    SCRIPT_DIR,
    keynote_slides_metadata,
    parse_frontmatter,
    split_slides,
)

DECK_VERSION = 1


def slides_chunks_from_markdown(keynote_path: Path) -> tuple[dict, list[dict]]:
    """Frontmatter plus one ``{kind, markdown}`` per slide (deck order)."""
    text = keynote_path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    raw = split_slides(body)
    chunks: list[dict] = []
    for sep, content in raw:
        if not content.strip():
            continue
        st = sep.strip().lstrip("-").strip().lower() or "single"
        kind = "title" if st == "title" else ("quote" if st == "quote" else "content")
        chunks.append({"kind": kind, "markdown": content.strip()})
    return fm, chunks


def import_keynote_md_to_deck(keynote_path: Path) -> dict:
    """Build a new deck dict from ``keynote.md`` (new UUID per slide)."""
    fm, chunks = slides_chunks_from_markdown(keynote_path)
    metas = keynote_slides_metadata(keynote_path)
    if len(chunks) != len(metas):
        raise ValueError(
            f"Slide count mismatch: {len(chunks)} markdown chunks vs {len(metas)} metadata entries"
        )
    slides: list[dict] = []
    for ch, m in zip(chunks, metas):
        slides.append(
            {
                "id": str(uuid.uuid4()),
                "kind": m["kind"],
                "markdown": ch["markdown"],
                "title": m["title"],
                "body": m["body"],
                "image_prompt": "",
            }
        )
    return default_deck_shell(fm, slides)


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
    return data


def save_deck(path: Path, deck: dict) -> None:
    path.write_text(json.dumps(deck, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def migrate_indexed_images_to_ids(deck: dict, image_dir: Path, *, dry_run: bool = False) -> list[str]:
    """
    For each slide in order, if ``NN.png`` exists and ``{id}.png`` does not, copy
    ``NN.png`` → ``{id}.png``. Does not delete numbered files.
    """
    image_dir = image_dir.resolve()
    log: list[str] = []
    slides = deck.get("slides") or []
    if not isinstance(slides, list):
        return ["No slides in deck"]
    exts = (".png", ".jpg", ".jpeg", ".webp")
    for i, spec in enumerate(slides):
        sid = str(spec.get("id", "")).strip()
        if not sid:
            log.append(f"[{i:02d}] skip: no id")
            continue
        src: Path | None = None
        for ext in exts:
            cand = image_dir / f"{i:02d}{ext}"
            if cand.is_file():
                src = cand
                break
        if src is None:
            log.append(f"[{i:02d}] no {i:02d}.* for id {sid[:8]}…")
            continue
        dest = image_dir / f"{sid}{src.suffix}"
        if dest.is_file():
            log.append(f"[{i:02d}] skip: {dest.name} already exists")
            continue
        if dry_run:
            log.append(f"[{i:02d}] would copy {src.name} → {dest.name}")
            continue
        shutil.copy2(src, dest)
        log.append(f"[{i:02d}] copied {src.name} → {dest.name}")
    return log


def main() -> None:
    p = argparse.ArgumentParser(description="keynote.json deck import / image migration")
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("import", help="Create keynote.json from keynote.md")
    pi.add_argument("keynote_md", type=Path)
    pi.add_argument("out_json", type=Path, nargs="?", default=None)

    pm = sub.add_parser("migrate-images", help="Copy 00.png… to {slide id}.png in deck order")
    pm.add_argument("deck_json", type=Path)
    pm.add_argument("image_dir", type=Path)
    pm.add_argument("--dry-run", action="store_true")

    args = p.parse_args()
    if args.cmd == "import":
        out = args.out_json or (SCRIPT_DIR / "keynote.json")
        deck = import_keynote_md_to_deck(args.keynote_md.resolve())
        save_deck(out.resolve(), deck)
        print(f"Wrote {out} with {len(deck['slides'])} slides (stable id per slide).")
        print("Next: python keynote_deck.py migrate-images …/keynote.json slide_images/")
        return

    deck = load_deck(args.deck_json.resolve())
    lines = migrate_indexed_images_to_ids(deck, args.image_dir, dry_run=args.dry_run)
    for line in lines:
        print(line)


if __name__ == "__main__":
    try:
        main()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
