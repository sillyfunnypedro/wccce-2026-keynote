#!/usr/bin/env python3
"""
Interactive editor: per-slide layout preview (slide text left, image right), image prompt,
LLM suggest, OpenRouter render.

  python slide_editor.py --deck keynote.json

Requires Pillow for PNG previews in the right column (pip install pillow).

List previews use ``slide_images/.thumbs/{id}_{size}.png`` when possible; they are
regenerated when the slide image is newer than the cached thumbnail.

**Paste image:** With focus on the slide's **preview square** (or the **Paste image** button), use
``Ctrl+V`` / ``Cmd+V`` to save the clipboard image as this slide's ``{id}.png`` (or ``NN.png`` in
manifest mode), replacing any existing file.

With ``--deck keynote.json``, each slide's title/body/prompt and image path ``{id}.png`` live in the deck.

With ``--manifest …`` (legacy), titles/bodies live in the manifest JSON; images stay ``00.png`` … order.
Render/suggest use generator.py and OPENROUTER_API_KEY (or .env key files).

Presenter (read-only):

  python slide_editor.py --present --deck keynote.json
  python slide_editor.py --present --manifest slide_images_manifest.json

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
import threading
import time
import tkinter as tk
import uuid
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext

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
    text_widget.tag_configure("md_base", foreground=SLIDE_TEXT, font=f)
    text_widget.tag_configure("md_bold", foreground=SLIDE_TEXT, font=fb)
    text_widget.tag_configure("md_italic", foreground=SLIDE_TEXT, font=fi)
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
    inline_pat = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)")
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
            elif part.startswith("*") and part.endswith("*") and len(part) >= 3:
                text_widget.insert(tk.END, part[1:-1], ("md_italic",))
            elif part.startswith("`") and part.endswith("`") and len(part) >= 3:
                text_widget.insert(tk.END, part[1:-1], ("md_code",))
            else:
                text_widget.insert(tk.END, part, (line_tag,))
        if i < len(lines) - 1:
            text_widget.insert(tk.END, "\n", ("md_base",))


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
    return rest if rest else "(no body)"


def _present_slide_image_path(output_dir: Path, spec: dict, index: int, *, use_slide_id: bool) -> Path | None:
    exts = (".png", ".jpg", ".jpeg", ".webp")
    if use_slide_id:
        sid = str(spec.get("id", "")).strip()
        if sid:
            for ext in exts:
                p = output_dir / f"{sid}{ext}"
                if p.is_file():
                    return p
        return None
    for ext in exts:
        p = output_dir / f"{index:02d}{ext}"
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
        slide_id: str | None = None,
        can_edit_content: bool = True,
        can_reorder: bool = True,
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
        self._can_edit_content = can_edit_content
        self._can_reorder = can_reorder

        # Editor widgets are built lazily (see ``ensure_editor``); until then these are None.
        self._editor_built = False
        self.title_edit_var = tk.StringVar(value=self._preview_title)
        self.title_edit: tk.Entry | None = None
        self.body_edit: scrolledtext.ScrolledText | None = None
        self.txt: scrolledtext.ScrolledText | None = None
        self._prompt_label: tk.Label | None = None
        self._editor_frame: tk.Frame | None = None
        self._button_frame: tk.Frame | None = None
        self.btn_suggest: tk.Button | None = None
        self.btn_preview: tk.Button | None = None
        self.btn_render: tk.Button | None = None
        self.btn_paste: tk.Button | None = None
        self.btn_insert: tk.Button | None = None
        self.btn_delete: tk.Button | None = None

        self._build_card()

        self.columnconfigure(0, weight=1)
        self.columnconfigure(3, weight=0)
        self.rowconfigure(3, weight=0)

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

        self._title_preview = tk.Label(
            left,
            text=self._preview_title,
            bg=SLIDE_BG,
            fg=SLIDE_TEXT,
            font=("TkDefaultFont", 12, "bold"),
            anchor="w",
            justify="left",
            wraplength=280,
        )
        self._title_preview.pack(anchor="w", fill=tk.X, pady=(0, 8))

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
        left.bind("<Configure>", self._on_left_configure)

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
        tk.Label(editor, text="Content (markdown)", anchor="w").pack(anchor="w", pady=(8, 2))
        self.body_edit = scrolledtext.ScrolledText(
            editor, height=11, width=42, wrap=tk.WORD, font=("TkDefaultFont", 10)
        )
        self.body_edit.pack(fill=tk.BOTH, expand=True, anchor="w")
        self.body_edit.insert("1.0", self._preview_body)
        if self._can_edit_content:
            self.title_edit.bind("<KeyRelease>", self._on_content_edit)
            self.body_edit.bind("<KeyRelease>", self._on_content_edit)
            self.title_edit.bind("<FocusOut>", self._on_content_edit)
            self.body_edit.bind("<FocusOut>", self._on_content_edit)
        else:
            self.title_edit.config(state=tk.DISABLED)
            self.body_edit.config(state=tk.DISABLED)

        self._prompt_label = tk.Label(self, text="Image prompt (LLM → OpenRouter):", anchor="w")
        self._prompt_label.grid(row=2, column=0, columnspan=4, sticky="w", pady=(0, 2))
        self.txt = scrolledtext.ScrolledText(
            self, height=4, width=72, wrap=tk.WORD, font=("TkFixedFont", 10)
        )
        self.txt.grid(row=3, column=0, columnspan=3, sticky="nsew", pady=(0, 4))
        self.txt.insert("1.0", self._prompt_cache)
        if self.app.deck is not None:
            self.txt.bind("<KeyRelease>", lambda _e: self.app.schedule_autosave())

        bf = tk.Frame(self)
        bf.grid(row=3, column=3, sticky="ne", padx=(8, 0))
        self._button_frame = bf
        self.btn_suggest = tk.Button(bf, text="Suggest\n(LLM)", width=10, command=self._on_suggest)
        self.btn_suggest.pack(pady=(0, 4))
        self.btn_preview = tk.Button(bf, text="Preview\nrender", width=10, command=self._on_preview_render_prompt)
        self.btn_preview.pack(pady=(0, 4))
        self.btn_render = tk.Button(bf, text="Render", width=10, command=self._on_render)
        self.btn_render.pack()
        self.btn_paste = tk.Button(bf, text="Paste\nimage", width=10, command=self._on_paste_image_button)
        self.btn_paste.pack(pady=(4, 0))
        self.btn_insert = tk.Button(bf, text="Insert\nabove", width=10, command=self._on_insert_above)
        self.btn_insert.pack(pady=(6, 4))
        self.btn_delete = tk.Button(bf, text="Delete", width=10, command=self._on_delete)
        self.btn_delete.pack()
        if not self._can_reorder:
            self.btn_insert.config(state=tk.DISABLED)
            self.btn_delete.config(state=tk.DISABLED)

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
        return f"{self._header_line()}  {self._preview_title}"

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

    def _on_left_configure(self, event: tk.Event) -> None:
        wrap = max(int(event.width) - 20, 160)
        self._title_preview.config(wraplength=wrap)

    def _insert_markdown(self, text: str) -> None:
        insert_markdown_lines(self._body_preview, text, base_pt=10)

    def get_prompt(self) -> str:
        if self.txt is not None:
            return self.txt.get("1.0", "end-1c").strip()
        return (self._prompt_cache or "").strip()

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

    def _on_content_edit(self, _event=None):
        title = self.get_title_text() or "(untitled)"
        body = self.get_body_text()
        self._preview_title = title
        self._preview_body = body
        self._top_title_label.config(text=self._title_line())
        self._title_preview.config(text=self._preview_title)
        self._fill_body_preview()
        if self.app.deck is not None:
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
            if not self._can_edit_content:
                self.body_edit.config(state=tk.DISABLED)
        self._top_title_label.config(text=self._title_line())
        self._title_preview.config(text=self._preview_title)
        self._fill_body_preview()

    def set_slide_title(self, title: str) -> None:
        self.update_slide_preview(title, None)

    def set_busy(self, busy: bool) -> None:
        st = tk.DISABLED if busy else tk.NORMAL
        for btn in (self.btn_suggest, self.btn_preview, self.btn_render, self.btn_paste):
            if btn is not None:
                btn.config(state=st)
        if self._can_reorder:
            for btn in (self.btn_insert, self.btn_delete):
                if btn is not None:
                    btn.config(state=st)

    def _slide_png_output_path(self) -> Path:
        if self.slide_id:
            return self.app.output_dir / f"{self.slide_id}.png"
        return self.app.output_dir / f"{self.index:02d}.png"

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
        if self.app.deck is not None:
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

    def _on_insert_above(self) -> None:
        self.app.insert_slide_above(self.index)

    def _on_delete(self) -> None:
        self.app.delete_slide(self.index)

    def refresh_preview(self) -> None:
        if self.slide_id:
            out = self.app.output_dir / f"{self.slide_id}.png"
        else:
            out = self.app.output_dir / f"{self.index:02d}.png"
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

    def _on_suggest(self) -> None:
        key = gen.load_api_key()
        if not key:
            messagebox.showerror("API key", "Set OPENROUTER_API_KEY or .env/OpenRouter.md")
            return
        model = self.app.text_model_var.get().strip()
        if not model:
            messagebox.showerror("Model", "Set a text model for Suggest (e.g. openai/gpt-4o-mini).")
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
                    style_excerpt=self.app.style_excerpt,
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
        if self.app.deck is not None:
            self.app.deck["slides"][self.index]["image_prompt"] = text
            self.app.schedule_autosave()
        else:
            self.app.manifest["slides"][self.index]["prompt"] = text
        self.app.set_status(f"Slide {self.index:02d}: prompt updated from LLM.")

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
            messagebox.showerror("Model", "Set an image model (e.g. google/gemini-2.5-flash-image).")
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
        if self.app.deck is not None:
            self.app.deck["slides"][self.index]["image_prompt"] = self.get_prompt()
            self.app.schedule_autosave()
        else:
            self.app.manifest["slides"][self.index]["prompt"] = self.get_prompt()
        self.refresh_preview()
        out = (
            self.app.output_dir / f"{self.slide_id}.png"
            if self.slide_id
            else self.app.output_dir / f"{self.index:02d}.png"
        )
        self.app.set_status(f"Slide {self.index:02d}: saved {out.name}")


class SlideEditorApp:
    def __init__(
        self,
        root: tk.Tk,
        manifest_path: Path | None = None,
        deck_path: Path | None = None,
        *,
        profile_startup: bool = False,
        profile_startup_exit: bool = False,
        perf_minimal_rows: bool = False,
    ):
        _init_scroll_debug_log()
        _log_scroll(f"app start cwd={Path.cwd()} log={SCROLL_DEBUG_FILE}")
        self._last_probe_log = 0.0
        self._drag_last_y: int | None = None
        self._autosave_after_id: str | None = None
        self._thumb_refresh_job: str | None = None
        self._thumb_refresh_i = 0
        self._thumb_refresh_t0 = 0.0
        self._bulk_thumb_refresh = False
        self._editor_build_job: str | None = None
        self._editor_build_i = 0
        self._editor_build_t0 = 0.0
        self._bulk_editor_build = False
        self._last_self_mtime_ns: int | None = None
        self._external_check_job: str | None = None
        self._external_check_interval_ms = 2000
        self._profile_startup = profile_startup
        self._profile_startup_exit = profile_startup_exit
        self._perf_minimal_rows = perf_minimal_rows
        self._startup_profiler: cProfile.Profile | None = None
        self._startup_profiler_wall_t0: float | None = None
        if bool(manifest_path) == bool(deck_path):
            raise ValueError("Provide exactly one of manifest_path or deck_path")
        self.root = root
        self.deck: dict | None = None
        self.manifest: dict | None = None
        self.manifest_path: Path | None = None
        self.deck_path: Path | None = None
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.minsize(min(1200, max(720, sw - 48)), min(700, max(480, sh - 100)))

        if deck_path is not None:
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
            self.style_excerpt = self.style_full[:4000]
            _sync_msg = "Deck mode — prompts and images keyed by slide id; reorder slides in JSON safely."
            path_label = "Deck:"
            path_initial = str(self.deck_path)
            source_hint = "keynote.json (markdown + prompts in one file)"
            text_model = str(self.deck.get("text_model", "openai/gpt-4o-mini"))
            image_model = str(self.deck.get("model", gen.DEFAULT_MODEL))
        else:
            assert manifest_path is not None
            self.manifest_path = manifest_path.resolve()
            if not self.manifest_path.is_file():
                raise FileNotFoundError(str(self.manifest_path))
            self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            slides = self.manifest.get("slides")
            if not isinstance(slides, list) or not slides:
                raise ValueError("Manifest has no slides[]")
            root.title(f"Slide images — {self.manifest_path.name}")
            self.output_dir = SCRIPT_DIR / self.manifest.get("output_directory", "slide_images")
            style_path = gen.resolve_style_path(self.manifest, None)
            self.style_full = gen.load_global_style(style_path, self.manifest)
            self.style_excerpt = self.style_full[:4000]
            _sync_msg = "Manifest mode — titles/bodies in JSON; edit prompts here (legacy 00.png order)."
            path_label = "Manifest:"
            path_initial = str(self.manifest_path)
            source_hint = self.manifest_path.name
            text_model = str(self.manifest.get("text_model", "openai/gpt-4o-mini"))
            image_model = str(self.manifest.get("model", gen.DEFAULT_MODEL))

        menubar = tk.Menu(root)
        fm = tk.Menu(menubar, tearoff=0)
        open_label = "Open deck…" if self.deck else "Open manifest…"
        fm.add_command(label=open_label, command=self._open_data)
        fm.add_command(label="Save", command=self.save_manifest)
        fm.add_command(label="Save as…", command=self._save_manifest_as)
        fm.add_separator()
        fm.add_command(label="Quit", command=root.quit)
        menubar.add_cascade(label="File", menu=fm)
        root.config(menu=menubar)

        top = tk.Frame(root)
        top.pack(fill=tk.X, padx=8, pady=6)

        tk.Label(top, text=path_label).pack(side=tk.LEFT)
        self.path_var = tk.StringVar(value=path_initial)
        tk.Entry(top, textvariable=self.path_var, width=70).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        tk.Button(top, text="Browse…", command=self._browse_data).pack(side=tk.LEFT)
        tk.Button(top, text="Reload", command=self._reload).pack(side=tk.LEFT, padx=4)
        tk.Button(top, text="Save", command=self.save_manifest, width=8).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(top, text="Present", command=self._open_present_mode, width=8).pack(side=tk.LEFT, padx=(8, 0))
        tk.Label(top, text=f"Source: {source_hint}", fg="#246").pack(side=tk.RIGHT, padx=8)

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
            if self.deck is not None:
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

        self.status = tk.StringVar(value=_sync_msg)
        tk.Label(root, textvariable=self.status, anchor="w", relief=tk.GROOVE).pack(
            fill=tk.X, padx=8, pady=(0, 6)
        )

        self._scroll_canvas = tk.Canvas(root, highlightthickness=0)
        sb = tk.Scrollbar(root, orient=tk.VERTICAL, command=self._scroll_canvas.yview)
        self._scroll_canvas.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.inner = tk.Frame(self._scroll_canvas)
        self._inner_win = self._scroll_canvas.create_window((0, 0), window=self.inner, anchor="nw")

        def _scroll(event):
            c = self._scroll_canvas
            delta = getattr(event, "delta", 0)
            num = getattr(event, "num", None)
            if sys.platform == "darwin":
                # Magic Mouse / trackpad can send tiny delta values (e.g. +/-1).
                if delta:
                    steps = int(-1 * (delta / 120))
                    if steps == 0:
                        steps = -1 if delta > 0 else 1
                else:
                    steps = 0
                _log_scroll(f"event platform=darwin delta={delta} num={num} steps={steps}")
                if steps:
                    c.yview_scroll(steps, "units")
            else:
                if event.num == 4:
                    _log_scroll(f"event platform=other delta={delta} num={num} steps=-1")
                    c.yview_scroll(-1, "units")
                elif event.num == 5:
                    _log_scroll(f"event platform=other delta={delta} num={num} steps=1")
                    c.yview_scroll(1, "units")
                elif delta:
                    steps = int(-1 * (delta / 120))
                    if steps == 0:
                        steps = -1 if delta > 0 else 1
                    _log_scroll(f"event platform=other delta={delta} num={num} steps={steps}")
                    c.yview_scroll(steps, "units")
                else:
                    _log_scroll(f"event ignored platform=other delta={delta} num={num}")
            return "break"

        def _middle_up(_event):
            # Convenience: middle-click anywhere on a slide scrolls upward.
            _log_scroll("middle-click scroll up steps=-5")
            self._scroll_canvas.yview_scroll(-5, "units")
            return "break"

        def _probe_input(event):
            if not _scroll_debug_enabled():
                return None
            # Throttle only extremely noisy move/drag style events.
            noisy = str(getattr(event, "type", "")).lower() in {"motion", "mousemove"}
            now = time.monotonic()
            if noisy and now - self._last_probe_log < 0.2:
                return None
            self._last_probe_log = now
            cls = "?"
            if hasattr(event, "widget"):
                w = event.widget
                if hasattr(w, "winfo_class"):
                    cls = w.winfo_class()
                elif isinstance(w, str):
                    # Some Tk callbacks can pass widget path strings.
                    try:
                        cls = self.root.nametowidget(w).winfo_class()
                    except Exception:
                        cls = "?"
            _log_scroll(
                "probe "
                f"type={getattr(event, 'type', '?')} "
                f"widget={cls} "
                f"delta={getattr(event, 'delta', 0)} "
                f"num={getattr(event, 'num', None)} "
                f"state={getattr(event, 'state', None)}"
            )
            return None

        def _can_drag_scroll(widget: tk.Widget) -> bool:
            # Keep text-entry widgets untouched so editing still feels native.
            return widget.winfo_class() in {"Frame", "Canvas", "Label"}

        def _drag_start(event):
            if not _can_drag_scroll(event.widget):
                return None
            self._drag_last_y = int(getattr(event, "y_root", 0))
            _log_scroll(f"drag start widget={event.widget.winfo_class()} y={self._drag_last_y}")
            return None

        def _drag_motion(event):
            if self._drag_last_y is None or not _can_drag_scroll(event.widget):
                return None
            y = int(getattr(event, "y_root", 0))
            dy = y - self._drag_last_y
            # Positive dy means pointer moved down; content should scroll up and vice versa.
            steps = int(-dy / 6)
            if steps:
                self._scroll_canvas.yview_scroll(steps, "units")
                self._drag_last_y = y
                _log_scroll(f"drag scroll dy={dy} steps={steps} widget={event.widget.winfo_class()}")
                return "break"
            return None

        def _drag_end(event):
            if self._drag_last_y is not None and _can_drag_scroll(event.widget):
                _log_scroll(f"drag end widget={event.widget.winfo_class()} y={getattr(event, 'y_root', 0)}")
            self._drag_last_y = None
            return None

        def _bind_scroll_handlers(widget: tk.Widget) -> None:
            # Capture-tag runs BEFORE widget/class bindings (Text class can swallow wheel events).
            tags = widget.bindtags()
            if "WheelCapture" not in tags:
                widget.bindtags(("WheelCapture",) + tags)
                LOG.debug("bindtags WheelCapture widget=%s", widget.winfo_class())
            if _can_drag_scroll(widget):
                widget.bind("<ButtonPress-1>", _drag_start, add="+")
                widget.bind("<B1-Motion>", _drag_motion, add="+")
                widget.bind("<ButtonRelease-1>", _drag_end, add="+")
            for child in widget.winfo_children():
                _bind_scroll_handlers(child)

        # Bind capture class once (applies to any widget that has WheelCapture in bindtags).
        self.root.bind_class("WheelCapture", "<MouseWheel>", _scroll)
        self.root.bind_class("WheelCapture", "<Button-4>", _scroll)
        self.root.bind_class("WheelCapture", "<Button-5>", _scroll)
        self.root.bind_class("WheelCapture", "<Button-2>", _middle_up)
        self.root.bind_class("WheelCapture", "<ButtonPress-1>", _probe_input)
        self.root.bind_class("WheelCapture", "<ButtonRelease-1>", _probe_input)
        self.root.bind_class("WheelCapture", "<ButtonPress-2>", _probe_input)
        self.root.bind_class("WheelCapture", "<ButtonRelease-2>", _probe_input)
        # Do not bind Enter/Leave/Focus* to _probe_input: building the slide tree fires
        # thousands of those events; with --debug each one opened scroll_debug.log (70s+ stalls).

        self._scroll_canvas.bind("<Enter>", lambda _e: self._scroll_canvas.focus_set())
        self._scroll_canvas.bind("<MouseWheel>", _scroll)
        self._scroll_canvas.bind("<Button-4>", _scroll)
        self._scroll_canvas.bind("<Button-5>", _scroll)
        self.root.bind_all("<MouseWheel>", _scroll, add="+")
        self.root.bind_all("<Shift-MouseWheel>", _scroll, add="+")
        self.root.bind_all("<Option-MouseWheel>", _scroll, add="+")
        self.root.bind_all("<Control-MouseWheel>", _scroll, add="+")
        self.root.bind_all("<Button-4>", _scroll, add="+")
        self.root.bind_all("<Button-5>", _scroll, add="+")
        self.root.bind_all("<Button-2>", _middle_up, add="+")

        def _on_canvas_configure(event):
            self._scroll_canvas.itemconfig(self._inner_win, width=event.width)

        self.inner.bind("<Configure>", self._on_inner_configure)
        self._scroll_canvas.bind("<Configure>", _on_canvas_configure)
        _bind_scroll_handlers(self._scroll_canvas)
        _bind_scroll_handlers(self.inner)
        self._bind_scroll_handlers = _bind_scroll_handlers

        self.rows: list[SlideRow] = []
        tk.Label(
            self.inner,
            text="Loading slides…",
            fg=SLIDE_DIM,
            bg=SLIDE_BG,
            font=("TkDefaultFont", 12),
        ).pack(anchor=tk.NW, padx=24, pady=40)
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
        src = self.deck if self.deck is not None else self.manifest
        assert src is not None
        return int(src.get("width", 1024)), int(src.get("height", 1024))

    def set_status(self, msg: str) -> None:
        self.status.set(msg)

    def get_content_guide_text(self) -> str:
        return self.content_guide.get("1.0", "end-1c").strip()

    def _sync_content_guide_widget_from_json(self) -> None:
        src = self.deck if self.deck is not None else self.manifest
        assert src is not None
        raw = src.get("content_guide")
        text = gen.DEFAULT_CONTENT_GUIDE
        if isinstance(raw, str) and raw.strip():
            text = raw
        self.content_guide.delete("1.0", tk.END)
        self.content_guide.insert("1.0", text)

    def _neighbor_slides_markdown_for_insert(self, insert_at: int) -> str:
        """Title + body of slides around the insertion point for LLM continuity."""
        if self.deck is None:
            return ""
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

    def _open_present_mode(self) -> None:
        """Open read-only presenter in a ``Toplevel`` (current in-memory deck/manifest)."""
        top = tk.Toplevel(self.root)
        top.transient(self.root)
        top.title("Present")
        top.minsize(800, 500)
        top.geometry("1280x820")
        try:
            if self.deck is not None:
                assert self.deck_path is not None
                PresentModeApp(
                    top,
                    deck_data=copy.deepcopy(self.deck),
                    deck_path=self.deck_path,
                    fullscreen=False,
                    embedded=True,
                )
            else:
                assert self.manifest is not None and self.manifest_path is not None
                PresentModeApp(
                    top,
                    manifest_data=copy.deepcopy(self.manifest),
                    manifest_path=self.manifest_path,
                    fullscreen=False,
                    embedded=True,
                )
        except ValueError as e:
            messagebox.showerror("Present", str(e), parent=self.root)
            top.destroy()
            return
        top.focus_set()

    def schedule_autosave(self) -> None:
        """Deck only: debounced write to ``keynote.json`` after edits."""
        if self.deck is None:
            return
        if self._autosave_after_id is not None:
            self.root.after_cancel(self._autosave_after_id)
        self._autosave_after_id = self.root.after(1200, self._flush_autosave)

    def _flush_autosave(self) -> None:
        self._autosave_after_id = None
        if self.deck is None:
            return
        self.save_manifest(autosave=True)

    def _current_data_path(self) -> Path | None:
        return self.deck_path if self.deck is not None else self.manifest_path

    def _record_self_mtime(self) -> None:
        """Record the current file mtime so the watcher doesn't treat our own writes as external."""
        p = self._current_data_path()
        if p is None:
            self._last_self_mtime_ns = None
            return
        try:
            self._last_self_mtime_ns = p.stat().st_mtime_ns
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
            if p is None or not p.is_file():
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
        src = self.deck if self.deck is not None else self.manifest
        if src is None:
            return []
        slides = src.get("slides")
        return slides if isinstance(slides, list) else []

    def _cancel_thumb_refresh_scheduler(self) -> None:
        if self._thumb_refresh_job is not None:
            try:
                self.root.after_cancel(self._thumb_refresh_job)
            except tk.TclError:
                pass
            self._thumb_refresh_job = None
        if self._bulk_thumb_refresh:
            self._bulk_thumb_refresh = False
            self._apply_scroll_region()

    def _cancel_editor_build_scheduler(self) -> None:
        if self._editor_build_job is not None:
            try:
                self.root.after_cancel(self._editor_build_job)
            except tk.TclError:
                pass
            self._editor_build_job = None
        if self._bulk_editor_build:
            self._bulk_editor_build = False
            self._apply_scroll_region()

    def _on_inner_configure(self, _event=None) -> None:
        # During thumbnail refresh / background editor build each preview/widget resize fires
        # <Configure>; bbox("all") on a large inner window is O(tree) and dominated startup
        # (~1s × slide count) even with a warm disk cache. Defer scrollregion until bursts end.
        if self._bulk_thumb_refresh or self._bulk_editor_build:
            return
        self._apply_scroll_region()

    def _apply_scroll_region(self) -> None:
        self._scroll_canvas.configure(scrollregion=self._scroll_canvas.bbox("all"))

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

    def _schedule_row_thumbnail_refresh(self) -> None:
        """Load all list previews in one ``after_idle`` slice.

        Returning to ``mainloop`` between each slide (e.g. ``after(1)`` per row) lets macOS Tk run a
        full display/layout pass per image; wall time was ~1s × slide count while Python (cProfile)
        stayed ~1–2s total. One idle callback keeps compositor work batched.
        """
        self._cancel_thumb_refresh_scheduler()
        self._thumb_refresh_i = 0
        self._thumb_refresh_t0 = time.monotonic()
        self._bulk_thumb_refresh = True
        self._thumb_refresh_job = self.root.after_idle(self._thumb_refresh_advance)

    def _thumb_refresh_advance(self) -> None:
        self._thumb_refresh_job = None
        n = len(self.rows)
        if self._thumb_refresh_i >= n:
            self._bulk_thumb_refresh = False
            self._apply_scroll_region()
            self._schedule_editor_build()
            return
        while self._thumb_refresh_i < n:
            self.rows[self._thumb_refresh_i].refresh_preview()
            self._thumb_refresh_i += 1
        self._bulk_thumb_refresh = False
        self._apply_scroll_region()
        dt = time.monotonic() - self._thumb_refresh_t0
        print(
            f"[startup] thumbnails: {dt:.2f}s ({n} rows)",
            file=sys.stderr,
            flush=True,
        )
        if _scroll_debug_enabled():
            _log_scroll(f"slide preview thumbnails finished in {dt:.2f}s ({n} slides)")
        self._schedule_editor_build()

    def _schedule_editor_build(self) -> None:
        """Build each row's editor pane in the background, one per idle tick.

        Startup shows all slide cards (title + body preview + image) immediately; editor
        widgets (``Entry`` + two ``ScrolledText``s + six ``Button``s per row) are heavy on
        macOS Tk (~1 s/row of layout/compositing). Spreading them across idle ticks keeps
        the UI responsive while the queue drains.
        """
        if _PERF_COLLAPSED_ROWS:
            # Diagnostic: never build editors. Finish startup profile now.
            self._finish_startup_profile_if_active()
            return
        self._cancel_editor_build_scheduler()
        self._editor_build_i = 0
        self._editor_build_t0 = time.monotonic()
        self._bulk_editor_build = True
        # ``after(1, …)`` rather than ``after_idle`` so scroll/click events queued by the
        # user interleave between rows instead of being starved by the idle queue.
        self._editor_build_job = self.root.after(1, self._editor_build_advance)

    def _editor_build_advance(self) -> None:
        self._editor_build_job = None
        n = len(self.rows)
        if self._editor_build_i >= n:
            self._bulk_editor_build = False
            self._apply_scroll_region()
            dt = time.monotonic() - self._editor_build_t0
            print(
                f"[startup] editors: {dt:.2f}s ({n} rows)",
                file=sys.stderr,
                flush=True,
            )
            startup_t0 = getattr(self, "_startup_wall_t0", None)
            if startup_t0 is not None:
                print(
                    f"[startup] total: {time.monotonic() - startup_t0:.2f}s",
                    file=sys.stderr,
                    flush=True,
                )
            if _scroll_debug_enabled():
                _log_scroll(f"editor build finished in {dt:.2f}s ({n} rows)")
            self._finish_startup_profile_if_active()
            return
        row = self.rows[self._editor_build_i]
        try:
            row.ensure_editor()
        except Exception as e:  # build should be robust; one bad row shouldn't stall queue
            LOG.warning("ensure_editor failed for row %d: %s", self._editor_build_i, e)
        self._editor_build_i += 1
        self._editor_build_job = self.root.after(1, self._editor_build_advance)

    def _rebuild_rows(self) -> None:
        self._bulk_thumb_refresh = False
        self._cancel_thumb_refresh_scheduler()
        self._cancel_editor_build_scheduler()
        build_t0 = time.monotonic()
        for child in list(self.inner.winfo_children()):
            child.destroy()
        self.rows = []
        slides = self._current_slides()
        if self._perf_minimal_rows:
            for i, spec in enumerate(slides):
                if not isinstance(spec, dict):
                    continue
                title = str(spec.get("title", f"Slide {i}"))
                lbl = tk.Label(
                    self.inner,
                    text=f"[{i:02d}]  {title}",
                    anchor="w",
                    justify="left",
                    font=("TkDefaultFont", 12),
                    padx=8,
                    pady=6,
                )
                lbl.pack(fill=tk.X, expand=True, padx=4, pady=2)
            self._bind_scroll_handlers(self.inner)
            self._last_build_wall_s = time.monotonic() - build_t0
            print(
                f"[startup] widgets: {self._last_build_wall_s:.2f}s"
                f" ({len(slides)} minimal rows)",
                file=sys.stderr,
                flush=True,
            )
            self._apply_scroll_region()
            self.root.after_idle(self._perf_minimal_idle_done)
            return
        for i, spec in enumerate(slides):
            if not isinstance(spec, dict):
                continue
            title = str(spec.get("title", f"Slide {i}"))
            body = str(spec.get("body", ""))
            if self.deck is not None:
                prompt = str(spec.get("image_prompt", spec.get("prompt", "")))
                sid = str(spec.get("id", "")).strip() or None
                can_edit_content = True
                can_reorder = True
            else:
                prompt = str(spec.get("prompt", ""))
                sid = None
                can_edit_content = False
                can_reorder = False
            row = SlideRow(
                self.inner,
                self,
                i,
                title,
                body,
                prompt,
                slide_id=sid,
                can_edit_content=can_edit_content,
                can_reorder=can_reorder,
                skip_initial_preview=True,
            )
            row.pack(fill=tk.X, expand=True, padx=4, pady=10)
            self.rows.append(row)
        self._bind_scroll_handlers(self.inner)
        self._last_build_wall_s = time.monotonic() - build_t0
        print(
            f"[startup] widgets: {self._last_build_wall_s:.2f}s ({len(self.rows)} rows)",
            file=sys.stderr,
            flush=True,
        )
        self._schedule_row_thumbnail_refresh()

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
        if self.deck is None:
            self.set_status("Insert/delete only available in deck mode.")
            return
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
            self._rebuild_rows()
            self.save_manifest(autosave=True)
            self.set_status(f"Inserted new slide above [{insert_at:02d}].")
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
            model = self.text_model_var.get().strip() or "openai/gpt-4o-mini"
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
        if self.deck is None:
            self.set_status("Insert/delete only available in deck mode.")
            return
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
        self._rebuild_rows()
        self.save_manifest(autosave=True)
        self.set_status(f"Deleted slide [{index:02d}].")

    def save_manifest(self, *, autosave: bool = False) -> None:
        if self.deck is not None:
            assert self.deck_path is not None
            self.deck["text_model"] = self.text_model_var.get().strip()
            self.deck["model"] = self.image_model_var.get().strip()
            self.deck["content_guide"] = self.get_content_guide_text()
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
            kd.save_deck(self.deck_path, self.deck)
            self._record_self_mtime()
            self.set_status(
                f"Auto-saved {self.deck_path.name}" if autosave else f"Saved {self.deck_path.name}"
            )
            return
        assert self.manifest is not None and self.manifest_path is not None
        self.manifest["text_model"] = self.text_model_var.get().strip()
        self.manifest["model"] = self.image_model_var.get().strip()
        self.manifest["content_guide"] = self.get_content_guide_text()
        for row in self.rows:
            spec = self.manifest["slides"][row.index]
            spec["prompt"] = row.get_prompt()
        gen.save_manifest(self.manifest_path, self.manifest)
        self._record_self_mtime()
        self.set_status(f"Saved {self.manifest_path.name}")

    def _save_manifest_as(self) -> None:
        initial = (
            self.deck_path.name if self.deck_path is not None else self.manifest_path.name
        )
        p = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("All", "*")],
            initialfile=initial,
        )
        if not p:
            return
        new_p = Path(p)
        self.path_var.set(str(new_p))
        if self.deck is not None:
            self.deck_path = new_p
        else:
            self.manifest_path = new_p
        self.save_manifest()

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
        """Re-read JSON from path_var and refresh rows."""
        if self._autosave_after_id is not None:
            self.root.after_cancel(self._autosave_after_id)
            self._autosave_after_id = None
        p = Path(self.path_var.get().strip())
        if not p.is_file():
            messagebox.showerror("File", f"Not found:\n{p}")
            return
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            messagebox.showerror("JSON", str(e))
            return
        slides = data.get("slides")
        if not isinstance(slides, list):
            messagebox.showerror(
                "File",
                "Invalid slides[] in JSON.",
            )
            return
        if self.deck is not None:
            if not self._is_deck_json(data):
                messagebox.showerror("File", "Not a keynote deck (expected frontmatter + slides).")
                return
            self.deck_path = p.resolve()
            self.deck = data
            self.text_model_var.set(str(data.get("text_model", "openai/gpt-4o-mini")))
            self.image_model_var.set(str(data.get("model", gen.DEFAULT_MODEL)))
            style_path = gen.resolve_style_path(self.deck, None)
            self.style_full = gen.load_global_style(style_path, self.deck)
            self.style_excerpt = self.style_full[:4000]
            self._sync_content_guide_widget_from_json()
            self._rebuild_rows()
            self._record_self_mtime()
            self.set_status(f"Reloaded {self.deck_path.name}.")
            return

        if self._is_deck_json(data):
            messagebox.showerror("File", "This looks like keynote.json; restart with --deck.")
            return
        self.manifest_path = p.resolve()
        self.manifest = data
        self.text_model_var.set(str(data.get("text_model", "openai/gpt-4o-mini")))
        self.image_model_var.set(str(data.get("model", gen.DEFAULT_MODEL)))
        style_path = gen.resolve_style_path(self.manifest, None)
        self.style_full = gen.load_global_style(style_path, self.manifest)
        self.style_excerpt = self.style_full[:4000]
        self._sync_content_guide_widget_from_json()
        self._rebuild_rows()
        self._record_self_mtime()
        self.set_status(f"Reloaded {self.manifest_path.name}.")


class PresentModeApp:
    """Read-only presenter: markdown + optional slide image (``Tk`` or ``Toplevel`` host)."""

    def __init__(
        self,
        win: tk.Misc,
        *,
        deck_path: Path | None = None,
        manifest_path: Path | None = None,
        deck_data: dict | None = None,
        manifest_data: dict | None = None,
        fullscreen: bool = True,
        embedded: bool = False,
    ):
        deck_src = bool(deck_path or deck_data)
        man_src = bool(manifest_path or manifest_data)
        if deck_src == man_src:
            raise ValueError(
                "PresentModeApp: provide exactly one of deck (path or data) or manifest (path or data)."
            )
        self.win = win
        self.embedded = embedded
        self.fullscreen = fullscreen
        self._photo: object | None = None
        self._img_job: str | None = None
        self._pending_image_path: Path | None = None
        self.manifest: dict | None = None
        self.manifest_path: Path | None = None
        self.deck: dict | None = None
        self.deck_path: Path | None = None

        if deck_src:
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
            self.use_slide_id = True
            label = self.deck_path.name if self.deck_path else "deck"
            win.title(f"Present — {label}")
        else:
            if manifest_data is not None:
                self.manifest = manifest_data
                self.manifest_path = manifest_path.resolve() if manifest_path is not None else None
            else:
                assert manifest_path is not None
                self.manifest_path = manifest_path.resolve()
                self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            slides = self.manifest.get("slides")
            if not isinstance(slides, list) or not slides:
                raise ValueError("Manifest has no slides[]")
            self.slides = [s for s in slides if isinstance(s, dict)]
            self.output_dir = SCRIPT_DIR / str(self.manifest.get("output_directory", "slide_images"))
            self.use_slide_id = False
            label = self.manifest_path.name if self.manifest_path else "manifest"
            win.title(f"Present — {label}")

        self.index = 0
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
        tk.Label(foot, textvariable=self._hint, font=("TkDefaultFont", 10), fg=SLIDE_DIM, bg=SLIDE_BG).pack(
            side=tk.RIGHT, fill=tk.X, expand=True, anchor="e"
        )

        nav = tk.Frame(win, bg=SLIDE_BG)
        nav.pack(fill=tk.X, pady=(0, 8))
        tk.Button(nav, text="← Previous", command=self._prev).pack(side=tk.LEFT, padx=6)
        tk.Button(nav, text="Next →", command=self._next).pack(side=tk.LEFT, padx=6)
        quit_label = "Back to editor" if embedded else "Quit"
        tk.Button(nav, text=quit_label, command=self._close_present).pack(side=tk.RIGHT, padx=12)
        tk.Button(nav, text="Reload", command=self._reload_from_disk, width=8).pack(side=tk.RIGHT, padx=(0, 6))

        self._bind_present_keys(win)

        if embedded and hasattr(win, "protocol"):
            win.protocol("WM_DELETE_WINDOW", self._close_present)

        self._show_slide()

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

    def _reload_from_disk(self) -> None:
        """Re-read ``keynote.json`` or manifest from disk; keep slide index when possible."""
        if self.deck_path is None and self.manifest_path is None:
            messagebox.showinfo(
                "Reload",
                "No JSON path is associated with this presenter (in-memory only). "
                "Close and use Present again from the editor after saving.",
                parent=self.win,
            )
            return
        try:
            if self.deck_path is not None:
                self.deck = kd.load_deck(self.deck_path)
                slides = self.deck.get("slides")
                if not isinstance(slides, list) or not slides:
                    messagebox.showwarning("Reload", "Deck has no slides after reload.", parent=self.win)
                    return
                self.slides = [s for s in slides if isinstance(s, dict)]
                self.output_dir = SCRIPT_DIR / str(self.deck.get("output_directory", "slide_images"))
            else:
                assert self.manifest_path is not None
                self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
                slides = self.manifest.get("slides")
                if not isinstance(slides, list) or not slides:
                    messagebox.showwarning("Reload", "Manifest has no slides after reload.", parent=self.win)
                    return
                self.slides = [s for s in slides if isinstance(s, dict)]
                self.output_dir = SCRIPT_DIR / str(self.manifest.get("output_directory", "slide_images"))
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
        self.index = max(0, min(self.index, n - 1))
        spec = self.slides[self.index]
        title = str(spec.get("title", f"Slide {self.index}")).strip() or f"Slide {self.index}"
        self.title_lbl.config(text=title, font=("TkDefaultFont", self._present_title_pt(), "bold"))

        md = _strip_leading_title_heading_for_present(_present_slide_markdown(spec, self.index), title)
        self.md_text.config(state=tk.NORMAL)
        self.md_text.delete("1.0", tk.END)
        insert_markdown_lines(self.md_text, md, base_pt=self._present_body_pt)
        self.md_text.config(state=tk.DISABLED)

        img_path = _present_slide_image_path(self.output_dir, spec, self.index, use_slide_id=self.use_slide_id)
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
        default=None,
        help="Edit keynote.json (stable slide ids, {id}.png)",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=SCRIPT_DIR / "slide_images_manifest.json",
        help="Path to slide_images_manifest.json (legacy)",
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

    root = tk.Tk()
    try:
        if args.present:
            fullscreen = not args.present_windowed
            if args.deck is not None:
                if not args.deck.is_file():
                    print(f"Error: deck not found: {args.deck}", file=sys.stderr)
                    sys.exit(1)
                PresentModeApp(
                    root,
                    deck_path=args.deck.resolve(),
                    fullscreen=fullscreen,
                    embedded=False,
                )
            else:
                if not args.manifest.is_file():
                    print(f"Error: manifest not found: {args.manifest}", file=sys.stderr)
                    sys.exit(1)
                PresentModeApp(
                    root,
                    manifest_path=args.manifest.resolve(),
                    fullscreen=fullscreen,
                    embedded=False,
                )
        elif args.deck is not None:
            if not args.deck.is_file():
                print(f"Error: deck not found: {args.deck}", file=sys.stderr)
                print("Create with: python keynote_deck.py import talk.md keynote.json", file=sys.stderr)
                sys.exit(1)
            SlideEditorApp(
                root,
                deck_path=args.deck,
                profile_startup=args.profile_startup,
                profile_startup_exit=args.profile_startup_exit,
                perf_minimal_rows=args.perf_minimal_rows,
            )
        else:
            if not args.manifest.is_file():
                print(f"Error: manifest not found: {args.manifest}", file=sys.stderr)
                print("Prefer: python slide_editor.py --deck keynote.json", file=sys.stderr)
                sys.exit(1)
            SlideEditorApp(
                root,
                manifest_path=args.manifest,
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
