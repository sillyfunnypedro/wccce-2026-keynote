#!/usr/bin/env python3
"""
Interactive editor: per-slide layout preview (slide text left, image right), image prompt,
LLM suggest, OpenRouter render.

  python slide_editor.py --deck keynote.json

Requires Pillow for PNG previews in the right column (pip install pillow).

List previews use ``slide_images/.thumbs/{id}_{size}.png`` when possible; they are
regenerated when the slide image is newer than the cached thumbnail.

**Paste image:** With focus on the slide's **preview square** (or the **Paste image** button), use
``Ctrl+V`` / ``Cmd+V`` to save the clipboard image as this slide's ``{id}.png``, replacing any
existing file.

Each slide's title, body, and image_prompt — plus its image at ``{id}.png`` — live in
``keynote.json``. Render/suggest use generator.py and OPENROUTER_API_KEY (or .env key files).

Presenter (read-only):

  python slide_editor.py --present --deck keynote.json

  ``←`` / ``→`` / Space: change slide; ``Esc`` exits fullscreen or closes. Add ``--present-windowed`` to skip fullscreen.

In the editor, use the **Present** toolbar button to open the same presenter in a window; **Quit** / ``Esc`` returns to the editor.

Optional: pass ``--debug`` for scroll/button probe logging and a one-line slide build timing (off by default).

Optional: ``--profile-startup`` runs ``cProfile`` from first slide-row build through the end of the
thumbnail queue, prints cumulative stats to stderr, and writes ``slide_editor_startup.prof`` in this
directory (inspect with ``python -m pstats slide_editor_startup.prof`` or snakeviz).
``--profile-startup-exit`` turns that on as well and closes the app right after the profile is written
(handy for ``py-spy record …``).
"""

from __future__ import annotations

import argparse
import cProfile
import copy
import json
import logging
import pstats
import re
import sys
from collections import OrderedDict
from collections.abc import Callable
import threading
import time
import tkinter as tk
import uuid
from pathlib import Path
from tkinter import filedialog, font as tkfont, messagebox, scrolledtext

import generator as gen
import keynote_deck as kd

SCRIPT_DIR = Path(__file__).parent
LOG = logging.getLogger("slide_editor")
SCROLL_DEBUG_FILE = SCRIPT_DIR / "scroll_debug.log"
SETTINGS_PATH = SCRIPT_DIR / "settings.json"

# Set True from CLI ``--debug`` (see ``main()``). When False, skip scroll probe file I/O.
_SCROLL_DEBUG = False

# Set True from CLI ``--perf-label-body``. Diagnostic: replace the body-preview ``Text``
# widget with a plain ``Label`` to measure how much of startup is the ``Text`` widget.
_PERF_LABEL_BODY = False

# Set True from CLI ``--perf-collapsed-rows``. Diagnostic: skip the right-hand editor pane,
# the image-prompt text box, and the action button column per row. Simulates a collapsed-
# row design where the editor widgets are created lazily on expand.
_PERF_COLLAPSED_ROWS = False


def _scroll_debug_enabled() -> bool:
    return _SCROLL_DEBUG

# Slide-card preview (approximates PPTX: text left, square image right)
SLIDE_BG = "#1a1a2e"
SLIDE_PANEL_BG = "#16162a"
SLIDE_TEXT = "#f5f5f5"
SLIDE_DIM = "#a0a8c0"
SLIDE_IMG_PX = 240
# Editor slide-card: text column padx (left, right) — wider left inset when there is no PNG yet.
SLIDE_CARD_TEXT_PADX_WITH_IMG = (12, 4)
SLIDE_CARD_TEXT_PADX_NO_IMG = (52, 4)
# Presenter: md_frame grid padx when split with image vs full-width text only.
PRESENT_MD_FRAME_PADX_WITH_IMG = (0, 6)
PRESENT_MD_FRAME_PADX_NO_IMG = (56, 12)

try:
    from PIL import Image, ImageGrab, ImageTk

    HAS_PIL = True
    # List previews only — fast downscale (presenter / render still use their own paths).
    _THUMB_RESAMPLE = Image.Resampling.BILINEAR
except ImportError:
    HAS_PIL = False
    ImageGrab = None  # type: ignore[misc, assignment]
    _THUMB_RESAMPLE = None  # type: ignore[misc, assignment]

# LRU cache: (resolved path, mtime_ns or -1, max_side) -> (PhotoImage|None, err)
_THUMB_CACHE: OrderedDict[tuple[str, int, int], tuple[object | None, str]] = OrderedDict()
_THUMB_CACHE_LIMIT = 256


def _clipboard_pil_image() -> Image.Image | None:
    """Return a PIL image from the system clipboard, or None if unavailable or not an image."""
    if not HAS_PIL or ImageGrab is None:
        return None
    try:
        data = ImageGrab.grabclipboard()
    except Exception:
        return None
    if data is None:
        return None
    if isinstance(data, Image.Image):
        return data
    if isinstance(data, list):
        for item in data:
            path = Path(str(item))
            if path.suffix.lower() in (
                ".png",
                ".jpg",
                ".jpeg",
                ".webp",
                ".gif",
                ".bmp",
                ".tif",
                ".tiff",
            ):
                try:
                    return Image.open(path)
                except OSError:
                    continue
        return None
    return None


def _load_settings() -> dict:
    if not SETTINGS_PATH.is_file():
        return {}
    try:
        raw = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _save_settings(data: dict) -> None:
    try:
        SETTINGS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    except OSError:
        LOG.debug("Could not write settings file: %s", SETTINGS_PATH)


def _thumb_cache_key(path: Path, max_side: int) -> tuple[str, int, int] | None:
    try:
        resolved = str(path.resolve())
    except OSError:
        return None
    if not path.is_file():
        return (resolved, -1, max_side)
    try:
        return (resolved, int(path.stat().st_mtime_ns), max_side)
    except OSError:
        return (resolved, -1, max_side)


def _thumb_cache_store(key: tuple[str, int, int], out: tuple[object | None, str]) -> tuple[object | None, str]:
    _THUMB_CACHE[key] = out
    _THUMB_CACHE.move_to_end(key)
    while len(_THUMB_CACHE) > _THUMB_CACHE_LIMIT:
        _THUMB_CACHE.popitem(last=False)
    return out


def _thumb_disk_cache_path(source: Path, max_side: int) -> Path:
    """Small PNG next to slide images: ``slide_images/.thumbs/{id}_{max_side}.png``."""
    return source.parent / ".thumbs" / f"{source.stem}_{max_side}{source.suffix}"


def _thumb_disk_cache_is_fresh(source: Path, cache_path: Path) -> bool:
    """True if ``cache_path`` exists and was written at or after the source file's current mtime."""
    try:
        if not cache_path.is_file() or not source.is_file():
            return False
        return source.stat().st_mtime_ns <= cache_path.stat().st_mtime_ns
    except OSError:
        return False


def _write_thumb_disk_cache(im: Image.Image, cache_path: Path) -> None:
    """Write PNG atomically; ignore failures (read-only tree, etc.)."""
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return
    tmp = cache_path.with_name(cache_path.name + ".tmp")
    try:
        im.save(tmp, "PNG", optimize=True)
        tmp.replace(cache_path)
    except OSError:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def _thumb_photo(path: Path, max_side: int = SLIDE_IMG_PX) -> tuple[object | None, str]:
    """Return (PhotoImage or None, status text when preview cannot be shown)."""
    key = _thumb_cache_key(path, max_side)
    if key is None:
        return None, "No image"
    hit = _THUMB_CACHE.get(key)
    if hit is not None:
        _THUMB_CACHE.move_to_end(key)
        return hit
    if not path.is_file():
        return _thumb_cache_store(key, (None, "No image"))
    if not HAS_PIL:
        return _thumb_cache_store(key, (None, "pip install pillow\nfor preview"))
    disk = _thumb_disk_cache_path(path, max_side)
    try:
        if _thumb_disk_cache_is_fresh(path, disk):
            im = Image.open(disk)
            if im.mode != "RGBA":
                im = im.convert("RGBA")
            photo = ImageTk.PhotoImage(im)
            return _thumb_cache_store(key, (photo, ""))
        im = Image.open(path)
        im.thumbnail((max_side, max_side), _THUMB_RESAMPLE)
        if im.mode != "RGBA":
            im = im.convert("RGBA")
        _write_thumb_disk_cache(im, disk)
        photo = ImageTk.PhotoImage(im)
        return _thumb_cache_store(key, (photo, ""))
    except Exception as e:
        return _thumb_cache_store(key, (None, str(e)[:80]))


def configure_markdown_tags(text_widget: tk.Text, *, base_pt: int = 10) -> None:
    f = ("TkDefaultFont", base_pt)
    fb = ("TkDefaultFont", base_pt, "bold")
    fi = ("TkDefaultFont", base_pt, "italic")
    fc = ("TkFixedFont", base_pt)
    fs = tkfont.Font(family="TkDefaultFont", size=base_pt, overstrike=1)
    fs_h1 = tkfont.Font(family="TkDefaultFont", size=base_pt + 2, weight="bold", overstrike=1)
    fs_h2 = tkfont.Font(family="TkDefaultFont", size=base_pt, weight="bold", overstrike=1)
    fs_h3 = tkfont.Font(family="TkDefaultFont", size=base_pt, weight="bold", overstrike=1)
    text_widget.tag_configure("md_base", foreground=SLIDE_TEXT, font=f)
    text_widget.tag_configure("md_bold", foreground=SLIDE_TEXT, font=fb)
    text_widget.tag_configure("md_italic", foreground=SLIDE_TEXT, font=fi)
    text_widget.tag_configure("md_strike", foreground=SLIDE_TEXT, font=fs)
    text_widget.tag_configure("md_strike_h1", foreground=SLIDE_TEXT, font=fs_h1)
    text_widget.tag_configure("md_strike_h2", foreground=SLIDE_TEXT, font=fs_h2)
    text_widget.tag_configure("md_strike_h3", foreground="#d7d7df", font=fs_h3)
    text_widget.tag_configure(
        "md_code", foreground="#d7d7df", font=fc, background="#22263d"
    )
    text_widget.tag_configure("md_bullet", foreground="#e94f37", font=fb)
    text_widget.tag_configure("md_h1", foreground=SLIDE_TEXT, font=("TkDefaultFont", base_pt + 2, "bold"))
    text_widget.tag_configure("md_h2", foreground=SLIDE_TEXT, font=fb)
    text_widget.tag_configure("md_h3", foreground="#d7d7df", font=fb)


def insert_markdown_lines(text_widget: tk.Text, text: str, *, base_pt: int = 10) -> None:
    """Append markdown-ish lines to ``text_widget`` (caller clears first if needed)."""
    configure_markdown_tags(text_widget, base_pt=base_pt)
    lines = text.splitlines() or [""]
    inline_pat = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|~~[^~]+~~)")
    for i, line in enumerate(lines):
        stripped = line.strip()
        line_tag = "md_base"
        if stripped.startswith("### "):
            line = stripped[4:]
            line_tag = "md_h3"
        elif stripped.startswith("## "):
            line = stripped[3:]
            line_tag = "md_h2"
        elif stripped.startswith("# "):
            line = stripped[2:]
            line_tag = "md_h1"
        if stripped.startswith("- "):
            text_widget.insert(tk.END, "• ", ("md_bullet",))
            line = stripped[2:]
        parts = inline_pat.split(line)
        for part in parts:
            if not part:
                continue
            if part.startswith("**") and part.endswith("**") and len(part) >= 4:
                text_widget.insert(tk.END, part[2:-2], ("md_bold",))
            elif part.startswith("~~") and part.endswith("~~") and len(part) >= 5:
                strike_tag = {
                    "md_h1": "md_strike_h1",
                    "md_h2": "md_strike_h2",
                    "md_h3": "md_strike_h3",
                }.get(line_tag, "md_strike")
                text_widget.insert(tk.END, part[2:-2], (strike_tag,))
            elif part.startswith("*") and part.endswith("*") and len(part) >= 3:
                text_widget.insert(tk.END, part[1:-1], ("md_italic",))
            elif part.startswith("`") and part.endswith("`") and len(part) >= 3:
                text_widget.insert(tk.END, part[1:-1], ("md_code",))
            else:
                text_widget.insert(tk.END, part, (line_tag,))
        if i < len(lines) - 1:
            text_widget.insert(tk.END, "\n", ("md_base",))


_INLINE_MD_STRIP_PAT = re.compile(r"\*\*([^*]+)\*\*|~~([^~]+)~~|\*([^*]+)\*|`([^`]+)`")


def strip_inline_markdown(text: str) -> str:
    """Remove inline markdown markers (bold/strike/italic/code) for plain display."""
    def _sub(m: re.Match) -> str:
        return next(g for g in m.groups() if g is not None)
    return _INLINE_MD_STRIP_PAT.sub(_sub, text)


def insert_title_markdown(text_widget: tk.Text, text: str, *, base_pt: int = 12) -> None:
    """Render a slide title with inline markdown — bold by default, plus strike/italic."""
    fb = tkfont.Font(family="TkDefaultFont", size=base_pt, weight="bold")
    fi = tkfont.Font(family="TkDefaultFont", size=base_pt, weight="bold", slant="italic")
    fs = tkfont.Font(family="TkDefaultFont", size=base_pt, weight="bold", overstrike=1)
    text_widget.tag_configure("title_base", foreground=SLIDE_TEXT, font=fb)
    text_widget.tag_configure("title_italic", foreground=SLIDE_TEXT, font=fi)
    text_widget.tag_configure("title_strike", foreground=SLIDE_TEXT, font=fs)

    inline_pat = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*|~~[^~]+~~)")
    parts = inline_pat.split(text)
    for part in parts:
        if not part:
            continue
        if part.startswith("**") and part.endswith("**") and len(part) >= 4:
            text_widget.insert(tk.END, part[2:-2], ("title_base",))
        elif part.startswith("~~") and part.endswith("~~") and len(part) >= 5:
            text_widget.insert(tk.END, part[2:-2], ("title_strike",))
        elif part.startswith("*") and part.endswith("*") and len(part) >= 3:
            text_widget.insert(tk.END, part[1:-1], ("title_italic",))
        else:
            text_widget.insert(tk.END, part, ("title_base",))


def _present_slide_markdown(spec: dict, index: int) -> str:
    md = str(spec.get("markdown", "")).strip()
    if md:
        return md
    title = str(spec.get("title", f"Slide {index}")).strip()
    body = str(spec.get("body", "")).strip()
    if body:
        return f"# {title}\n\n{body}".strip()
    return f"# {title}" if title else "(empty slide)"


def _strip_leading_title_heading_for_present(markdown: str, slide_title: str) -> str:
    """Drop the first heading line if it duplicates ``slide_title`` (title already shown above the body)."""
    st = slide_title.strip()
    if not st:
        return markdown
    lines = markdown.splitlines()
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines):
        return markdown
    m = re.match(r"^#{1,6}\s+(.*)$", lines[i].strip())
    if not m:
        return markdown
    heading_inner = m.group(1).strip()

    def _plain(s: str) -> str:
        t = re.sub(r"[*_`]+", "", s)
        t = re.sub(r"\s+", " ", t).strip().lower()
        return t

    if _plain(heading_inner) != _plain(st):
        return markdown
    j = i + 1
    while j < len(lines) and not lines[j].strip():
        j += 1
    rest = "\n".join(lines[j:]).strip()
    return rest if rest else ""


def _present_slide_image_path(output_dir: Path, spec: dict) -> Path | None:
    """Resolve the rendered image for one deck slide (``{id}.png``)."""
    sid = str(spec.get("id", "")).strip()
    if not sid:
        return None
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        p = output_dir / f"{sid}{ext}"
        if p.is_file():
            return p
    return None


def _load_scaled_photo(path: Path, max_w: int, max_h: int) -> tuple[object | None, str]:
    """One-off PhotoImage scaled to fit inside max_w × max_h (presenter, not LRU cache)."""
    if not path.is_file():
        return None, "No image"
    if not HAS_PIL:
        return None, "pip install pillow"
    try:
        im = Image.open(path)
        mw, mh = max(1, max_w), max(1, max_h)
        im.thumbnail((mw, mh), Image.Resampling.LANCZOS)
        if im.mode != "RGBA":
            im = im.convert("RGBA")
        return ImageTk.PhotoImage(im), ""
    except Exception as e:
        return None, str(e)[:120]


def _log_scroll(msg: str) -> None:
    """Scroll/input debug (expensive: file + stderr). On only with ``--debug``."""
    if not _scroll_debug_enabled():
        return
    LOG.info(msg)
    print(f"[scroll] {msg}", file=sys.stderr, flush=True)
    try:
        with SCROLL_DEBUG_FILE.open("a", encoding="utf-8") as f:
            f.write(f"{msg}\n")
    except OSError:
        pass


def _init_scroll_debug_log() -> None:
    """Reset debug log when scroll debug is enabled."""
    if not _scroll_debug_enabled():
        return
    try:
        SCROLL_DEBUG_FILE.write_text("", encoding="utf-8")
        with SCROLL_DEBUG_FILE.open("a", encoding="utf-8") as f:
            f.write("scroll debug log initialized\n")
    except OSError:
        pass


class SlideRow(tk.Frame):
    def __init__(
        self,
        master,
        app: "SlideEditorApp",
        index: int,
        title: str,
        body: str,
        prompt: str,
        *,
        slide_id: str,
        credits: bool = False,
        skip_initial_preview: bool = False,
    ):
        super().__init__(master)
        self.app = app
        self.index = index
        self.slide_id = slide_id
        self._photo: object | None = None
        self._preview_title = title
        self._preview_body = body
        self._prompt_cache = prompt
        self._credits_cache = bool(credits)

        # Editor widgets are built lazily (see ``ensure_editor``); until then these are None.
        self._editor_built = False
        self.title_edit_var = tk.StringVar(value=self._preview_title)
        self.credits_var = tk.BooleanVar(value=self._credits_cache)
        self.credits_check: tk.Checkbutton | None = None
        self.title_edit: tk.Entry | None = None
        self.body_edit: scrolledtext.ScrolledText | None = None
        self.txt: scrolledtext.ScrolledText | None = None
        self._prompt_label: tk.Label | None = None
        self._editor_frame: tk.Frame | None = None
        self._button_frame: tk.Frame | None = None
        self.btn_request_edit: tk.Button | None = None
        self.btn_suggest: tk.Button | None = None
        self.btn_preview: tk.Button | None = None
        self.btn_render: tk.Button | None = None
        self.btn_paste: tk.Button | None = None
        self.btn_delete_image: tk.Button | None = None
        self.btn_present: tk.Button | None = None
        self.btn_copy_locator: tk.Button | None = None
        self.btn_insert: tk.Button | None = None
        self.btn_delete: tk.Button | None = None

        self._build_card()

        self.columnconfigure(0, weight=1)
        self.columnconfigure(3, weight=0)
        self.rowconfigure(3, weight=0)

        # Collapse state: start collapsed; visibility tracker will expand visible rows.
        self._collapsed = True
        self._slide_card: tk.Frame | None = None  # set in _build_card

        if skip_initial_preview:
            self._show_preview_placeholder()
            self._slide_card_text.grid_configure(padx=SLIDE_CARD_TEXT_PADX_NO_IMG)
        else:
            self.refresh_preview()

    def _build_card(self) -> None:
        """Build the always-on part of the row: header, slide card, preview canvas, dividers."""
        self._top_title_label = tk.Label(
            self,
            text=self._title_line(),
            fg="#1a1a2e",
            font=("TkDefaultFont", 12, "bold"),
            anchor="w",
            justify="left",
        )
        self._top_title_label.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 6))

        slide_card = tk.Frame(self, bg=SLIDE_BG, highlightbackground="#4a4a62", highlightthickness=1)
        slide_card.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        self._slide_card = slide_card
        slide_card.columnconfigure(0, weight=1, minsize=280)
        slide_card.columnconfigure(1, weight=0)

        left = tk.Frame(slide_card, bg=SLIDE_BG)
        self._slide_card_text = left
        left.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=SLIDE_CARD_TEXT_PADX_NO_IMG,
            pady=12,
        )

        self._title_preview = tk.Text(
            left,
            height=2,
            bg=SLIDE_BG,
            fg=SLIDE_TEXT,
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0,
            wrap=tk.WORD,
            cursor="arrow",
            takefocus=0,
            padx=0,
            pady=0,
        )
        self._title_preview.pack(anchor="w", fill=tk.X, pady=(0, 8))
        self._render_title_preview()

        if _PERF_LABEL_BODY:
            self._body_preview = tk.Label(
                left,
                text="",
                bg=SLIDE_PANEL_BG,
                fg=SLIDE_TEXT,
                font=("TkDefaultFont", 10),
                anchor="nw",
                justify="left",
                wraplength=280,
                padx=8,
                pady=8,
            )
        else:
            self._body_preview = tk.Text(
                left,
                height=10,
                width=40,
                wrap="word",
                font=("TkDefaultFont", 10),
                bg=SLIDE_PANEL_BG,
                fg=SLIDE_TEXT,
                relief=tk.FLAT,
                padx=8,
                pady=8,
                highlightthickness=0,
                cursor="arrow",
                insertwidth=0,
            )
            configure_markdown_tags(self._body_preview, base_pt=10)
            self._body_preview.bind("<Key>", lambda _e: "break")
        self._body_preview.pack(fill=tk.BOTH, expand=True, anchor="nw")
        self._fill_body_preview()

        right_wrap = tk.Frame(slide_card, bg=SLIDE_BG)
        right_wrap.grid(row=0, column=1, sticky="ne", padx=(8, 12), pady=12)
        border = tk.Frame(right_wrap, relief=tk.GROOVE, borderwidth=1, bg="#2a2e48")
        border.pack()
        self.preview_canvas = tk.Canvas(
            border,
            width=SLIDE_IMG_PX,
            height=SLIDE_IMG_PX,
            bg="#2a2e48",
            highlightthickness=0,
        )
        self.preview_canvas.pack(padx=4, pady=4)
        for widget in (self.preview_canvas, border, right_wrap):
            for seq in ("<Control-v>", "<Command-v>"):
                widget.bind(seq, self._on_paste_image_shortcut)

        # Strong visual divider between slide cards.
        self._divider = tk.Frame(self, bg="#e94f37", height=3)
        self._divider.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(8, 2))
        self._divider_shadow = tk.Frame(self, bg="#3f435f", height=1)
        self._divider_shadow.grid(row=5, column=0, columnspan=4, sticky="ew", pady=(0, 2))

        # Card-area interactions expedite editor build. Using add="+" keeps any widget-
        # specific default behavior (text cursor placement, canvas click, etc.).
        expand_targets = (
            self._top_title_label,
            self._title_preview,
            left,
            self._body_preview,
            self.preview_canvas,
            slide_card,
        )
        for w in expand_targets:
            w.bind("<Button-1>", self._on_card_activate, add="+")
            w.bind("<FocusIn>", self._on_card_activate, add="+")

    def ensure_editor(self) -> None:
        """Idempotent; create the editor pane, prompt box, and button column if not yet built.

        Called by the app's idle-time build queue and on first card interaction.
        """
        if self._editor_built:
            return
        if _PERF_COLLAPSED_ROWS:
            return
        self._build_editor()
        self._editor_built = True
        bind = getattr(self.app, "_bind_scroll_handlers", None)
        if bind is not None:
            bind(self)
        # Update scroll region after new widgets change the inner frame height.
        apply = getattr(self.app, "_apply_scroll_region", None)
        if apply is not None:
            self.after_idle(apply)

    def _on_card_activate(self, _event: tk.Event | None = None) -> None:
        self.ensure_editor()

    def _build_editor(self) -> None:
        """Build the right-column content editor + image-prompt textbox + action buttons."""
        editor = tk.Frame(self, relief=tk.GROOVE, borderwidth=1, padx=8, pady=8)
        editor.grid(row=1, column=3, sticky="nsew", padx=(10, 0), pady=(0, 8))
        self._editor_frame = editor
        tk.Label(editor, text="Content editor", font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        tk.Label(editor, text="Title", anchor="w").pack(anchor="w", pady=(8, 2))
        self.title_edit = tk.Entry(editor, textvariable=self.title_edit_var, width=42)
        self.title_edit.pack(fill=tk.X, anchor="w")
        self.credits_check = tk.Checkbutton(
            editor,
            text="Credits — scroll markdown up during presentation",
            variable=self.credits_var,
            anchor="w",
            command=lambda: self.app.schedule_autosave(),
        )
        self.credits_check.pack(anchor="w", pady=(6, 0))
        tk.Label(editor, text="Content (markdown)", anchor="w").pack(anchor="w", pady=(8, 2))
        self.body_edit = scrolledtext.ScrolledText(
            editor, height=11, width=42, wrap=tk.WORD, font=("TkDefaultFont", 10)
        )
        self.body_edit.pack(fill=tk.BOTH, expand=True, anchor="w")
        self.body_edit.insert("1.0", self._preview_body)
        self.title_edit.bind("<KeyRelease>", self._on_content_edit)
        self.body_edit.bind("<KeyRelease>", self._on_content_edit)
        self.title_edit.bind("<FocusOut>", self._on_content_edit)
        self.body_edit.bind("<FocusOut>", self._on_content_edit)

        self._prompt_label = tk.Label(self, text="Image prompt (LLM → OpenRouter):", anchor="w")
        self._prompt_label.grid(row=2, column=0, columnspan=4, sticky="w", pady=(0, 2))
        self.txt = scrolledtext.ScrolledText(
            self, height=4, width=72, wrap=tk.WORD, font=("TkFixedFont", 10)
        )
        self.txt.grid(row=3, column=0, columnspan=3, sticky="nsew", pady=(0, 4))
        self.txt.insert("1.0", self._prompt_cache)
        self.txt.bind("<KeyRelease>", lambda _e: self.app.schedule_autosave())

        bf = tk.Frame(self)
        bf.grid(row=3, column=3, sticky="ne", padx=(8, 0))
        self._button_frame = bf
        # Buttons in a 2-column grid so each slide row is roughly half as tall.
        # Left column = content/LLM actions; right column = image/file actions.
        self.btn_request_edit = tk.Button(
            bf, text="Suggest", width=9, command=self._on_suggest_edit
        )
        self.btn_suggest = tk.Button(
            bf, text="Image\nprompt", width=9, command=self._on_suggest
        )
        self.btn_preview = tk.Button(
            bf, text="Preview\nrender", width=9, command=self._on_preview_render_prompt
        )
        self.btn_render = tk.Button(
            bf, text="Render", width=9, command=self._on_render
        )
        self.btn_paste = tk.Button(
            bf, text="Paste\nimage", width=9, command=self._on_paste_image_button
        )
        self.btn_delete_image = tk.Button(
            bf, text="Delete\nimage", width=9, command=self._on_delete_image
        )
        self.btn_present = tk.Button(
            bf, text="Present\nfrom here", width=9, command=self._on_present_from_here
        )
        self.btn_copy_locator = tk.Button(
            bf, text="Copy AI\nlocator", width=9, command=self._on_copy_ai_locator
        )
        self.btn_insert = tk.Button(
            bf, text="Insert\nabove", width=9, command=self._on_insert_above
        )
        self.btn_delete = tk.Button(
            bf, text="Delete", width=9, command=self._on_delete
        )
        grid = (
            (self.btn_request_edit, self.btn_suggest),
            (self.btn_preview,      self.btn_render),
            (self.btn_paste,        self.btn_delete_image),
            (self.btn_present,      self.btn_copy_locator),
            (self.btn_insert,       self.btn_delete),
        )
        for r, (left, right) in enumerate(grid):
            left.grid(row=r, column=0, sticky="ew", padx=(0, 3), pady=2)
            right.grid(row=r, column=1, sticky="ew", padx=(3, 0), pady=2)
        bf.columnconfigure(0, weight=1)
        bf.columnconfigure(1, weight=1)

    def collapse(self) -> None:
        """Hide the slide card body to reduce height — only title header visible."""
        if self._collapsed:
            return
        self._collapsed = True
        if self._slide_card is not None:
            self._slide_card.grid_remove()
        if self._divider is not None:
            self._divider.grid_remove()
        if self._divider_shadow is not None:
            self._divider_shadow.grid_remove()
        # Also hide editor/prompt if built
        if self._editor_frame is not None:
            self._editor_frame.grid_remove()
        if self._prompt_label is not None:
            self._prompt_label.grid_remove()
        if self.txt is not None:
            self.txt.grid_remove()
        if self._button_frame is not None:
            self._button_frame.grid_remove()

    def expand(self) -> None:
        """Show the full slide card."""
        if not self._collapsed:
            return
        self._collapsed = False
        if self._slide_card is not None:
            self._slide_card.grid()
        if self._divider is not None:
            self._divider.grid()
        if self._divider_shadow is not None:
            self._divider_shadow.grid()
        # Also show editor/prompt if built
        if self._editor_frame is not None:
            self._editor_frame.grid()
        if self._prompt_label is not None:
            self._prompt_label.grid()
        if self.txt is not None:
            self.txt.grid()
        if self._button_frame is not None:
            self._button_frame.grid()

    def _show_preview_placeholder(self) -> None:
        c = self.preview_canvas
        c.delete("all")
        c.create_text(
            SLIDE_IMG_PX // 2,
            SLIDE_IMG_PX // 2,
            text="…",
            fill="#a8a8b8",
            font=("TkDefaultFont", 11),
        )

    def _header_line(self) -> str:
        sid = (self.slide_id or "")[:8]
        if self.slide_id:
            return f"[{self.index:02d}]  id {sid}…"
        return f"[{self.index:02d}]"

    def _title_line(self) -> str:
        return f"{self._header_line()}  {strip_inline_markdown(self._preview_title)}"

    def _fill_body_preview(self) -> None:
        raw = (self._preview_body or "").strip()
        display = raw if raw else "(no body)"
        if _PERF_LABEL_BODY:
            self._body_preview.config(text=display)
            return
        self._body_preview.config(state=tk.NORMAL)
        self._body_preview.delete("1.0", tk.END)
        self._insert_markdown(display)
        self._body_preview.config(state=tk.DISABLED)

    def _insert_markdown(self, text: str) -> None:
        insert_markdown_lines(self._body_preview, text, base_pt=10)

    def get_prompt(self) -> str:
        if self.txt is not None:
            return self.txt.get("1.0", "end-1c").strip()
        return (self._prompt_cache or "").strip()

    def get_credits(self) -> bool:
        if self.credits_check is not None:
            return bool(self.credits_var.get())
        return bool(self._credits_cache)

    def get_title_text(self) -> str:
        return self.title_edit_var.get().strip()

    def get_body_text(self) -> str:
        if self.body_edit is not None:
            return self.body_edit.get("1.0", "end-1c").strip()
        return (self._preview_body or "").strip()

    def set_prompt(self, text: str) -> None:
        self._prompt_cache = text
        if self.txt is None:
            return
        self.txt.delete("1.0", tk.END)
        self.txt.insert("1.0", text)

    def _render_title_preview(self) -> None:
        self._title_preview.config(state=tk.NORMAL)
        self._title_preview.delete("1.0", tk.END)
        insert_title_markdown(self._title_preview, self._preview_title or "")
        self._title_preview.config(state=tk.DISABLED)

    def _on_content_edit(self, _event=None):
        title = self.get_title_text() or "(untitled)"
        body = self.get_body_text()
        self._preview_title = title
        self._preview_body = body
        self._top_title_label.config(text=self._title_line())
        self._render_title_preview()
        self._fill_body_preview()
        self.app.schedule_autosave()

    def update_slide_preview(self, title: str, body: str | None = None) -> None:
        self._preview_title = title
        if body is not None:
            self._preview_body = body
        self.title_edit_var.set(self._preview_title)
        if self.body_edit is not None:
            self.body_edit.config(state=tk.NORMAL)
            self.body_edit.delete("1.0", tk.END)
            self.body_edit.insert("1.0", self._preview_body)
        self._top_title_label.config(text=self._title_line())
        self._render_title_preview()
        self._fill_body_preview()

    def set_slide_title(self, title: str) -> None:
        self.update_slide_preview(title, None)

    def set_busy(self, busy: bool) -> None:
        st = tk.DISABLED if busy else tk.NORMAL
        for btn in (
            self.btn_present,
            self.btn_copy_locator,
            self.btn_request_edit,
            self.btn_suggest,
            self.btn_preview,
            self.btn_render,
            self.btn_paste,
            self.btn_delete_image,
        ):
            if btn is not None:
                btn.config(state=st)
        for btn in (self.btn_insert, self.btn_delete):
            if btn is not None:
                btn.config(state=st)

    def _slide_png_output_path(self) -> Path:
        return self.app.output_dir / f"{self.slide_id}.png"

    def _on_paste_image_shortcut(self, _event: tk.Event | None = None) -> str:
        self._paste_clipboard_image()
        return "break"

    def _on_paste_image_button(self) -> None:
        self._paste_clipboard_image()

    def _paste_clipboard_image(self) -> None:
        if not HAS_PIL:
            messagebox.showerror("Paste image", "Install Pillow: pip install pillow")
            return
        im = _clipboard_pil_image()
        if im is None:
            messagebox.showinfo(
                "Paste image",
                "No raster image found on the clipboard. Copy an image, click the preview square "
                "(or use Paste image), then try again.",
            )
            return
        self.app.output_dir.mkdir(parents=True, exist_ok=True)
        out_path = self._slide_png_output_path()
        existed_before = out_path.is_file()
        try:
            save_im = im
            if save_im.mode not in ("RGB", "RGBA"):
                save_im = save_im.convert("RGBA")
            save_im.save(out_path, "PNG")
            w, h = self.app.image_wh()
            gen.maybe_resize_png(out_path, w, h)
        except Exception as e:
            messagebox.showerror("Paste image", f"Could not save PNG:\n{e}")
            return
        self.refresh_preview()
        self.app.schedule_autosave()
        try:
            written_w, written_h = Image.open(out_path).size
            dim_line = f"\nDimensions: {written_w} × {written_h}"
        except Exception:
            dim_line = ""
        verb = "Overwrote" if existed_before else "Wrote"
        messagebox.showinfo(
            "Paste image",
            f"{verb} slide {self.index:02d} image.\n\n"
            f"File: {out_path}{dim_line}",
        )
        self.app.set_status(
            f"Slide {self.index:02d}: {verb.lower()} → {out_path.name}"
        )

    def _on_delete_image(self) -> None:
        """Remove this slide's rendered PNG and any cached thumbnails, then autosave."""
        out_path = self._slide_png_output_path()
        thumbs_dir = out_path.parent / ".thumbs"
        removed_main = False
        try:
            if out_path.is_file():
                out_path.unlink()
                removed_main = True
        except OSError as e:
            messagebox.showerror(
                "Delete image",
                f"Could not remove image:\n{out_path}\n\n{e}",
            )
            return
        removed_thumbs = 0
        if thumbs_dir.is_dir():
            stem = out_path.stem
            for tp in thumbs_dir.iterdir():
                if not tp.is_file():
                    continue
                tname = tp.name
                if tname == stem or tname.startswith(f"{stem}_") or tname.startswith(f"{stem}."):
                    try:
                        tp.unlink()
                        removed_thumbs += 1
                    except OSError:
                        pass
        if not removed_main and removed_thumbs == 0:
            self.app.set_status(f"Slide {self.index:02d}: no image to delete.")
            return
        self.refresh_preview()
        self.app.schedule_autosave()
        bits = []
        if removed_main:
            bits.append(out_path.name)
        if removed_thumbs:
            bits.append(f"{removed_thumbs} thumbnail{'s' if removed_thumbs != 1 else ''}")
        self.app.set_status(
            f"Slide {self.index:02d}: deleted {' + '.join(bits)}."
        )

    def _on_present_from_here(self) -> None:
        """Open the presenter starting at this slide."""
        self.app._open_present_mode(start_index=self.index)

    def _on_copy_ai_locator(self) -> None:
        """Copy this slide's UUID to the clipboard for chat with the assistant.

        The assistant can grep ``keynote.json`` for the id to find the exact slide.
        """
        locator = self.slide_id
        try:
            r = self.app.root
            r.clipboard_clear()
            r.clipboard_append(locator)
            r.update()
        except tk.TclError as e:
            messagebox.showerror(
                "Copy AI locator",
                f"Could not write to the clipboard:\n{e}",
            )
            return
        self.app.set_status(
            f"Slide {self.index:02d}: copied slide id → {locator}"
        )

    def _on_insert_above(self) -> None:
        self.app.insert_slide_above(self.index)

    def _on_delete(self) -> None:
        self.app.delete_slide(self.index)

    def refresh_preview(self) -> None:
        out = self.app.output_dir / f"{self.slide_id}.png"
        photo, err = _thumb_photo(out, SLIDE_IMG_PX)
        self._photo = photo
        c = self.preview_canvas
        c.delete("all")
        cx, cy = SLIDE_IMG_PX // 2, SLIDE_IMG_PX // 2
        if photo is not None:
            c.create_image(cx, cy, image=photo)
            self._slide_card_text.grid_configure(padx=SLIDE_CARD_TEXT_PADX_WITH_IMG)
        else:
            c.create_text(
                cx,
                cy,
                text=err,
                fill="#a8a8b8",
                font=("TkDefaultFont", 11),
                justify=tk.CENTER,
                width=SLIDE_IMG_PX - 24,
            )
            self._slide_card_text.grid_configure(padx=SLIDE_CARD_TEXT_PADX_NO_IMG)

    def reload_slide(self, spec: dict, index: int) -> None:
        """Populate this widget with data from a different slide spec (in-place navigation)."""
        self.index = index
        self.slide_id = str(spec.get("id", "")).strip()
        self._preview_title = str(spec.get("title", f"Slide {index}"))
        self._preview_body = str(spec.get("body", ""))
        self._prompt_cache = str(spec.get("image_prompt", ""))
        self._credits_cache = bool(spec.get("credits", False))

        self.title_edit_var.set(self._preview_title)
        self._top_title_label.config(text=self._title_line())
        self._render_title_preview()
        self._fill_body_preview()

        if self._editor_built:
            if self.body_edit is not None:
                self.body_edit.config(state=tk.NORMAL)
                self.body_edit.delete("1.0", tk.END)
                self.body_edit.insert("1.0", self._preview_body)
            if self.txt is not None:
                self.txt.delete("1.0", tk.END)
                self.txt.insert("1.0", self._prompt_cache)
            self.credits_var.set(self._credits_cache)

        self.refresh_preview()

    def _on_suggest(self) -> None:
        key = gen.load_api_key()
        if not key:
            messagebox.showerror("API key", "Set OPENROUTER_API_KEY or .env/OpenRouter.md")
            return
        model = self.app.text_model_var.get().strip()
        if not model:
            messagebox.showerror("Model", "Set a text model for Suggest (e.g. anthropic/claude-haiku-4.5).")
            return
        self.set_busy(True)
        self.app.set_status(f"Suggesting slide {self.index:02d}…")

        def work():
            try:
                slide_title = self.get_title_text()
                slide_body = self.get_body_text()
                text = gen.suggest_slide_prompt(
                    api_key=key,
                    text_model=model,
                    slide_title=slide_title,
                    slide_body=slide_body,
                    current_prompt=self.get_prompt(),
                    content_guide=self.app.get_content_guide_text(),
                )
                self.app.root.after(0, lambda: self._suggest_done(text, None))
            except Exception as e:
                self.app.root.after(0, lambda: self._suggest_done("", e))

        threading.Thread(target=work, daemon=True).start()

    def _suggest_done(self, text: str, err: BaseException | None) -> None:
        self.set_busy(False)
        if err is not None:
            messagebox.showerror("Suggest failed", str(err))
            self.app.set_status("Suggest failed.")
            return
        self.set_prompt(text)
        self.app.deck["slides"][self.index]["image_prompt"] = text
        self.app.schedule_autosave()
        self.app.set_status(f"Slide {self.index:02d}: prompt updated from LLM.")

    def _slide_edit_context(self) -> tuple[str, str, str]:
        """Talk title, talk subtitle, and content guide — empty strings if unavailable."""
        fm = self.app.deck.get("frontmatter") or {}
        talk_title = (fm.get("title") or "").strip()
        talk_subtitle = (fm.get("subtitle") or "").strip()
        content_guide = self.app.get_content_guide_text() or ""
        return talk_title, talk_subtitle, content_guide

    def _neighbor_slides(
        self, before: int = 2, after: int = 2
    ) -> tuple[list[dict], list[dict]]:
        """Compact ``{index, title, body}`` dicts for the rows around this one.

        Reads live row state (``get_title_text``/``get_body_text``) so unsaved
        edits in adjacent rows are reflected.
        """
        rows = getattr(self.app, "rows", None) or []
        n = len(rows)
        prev: list[dict] = []
        nxt: list[dict] = []
        if n == 0 or self.index < 0:
            return prev, nxt
        start = max(0, self.index - before)
        for i in range(start, self.index):
            row = rows[i]
            prev.append({
                "index": i,
                "title": row.get_title_text(),
                "body": row.get_body_text(),
            })
        end = min(n, self.index + 1 + after)
        for i in range(self.index + 1, end):
            row = rows[i]
            nxt.append({
                "index": i,
                "title": row.get_title_text(),
                "body": row.get_body_text(),
            })
        return prev, nxt

    def _build_slide_edit_messages(self, user_request: str) -> tuple[str, str]:
        talk_title, talk_subtitle, content_guide = self._slide_edit_context()
        prev_slides, next_slides = self._neighbor_slides()
        return gen.compose_slide_edit_prompt(
            talk_title=talk_title,
            talk_subtitle=talk_subtitle,
            content_guide=content_guide,
            slide_index=self.index,
            slide_title=self.get_title_text(),
            slide_body=self.get_body_text(),
            user_request=user_request,
            prev_slides=prev_slides,
            next_slides=next_slides,
        )

    def _on_suggest_edit(self) -> None:
        self.ensure_editor()
        self._open_slide_edit_dialog()

    def _open_slide_edit_dialog(self) -> None:
        dlg = tk.Toplevel(self.app.root)
        dlg.title(f"Suggest edits — slide {self.index:02d}")
        dlg.transient(self.app.root)
        dlg.geometry("680x460")

        header_title = self._preview_title or "(untitled)"
        tk.Label(
            dlg,
            text=f"Slide {self.index:02d}: {header_title}",
            font=("TkDefaultFont", 11, "bold"),
            anchor="w",
        ).pack(fill=tk.X, padx=12, pady=(12, 4))

        tk.Label(
            dlg,
            text=(
                "What change do you want? "
                "(e.g. \"tighten the opening\", \"add the 75% Google data point\", "
                "\"rewrite the body in plain language\")"
            ),
            anchor="w",
            wraplength=640,
            justify=tk.LEFT,
        ).pack(fill=tk.X, padx=12, pady=(4, 4))

        request_box = scrolledtext.ScrolledText(
            dlg, wrap=tk.WORD, height=10, font=("TkDefaultFont", 11)
        )
        request_box.pack(fill=tk.BOTH, expand=True, padx=12, pady=(2, 8))
        request_box.focus_set()

        status_var = tk.StringVar(value="")
        tk.Label(dlg, textvariable=status_var, anchor="w", fg="#5a5a5a").pack(
            fill=tk.X, padx=12
        )

        bf = tk.Frame(dlg)
        bf.pack(fill=tk.X, padx=12, pady=(6, 12))

        state = {"applying": False}

        def get_request() -> str:
            return request_box.get("1.0", "end-1c").strip()

        def on_preview() -> None:
            try:
                system, user_msg = self._build_slide_edit_messages(get_request())
            except Exception as e:
                messagebox.showerror("Preview prompt", str(e), parent=dlg)
                return
            self._show_slide_edit_preview(dlg, system, user_msg)

        def on_cancel() -> None:
            dlg.destroy()

        def on_apply() -> None:
            if state["applying"]:
                return
            request = get_request()
            if not request:
                messagebox.showwarning(
                    "Suggest edits",
                    "Please describe the change you want.",
                    parent=dlg,
                )
                return
            key = gen.load_api_key()
            if not key:
                messagebox.showerror(
                    "API key",
                    "Set OPENROUTER_API_KEY or .env/OpenRouter.md",
                    parent=dlg,
                )
                return
            model = self.app.text_model_var.get().strip()
            if not model:
                messagebox.showerror(
                    "Model",
                    "Set a text model (e.g. anthropic/claude-haiku-4.5).",
                    parent=dlg,
                )
                return
            state["applying"] = True
            btn_apply.config(state=tk.DISABLED, text="Working…")
            btn_preview.config(state=tk.DISABLED)
            btn_cancel.config(state=tk.DISABLED)
            request_box.config(state=tk.DISABLED)
            status_var.set("Calling LLM…")
            self.set_busy(True)
            self.app.set_status(f"Slide {self.index:02d}: requesting edit…")

            talk_title, talk_subtitle, content_guide = self._slide_edit_context()
            slide_title = self.get_title_text()
            slide_body = self.get_body_text()
            slide_index = self.index
            prev_slides, next_slides = self._neighbor_slides()

            def work():
                try:
                    result = gen.suggest_slide_edit(
                        api_key=key,
                        text_model=model,
                        talk_title=talk_title,
                        talk_subtitle=talk_subtitle,
                        content_guide=content_guide,
                        slide_index=slide_index,
                        slide_title=slide_title,
                        slide_body=slide_body,
                        user_request=request,
                        prev_slides=prev_slides,
                        next_slides=next_slides,
                    )
                    self.app.root.after(0, lambda: done(result, None))
                except Exception as e:
                    self.app.root.after(0, lambda: done(None, e))

            def done(result, err):
                self.set_busy(False)
                state["applying"] = False
                if err is not None:
                    messagebox.showerror(
                        "Suggest edits failed", str(err), parent=dlg
                    )
                    self.app.set_status("Suggest edits failed.")
                    btn_apply.config(state=tk.NORMAL, text="Apply")
                    btn_preview.config(state=tk.NORMAL)
                    btn_cancel.config(state=tk.NORMAL)
                    request_box.config(state=tk.NORMAL)
                    status_var.set("")
                    return
                self._apply_slide_edit_result(result)
                self.app.set_status(f"Slide {self.index:02d}: applied LLM edit.")
                dlg.destroy()

            threading.Thread(target=work, daemon=True).start()

        btn_preview = tk.Button(bf, text="Preview prompt", command=on_preview, width=14)
        btn_preview.pack(side=tk.LEFT)
        btn_cancel = tk.Button(bf, text="Cancel", command=on_cancel, width=10)
        btn_cancel.pack(side=tk.RIGHT)
        btn_apply = tk.Button(bf, text="Apply", command=on_apply, width=10)
        btn_apply.pack(side=tk.RIGHT, padx=(0, 8))

    def _show_slide_edit_preview(
        self, parent: tk.Toplevel, system: str, user_msg: str
    ) -> None:
        win = tk.Toplevel(parent)
        win.title(f"Prompt preview — slide {self.index:02d}")
        win.transient(parent)
        win.geometry("820x620")

        model = self.app.text_model_var.get().strip() or "(no text model set)"
        tk.Label(win, text=f"Text model: {model}", anchor="w").pack(
            fill=tk.X, padx=10, pady=(10, 4)
        )

        tk.Label(
            win,
            text="System message:",
            anchor="w",
            font=("TkDefaultFont", 10, "bold"),
        ).pack(fill=tk.X, padx=10, pady=(6, 2))
        sys_box = scrolledtext.ScrolledText(
            win, wrap=tk.WORD, height=6, font=("TkFixedFont", 10)
        )
        sys_box.pack(fill=tk.X, padx=10, pady=(0, 6))
        sys_box.insert("1.0", system)
        sys_box.config(state=tk.DISABLED)

        tk.Label(
            win,
            text="User message:",
            anchor="w",
            font=("TkDefaultFont", 10, "bold"),
        ).pack(fill=tk.X, padx=10, pady=(6, 2))
        user_box = scrolledtext.ScrolledText(
            win, wrap=tk.WORD, font=("TkFixedFont", 10)
        )
        user_box.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 6))
        user_box.insert("1.0", user_msg)
        user_box.config(state=tk.DISABLED)

        bf = tk.Frame(win)
        bf.pack(fill=tk.X, padx=10, pady=(4, 10))
        tk.Button(bf, text="Close", command=win.destroy, width=12).pack(side=tk.RIGHT)

    def _apply_slide_edit_result(self, result: dict) -> None:
        """Push LLM-suggested ``{title, body}`` into the row's widgets and trigger autosave.

        Empty fields in ``result`` are treated as "leave unchanged" so a partial reply does
        not wipe out existing content. The slide's image prompt is intentionally untouched
        by this flow.
        """
        new_title = (result.get("title") or "").strip()
        new_body = (result.get("body") or "").strip()

        if new_title or new_body:
            self.update_slide_preview(
                new_title or self._preview_title,
                new_body if new_body else None,
            )
            self.app.schedule_autosave()

    def _on_preview_render_prompt(self) -> None:
        prompt = self.get_prompt()
        if not prompt.strip():
            messagebox.showwarning("Prompt", "Image prompt is empty.")
            return
        w, h = self.app.image_wh()
        full = gen.compose_render_image_prompt(
            user_prompt=prompt,
            style_prompt=self.app.style_full,
            width=w,
            height=h,
            content_guide=self.app.get_content_guide_text(),
            slide_title=self.get_title_text(),
            slide_body=self.get_body_text(),
        )
        model = self.app.image_model_var.get().strip()
        dlg = tk.Toplevel(self.app.root)
        dlg.title(f"Render prompt — slide {self.index:02d}")
        dlg.transient(self.app.root)
        dlg.geometry("760x560")
        tk.Label(
            dlg,
            text=f"Image model (chosen separately in API JSON, not inside this text): {model or '(none)'}",
            anchor="w",
        ).pack(fill=tk.X, padx=10, pady=(10, 4))
        tk.Label(
            dlg,
            text="Full user message sent as the render request content:",
            anchor="w",
            font=("TkDefaultFont", 10, "bold"),
        ).pack(fill=tk.X, padx=10, pady=(4, 2))
        body = scrolledtext.ScrolledText(dlg, wrap=tk.WORD, font=("TkFixedFont", 10))
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
        body.insert("1.0", full)
        bf = tk.Frame(dlg)
        bf.pack(fill=tk.X, padx=10, pady=(4, 10))
        tk.Button(bf, text="Close", command=dlg.destroy, width=12).pack(side=tk.RIGHT)

    def _on_render(self) -> None:
        prompt = self.get_prompt()
        if not prompt:
            messagebox.showwarning("Prompt", "Description is empty.")
            return
        key = gen.load_api_key()
        if not key:
            messagebox.showerror("API key", "Set OPENROUTER_API_KEY or .env/OpenRouter.md")
            return
        model = self.app.image_model_var.get().strip()
        if not model:
            messagebox.showerror("Model", "Set an image model (e.g. google/gemini-3.1-flash-image-preview).")
            return
        self.set_busy(True)
        self.app.set_status(f"Rendering slide {self.index:02d}…")
        self.app.output_dir.mkdir(parents=True, exist_ok=True)
        if self.slide_id:
            out_path = self.app.output_dir / f"{self.slide_id}.png"
        else:
            out_path = self.app.output_dir / f"{self.index:02d}.png"
        w, h = self.app.image_wh()
        slide_title = self.get_title_text()
        slide_body = self.get_body_text()
        content_guide = self.app.get_content_guide_text()

        def work():
            try:
                ok = gen.generate_image_api(
                    user_prompt=prompt,
                    style_prompt=self.app.style_full,
                    output_path=out_path,
                    api_key=key,
                    model=model,
                    width=w,
                    height=h,
                    content_guide=content_guide,
                    slide_title=slide_title,
                    slide_body=slide_body,
                )
                if ok:
                    gen.maybe_resize_png(out_path, w, h)
                self.app.root.after(0, lambda: self._render_done(ok, None))
            except Exception as e:
                self.app.root.after(0, lambda: self._render_done(False, e))

        threading.Thread(target=work, daemon=True).start()

    def _render_done(self, ok: bool, err: BaseException | None) -> None:
        self.set_busy(False)
        if err is not None:
            messagebox.showerror("Render failed", str(err))
            self.app.set_status("Render failed.")
            return
        if not ok:
            messagebox.showerror("Render failed", "API returned no image (see terminal).")
            self.app.set_status("Render failed.")
            return
        self.app.deck["slides"][self.index]["image_prompt"] = self.get_prompt()
        self.app.schedule_autosave()
        self.refresh_preview()
        out = self.app.output_dir / f"{self.slide_id}.png"
        self.app.set_status(f"Slide {self.index:02d}: saved {out.name}")


class SlideEditorApp:
    def __init__(
        self,
        root: tk.Tk,
        deck_path: Path,
        *,
        profile_startup: bool = False,
        profile_startup_exit: bool = False,
        perf_minimal_rows: bool = False,
    ):
        _init_scroll_debug_log()
        _log_scroll(f"app start cwd={Path.cwd()} log={SCROLL_DEBUG_FILE}")
        self._autosave_after_id: str | None = None
        self._last_self_mtime_ns: int | None = None
        self._external_check_job: str | None = None
        self._external_check_interval_ms = 2000
        self._profile_startup = profile_startup
        self._profile_startup_exit = profile_startup_exit
        self._perf_minimal_rows = perf_minimal_rows
        self._startup_profiler: cProfile.Profile | None = None
        self._startup_profiler_wall_t0: float | None = None
        self.root = root
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.minsize(min(1200, max(720, sw - 48)), min(700, max(480, sh - 100)))

        self.deck_path = deck_path.resolve()
        if not self.deck_path.is_file():
            raise FileNotFoundError(str(self.deck_path))
        self.deck = kd.load_deck(self.deck_path)
        slides = self.deck.get("slides")
        if not isinstance(slides, list) or not slides:
            raise ValueError("Deck has no slides[]")
        root.title(f"Slide images — {self.deck_path.name}")
        self.output_dir = SCRIPT_DIR / str(self.deck.get("output_directory", "slide_images"))
        style_path = gen.resolve_style_path(self.deck, None)
        self.style_full = gen.load_global_style(style_path, self.deck)
        _sync_msg = "Deck loaded — prompts and images keyed by slide id; reorder slides in JSON safely."
        text_model = str(self.deck.get("text_model", "anthropic/claude-haiku-4.5"))
        image_model = str(self.deck.get("model", gen.DEFAULT_MODEL))

        menubar = tk.Menu(root)
        fm = tk.Menu(menubar, tearoff=0)
        fm.add_command(label="Open deck…", command=self._open_data)
        fm.add_command(label="Save", command=self.save_deck)
        fm.add_command(label="Save as…", command=self._save_deck_as)
        fm.add_separator()
        fm.add_command(label="Quit", command=root.quit)
        menubar.add_cascade(label="File", menu=fm)
        root.config(menu=menubar)

        top = tk.Frame(root)
        top.pack(fill=tk.X, padx=8, pady=6)

        tk.Label(top, text="Deck:").pack(side=tk.LEFT)
        self.path_var = tk.StringVar(value=str(self.deck_path))
        tk.Entry(top, textvariable=self.path_var, width=70).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        tk.Button(top, text="Browse…", command=self._browse_data).pack(side=tk.LEFT)
        tk.Button(top, text="Reload", command=self._reload).pack(side=tk.LEFT, padx=4)
        tk.Button(top, text="Save", command=self.save_deck, width=8).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(top, text="Present", command=self._open_present_mode, width=8).pack(side=tk.LEFT, padx=(8, 0))
        tk.Label(top, text="Source: keynote.json (markdown + prompts in one file)", fg="#246").pack(side=tk.RIGHT, padx=8)

        theme = tk.LabelFrame(
            root,
            text="Keynote theme / content guide (used by Suggest and new-slide LLM)",
            padx=6,
            pady=4,
        )
        theme.pack(fill=tk.X, padx=8, pady=(0, 4))
        self.content_guide = scrolledtext.ScrolledText(
            theme, height=4, wrap=tk.WORD, font=("TkDefaultFont", 10)
        )
        self.content_guide.pack(fill=tk.BOTH, expand=True)
        self._sync_content_guide_widget_from_json()

        def _on_content_guide_edit(_event=None) -> None:
            self.schedule_autosave()

        self.content_guide.bind("<KeyRelease>", _on_content_guide_edit)
        self.content_guide.bind("<FocusOut>", _on_content_guide_edit)

        opts = tk.Frame(root)
        opts.pack(fill=tk.X, padx=8, pady=4)
        tk.Label(opts, text="Text model (Suggest):").pack(side=tk.LEFT)
        self.text_model_var = tk.StringVar(value=text_model)
        tk.Entry(opts, textvariable=self.text_model_var, width=36).pack(side=tk.LEFT, padx=(0, 16))
        tk.Label(opts, text="Image model (Render):").pack(side=tk.LEFT)
        self.image_model_var = tk.StringVar(value=image_model)
        tk.Entry(opts, textvariable=self.image_model_var, width=36).pack(side=tk.LEFT)

        key = gen.load_api_key()
        key_lbl = "API key: OK" if key else "API key: missing"
        tk.Label(opts, text=key_lbl, fg="#080" if key else "#a00").pack(side=tk.RIGHT, padx=8)

        credits_bar = tk.Frame(root)
        credits_bar.pack(fill=tk.X, padx=8, pady=(0, 4))
        tk.Label(credits_bar, text="Credits roll —", fg="#246").pack(side=tk.LEFT)
        tk.Label(credits_bar, text="delay (s):").pack(side=tk.LEFT, padx=(8, 2))
        self.credits_delay_var = tk.StringVar(
            value=f"{float(self.deck.get('credits_start_delay_seconds', kd.CREDITS_DELAY_DEFAULT)):g}"
        )
        e_delay = tk.Entry(credits_bar, textvariable=self.credits_delay_var, width=6)
        e_delay.pack(side=tk.LEFT)
        tk.Label(credits_bar, text="speed (px/s):").pack(side=tk.LEFT, padx=(12, 2))
        self.credits_speed_var = tk.StringVar(
            value=f"{float(self.deck.get('credits_scroll_pixels_per_second', kd.CREDITS_SPEED_DEFAULT)):g}"
        )
        e_speed = tk.Entry(credits_bar, textvariable=self.credits_speed_var, width=6)
        e_speed.pack(side=tk.LEFT)
        tk.Label(
            credits_bar,
            text=f"(delay {kd.CREDITS_DELAY_MIN:g}–{kd.CREDITS_DELAY_MAX:g}, speed {kd.CREDITS_SPEED_MIN:g}–{kd.CREDITS_SPEED_MAX:g})",
            fg="#777",
        ).pack(side=tk.LEFT, padx=(12, 0))
        for w in (e_delay, e_speed):
            w.bind("<FocusOut>", lambda _e: self.schedule_autosave())
            w.bind("<Return>", lambda _e: self.schedule_autosave())

        self.status = tk.StringVar(value=_sync_msg)
        tk.Label(root, textvariable=self.status, anchor="w", relief=tk.GROOVE).pack(
            fill=tk.X, padx=8, pady=(0, 6)
        )

        # Navigation bar: Prev / Next buttons + slide counter + scrub slider
        nav_bar = tk.Frame(root)
        nav_bar.pack(fill=tk.X, padx=8, pady=(0, 4))
        tk.Button(nav_bar, text="◀ Prev", command=lambda: self._navigate(-1), width=8).pack(side=tk.LEFT)
        tk.Button(nav_bar, text="Next ▶", command=lambda: self._navigate(1), width=8).pack(side=tk.LEFT, padx=(4, 0))
        tk.Button(nav_bar, text="▲", command=lambda: self._navigate(-1), width=3).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(nav_bar, text="▼", command=lambda: self._navigate(1), width=3).pack(side=tk.LEFT, padx=(2, 0))
        self._slide_counter = tk.StringVar(value="")
        tk.Label(nav_bar, textvariable=self._slide_counter, font=("TkDefaultFont", 11)).pack(side=tk.LEFT, padx=(16, 8))
        self._scale_updating = False
        self._slide_scale = tk.Scale(
            nav_bar,
            from_=0,
            to=0,
            orient=tk.HORIZONTAL,
            showvalue=False,
            command=self._on_scale_change,
        )
        self._slide_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        self._slide_container = tk.Frame(root)
        self._slide_container.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self.rows: list[SlideRow] = []
        self.current_idx = 0

        # Click on background (canvas, frames, labels) moves focus to the canvas
        # so arrow keys navigate slides instead of staying trapped in a text widget.
        def _defocus_text(event):
            w = event.widget
            try:
                cls = w.winfo_class() if hasattr(w, 'winfo_class') else ''
            except tk.TclError:
                cls = ''
            if cls not in ('Text', 'Entry', 'TEntry', 'Spinbox'):
                try:
                    self._scroll_canvas.focus_set()
                except (tk.TclError, AttributeError):
                    pass
        root.bind_all("<Button-1>", _defocus_text, add="+")

        def _nav_if_not_editing(event, delta):
            """Only navigate slides if focus is NOT in an editable text input widget."""
            w = event.widget
            try:
                cls = w.winfo_class() if hasattr(w, 'winfo_class') else ''
                # Check if it's an editable text widget (not disabled/read-only)
                if cls in ('Entry', 'TEntry', 'Spinbox'):
                    return  # always let Entry/Spinbox handle arrows
                if cls == 'Text':
                    # Only skip navigation if the Text widget is editable
                    state = str(w.cget('state'))
                    if state != 'disabled':
                        return  # editable Text — let it handle arrows
            except (tk.TclError, AttributeError):
                pass
            self._navigate(delta)

        root.bind_all("<Up>", lambda e: _nav_if_not_editing(e, -1))
        root.bind_all("<Down>", lambda e: _nav_if_not_editing(e, 1))
        root.bind_all("<Left>", lambda e: _nav_if_not_editing(e, -1))
        root.bind_all("<Right>", lambda e: _nav_if_not_editing(e, 1))

        self.root.after_idle(self._bootstrap_slide_rows)
        self.root.update_idletasks()

        # Watch the backing JSON for external edits (another editor, ``git pull``, etc.).
        self._record_self_mtime()
        self._schedule_external_check()

    def _bootstrap_slide_rows(self) -> None:
        """Build slide rows after the root window has mapped (avoids long frozen startup)."""
        if self._profile_startup:
            self._startup_profiler_wall_t0 = time.monotonic()
            self._startup_profiler = cProfile.Profile()
            self._startup_profiler.enable()
        self._startup_wall_t0 = time.monotonic()
        self._rebuild_rows()
        if _scroll_debug_enabled():
            _log_scroll(
                f"slide widgets built in {time.monotonic() - self._startup_wall_t0:.2f}s"
                " (thumbnails load next)"
            )

    def image_wh(self) -> tuple[int, int]:
        return int(self.deck.get("width", 1024)), int(self.deck.get("height", 1024))

    def set_status(self, msg: str) -> None:
        self.status.set(msg)

    def get_content_guide_text(self) -> str:
        return self.content_guide.get("1.0", "end-1c").strip()

    def _sync_content_guide_widget_from_json(self) -> None:
        raw = self.deck.get("content_guide")
        text = gen.DEFAULT_CONTENT_GUIDE
        if isinstance(raw, str) and raw.strip():
            text = raw
        self.content_guide.delete("1.0", tk.END)
        self.content_guide.insert("1.0", text)

    def _neighbor_slides_markdown_for_insert(self, insert_at: int) -> str:
        """Title + body of slides around the insertion point for LLM continuity."""
        slides = self.deck.get("slides")
        if not isinstance(slides, list):
            return ""
        parts: list[str] = []
        if insert_at > 0:
            j = insert_at - 1
            if j < len(slides) and isinstance(slides[j], dict):
                s = slides[j]
                parts.append(
                    f"[Slide {j:02d} — before the new slide]\n"
                    f"Title: {s.get('title', '')}\n"
                    f"Body:\n{s.get('body', '')}"
                )
        if insert_at < len(slides):
            s = slides[insert_at]
            if isinstance(s, dict):
                parts.append(
                    f"[Slide {insert_at:02d} — new slide will be inserted above this one]\n"
                    f"Title: {s.get('title', '')}\n"
                    f"Body:\n{s.get('body', '')}"
                )
        return "\n\n---\n\n".join(parts) if parts else ""

    def _open_present_mode(self, start_index: int = 0) -> None:
        """Open read-only presenter in a ``Toplevel`` (current in-memory deck).

        ``start_index`` jumps the presenter to that slide (clamped). The toolbar
        button passes 0 (start at the beginning); per-row Present buttons pass
        their own index so the speaker can rehearse from the current spot.
        """
        top = tk.Toplevel(self.root)
        top.transient(self.root)
        top.title("Present")
        top.minsize(800, 500)
        top.geometry("1280x820")
        try:
            PresentModeApp(
                top,
                deck_data=copy.deepcopy(self.deck),
                deck_path=self.deck_path,
                fullscreen=False,
                embedded=True,
                start_index=start_index,
                on_slide_change=self._jump_to_slide_id,
            )
        except ValueError as e:
            messagebox.showerror("Present", str(e), parent=self.root)
            top.destroy()
            return
        top.focus_set()

    def schedule_autosave(self) -> None:
        """Debounced write to ``keynote.json`` after edits."""
        if self._autosave_after_id is not None:
            self.root.after_cancel(self._autosave_after_id)
        self._autosave_after_id = self.root.after(1200, self._flush_autosave)

    def _flush_autosave(self) -> None:
        self._autosave_after_id = None
        self.save_deck(autosave=True)

    def _current_data_path(self) -> Path:
        return self.deck_path

    def _record_self_mtime(self) -> None:
        """Record the current file mtime so the watcher doesn't treat our own writes as external."""
        try:
            self._last_self_mtime_ns = self._current_data_path().stat().st_mtime_ns
        except OSError:
            self._last_self_mtime_ns = None

    def _schedule_external_check(self) -> None:
        self._external_check_job = self.root.after(
            self._external_check_interval_ms, self._check_external_change
        )

    def _check_external_change(self) -> None:
        """Poll the backing JSON; if another process wrote it, offer or auto-apply a reload."""
        self._external_check_job = None
        try:
            p = self._current_data_path()
            if not p.is_file():
                return
            try:
                mt = p.stat().st_mtime_ns
            except OSError:
                return
            if self._last_self_mtime_ns is None:
                self._last_self_mtime_ns = mt
                return
            if mt == self._last_self_mtime_ns:
                return
            # mtime diverged from our last known self-write: external change.
            has_pending_autosave = self._autosave_after_id is not None
            if has_pending_autosave:
                ok = messagebox.askyesno(
                    "External change",
                    f"{p.name} was modified outside the editor while you have unsaved edits.\n\n"
                    "Reload from disk and discard your pending edits?",
                    parent=self.root,
                )
                if not ok:
                    # Keep the new mtime as baseline so we don't re-prompt every poll tick
                    # for the same external write.
                    self._last_self_mtime_ns = mt
                    return
                self.root.after_cancel(self._autosave_after_id)
                self._autosave_after_id = None
            self.set_status(f"External change detected; reloading {p.name}…")
            try:
                self._reload()
            except Exception as e:
                LOG.warning("auto-reload failed: %s", e)
                # Avoid looping on a broken/partial write; update baseline so next poll
                # only fires after the file changes again.
                self._last_self_mtime_ns = mt
        finally:
            self._schedule_external_check()

    def _current_slides(self) -> list[dict]:
        slides = self.deck.get("slides")
        return slides if isinstance(slides, list) else []

    def _capture_focus_slide_id(self) -> str | None:
        """Return the slide id currently shown in the editor."""
        if self.rows:
            return self.rows[0].slide_id or None
        return None

    def _flush_current_to_deck(self) -> None:
        """Write the current row's edits back into self.deck["slides"] without saving to disk."""
        if not self.rows:
            return
        row = self.rows[0]
        slides = self._current_slides()
        if row.index < 0 or row.index >= len(slides):
            return
        spec = slides[row.index]
        title = row.get_title_text() or str(spec.get("title", f"Slide {row.index}"))
        body = row.get_body_text()
        spec["title"] = title
        spec["body"] = body
        kind = str(spec.get("kind", "content")).strip().lower()
        if kind == "quote":
            quote_lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
            spec["markdown"] = "\n\n".join(f"# {ln}" for ln in quote_lines) if quote_lines else f"# {title}"
        else:
            spec["markdown"] = f"# {title}\n\n{body}".strip()
        spec["image_prompt"] = row.get_prompt()
        spec["credits"] = bool(row.get_credits())

    def _on_scale_change(self, value: str) -> None:
        """Called by the scrub slider; navigate to the selected slide."""
        if self._scale_updating:
            return
        idx = int(float(value))
        if idx != self.current_idx:
            self._flush_current_to_deck()
            self._show_slide(idx)
            self.schedule_autosave()

    def _navigate(self, delta: int) -> None:
        """Move forward or backward by delta slides, flushing current edits first."""
        slides = self._current_slides()
        if not slides:
            return
        self._flush_current_to_deck()
        new_idx = max(0, min(self.current_idx + delta, len(slides) - 1))
        if new_idx == self.current_idx and self.rows:
            return
        self._show_slide(new_idx)
        self.schedule_autosave()

    def _show_slide(self, idx: int) -> None:
        """Display the slide at idx, reusing the single SlideRow widget."""
        slides = self._current_slides()
        if not slides:
            return
        idx = max(0, min(idx, len(slides) - 1))
        self.current_idx = idx
        spec = slides[idx]
        self._slide_counter.set(f"Slide {idx + 1} / {len(slides)}")
        self._scale_updating = True
        self._slide_scale.set(idx)
        self._scale_updating = False
        if self.rows:
            self.rows[0].reload_slide(spec, idx)

    def _jump_to_slide_id(self, sid: str | None) -> None:
        """Navigate to the slide with the given id."""
        if not sid:
            return
        slides = self._current_slides()
        for i, s in enumerate(slides):
            if isinstance(s, dict) and str(s.get("id", "")) == sid:
                self._show_slide(i)
                return

    def _finish_startup_profile_if_active(self) -> None:
        if self._startup_profiler is None:
            return
        p = self._startup_profiler
        self._startup_profiler = None
        p.disable()
        out_path = SCRIPT_DIR / "slide_editor_startup.prof"
        p.dump_stats(str(out_path))
        wall = (
            time.monotonic() - self._startup_profiler_wall_t0
            if self._startup_profiler_wall_t0 is not None
            else 0.0
        )
        self._startup_profiler_wall_t0 = None
        print(
            "\nNote: cProfile measures Python CPU only. Tcl/Tk layout, mainloop waits, and "
            "macOS window compositing do not appear as Python time — wall clock during this "
            f"window was ~{wall:.1f}s. For native stack samples use py-spy or Instruments.\n",
            file=sys.stderr,
        )
        stats = pstats.Stats(p, stream=sys.stderr)
        stats.strip_dirs()
        print("\n======== slide_editor startup profile (cumulative top 50) ========", file=sys.stderr)
        stats.sort_stats(pstats.SortKey.CUMULATIVE)
        stats.print_stats(50)
        print("\n======== same profile by internal time (tottime) top 30 ========", file=sys.stderr)
        stats.sort_stats(pstats.SortKey.TIME)
        stats.print_stats(30)
        print(f"\nWrote {out_path}", file=sys.stderr)
        if self._profile_startup_exit:
            # ``destroy`` walks the full slide tree and can take ~60s on macOS Tk; ``quit`` ends
            # mainloop immediately (this path is only for automated profiling).
            self.root.after(150, self.root.quit)

    def _rebuild_rows(self) -> None:
        """Destroy the current SlideRow (if any) and create one for self.current_idx."""
        for child in list(self._slide_container.winfo_children()):
            child.destroy()
        self.rows = []
        slides = self._current_slides()
        if not slides:
            return
        self.current_idx = max(0, min(self.current_idx, len(slides) - 1))
        self._scale_updating = True
        self._slide_scale.config(to=max(0, len(slides) - 1))
        self._slide_scale.set(self.current_idx)
        self._scale_updating = False
        spec = slides[self.current_idx]
        if not isinstance(spec, dict):
            return
        sid = str(spec.get("id", "")).strip()
        if not sid:
            raise ValueError(f"Slide [{self.current_idx:02d}] is missing a non-empty 'id' in the deck.")
        row = SlideRow(
            self._slide_container,
            self,
            self.current_idx,
            str(spec.get("title", f"Slide {self.current_idx}")),
            str(spec.get("body", "")),
            str(spec.get("image_prompt", "")),
            slide_id=sid,
            credits=bool(spec.get("credits", False)),
        )
        row.pack(fill=tk.X, expand=True, padx=4, pady=10)
        row.ensure_editor()
        self.rows.append(row)
        self._slide_counter.set(f"Slide {self.current_idx + 1} / {len(slides)}")
        self._finish_startup_profile_if_active()

    def _perf_minimal_idle_done(self) -> None:
        """Minimal-rows mode: report layout-settled time, then exit if profiling."""
        startup_t0 = getattr(self, "_startup_wall_t0", None)
        if startup_t0 is not None:
            print(
                f"[startup] idle-settled: {time.monotonic() - startup_t0:.2f}s",
                file=sys.stderr,
                flush=True,
            )
        self._finish_startup_profile_if_active()

    def insert_slide_above(self, index: int) -> None:
        slides = self.deck.get("slides")
        if not isinstance(slides, list):
            return
        i = max(0, min(index, len(slides)))
        dlg = tk.Toplevel(self.root)
        dlg.title(f"New slide above [{i:02d}]")
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.geometry("680x360")

        tk.Label(
            dlg,
            text="What should the slide say? (Conversational brief)",
            font=("TkDefaultFont", 11, "bold"),
            anchor="w",
        ).pack(fill=tk.X, padx=10, pady=(10, 4))
        brief = scrolledtext.ScrolledText(dlg, wrap=tk.WORD, height=10, font=("TkDefaultFont", 10))
        brief.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))

        status = tk.StringVar(value="LLM will generate title + content.")
        tk.Label(dlg, textvariable=status, anchor="w", fg="#444").pack(fill=tk.X, padx=10, pady=(0, 8))

        btns = tk.Frame(dlg)
        btns.pack(fill=tk.X, padx=10, pady=(0, 10))
        btn_cancel = tk.Button(btns, text="Cancel", command=dlg.destroy, width=12)
        btn_cancel.pack(side=tk.RIGHT)
        btn_create = tk.Button(btns, text="Ask LLM + Insert", width=16)
        btn_create.pack(side=tk.RIGHT, padx=(0, 8))

        def _set_busy(busy: bool) -> None:
            st = tk.DISABLED if busy else tk.NORMAL
            btn_cancel.config(state=st)
            btn_create.config(state=st)
            brief.config(state=st)

        def _apply_insert(title: str, body: str) -> None:
            slides_now = self.deck.get("slides")
            if not isinstance(slides_now, list):
                return
            insert_at = max(0, min(i, len(slides_now)))
            t = title.strip() or "New slide"
            b = body.strip()
            new_slide = {
                "id": str(uuid.uuid4()),
                "kind": "content",
                "markdown": f"# {t}\n\n{b}".strip(),
                "title": t,
                "body": b,
                "image_prompt": "",
            }
            slides_now.insert(insert_at, new_slide)
            self.current_idx = insert_at
            self._rebuild_rows()
            self.save_deck(autosave=True)
            self.set_status(f"Inserted new slide above [{insert_at:02d}].")
            # Scroll to the new slide so it's visible after rebuild
            self.root.after_idle(lambda sid=new_slide["id"]: self._jump_to_slide_id(sid))
            dlg.destroy()

        def _on_create() -> None:
            request = brief.get("1.0", "end-1c").strip()
            if not request:
                messagebox.showwarning("New slide", "Please describe what the slide should say.")
                return
            api_key = gen.load_api_key()
            if not api_key:
                messagebox.showerror("API key", "Set OPENROUTER_API_KEY or .env/OpenRouter.md")
                return
            model = self.text_model_var.get().strip() or "anthropic/claude-haiku-4.5"
            _set_busy(True)
            status.set("Asking LLM for title + content…")

            def work():
                try:
                    draft = gen.suggest_new_slide_content(
                        api_key=api_key,
                        text_model=model,
                        user_request=request,
                        content_guide=self.get_content_guide_text(),
                        slide_context=self._neighbor_slides_markdown_for_insert(i),
                    )
                    self.root.after(
                        0,
                        lambda: _apply_insert(
                            str(draft.get("title", "New slide")),
                            str(draft.get("body", "")),
                        ),
                    )
                except Exception as e:
                    self.root.after(0, lambda: _on_fail(e))

            def _on_fail(err: BaseException) -> None:
                _set_busy(False)
                status.set("LLM request failed.")
                messagebox.showerror("Insert slide failed", str(err))

            threading.Thread(target=work, daemon=True).start()

        btn_create.config(command=_on_create)

    def delete_slide(self, index: int) -> None:
        slides = self.deck.get("slides")
        if not isinstance(slides, list):
            return
        if len(slides) <= 1:
            self.set_status("Cannot delete the last remaining slide.")
            return
        if index < 0 or index >= len(slides):
            return
        label = str(slides[index].get("title", f"Slide {index}"))[:60]
        if not messagebox.askyesno("Delete slide", f"Delete slide [{index:02d}] \"{label}\"?"):
            return
        slides.pop(index)
        self.current_idx = max(0, min(self.current_idx, len(slides) - 1))
        self._rebuild_rows()
        self.save_deck(autosave=True)
        self.set_status(f"Deleted slide [{index:02d}].")
        # Scroll to the nearest slide after deletion
        if slides and index < len(slides):
            sid = slides[min(index, len(slides) - 1)].get("id", "")
            if sid:
                self.root.after_idle(lambda s=sid: self._jump_to_slide_id(s))

    def save_deck(self, *, autosave: bool = False) -> None:
        """Flush in-memory edits back to ``keynote.json``."""
        self.deck["text_model"] = self.text_model_var.get().strip()
        self.deck["model"] = self.image_model_var.get().strip()
        self.deck["content_guide"] = self.get_content_guide_text()
        self.deck["credits_start_delay_seconds"] = kd._coerce_float(
            self.credits_delay_var.get(),
            kd.CREDITS_DELAY_DEFAULT,
            kd.CREDITS_DELAY_MIN,
            kd.CREDITS_DELAY_MAX,
        )
        self.deck["credits_scroll_pixels_per_second"] = kd._coerce_float(
            self.credits_speed_var.get(),
            kd.CREDITS_SPEED_DEFAULT,
            kd.CREDITS_SPEED_MIN,
            kd.CREDITS_SPEED_MAX,
        )
        kd.ensure_deck_defaults(self.deck)
        for row in self.rows:
            spec = self.deck["slides"][row.index]
            title = row.get_title_text() or str(spec.get("title", f"Slide {row.index}"))
            body = row.get_body_text()
            spec["title"] = title
            spec["body"] = body
            kind = str(spec.get("kind", "content")).strip().lower()
            if kind == "quote":
                quote_lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
                spec["markdown"] = "\n\n".join(f"# {ln}" for ln in quote_lines) if quote_lines else f"# {title}"
            else:
                spec["markdown"] = f"# {title}\n\n{body}".strip()
            spec["image_prompt"] = row.get_prompt()
            spec["credits"] = bool(row.get_credits())
        kd.save_deck(self.deck_path, self.deck)
        self._record_self_mtime()
        self.set_status(
            f"Auto-saved {self.deck_path.name}" if autosave else f"Saved {self.deck_path.name}"
        )

    def _save_deck_as(self) -> None:
        p = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("All", "*")],
            initialfile=self.deck_path.name,
        )
        if not p:
            return
        new_p = Path(p)
        self.path_var.set(str(new_p))
        self.deck_path = new_p
        self.save_deck()

    def _is_deck_json(self, data: dict) -> bool:
        return isinstance(data.get("frontmatter"), dict) and isinstance(data.get("slides"), list)

    def _open_data(self) -> None:
        p = filedialog.askopenfilename(filetypes=[("JSON", "*.json"), ("All", "*")])
        if not p:
            return
        self.path_var.set(str(Path(p)))
        self._reload()

    def _browse_data(self) -> None:
        self._open_data()

    def _reload(self) -> None:
        """Re-read keynote.json from path_var and refresh rows."""
        if self._autosave_after_id is not None:
            self.root.after_cancel(self._autosave_after_id)
            self._autosave_after_id = None
        p = Path(self.path_var.get().strip())
        if not p.is_file():
            messagebox.showerror("File", f"Not found:\n{p}")
            return
        try:
            data = kd.load_deck(p)
        except json.JSONDecodeError as e:
            messagebox.showerror("JSON", str(e))
            return
        except (ValueError, OSError) as e:
            messagebox.showerror("File", str(e))
            return
        # Preserve the user's place across reload (external write, manual reload, etc.)
        focus_sid = self._capture_focus_slide_id()
        self.deck_path = p.resolve()
        self.deck = data
        self.text_model_var.set(str(data.get("text_model", "anthropic/claude-haiku-4.5")))
        self.image_model_var.set(str(data.get("model", gen.DEFAULT_MODEL)))
        self.credits_delay_var.set(
            f"{float(data.get('credits_start_delay_seconds', kd.CREDITS_DELAY_DEFAULT)):g}"
        )
        self.credits_speed_var.set(
            f"{float(data.get('credits_scroll_pixels_per_second', kd.CREDITS_SPEED_DEFAULT)):g}"
        )
        style_path = gen.resolve_style_path(self.deck, None)
        self.style_full = gen.load_global_style(style_path, self.deck)
        self._sync_content_guide_widget_from_json()
        self._rebuild_rows()
        self._record_self_mtime()
        if focus_sid is not None:
            self._jump_to_slide_id(focus_sid)
        self.set_status(f"Reloaded {self.deck_path.name}.")


class PresentModeApp:
    """Read-only presenter: markdown + optional slide image (``Tk`` or ``Toplevel`` host)."""

    def __init__(
        self,
        win: tk.Misc,
        *,
        deck_path: Path | None = None,
        deck_data: dict | None = None,
        fullscreen: bool = True,
        embedded: bool = False,
        start_index: int = 0,
        on_slide_change: Callable[[str], None] | None = None,
    ):
        if not (deck_path or deck_data):
            raise ValueError(
                "PresentModeApp: provide deck_path or deck_data."
            )
        self.win = win
        self.embedded = embedded
        self.fullscreen = fullscreen
        self._on_slide_change = on_slide_change
        self._photo: object | None = None
        self._img_job: str | None = None
        self._pending_image_path: Path | None = None
        self._credits_after_id: str | None = None
        self._credits_active: bool = False
        self._credits_start_t: float = 0.0
        self._credits_total_px: int = 0
        self._credits_pad_lines: int = 0
        self._credits_speed: float = kd.CREDITS_SPEED_DEFAULT
        self.deck: dict
        self.deck_path: Path | None = None

        if deck_data is not None:
            self.deck = deck_data
            self.deck_path = deck_path.resolve() if deck_path is not None else None
        else:
            assert deck_path is not None
            self.deck_path = deck_path.resolve()
            self.deck = kd.load_deck(self.deck_path)
        slides = self.deck.get("slides")
        if not isinstance(slides, list) or not slides:
            raise ValueError("Deck has no slides[]")
        self.slides: list[dict] = [s for s in slides if isinstance(s, dict)]
        self.output_dir = SCRIPT_DIR / str(self.deck.get("output_directory", "slide_images"))
        label = self.deck_path.name if self.deck_path else "deck"
        win.title(f"Present — {label}")

        if not self.slides:
            self.index = 0
        else:
            self.index = max(0, min(int(start_index or 0), len(self.slides) - 1))
        win.configure(bg=SLIDE_BG)
        if fullscreen:
            win.attributes("-fullscreen", True)

        hint = (
            "← / PgUp  previous   → / Space / PgDn  next   Home / End   F5  reload from disk   Esc  back to editor   − / +  text size"
            if embedded
            else "← / PgUp  previous   → / Space / PgDn  next   Home / End   F5  reload from disk   Esc  exit fullscreen or quit   − / +  text size"
        )
        self._hint = tk.StringVar(value=hint)
        self._present_body_pt_min = 9
        self._present_body_pt_max = 30
        self._present_settings = _load_settings()
        saved_pt = self._present_settings.get("present_body_pt", 14)
        if not isinstance(saved_pt, int):
            saved_pt = 14
        self._present_body_pt = max(self._present_body_pt_min, min(self._present_body_pt_max, saved_pt))

        top = tk.Frame(win, bg=SLIDE_BG)
        top.pack(fill=tk.X, padx=12, pady=(8, 4))
        top.columnconfigure(0, weight=1)
        self.title_lbl = tk.Label(
            top,
            text="",
            font=("TkDefaultFont", 22, "bold"),
            fg=SLIDE_TEXT,
            bg=SLIDE_BG,
            anchor="w",
        )
        self.title_lbl.grid(row=0, column=0, sticky="ew")

        font_bar = tk.Frame(top, bg=SLIDE_BG)
        font_bar.grid(row=0, column=1, sticky="e", padx=(16, 0))
        tk.Label(font_bar, text="Text size", fg=SLIDE_DIM, bg=SLIDE_BG, font=("TkDefaultFont", 10)).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        tk.Button(
            font_bar,
            text="−",
            width=2,
            command=self._present_font_smaller,
            font=("TkDefaultFont", 14, "bold"),
        ).pack(side=tk.LEFT, padx=2)
        tk.Button(
            font_bar,
            text="+",
            width=2,
            command=self._present_font_larger,
            font=("TkDefaultFont", 14, "bold"),
        ).pack(side=tk.LEFT, padx=2)

        self.center = tk.Frame(win, bg=SLIDE_BG)
        self.center.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
        self.center.rowconfigure(0, weight=1)
        self.center.columnconfigure(0, weight=1)
        self.center.columnconfigure(1, weight=1)

        md_frame = tk.Frame(self.center, bg=SLIDE_PANEL_BG, highlightbackground="#3f435f", highlightthickness=1)
        self.md_frame = md_frame
        sb = tk.Scrollbar(md_frame)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.md_text = tk.Text(
            md_frame,
            wrap="word",
            bg=SLIDE_PANEL_BG,
            fg=SLIDE_TEXT,
            relief=tk.FLAT,
            padx=14,
            pady=14,
            highlightthickness=0,
            insertwidth=0,
        )
        self.md_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.md_text.config(yscrollcommand=sb.set)
        sb.config(command=self.md_text.yview)
        self.md_text.bind("<Key>", lambda _e: "break")

        self.img_frame = tk.Frame(self.center, bg="#2a2e48", highlightbackground="#4a4a62", highlightthickness=1)
        self.img_canvas = tk.Canvas(self.img_frame, bg="#2a2e48", highlightthickness=0)
        self.img_canvas.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.img_canvas.bind("<Configure>", self._schedule_image_resize)

        foot = tk.Frame(win, bg=SLIDE_BG)
        foot.pack(fill=tk.X, padx=12, pady=(4, 10))
        self.counter_lbl = tk.Label(
            foot,
            text="",
            font=("TkDefaultFont", 11),
            fg=SLIDE_DIM,
            bg=SLIDE_BG,
            anchor="w",
        )
        self.counter_lbl.pack(side=tk.LEFT)

        # Timer setup (label placed in nav bar below)
        target_minutes = self._present_settings.get("target_time", 45)
        if not isinstance(target_minutes, (int, float)):
            target_minutes = 45
        self._timer_target_s = float(target_minutes) * 60.0
        self._timer_start = time.monotonic()

        tk.Label(foot, textvariable=self._hint, font=("TkDefaultFont", 10), fg=SLIDE_DIM, bg=SLIDE_BG).pack(
            side=tk.RIGHT, fill=tk.X, expand=True, anchor="e"
        )

        nav = tk.Frame(win, bg=SLIDE_BG)
        nav.pack(fill=tk.X, pady=(0, 8))
        tk.Button(nav, text="← Previous", command=self._prev).pack(side=tk.LEFT, padx=6)
        tk.Button(nav, text="Next →", command=self._next).pack(side=tk.LEFT, padx=6)

        # Countdown timer — between Next and Reload
        self._timer_lbl = tk.Label(
            nav,
            text="",
            font=("TkDefaultFont", 14, "bold"),
            fg=SLIDE_DIM,
            bg=SLIDE_BG,
        )
        self._timer_lbl.pack(side=tk.LEFT, expand=True)
        self._timer_tick()

        quit_label = "Back to editor" if embedded else "Quit"
        tk.Button(nav, text=quit_label, command=self._close_present).pack(side=tk.RIGHT, padx=12)
        tk.Button(nav, text="Reload", command=self._reload_from_disk, width=8).pack(side=tk.RIGHT, padx=(0, 6))

        self._bind_present_keys(win)

        # Initialize timing log for this presentation session
        self._init_timing_log()

        self._show_slide()

    # ── Presentation timing log ──────────────────────────────────────────────

    def _init_timing_log(self) -> None:
        """Create logs/ directory and start a new timing log for this session."""
        import datetime
        log_dir = SCRIPT_DIR / "logs"
        log_dir.mkdir(exist_ok=True)
        self._timing_log_path = log_dir / "time.log"
        self._timing_session_start = time.monotonic()
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self._timing_log_path, "a", encoding="utf-8") as f:
            f.write(f"\n--- Session started: {ts} ---\n")

    def _log_slide_event(self, slide_index: int, slide_title: str) -> None:
        """Log a slide navigation event with elapsed time."""
        if not hasattr(self, '_timing_log_path'):
            return
        elapsed = time.monotonic() - self._timing_session_start
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        try:
            with open(self._timing_log_path, "a", encoding="utf-8") as f:
                f.write(f"{minutes:02d}:{seconds:02d}  [{slide_index:02d}]  {slide_title}\n")
        except OSError:
            pass

    def _present_title_pt(self) -> int:
        return max(14, min(34, int(round(self._present_body_pt * 1.35 + 3))))

    def _present_font_smaller(self) -> None:
        if self._present_body_pt <= self._present_body_pt_min:
            return
        self._present_body_pt -= 1
        self._persist_present_settings()
        self._show_slide()

    def _present_font_larger(self) -> None:
        if self._present_body_pt >= self._present_body_pt_max:
            return
        self._present_body_pt += 1
        self._persist_present_settings()
        self._show_slide()

    def _persist_present_settings(self) -> None:
        self._present_settings["present_body_pt"] = int(self._present_body_pt)
        _save_settings(self._present_settings)

    def _timer_tick(self) -> None:
        """Update the countdown timer every second."""
        try:
            elapsed = time.monotonic() - self._timer_start
            remaining_s = max(0, self._timer_target_s - elapsed)
            remaining_min = remaining_s / 60.0
            minutes = int(remaining_min)
            seconds = int(remaining_s) % 60

            if remaining_s <= 0:
                self._timer_lbl.config(text="TIME", fg="#ff3333", font=("TkDefaultFont", 22, "bold"))
            elif remaining_min < 5:
                self._timer_lbl.config(
                    text=f"{minutes}:{seconds:02d}",
                    fg="#ff3333",
                    font=("TkDefaultFont", 20, "bold"),
                )
            else:
                self._timer_lbl.config(
                    text=f"{minutes} min",
                    fg=SLIDE_DIM,
                    font=("TkDefaultFont", 14, "bold"),
                )
            self.win.after(1000, self._timer_tick)
        except tk.TclError:
            pass  # window closed

    def _reload_from_disk(self) -> None:
        """Re-read ``keynote.json`` from disk; keep slide index when possible."""
        if self.deck_path is None:
            messagebox.showinfo(
                "Reload",
                "No deck path is associated with this presenter (in-memory only). "
                "Close and use Present again from the editor after saving.",
                parent=self.win,
            )
            return
        try:
            self.deck = kd.load_deck(self.deck_path)
            slides = self.deck.get("slides")
            if not isinstance(slides, list) or not slides:
                messagebox.showwarning("Reload", "Deck has no slides after reload.", parent=self.win)
                return
            self.slides = [s for s in slides if isinstance(s, dict)]
            self.output_dir = SCRIPT_DIR / str(self.deck.get("output_directory", "slide_images"))
        except OSError as e:
            messagebox.showerror("Reload", str(e), parent=self.win)
            return
        except json.JSONDecodeError as e:
            messagebox.showerror("Reload", f"Invalid JSON: {e}", parent=self.win)
            return
        self.index = max(0, min(self.index, len(self.slides) - 1))
        self._show_slide()

    def _bind_present_keys(self, w: tk.Misc) -> None:
        pairs = (
            ("<Left>", self._on_key_prev),
            ("<Prior>", self._on_key_prev),
            ("<Up>", self._on_key_prev),
            ("<Right>", self._on_key_next),
            ("<Next>", self._on_key_next),
            ("<Down>", self._on_key_next),
            ("<space>", self._on_key_next),
            ("<Home>", self._on_key_home),
            ("<End>", self._on_key_end),
            ("<F5>", self._on_reload_key),
            ("<Escape>", self._on_escape),
        )
        for seq, cmd in pairs:
            w.bind(seq, cmd)
        for child in w.winfo_children():
            self._bind_present_keys(child)

    def _close_present(self) -> None:
        self._credits_cancel()
        if self.embedded:
            self.win.destroy()
        else:
            self.win.quit()

    def _schedule_image_resize(self, _event: tk.Event | None = None) -> None:
        if self._img_job is not None:
            try:
                self.win.after_cancel(self._img_job)
            except tk.TclError:
                pass
        self._img_job = self.win.after(120, self._paint_image)

    def _paint_image(self) -> None:
        self._img_job = None
        path = self._pending_image_path
        c = self.img_canvas
        c.delete("all")
        self._photo = None
        if path is None:
            return
        w = max(c.winfo_width() - 8, 80)
        h = max(c.winfo_height() - 8, 80)
        photo, err = _load_scaled_photo(path, w, h)
        self._photo = photo
        cx, cy = c.winfo_width() // 2, c.winfo_height() // 2
        if photo is not None:
            c.create_image(cx, cy, image=photo)
        else:
            c.create_text(cx, cy, text=err, fill=SLIDE_DIM, font=("TkDefaultFont", 12), justify=tk.CENTER)

    def _show_slide(self) -> None:
        n = len(self.slides)
        if n == 0:
            return
        self._credits_cancel()
        self.index = max(0, min(self.index, n - 1))
        spec = self.slides[self.index]
        is_credits = bool(spec.get("credits", False))
        title = str(spec.get("title", f"Slide {self.index}")).strip() or f"Slide {self.index}"
        self.title_lbl.config(text=title, font=("TkDefaultFont", self._present_title_pt(), "bold"))

        # Log slide navigation for timing report
        self._log_slide_event(self.index, title)

        md = _strip_leading_title_heading_for_present(_present_slide_markdown(spec, self.index), title)
        if is_credits:
            self._credits_pad_lines = 60
            md = md + ("\n" * self._credits_pad_lines)
        self.md_text.config(state=tk.NORMAL)
        self.md_text.delete("1.0", tk.END)
        insert_markdown_lines(self.md_text, md, base_pt=self._present_body_pt)
        self.md_text.config(state=tk.DISABLED)

        img_path = None if is_credits else _present_slide_image_path(self.output_dir, spec)
        self._pending_image_path = img_path

        self.md_frame.grid_forget()
        self.img_frame.grid_forget()
        if img_path is not None:
            self.center.columnconfigure(0, weight=1, uniform="slide")
            self.center.columnconfigure(1, weight=1, uniform="slide")
            self.md_frame.grid(
                row=0,
                column=0,
                sticky="nsew",
                padx=PRESENT_MD_FRAME_PADX_WITH_IMG,
            )
            self.img_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
            self.win.update_idletasks()
            self._schedule_image_resize()
        else:
            self.center.columnconfigure(0, weight=1)
            self.center.columnconfigure(1, weight=0)
            self.md_frame.grid(
                row=0,
                column=0,
                columnspan=2,
                sticky="nsew",
                padx=PRESENT_MD_FRAME_PADX_NO_IMG,
            )
            if self._img_job is not None:
                try:
                    self.win.after_cancel(self._img_job)
                except tk.TclError:
                    pass
                self._img_job = None
            self.img_canvas.delete("all")
            self._photo = None

        self.counter_lbl.config(text=f"Slide {self.index + 1} / {n}")

        if is_credits:
            self.md_text.yview_moveto(0.0)
            delay_s = kd._coerce_float(
                self.deck.get("credits_start_delay_seconds", kd.CREDITS_DELAY_DEFAULT),
                kd.CREDITS_DELAY_DEFAULT,
                kd.CREDITS_DELAY_MIN,
                kd.CREDITS_DELAY_MAX,
            )
            self._credits_speed = kd._coerce_float(
                self.deck.get("credits_scroll_pixels_per_second", kd.CREDITS_SPEED_DEFAULT),
                kd.CREDITS_SPEED_DEFAULT,
                kd.CREDITS_SPEED_MIN,
                kd.CREDITS_SPEED_MAX,
            )
            self._credits_active = True
            self._credits_after_id = self.win.after(
                max(0, int(delay_s * 1000)), self._credits_start_scroll
            )

        if self._on_slide_change is not None:
            sid = str(spec.get("id", "")).strip()
            if sid:
                try:
                    # Defer the callback so the presenter finishes rendering first.
                    self.win.after_idle(lambda s=sid: self._fire_slide_change(s))
                except Exception:
                    LOG.warning("present on_slide_change callback failed", exc_info=True)

    def _fire_slide_change(self, sid: str) -> None:
        if self._on_slide_change is not None:
            try:
                self._on_slide_change(sid)
            except Exception:
                LOG.warning("present on_slide_change callback failed", exc_info=True)

    def _credits_cancel(self) -> None:
        """Stop any pending or running credits animation. Safe to call repeatedly."""
        self._credits_active = False
        if self._credits_after_id is not None:
            try:
                self.win.after_cancel(self._credits_after_id)
            except tk.TclError:
                pass
            self._credits_after_id = None

    def _credits_start_scroll(self) -> None:
        self._credits_after_id = None
        if not self._credits_active:
            return
        try:
            self.win.update_idletasks()
            raw = self.md_text.count("1.0", "end", "ypixels", return_ints=True)
            total = int(raw if raw is not None else 0)
        except (tk.TclError, TypeError, ValueError):
            total = 0
        self._credits_total_px = max(total, 1)
        self._credits_start_t = time.monotonic()
        self._credits_tick()

    def _credits_tick(self) -> None:
        self._credits_after_id = None
        if not self._credits_active:
            return
        try:
            viewport = max(int(self.md_text.winfo_height()), 1)
        except tk.TclError:
            viewport = 1
        total = max(self._credits_total_px, 1)
        target_max = max(total - viewport, 1)
        elapsed = time.monotonic() - self._credits_start_t
        offset = elapsed * max(self._credits_speed, 1.0)
        if offset >= target_max:
            self.md_text.yview_moveto(target_max / total)
            self._credits_active = False
            return
        self.md_text.yview_moveto(offset / total)
        self._credits_after_id = self.win.after(33, self._credits_tick)

    def _prev(self) -> None:
        if self.index > 0:
            self.index -= 1
            self._show_slide()

    def _next(self) -> None:
        if self.index < len(self.slides) - 1:
            self.index += 1
            self._show_slide()

    def _on_key_prev(self, _event: tk.Event) -> str:
        self._prev()
        return "break"

    def _on_key_next(self, _event: tk.Event) -> str:
        self._next()
        return "break"

    def _on_key_home(self, _event: tk.Event) -> str:
        self.index = 0
        self._show_slide()
        return "break"

    def _on_key_end(self, _event: tk.Event) -> str:
        self.index = max(0, len(self.slides) - 1)
        self._show_slide()
        return "break"

    def _on_escape(self, _event: tk.Event) -> str:
        if self.fullscreen and bool(self.win.attributes("-fullscreen")):
            self.win.attributes("-fullscreen", False)
            return "break"
        self._close_present()
        return "break"

    def _on_reload_key(self, _event: tk.Event) -> str:
        self._reload_from_disk()
        return "break"


def main() -> None:
    global _SCROLL_DEBUG, _PERF_LABEL_BODY, _PERF_COLLAPSED_ROWS
    parser = argparse.ArgumentParser(description="Slide image prompt editor + preview + OpenRouter.")
    parser.add_argument(
        "--deck",
        type=Path,
        default=SCRIPT_DIR / "keynote.json",
        help="Path to keynote.json (default: keynote.json next to this script).",
    )
    parser.add_argument(
        "--present",
        action="store_true",
        help="Read-only presenter: slide markdown + image if available (else full-width text).",
    )
    parser.add_argument(
        "--present-windowed",
        action="store_true",
        help="With --present: use a normal window instead of fullscreen.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Scroll/button probe logging + slide build timing (see scroll_debug.log).",
    )
    parser.add_argument(
        "--profile-startup",
        action="store_true",
        help="cProfile from first slide build through thumbnail queue end; stderr + slide_editor_startup.prof",
    )
    parser.add_argument(
        "--profile-startup-exit",
        action="store_true",
        help="Same as --profile-startup, then close shortly after writing slide_editor_startup.prof (e.g. py-spy).",
    )
    parser.add_argument(
        "--perf-minimal-rows",
        action="store_true",
        help="Diagnostic: replace each slide row with a single Label (no editor widgets, no thumbnails).",
    )
    parser.add_argument(
        "--perf-label-body",
        action="store_true",
        help="Diagnostic: use a plain Label (no markdown) for each row's body preview; keep the rest of the row intact.",
    )
    parser.add_argument(
        "--perf-collapsed-rows",
        action="store_true",
        help="Diagnostic: skip the per-row editor pane, prompt textbox, and button column (simulates lazy-expand rows).",
    )
    args = parser.parse_args()
    if args.profile_startup_exit:
        args.profile_startup = True
    _SCROLL_DEBUG = bool(args.debug)
    _PERF_LABEL_BODY = bool(args.perf_label_body)
    _PERF_COLLAPSED_ROWS = bool(args.perf_collapsed_rows)
    logging.basicConfig(
        level=logging.INFO if _SCROLL_DEBUG else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if not args.deck.is_file():
        print(f"Error: deck not found: {args.deck}", file=sys.stderr)
        print("Create with: python keynote_deck.py import talk.md keynote.json", file=sys.stderr)
        sys.exit(1)

    root = tk.Tk()
    try:
        if args.present:
            PresentModeApp(
                root,
                deck_path=args.deck.resolve(),
                fullscreen=not args.present_windowed,
                embedded=False,
            )
        else:
            SlideEditorApp(
                root,
                deck_path=args.deck,
                profile_startup=args.profile_startup,
                profile_startup_exit=args.profile_startup_exit,
                perf_minimal_rows=args.perf_minimal_rows,
            )
    except FileNotFoundError as e:
        messagebox.showerror("File", str(e))
        sys.exit(1)
    except ValueError as e:
        messagebox.showerror("File", str(e))
        sys.exit(1)
    root.mainloop()


if __name__ == "__main__":
    main()
