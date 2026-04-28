# WCCCE keynote deck — handoff summary

For another agent continuing work on this repo.

## What this repo is

- **Deck format:** `keynote.json` — JSON with `frontmatter`, `slides[]`, models, paths. Each slide has stable `id` (UUID), `kind`, `markdown`, `title`, `body`, `image_prompt`, and **`credits`** (boolean).
- **Tools:** `slide_editor.py` — Tk UI to edit the deck, preview slides, generate images via OpenRouter, **Present** mode.
- **`keynote_deck.py`** — load/save deck; **`ensure_deck_defaults()`** adds/normalizes `credits` on slides and deck-level credits timing if missing.
- **`generator.py`** — LLM suggest/render; **`generate_slides.py`** — PowerPoint export from `markdown` (credits are presenter-only; PPTX treats credits slides as normal content).

## Credits slide feature (implemented)

When **`credits: true`** on a slide:

- **Presenter** (`PresentModeApp` in `slide_editor.py`): full-width markdown only (no side image). Markdown scrolls upward after a delay at configurable px/s. Navigating away and back **restarts** the animation.
- **Deck-level timing** (in JSON and editor toolbar): `credits_start_delay_seconds` (default `2.0`), `credits_scroll_pixels_per_second` (default `30`). Clamped in `keynote_deck.py`.
- **Editor:** per-slide checkbox **“Credits — scroll markdown up during presentation”** under Title in the content editor; toolbar row for delay/speed.

Implementation notes for debugging:

- `_show_slide()` calls `_credits_cancel()` first.
- Credits markdown is padded with blank lines; scroll uses `md_text.count(..., 'ypixels')` and `yview_moveto`.

## Bugfix (unrelated to credits)

- **`wraplength` on `_title_preview`:** `_title_preview` is `tk.Text`, not `Label`; `wraplength` is invalid. Removed `<Configure>` bind and `_on_left_configure` — Text already uses `wrap=WORD`.

## Deck content position you care about

- Slide **“Let’s Build”** id `b234d7ad-276e-4014-b6de-265de40a376d`.
- **Immediately after it:** a **Credits** slide id `4abab33a-db3c-4ff3-9cc2-026601a6fbec`, **`credits: true`**, placeholder Thanks/Sources body — **edit copy in the editor**.
- Next slide: **“The End”** (`80032e32-d769-493f-bd86-1fdc27a2c1da`).

## Commands

```bash
python slide_editor.py --deck keynote.json           # editor
python slide_editor.py --present --deck keynote.json # standalone presenter
```

Optional: `--present-windowed`, `--debug`.

## Files touched in this workstream

- `keynote_deck.py` — defaults + `ensure_deck_defaults`, `load_deck` normalization.
- `slide_editor.py` — credits UI, presenter scrolling, removed bad `wraplength` callback.
- `keynote.json` — all slides have `credits`; deck has timing keys; credits slide inserted as above.

---

If extending credits: consider per-slide delay/speed, looping scroll, or keeping image visible beside text — none of those are implemented yet.
