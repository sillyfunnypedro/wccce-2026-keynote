#!/usr/bin/env python3
"""
Generate square slide images for the WCCCE keynote via OpenRouter.

- **`global_style.md`** — global background / palette / art direction (read every run).
  Override path with manifest key `global_style_file` or CLI `--global-style`.
  Each render also appends optional ``content_guide`` plus slide title/body (when present), then the slide image prompt.
- **`slide_images_manifest.json`** — per-slide `prompt` plus output settings (legacy).
- **`keynote.json`** — canonical deck: stable slide `id`, `markdown`, `image_prompt`; images as `{id}.png`.
  Optional ``content_guide`` — overall keynote theme passed to LLM suggest / new-slide drafts.

API key: `OPENROUTER_API_KEY` or `.env/OpenRouter.md` (see `load_api_key`).

Usage:
  python generator.py --deck keynote.json --dry-run
  python generator.py --manifest slide_images_manifest.json --dry-run

Markdown → JSON (one-time): ``python keynote_deck.py import talk.md keynote.json``

GUI (per-slide preview, LLM suggest, render):
  python slide_editor.py --deck keynote.json
  python slide_editor.py --manifest slide_images_manifest.json
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DEFAULT_GLOBAL_STYLE_FILE = SCRIPT_DIR / "global_style.md"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemini-2.5-flash-image"

DEFAULT_CONTENT_GUIDE = (
    "This is a keynote lecture where we are advocating a return to thinking about "
    "computer science as the preparation of builders, not just certified CS graduates."
)

# Used only if no global_style file exists and manifest has no style_prompt
DEFAULT_STYLE_FALLBACK = """\
Output: 1024x1024 pixels, square 1:1 aspect ratio.
Black-and-white ink with crosshatching; medieval + modern tech blend; whimsical; no text."""

KNOWN_MODELS = {
    "google/gemini-2.5-flash-image": "Default — fast Nano Banana style",
    "google/gemini-2.5-flash-image-preview": "Preview variant",
    "google/gemini-3-pro-image-preview": "Higher quality / resolution options",
    "openai/gpt-5-image": "OpenAI image (often strong composition)",
    "openai/gpt-5-image-mini": "Cheaper OpenAI image",
}


# ── Keynote parsing (kept local; mirrors generate_slides.py) ─────────────────

def parse_frontmatter(text: str) -> tuple[dict, str]:
    meta: dict = {}
    if not text.startswith("---"):
        return meta, text
    end = text.find("\n---", 3)
    if end == -1:
        return meta, text
    fm_block = text[3:end].strip()
    rest = text[end + 4 :].lstrip("\n")
    for line in fm_block.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip().strip("'\"")
    return meta, rest


def split_slides(text: str) -> list[tuple[str, str]]:
    pattern = re.compile(r"^(---\s*\w*)\s*$", re.MULTILINE)
    parts = pattern.split(text)
    slides: list[tuple[str, str]] = []
    if parts[0].strip():
        slides.append(("---", parts[0]))
    i = 1
    while i < len(parts) - 1:
        slides.append((parts[i].strip(), parts[i + 1]))
        i += 2
    return slides


def extract_title_and_body(content: str) -> tuple[str, list[str]]:
    lines = content.strip().splitlines()
    title = ""
    body: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# ") and not title:
            title = stripped[2:]
        else:
            body.append(line)
    while body and not body[0].strip():
        body.pop(0)
    return title, body


def keynote_slides_metadata(keynote_path: Path) -> list[dict]:
    """One entry per slide in deck order: ``title`` (short label) and ``body`` (slide text for the LLM)."""
    text = keynote_path.read_text(encoding="utf-8")
    _meta, body = parse_frontmatter(text)
    raw = split_slides(body)
    out: list[dict] = []
    for sep, content in raw:
        if not content.strip():
            continue
        slide_type = sep.strip().lstrip("-").strip().lower() or "single"
        lines = content.strip().splitlines()

        if slide_type == "title":
            title = ""
            rest_i = 0
            for i, line in enumerate(lines):
                s = line.strip()
                if s.startswith("# ") and not title:
                    title = s[2:]
                    rest_i = i + 1
                    break
            title = title or "Title slide"
            slide_body = "\n".join(lines[rest_i:]).strip()

        elif slide_type == "quote":
            chunks: list[str] = []
            for line in lines:
                s = line.strip()
                if s.startswith("# "):
                    chunks.append(s[2:])
                elif s:
                    chunks.append(s)
            slide_body = "\n".join(chunks).strip()
            if chunks:
                head = chunks[0][:72] + ("…" if len(chunks[0]) > 72 else "")
                title = f"Quote: {head}" if len(chunks) > 1 or len(chunks[0]) > 60 else f"Quote: {chunks[0]}"
            else:
                title = "Quote slide"

        else:
            title, body_lines = extract_title_and_body(content)
            title = title or "Untitled slide"
            slide_body = "\n".join(body_lines).strip()

        kind = "title" if slide_type == "title" else ("quote" if slide_type == "quote" else "content")
        out.append({"title": title, "body": slide_body, "kind": kind})
    return out


def deck_slide_at(deck: dict, index: int) -> dict | None:
    """Return slide dict from ``keynote.json`` deck, or None."""
    slides = deck.get("slides")
    if not isinstance(slides, list) or index < 0 or index >= len(slides):
        return None
    s = slides[index]
    return s if isinstance(s, dict) else None


# ── API key ───────────────────────────────────────────────────────────────────

def find_repo_root() -> Path:
    current = SCRIPT_DIR
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return SCRIPT_DIR


def _parse_key_lines(lines: list[str]) -> str:
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("```"):
            continue
        if "=" in line:
            k, _, v = line.partition("=")
            if k.strip() == "OPENROUTER_API_KEY" and v.strip():
                return v.strip().strip("'\"")
        elif line.startswith("sk-or-") or line.startswith("sk-"):
            return line
    return ""


def load_api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if key:
        return key

    roots: list[Path] = []
    r = find_repo_root()
    roots.append(r)
    if SCRIPT_DIR.resolve() != r.resolve():
        roots.append(SCRIPT_DIR)

    tried: set[Path] = set()
    for name in ("OpenRouter.md", "openrouterkey.md", "OpenRouterKey.md"):
        for root in roots:
            key_file = (root / ".env" / name).resolve()
            if key_file in tried or not key_file.is_file():
                continue
            tried.add(key_file)
            with open(key_file, encoding="utf-8") as f:
                found = _parse_key_lines(f.readlines())
            if found:
                return found
    return ""


# ── OpenRouter image call ─────────────────────────────────────────────────────

def _save_data_url(data_url: str, output_path: Path) -> bool:
    try:
        b64_data = data_url.split(",", 1)[1] if "," in data_url else data_url
        raw = base64.b64decode(b64_data)
        output_path.write_bytes(raw)
        return True
    except Exception as e:
        print(f"  Error decoding image data: {e}")
        return False


def save_image_from_message(message: dict, output_path: Path) -> bool:
    images = message.get("images") or []
    if images:
        img = images[0]
        if isinstance(img, str):
            return _save_data_url(img, output_path)
        if isinstance(img, dict):
            if img.get("type") == "image_url":
                url = (img.get("image_url") or {}).get("url", "")
                if url:
                    return _save_data_url(url, output_path)
            url = img.get("url", "")
            if url:
                return _save_data_url(url, output_path)
            b64 = img.get("b64_json") or img.get("data") or img.get("b64") or ""
            if b64:
                output_path.write_bytes(base64.b64decode(b64))
                return True

    content = message.get("content", "")
    if isinstance(content, list):
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "image_url":
                url = (part.get("image_url") or {}).get("url", "")
                if url.startswith("data:image"):
                    return _save_data_url(url, output_path)
        for part in content:
            if isinstance(part, dict) and "inline_data" in part:
                b64 = part["inline_data"].get("data", "")
                if b64:
                    output_path.write_bytes(base64.b64decode(b64))
                    return True
    elif isinstance(content, str) and "data:image" in content:
        start = content.find("data:image")
        end = len(content)
        for delim in ('"', "'", " ", "\n", ")"):
            idx = content.find(delim, start)
            if idx != -1 and idx < end:
                end = idx
        return _save_data_url(content[start:end], output_path)

    print("  Error: No image found in API message")
    return False


def compose_render_image_prompt(
    *,
    user_prompt: str,
    style_prompt: str,
    width: int,
    height: int,
    content_guide: str = "",
    slide_title: str = "",
    slide_body: str = "",
) -> str:
    """
    Exact user message string sent to the image model: global style, optional deck
    theme and slide text for grounding, then the slide image brief and size line.
    """
    chunks: list[str] = [style_prompt.strip()]

    def _sep() -> None:
        chunks.append("\n\n---\n\n")

    _sep()
    cg = (content_guide or "").strip()
    if cg:
        if len(cg) > 6000:
            cg = cg[:6000] + "\n…(truncated)"
        chunks.extend(
            [
                "Overall keynote theme and goals (whole deck — align the illustration with this message):\n",
                cg,
            ]
        )
        _sep()
    st = (slide_title or "").strip()
    sb = (slide_body or "").strip()
    if st or sb:
        body_block = sb
        if len(body_block) > 8000:
            body_block = body_block[:8000] + "\n…(truncated)"
        chunks.append(
            "Slide title and body (speaker content — illustrate these ideas; "
            "do not paint readable letters, words, numbers, logos, or UI):\n"
        )
        if st:
            chunks.extend(["Title: ", st, "\n"])
        chunks.extend(["Body:\n", body_block if body_block else "(empty)"])
        _sep()
    chunks.extend(
        [
            "Subject for this slide only (no text in image):\n",
            user_prompt.strip(),
            "\n\n",
            f"Output a single {width}x{height} pixel PNG image.",
        ]
    )
    return "".join(chunks)


def generate_image_api(
    *,
    user_prompt: str,
    style_prompt: str,
    output_path: Path,
    api_key: str,
    model: str,
    width: int,
    height: int,
    content_guide: str = "",
    slide_title: str = "",
    slide_body: str = "",
) -> bool:
    """One OpenRouter multimodal image generation; writes PNG to output_path."""
    full_prompt = compose_render_image_prompt(
        user_prompt=user_prompt,
        style_prompt=style_prompt,
        width=width,
        height=height,
        content_guide=content_guide,
        slide_title=slide_title,
        slide_body=slide_body,
    )

    payload = json.dumps(
        {
            "model": model,
            "modalities": ["image", "text"],
            "messages": [{"role": "user", "content": full_prompt}],
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        OPENROUTER_API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/wccce-2026-keynote",
            "X-Title": "WCCCE Keynote Slide Images",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:500]}")
        return False
    except urllib.error.URLError as e:
        print(f"  URL error: {e.reason}")
        return False

    if "error" in result:
        print(f"  API error: {result['error']}")
        return False

    choices = result.get("choices") or []
    if not choices:
        print("  Error: empty choices")
        return False

    message = choices[0].get("message") or {}
    return save_image_from_message(message, output_path)


def maybe_resize_png(path: Path, width: int, height: int) -> None:
    try:
        from PIL import Image  # type: ignore
    except ImportError:
        return
    with Image.open(path) as im:
        if im.size == (width, height):
            return
        im = im.convert("RGBA")
        im = im.resize((width, height), Image.Resampling.LANCZOS)
        im.save(path, "PNG")


# ── Manifest ──────────────────────────────────────────────────────────────────

def resolve_style_path(manifest: dict, cli_style: Path | None) -> Path:
    """Path to the markdown file containing the global style prompt."""
    if cli_style is not None:
        p = cli_style.expanduser()
        return p if p.is_absolute() else SCRIPT_DIR / p
    rel = (manifest.get("global_style_file") or "").strip()
    if rel:
        p = Path(rel).expanduser()
        return p if p.is_absolute() else SCRIPT_DIR / p
    return DEFAULT_GLOBAL_STYLE_FILE


def load_global_style(style_path: Path, manifest: dict) -> str:
    """
    Read global style from markdown file. If missing, use manifest ``style_prompt``
    (legacy) or built-in fallback, and print a short warning when using fallback.
    """
    if style_path.is_file():
        text = style_path.read_text(encoding="utf-8").strip()
        if text:
            return text
        print(f"Warning: {style_path} is empty; using fallback style.", file=sys.stderr)

    legacy = str(manifest.get("style_prompt", "")).strip()
    if legacy:
        print(
            f"Warning: using manifest \"style_prompt\" (deprecated). Prefer {style_path.name}.",
            file=sys.stderr,
        )
        return legacy

    print(
        f"Warning: no style file at {style_path}; using DEFAULT_STYLE_FALLBACK.",
        file=sys.stderr,
    )
    return DEFAULT_STYLE_FALLBACK


def load_manifest(path: Path) -> dict:
    if not path.exists():
        print(f"Error: manifest not found: {path}", file=sys.stderr)
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def save_manifest(path: Path, manifest: dict) -> None:
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _assistant_text(message: dict) -> str:
    """Plain text from a chat/completions assistant message."""
    content = message.get("content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "text":
                parts.append(str(part.get("text", "")))
            elif "text" in part:
                parts.append(str(part["text"]))
        return "\n".join(parts).strip()
    return ""


def openrouter_chat_text(
    *,
    api_key: str,
    model: str,
    messages: list[dict],
    timeout: int = 120,
) -> str:
    """POST chat/completions (text only). Returns assistant message text or raises."""
    payload = json.dumps({"model": model, "messages": messages}).encode("utf-8")
    req = urllib.request.Request(
        OPENROUTER_API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/wccce-2026-keynote",
            "X-Title": "WCCCE Keynote Slide Editor",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    if "error" in result:
        raise RuntimeError(str(result["error"]))
    choices = result.get("choices") or []
    if not choices:
        raise RuntimeError("No choices in API response")
    text = _assistant_text(choices[0].get("message") or {})
    if not text:
        raise RuntimeError("Empty assistant message")
    return text


def suggest_slide_prompt(
    *,
    api_key: str,
    text_model: str,
    slide_title: str,
    slide_body: str,
    current_prompt: str = "",
    content_guide: str = "",
) -> str:
    """Ask an LLM for a content-only image prompt for one slide.

    The output describes WHAT the picture is — subject, scene, action,
    composition — and deliberately contains NO visual-style language.
    The deck's global visual style (medium, line quality, palette, mood,
    text-rendering rules, dimensions, etc.) lives in ``global_style.md``
    and is prepended at render time by :func:`compose_render_image_prompt`.
    Mixing styles into per-slide prompts causes the deck to drift.
    """
    system = (
        "You write concise CONTENT-ONLY image briefs for one keynote slide. "
        "Reply with ONLY the brief text: no title, no quotes, no markdown fences, no bullet wrapper. "
        "One or two short paragraphs, ~3-6 sentences total. "
        "Describe a single clear visual SCENE that illustrates the slide's idea: "
        "the subject(s), what they are doing, the setting/objects that matter, posture, "
        "and roughly where things sit in the frame. "
        "Strict prohibitions — DO NOT mention any visual style. That includes: "
        "art movements or genres (medieval, fantasy, cyberpunk, anime, XKCD, etc.); "
        "media or technique (line drawing, watercolor, oil, vector, 3D render, photo); "
        "color or palette (black-and-white, monochrome, vivid, pastel, sepia); "
        "lighting/mood adjectives (cinematic, dramatic, moody, whimsical); "
        "rendering quality phrases (highly detailed, photorealistic, hand-drawn); "
        "aspect ratio, resolution, camera, lens, or framing terminology. "
        "Do not reference the deck's global style file; assume style is applied separately. "
        "Do not invent on-image text, logos, captions, or UI."
    )
    body = (slide_body or "").strip()
    if len(body) > 8000:
        body = body[:8000] + "\n…(truncated)"

    user_parts: list[str] = []
    cg = (content_guide or "").strip()
    if cg:
        if len(cg) > 6000:
            cg = cg[:6000] + "\n…(truncated)"
        user_parts.extend(
            [
                "Overall keynote theme and content guidance (align the metaphor and subject matter with this — do NOT borrow style words from it):\n",
                cg,
                "\n\n",
            ]
        )
    user_parts.extend(
        [
            "Write a single content-only image brief for this slide.\n\n",
            "Slide title:\n",
            slide_title.strip(),
            "\n\nSlide content (speaker notes / body — illustrate these ideas):\n",
            body if body else "(no body text for this slide)",
        ]
    )
    if current_prompt.strip():
        user_parts.extend(
            [
                "\n\nCurrent image-brief draft (improve or replace if weak; strip any style language it contains):\n",
                current_prompt.strip(),
            ]
        )
    user_parts.append(
        "\n\nReturn ONLY the final content brief. "
        "Subject, action, setting, composition — no style, no medium, no palette, no lighting words."
    )
    user = "".join(user_parts)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    raw = openrouter_chat_text(api_key=api_key, model=text_model, messages=messages, timeout=120)
    return raw.strip().strip('"').strip("'")


def suggest_new_slide_content(
    *,
    api_key: str,
    text_model: str,
    user_request: str,
    content_guide: str = "",
    slide_context: str = "",
) -> dict:
    """
    Ask an LLM for slide title + body in a conversational tone.
    Returns ``{"title": str, "body": str}`` or raises.
    """
    system = (
        "You draft keynote slides from short requests. "
        "Return ONLY valid JSON with keys: title, body. "
        "The tone should feel conversational and speaker-friendly, not academic. "
        "Keep title concise and punchy. Keep body concise, with short paragraphs or bullets. "
        "Honor the overall keynote theme when provided. "
        "Use neighboring slide text only for continuity — do not copy it verbatim. "
        "Do not include markdown code fences."
    )
    chunks: list[str] = []
    cg = (content_guide or "").strip()
    if cg:
        if len(cg) > 6000:
            cg = cg[:6000] + "\n…(truncated)"
        chunks.append("Overall keynote theme and content guidance:\n" + cg)
    sc = (slide_context or "").strip()
    if sc:
        if len(sc) > 8000:
            sc = sc[:8000] + "\n…(truncated)"
        chunks.append("Neighboring slides (for tone and flow):\n" + sc)
    chunks.append("Create one new slide draft from this request.\n\nRequest:\n" + user_request.strip())
    chunks.append('Return JSON only:\n{"title":"...","body":"..."}')
    user = "\n\n---\n\n".join(chunks)
    raw = openrouter_chat_text(
        api_key=api_key,
        model=text_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        timeout=120,
    ).strip()

    payload = raw
    if not payload.startswith("{"):
        m = re.search(r"\{.*\}", payload, flags=re.DOTALL)
        if m:
            payload = m.group(0)
    try:
        obj = json.loads(payload)
    except json.JSONDecodeError as e:
        snippet = raw[:220].replace("\n", " ")
        raise RuntimeError(f"Could not parse slide draft JSON: {e}. Raw: {snippet}") from e
    if not isinstance(obj, dict):
        raise RuntimeError("Slide draft response is not a JSON object.")
    title = str(obj.get("title", "")).strip() or "New slide"
    body = str(obj.get("body", "")).strip()
    return {"title": title, "body": body}


def _format_neighbor_slide(slide: dict, *, max_body: int = 500) -> str:
    """Compact rendering of one neighbor slide for slide-edit context."""
    idx = slide.get("index")
    label = f"Slide {idx:02d}" if isinstance(idx, int) else "Slide"
    title = (slide.get("title") or "").strip() or "(untitled)"
    body = (slide.get("body") or "").strip()
    if len(body) > max_body:
        body = body[:max_body].rstrip() + " …(truncated)"
    if body:
        return f"### {label}: {title}\n{body}"
    return f"### {label}: {title}"


def compose_slide_edit_prompt(
    *,
    talk_title: str,
    talk_subtitle: str,
    content_guide: str,
    slide_index: int | None,
    slide_title: str,
    slide_body: str,
    user_request: str,
    prev_slides: list[dict] | None = None,
    next_slides: list[dict] | None = None,
) -> tuple[str, str]:
    """Build (system, user) messages for an LLM-driven slide-content edit.

    The image prompt is intentionally NOT included — this helper revises slide
    text only. ``prev_slides`` and ``next_slides`` are compact dicts
    (``{"index", "title", "body"}``) supplied for tone/flow continuity; they
    are truncated and included in a dedicated context section so the LLM does
    not duplicate or contradict adjacent slides. Returned as plain strings so
    callers (e.g. the editor's "Preview prompt" button) can show the speaker
    exactly what will be sent.
    """
    system = (
        "You revise the text of a single keynote slide based on the speaker's request. "
        "Return ONLY valid JSON with keys: title, body. "
        "Keep the slide grounded in the talk's stated purpose. "
        "Tone is conversational and speaker-friendly, not academic. "
        "Title is concise and punchy. Body is concise — short paragraphs and "
        "bullet lists are fine. Body uses lightweight markdown: section headings "
        "starting with '# ', '**bold**' for emphasis, and bullets with '- '. "
        "Surrounding slides are provided for context only — use them to keep tone, "
        "flow, and terminology consistent, but do not duplicate or paraphrase their content. "
        "Do not invent or modify the slide's image prompt. "
        "Do not wrap your reply in markdown code fences."
    )
    chunks: list[str] = ["# Talk purpose"]
    if talk_title.strip():
        chunks.append(f"Title: {talk_title.strip()}")
    if talk_subtitle.strip():
        chunks.append(f"Subtitle: {talk_subtitle.strip()}")
    cg = (content_guide or "").strip()
    if cg:
        if len(cg) > 6000:
            cg = cg[:6000] + "\n…(truncated)"
        chunks.append(f"Content guide:\n{cg}")

    label = f"Slide {slide_index:02d}" if slide_index is not None else "Slide"
    chunks.append(f"\n# Current slide ({label})")
    chunks.append(f"Title:\n{slide_title.strip() or '(empty)'}")
    body_text = slide_body.strip() or "(empty)"
    if len(body_text) > 8000:
        body_text = body_text[:8000] + "\n…(truncated)"
    chunks.append(f"\nBody (markdown):\n{body_text}")

    prev_list = prev_slides or []
    next_list = next_slides or []
    if prev_list or next_list:
        chunks.append("\n# Surrounding slides (context only — do NOT duplicate)")
        if prev_list:
            chunks.append("## Previous slides (in order)")
            for s in prev_list:
                chunks.append(_format_neighbor_slide(s))
        if next_list:
            chunks.append("## Next slides (in order)")
            for s in next_list:
                chunks.append(_format_neighbor_slide(s))

    chunks.append("\n# Speaker's edit request")
    chunks.append(user_request.strip() or "(no request — propose a small clarity improvement)")

    chunks.append("\n# Output")
    chunks.append('Return JSON only:\n{"title":"...","body":"..."}')
    user = "\n\n".join(chunks)
    return system, user


def suggest_slide_edit(
    *,
    api_key: str,
    text_model: str,
    talk_title: str,
    talk_subtitle: str,
    content_guide: str,
    slide_index: int | None,
    slide_title: str,
    slide_body: str,
    user_request: str,
    prev_slides: list[dict] | None = None,
    next_slides: list[dict] | None = None,
) -> dict:
    """Call the LLM to revise one slide's text. Returns ``{title, body}`` or raises.

    The slide's image prompt is deliberately not part of this round-trip.
    """
    system, user = compose_slide_edit_prompt(
        talk_title=talk_title,
        talk_subtitle=talk_subtitle,
        content_guide=content_guide,
        slide_index=slide_index,
        slide_title=slide_title,
        slide_body=slide_body,
        user_request=user_request,
        prev_slides=prev_slides,
        next_slides=next_slides,
    )
    raw = openrouter_chat_text(
        api_key=api_key,
        model=text_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        timeout=120,
    ).strip()

    payload = raw
    if not payload.startswith("{"):
        m = re.search(r"\{.*\}", payload, flags=re.DOTALL)
        if m:
            payload = m.group(0)
    try:
        obj = json.loads(payload)
    except json.JSONDecodeError as e:
        snippet = raw[:220].replace("\n", " ")
        raise RuntimeError(f"Could not parse slide edit JSON: {e}. Raw: {snippet}") from e
    if not isinstance(obj, dict):
        raise RuntimeError("Slide edit response is not a JSON object.")
    return {
        "title": str(obj.get("title", "")).strip(),
        "body": str(obj.get("body", "")).strip(),
    }


# ── Main pipeline ─────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate keynote slide images via OpenRouter (manifest-driven).",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=SCRIPT_DIR / "slide_images_manifest.json",
        help="Path to slide_images_manifest.json",
    )
    parser.add_argument(
        "--deck",
        type=Path,
        default=None,
        metavar="KEYNOTE.JSON",
        help="Batch-generate images from keynote.json (writes {id}.png, uses image_prompt)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print plan only")
    parser.add_argument("--force", action="store_true", help="Regenerate even if PNG exists")
    parser.add_argument("--model", type=str, default=None, help="Override model id")
    parser.add_argument(
        "--require-all-prompts",
        action="store_true",
        help="Exit with error if any slide has an empty prompt (before API calls)",
    )
    parser.add_argument(
        "--global-style",
        type=Path,
        default=None,
        metavar="FILE.md",
        help="Override global style markdown (default: manifest global_style_file or global_style.md)",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List suggested OpenRouter image models",
    )
    args = parser.parse_args()

    if args.list_models:
        for mid, desc in KNOWN_MODELS.items():
            tag = " [default]" if mid == DEFAULT_MODEL else ""
            print(f"  {mid:<50} {desc}{tag}")
        return

    if args.deck is not None:
        import keynote_deck as kd

        deck_path = args.deck.resolve()
        deck = kd.load_deck(deck_path)
        slides = deck.get("slides")
        if not isinstance(slides, list) or not slides:
            print('Error: deck must contain a non-empty "slides" array', file=sys.stderr)
            sys.exit(1)

        style_path = resolve_style_path(deck, args.global_style)
        style = load_global_style(style_path, deck)
        out_dir = SCRIPT_DIR / str(deck.get("output_directory", "slide_images"))
        w = int(deck.get("width", 1024))
        h = int(deck.get("height", 1024))
        model = args.model or deck.get("model") or DEFAULT_MODEL

        if args.require_all_prompts:
            missing = [i for i, s in enumerate(slides) if not str(s.get("image_prompt", s.get("prompt", ""))).strip()]
            if missing:
                print(f"Error: empty image_prompt for slide indices: {missing}", file=sys.stderr)
                sys.exit(1)

        api_key = load_api_key()
        if not api_key and not args.dry_run:
            print("Error: set OPENROUTER_API_KEY or add .env/OpenRouter.md", file=sys.stderr)
            sys.exit(1)

        if not args.dry_run:
            out_dir.mkdir(parents=True, exist_ok=True)

        print(f"Deck:    {deck_path}")
        print(f"Model:   {model}")
        print(f"Style:   {style_path}")
        print(f"Output:  {out_dir} ({w}x{h})\n")

        deck_content_guide = str(deck.get("content_guide", "")).strip()
        ok = skip = fail = 0
        for i, spec in enumerate(slides):
            if not isinstance(spec, dict):
                continue
            sid = str(spec.get("id", "")).strip()
            title = str(spec.get("title", f"slide-{i}"))
            slide_body = str(spec.get("body", ""))
            prompt = str(spec.get("image_prompt", spec.get("prompt", ""))).strip()
            if not sid:
                print(f"  [{i:02d}] SKIP (no id) — {title[:50]}", file=sys.stderr)
                skip += 1
                continue
            out_path = out_dir / f"{sid}.png"

            if not prompt:
                if args.dry_run:
                    print(f"  [{i:02d}] SKIP (empty image_prompt) — {title[:60]}")
                    skip += 1
                else:
                    print(f"  [{i:02d}] SKIP (empty image_prompt) — {title[:60]}")
                    skip += 1
                continue

            if args.dry_run:
                print(f"  [{i:02d}] {title[:55]}…")
                print(f"        → {out_path.name}")
                ok += 1
                continue

            if out_path.exists() and not args.force:
                print(f"  [{i:02d}] SKIP (exists) {out_path.name}")
                ok += 1
                continue

            print(f"  [{i:02d}] Generating… {title[:50]}", end=" ", flush=True)

            if generate_image_api(
                user_prompt=prompt,
                style_prompt=style,
                output_path=out_path,
                api_key=api_key,
                model=model,
                width=w,
                height=h,
                content_guide=deck_content_guide,
                slide_title=title,
                slide_body=slide_body,
            ):
                maybe_resize_png(out_path, w, h)
                print(f"OK → {out_path.name}")
                ok += 1
            else:
                print("FAILED")
                fail += 1

        print(f"\nDone: {ok} ok, {skip} skipped, {fail} failed")
        return

    manifest = load_manifest(args.manifest.resolve())

    model = args.model or manifest.get("model") or DEFAULT_MODEL
    w = int(manifest.get("width", 1024))
    h = int(manifest.get("height", 1024))
    style_path = resolve_style_path(manifest, args.global_style)
    style = load_global_style(style_path, manifest)
    out_dir = SCRIPT_DIR / manifest.get("output_directory", "slide_images")
    slides = manifest.get("slides")
    if not isinstance(slides, list) or not slides:
        print("Error: manifest must contain a non-empty \"slides\" array", file=sys.stderr)
        sys.exit(1)

    if args.require_all_prompts:
        missing = [i for i, s in enumerate(slides) if not str(s.get("prompt", "")).strip()]
        if missing:
            print(f"Error: empty prompt for slide indices: {missing}", file=sys.stderr)
            sys.exit(1)

    api_key = load_api_key()
    if not api_key and not args.dry_run:
        print("Error: set OPENROUTER_API_KEY or add .env/OpenRouter.md", file=sys.stderr)
        sys.exit(1)

    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Manifest: {args.manifest.resolve()}")
    print(f"Model:   {model}")
    print(f"Style:   {style_path}")
    print(f"Output:  {out_dir} ({w}x{h})\n")

    manifest_content_guide = str(manifest.get("content_guide", "")).strip()
    ok = skip = fail = 0
    for i, spec in enumerate(slides):
        title = spec.get("title", f"slide-{i}")
        slide_body = str(spec.get("body", ""))
        prompt = str(spec.get("prompt", "")).strip()
        out_path = out_dir / f"{i:02d}.png"

        if not prompt:
            if args.dry_run:
                print(f"  [{i:02d}] SKIP (empty prompt) — {title[:60]}")
                skip += 1
                continue
            print(f"  [{i:02d}] SKIP (empty prompt) — {title[:60]}")
            skip += 1
            continue

        if args.dry_run:
            print(f"  [{i:02d}] {title[:55]}…")
            print(f"        → {out_path.name}")
            ok += 1
            continue

        if out_path.exists() and not args.force:
            print(f"  [{i:02d}] SKIP (exists) {out_path.name}")
            ok += 1
            continue

        print(f"  [{i:02d}] Generating… {title[:50]}", end=" ", flush=True)

        if generate_image_api(
            user_prompt=prompt,
            style_prompt=style,
            output_path=out_path,
            api_key=api_key,
            model=model,
            width=w,
            height=h,
            content_guide=manifest_content_guide,
            slide_title=str(title),
            slide_body=slide_body,
        ):
            maybe_resize_png(out_path, w, h)
            print(f"OK → {out_path.name}")
            ok += 1
        else:
            print("FAILED")
            fail += 1

    print(f"\nDone: {ok} ok, {skip} skipped, {fail} failed")


if __name__ == "__main__":
    main()
