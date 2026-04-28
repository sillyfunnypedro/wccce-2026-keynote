# Design Document

## Overview

This design introduces a transparent serialization layer in `keynote_deck.py` that converts text fields between their on-disk array format and their in-memory string format. The conversion happens at the boundary (load/save) so that all consuming code continues to work with plain strings unchanged.

## Architecture

### Approach: Boundary Conversion in keynote_deck.py

The conversion logic lives entirely in `keynote_deck.py`, specifically in `load_deck()` and `save_deck()`. No other module needs modification.

```
┌─────────────────────────────────────────────────────────┐
│                    keynote.json (disk)                    │
│  "markdown": ["# Title", "", "- bullet 1", "- bullet 2"]│
│  "body": ["- bullet 1", "- bullet 2"]                   │
│  "title": ["My Title"]                                   │
└────────────────────────┬────────────────────────────────┘
                         │
              load_deck() normalizes
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  In-memory deck (dict)                    │
│  "markdown": "# Title\n\n- bullet 1\n- bullet 2"        │
│  "body": "- bullet 1\n- bullet 2"                        │
│  "title": "My Title"                                     │
└────────────────────────┬────────────────────────────────┘
                         │
           save_deck() converts to arrays
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                    keynote.json (disk)                    │
│  "markdown": ["# Title", "", "- bullet 1", "- bullet 2"]│
└─────────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **Conversion at boundary only** — `load_deck()` normalizes arrays to strings; `save_deck()` converts strings to arrays. All other code is unaware of the format change.

2. **Fields affected** — Only `markdown`, `body`, and `title` on each slide. Other string fields (`image_prompt`, `id`, `kind`) remain as plain strings.

3. **Backward compatibility** — `load_deck()` accepts both formats (string or array) for each field independently. A mixed-format file is valid.

4. **Empty string handling** — An empty string serializes to `[]` (empty array). On load, an empty array becomes `""`.

5. **No separate migration command** — The first `save_deck()` call after loading a legacy file automatically converts it.

## Detailed Design

### New Helper Functions

```python
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
```

### Modified `load_deck()`

After loading the JSON and before returning, iterate over all slides and normalize text fields:

```python
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
```

### Modified `save_deck()`

Before writing JSON, convert text fields to arrays:

```python
def save_deck(path: Path, deck: dict) -> None:
    # Deep-copy slides to avoid mutating the in-memory deck
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
```

### Impact on Other Modules

| Module | Change Required | Reason |
|--------|----------------|--------|
| `keynote_deck.py` | Yes — add helpers, modify load/save | Core of the feature |
| `slide_editor.py` | No | Reads/writes strings via `load_deck()`/`save_deck()` |
| `generator.py` | No | Reads slide fields as strings from loaded deck |
| `generate_slides.py` | No | Reads `spec.get("markdown")` as string from loaded deck |

### Edge Cases

- **Empty array `[]`** → loads as `""` → saves as `[]`
- **Array with one empty string `[""]`** → loads as `""` → saves as `[]` (minor normalization: single empty string collapses to empty)
- **String with trailing newline `"hello\n"`** → saves as `["hello", ""]` → loads as `"hello\n"` ✓
- **Array with non-string elements** → `_normalize_text_field` coerces each element via `str()`

## Correctness Properties

### Property 1: Round-Trip Preservation (serialize then normalize)

For any arbitrary string `s`:
```
_normalize_text_field(_serialize_text_field(s)) == s
```

This ensures no data loss through the save→load cycle.

### Property 2: Normalize Idempotence

For any value `v` that is either a string or list of strings:
```
_normalize_text_field(_normalize_text_field(v)) == _normalize_text_field(v)
```

Once normalized, re-normalizing produces the same result.

### Property 3: Serialize Produces Valid Array

For any string `s`:
```
isinstance(_serialize_text_field(s), list)
all(isinstance(item, str) for item in _serialize_text_field(s))
"\n" not in item for all items in _serialize_text_field(s)
```

No element in the serialized array contains a newline character.

### Property 4: Non-Text Fields Invariant

For any deck dict `d` with slides:
```
save then load preserves all non-text-field values exactly
(id, kind, image_prompt, credits, frontmatter, version, models, paths)
```

### Property 5: Load Always Returns Strings

For any valid on-disk slide (with text fields as arrays or strings):
```
isinstance(loaded_slide["markdown"], str)
isinstance(loaded_slide["body"], str)
isinstance(loaded_slide["title"], str)
```

## Testing Strategy

- **Property-based tests** using `hypothesis` for round-trip, idempotence, and array validity properties
- **Example-based tests** for edge cases (empty strings, None values, mixed-format decks)
- **Integration test** loading the actual `keynote.json`, saving to a temp file, reloading, and verifying content equality
