# Design Document

## Overview

This is a code-removal cleanup. No new features are introduced. The design specifies exactly which code blocks, imports, and documentation sections to remove from four files, and what the resulting clean state looks like.

## Approach

Pure deletion with minimal edits to docstrings and one function body simplification. No new abstractions, no new files, no dependency changes.

## Changes

### 1. `keynote_deck.py` — Remove Legacy Functions, CLI, and Unused Imports

**Remove these functions entirely:**
- `slides_chunks_from_markdown()` (lines ~107–120)
- `import_keynote_md_to_deck()` (lines ~123–145)
- `migrate_indexed_images_to_ids()` (lines ~186–215)
- `main()` (lines ~218–244)
- `if __name__ == "__main__":` block (lines ~247–251)

**Remove these imports:**
- `import argparse`
- `import shutil`
- `import uuid`
- From the `from generator import (...)` block, remove `keynote_slides_metadata`, `parse_frontmatter`, `split_slides`

**Keep these imports:**
- `from generator import (DEFAULT_MODEL, SCRIPT_DIR)` — used by `default_deck_shell()`
- `import json`, `import sys`, `from pathlib import Path`, `from __future__ import annotations`

**Update the module docstring:**
- Remove the two CLI usage lines (`python keynote_deck.py import ...` and `python keynote_deck.py migrate-images ...`)
- Keep the description of the deck format and the reference to `generator.py --deck` and `slide_editor.py --deck`

**Preserved functions (unchanged):**
- `_normalize_text_field()`
- `_serialize_text_field()`
- `_coerce_float()`
- `ensure_deck_defaults()`
- `default_deck_shell()`
- `load_deck()`
- `save_deck()`
- All constants (`DECK_VERSION`, `CREDITS_*`, `TEXT_FIELDS`)

### 2. `generate_slides.py` — Remove Legacy Image Fallback

**In `add_slide_image_column()`:**

Replace the current candidate-building logic:

```python
candidates: list[Path] = []
if slide_id:
    sid = slide_id.strip()
    if sid:
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            candidates.append(image_dir / f"{sid}{ext}")
for ext in (".png", ".jpg", ".jpeg", ".webp"):
    candidates.append(image_dir / f"{slide_index:02d}{ext}")
for cand in candidates:
    if cand.is_file():
        path = cand
        break
```

With UUID-only lookup:

```python
if slide_id:
    sid = slide_id.strip()
    if sid:
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            cand = image_dir / f"{sid}{ext}"
            if cand.is_file():
                path = cand
                break
```

**Update the docstring** of `add_slide_image_column` to remove the "legacy `{nn}.png`" reference.

**Update the module-level docstring** to remove the mention of `00.png`, `01.png` fallback.

**Update the `--images` argparse help text** to remove the "else 00.png …" reference.

### 3. `generator.py` — Remove Legacy Style Fallback

**In `load_global_style()`:**

Remove the middle block that reads `deck.get("style_prompt")`. The function becomes:

```python
def load_global_style(style_path: Path, deck: dict) -> str:
    """Read global style from the markdown file, falling back to a built-in default."""
    if style_path.is_file():
        text = style_path.read_text(encoding="utf-8").strip()
        if text:
            return text
        print(f"Warning: {style_path} is empty; using fallback style.", file=sys.stderr)

    print(
        f"Warning: no style file at {style_path}; using DEFAULT_STYLE_FALLBACK.",
        file=sys.stderr,
    )
    return DEFAULT_STYLE_FALLBACK
```

The `deck` parameter can remain in the signature for now (callers pass it) — removing it would be a separate refactor.

### 4. `README.md` — Remove Legacy Documentation

**Remove the "Migrate numbered images to UUID filenames" subsection** under "Forking and Customization" (the `### Migrate numbered images…` heading and its content including the `python keynote_deck.py migrate-images` code block).

**Remove the `python keynote_deck.py import` code block** under "Create a new deck" (the "Alternatively, if you have a markdown file…" paragraph and its code block).

**Update the `--images` CLI flag description** in the generate_slides section to remove the "else 00.png …" fallback mention.

## Correctness Properties

### Property 1: Deck Load/Save Round-Trip Preserved

**Requirement refs:** 1.6

**Property:** For any valid deck dict with slides containing text fields, `load_deck(save_deck(deck))` produces an equivalent deck. This verifies the surviving load/save code is not broken by the removal of adjacent functions.

**Test approach:** Example-based test. Create a deck with representative slides (title, body, markdown with newlines, credits flag), save to a temp file, load it back, and assert structural equivalence.

### Property 2: UUID-Only Image Lookup

**Requirement refs:** 4.1, 4.2, 4.3

**Property:** `add_slide_image_column` finds images only by `{slide_id}.ext` and ignores numbered files even when they exist on disk.

**Test approach:** Example-based test. Create a temp directory with both `{uuid}.png` and `00.png`. Call the function with `slide_id=uuid, slide_index=0`. Verify the UUID image is used. Then call with a non-existent UUID — verify placeholder is rendered and `00.png` is NOT used.

### Property 3: Style Loading Without Legacy Fallback

**Requirement refs:** 5.1, 5.2, 5.3

**Property:** `load_global_style` returns file content when the file exists, and `DEFAULT_STYLE_FALLBACK` otherwise — regardless of whether `deck["style_prompt"]` is set.

**Test approach:** Example-based test. Call with (a) a valid style file → returns file content, (b) an empty style file with `deck={"style_prompt": "legacy"}` → returns `DEFAULT_STYLE_FALLBACK`, not "legacy".

### Property 4: Removed Symbols Absent from Module

**Requirement refs:** 1.1–1.4, 2.1–2.2, 3.1–3.3

**Property:** After import, `keynote_deck` module has no attributes named `slides_chunks_from_markdown`, `import_keynote_md_to_deck`, `migrate_indexed_images_to_ids`, or `main`.

**Test approach:** Example-based test. Import the module and assert `hasattr()` returns False for each removed name.

### Property 5: No Codebase References to Removed Functions

**Requirement refs:** 7.1–7.4

**Property:** A grep across all `.py` files finds zero matches for the removed function names (excluding test files that verify absence).

**Test approach:** Example-based test using `grep` or source file reads.
