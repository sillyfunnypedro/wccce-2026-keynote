"""Property-based and edge-case tests for text field serialization helpers.

Tests cover round-trip integrity, serialization invariants, and idempotence
of _normalize_text_field and _serialize_text_field from keynote_deck.py.
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from keynote_deck import _normalize_text_field, _serialize_text_field


# ---------------------------------------------------------------------------
# 4.1  Round-trip: normalize(serialize(s)) == s  for arbitrary strings
# ---------------------------------------------------------------------------
# **Validates: Requirements 3.1, Property 1**


@given(s=st.text())
@settings(max_examples=300)
def test_round_trip_serialize_then_normalize(s: str) -> None:
    """Serializing a string to an array and normalizing back must recover
    the original string exactly."""
    assert _normalize_text_field(_serialize_text_field(s)) == s


# ---------------------------------------------------------------------------
# 4.2  Serialized arrays contain no newline characters in any element
# ---------------------------------------------------------------------------
# **Validates: Requirements 2.1, Property 3**


@given(s=st.text())
@settings(max_examples=300)
def test_serialized_elements_contain_no_newlines(s: str) -> None:
    """Every element produced by _serialize_text_field must be free of
    newline characters."""
    result = _serialize_text_field(s)
    assert isinstance(result, list)
    for element in result:
        assert isinstance(element, str)
        assert "\n" not in element, f"Newline found in serialized element: {element!r}"


# ---------------------------------------------------------------------------
# 4.3  Idempotence: normalizing twice equals normalizing once
# ---------------------------------------------------------------------------
# **Validates: Requirements 1.4, Property 2**


@given(s=st.text())
@settings(max_examples=300)
def test_normalize_idempotent_on_strings(s: str) -> None:
    """Normalizing a string value twice must yield the same result as
    normalizing once."""
    once = _normalize_text_field(s)
    twice = _normalize_text_field(once)
    assert once == twice


@given(items=st.lists(st.text(), max_size=50))
@settings(max_examples=300)
def test_normalize_idempotent_on_lists(items: list[str]) -> None:
    """Normalizing a list value twice must yield the same result as
    normalizing once."""
    once = _normalize_text_field(items)
    twice = _normalize_text_field(once)
    assert once == twice


# ---------------------------------------------------------------------------
# 4.4  Edge-case example tests
# ---------------------------------------------------------------------------
# **Validates: Requirements 1.1, 1.2, 1.3, 2.2, 3.2, 3.3**


class TestEdgeCases:
    """Concrete example tests for boundary conditions."""

    # -- empty string --
    def test_normalize_empty_string(self) -> None:
        assert _normalize_text_field("") == ""

    def test_serialize_empty_string(self) -> None:
        assert _serialize_text_field("") == []

    def test_round_trip_empty_string(self) -> None:
        assert _normalize_text_field(_serialize_text_field("")) == ""

    # -- None --
    def test_normalize_none(self) -> None:
        assert _normalize_text_field(None) == ""

    # -- empty array --
    def test_normalize_empty_array(self) -> None:
        assert _normalize_text_field([]) == ""

    # -- single-element array --
    def test_normalize_single_element_array(self) -> None:
        assert _normalize_text_field(["hello"]) == "hello"

    def test_serialize_single_line(self) -> None:
        assert _serialize_text_field("hello") == ["hello"]

    # -- trailing newlines --
    def test_round_trip_trailing_newline(self) -> None:
        s = "hello\n"
        assert _normalize_text_field(_serialize_text_field(s)) == s

    def test_round_trip_multiple_trailing_newlines(self) -> None:
        s = "hello\n\n\n"
        assert _normalize_text_field(_serialize_text_field(s)) == s

    def test_serialize_trailing_newline(self) -> None:
        assert _serialize_text_field("hello\n") == ["hello", ""]

    def test_serialize_multiple_trailing_newlines(self) -> None:
        assert _serialize_text_field("hello\n\n\n") == ["hello", "", "", ""]

    # -- whitespace-only lines --
    def test_round_trip_whitespace_only(self) -> None:
        s = "   \n  \n "
        assert _normalize_text_field(_serialize_text_field(s)) == s

    def test_normalize_whitespace_only_string(self) -> None:
        assert _normalize_text_field("   ") == "   "

    def test_normalize_whitespace_array(self) -> None:
        assert _normalize_text_field(["  ", " "]) == "  \n "

    # -- multi-line content --
    def test_round_trip_multiline(self) -> None:
        s = "# Title\n\n- bullet 1\n- bullet 2"
        assert _normalize_text_field(_serialize_text_field(s)) == s

    def test_serialize_multiline(self) -> None:
        assert _serialize_text_field("a\nb\nc") == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# 5.1  Integration: full deck round-trip (string → save → disk arrays → load)
# ---------------------------------------------------------------------------
# **Validates: Requirements 2.1, 2.4, 3.1, 3.2, 5.1**

import json
from pathlib import Path

from keynote_deck import default_deck_shell, load_deck, save_deck


def _make_slide(sid: str, markdown: str, body: str, title: str) -> dict:
    return {
        "id": sid,
        "kind": "content",
        "markdown": markdown,
        "body": body,
        "title": title,
        "image_prompt": "",
    }


def test_full_deck_round_trip_preserves_text(tmp_path: Path) -> None:
    """Create a deck with string-format text fields, save it, verify the
    on-disk JSON uses arrays, then reload and confirm all text is preserved."""
    slide_a = _make_slide(
        "aaa-111",
        markdown="# Intro\n\n- point one\n- point two",
        body="- point one\n- point two",
        title="Intro",
    )
    slide_b = _make_slide(
        "bbb-222",
        markdown="## Details\n\nSome paragraph.\n\nAnother paragraph.",
        body="Some paragraph.\n\nAnother paragraph.",
        title="Details",
    )
    slide_c = _make_slide(
        "ccc-333",
        markdown="",
        body="trailing newline\n",
        title="   whitespace   ",
    )

    deck = default_deck_shell({}, [slide_a, slide_b, slide_c])
    deck_path = tmp_path / "deck.json"

    # Save the deck
    save_deck(deck_path, deck)

    # Verify on-disk format uses arrays for text fields
    raw = json.loads(deck_path.read_text(encoding="utf-8"))
    for raw_slide in raw["slides"]:
        for field in ("markdown", "body", "title"):
            assert isinstance(raw_slide[field], list), (
                f"On-disk field '{field}' should be a list, got {type(raw_slide[field]).__name__}"
            )

    # Reload and verify all text content matches the originals
    reloaded = load_deck(deck_path)
    assert len(reloaded["slides"]) == 3

    for original, loaded in zip([slide_a, slide_b, slide_c], reloaded["slides"]):
        for field in ("markdown", "body", "title"):
            assert loaded[field] == original[field], (
                f"Round-trip mismatch for slide {original['id']!r} field {field!r}: "
                f"{loaded[field]!r} != {original[field]!r}"
            )
        # Non-text fields must also be preserved
        assert loaded["id"] == original["id"]
        assert loaded["kind"] == original["kind"]
        assert loaded["image_prompt"] == original["image_prompt"]


# ---------------------------------------------------------------------------
# 5.2  Integration: mixed-format deck (some array, some string) → load
# ---------------------------------------------------------------------------
# **Validates: Requirements 1.1, 1.2, 5.2**


def test_mixed_format_deck_normalizes_to_strings(tmp_path: Path) -> None:
    """Write a deck where some slides use array-format and others use
    string-format text fields. Load it and verify all fields are plain strings."""
    deck_data = {
        "version": 1,
        "frontmatter": {},
        "slides": [
            {
                "id": "slide-array",
                "kind": "content",
                "markdown": ["# Hello", "", "World"],
                "body": ["line1", "line2"],
                "title": ["Array Title"],
                "image_prompt": "",
            },
            {
                "id": "slide-string",
                "kind": "title",
                "markdown": "# Legacy\n\nOld format",
                "body": "old body",
                "title": "String Title",
                "image_prompt": "",
            },
            {
                "id": "slide-mixed",
                "kind": "content",
                "markdown": ["# Mixed", "array markdown"],
                "body": "string body in mixed slide",
                "title": ["Mixed Title"],
                "image_prompt": "",
            },
        ],
        "text_model": "test",
        "model": "test",
        "output_directory": "slide_images",
        "global_style_file": "global_style.md",
        "width": 1024,
        "height": 1024,
    }

    deck_path = tmp_path / "mixed.json"
    deck_path.write_text(json.dumps(deck_data, indent=2), encoding="utf-8")

    loaded = load_deck(deck_path)

    # All text fields must be plain strings after loading
    for slide in loaded["slides"]:
        for field in ("markdown", "body", "title"):
            assert isinstance(slide[field], str), (
                f"Slide {slide['id']!r} field {field!r} should be str, "
                f"got {type(slide[field]).__name__}"
            )

    # Verify specific expected values
    s0 = loaded["slides"][0]
    assert s0["markdown"] == "# Hello\n\nWorld"
    assert s0["body"] == "line1\nline2"
    assert s0["title"] == "Array Title"

    s1 = loaded["slides"][1]
    assert s1["markdown"] == "# Legacy\n\nOld format"
    assert s1["body"] == "old body"
    assert s1["title"] == "String Title"

    s2 = loaded["slides"][2]
    assert s2["markdown"] == "# Mixed\narray markdown"
    assert s2["body"] == "string body in mixed slide"
    assert s2["title"] == "Mixed Title"
