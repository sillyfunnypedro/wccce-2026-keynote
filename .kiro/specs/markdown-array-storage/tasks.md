# Tasks

## Task 1: Add text field conversion helpers to keynote_deck.py

- [x] 1.1 Add `TEXT_FIELDS` constant tuple `("markdown", "body", "title")` at module level
- [x] 1.2 Add `_normalize_text_field(value)` function that joins lists with newlines, passes strings through, and returns empty string for None/missing
- [x] 1.3 Add `_serialize_text_field(value)` function that splits strings on newlines, returning an empty list for empty strings

## Task 2: Modify load_deck() to normalize text fields

- [x] 2.1 Add normalization loop in `load_deck()` that iterates over all slides and calls `_normalize_text_field()` on each TEXT_FIELDS entry before `ensure_deck_defaults()` is called

## Task 3: Modify save_deck() to serialize text fields as arrays

- [x] 3.1 Update `save_deck()` to shallow-copy each slide dict and convert TEXT_FIELDS values using `_serialize_text_field()` before writing JSON, without mutating the in-memory deck

## Task 4: Write property-based tests for round-trip integrity

- [x] 4.1 Write a hypothesis property test verifying `_normalize_text_field(_serialize_text_field(s)) == s` for arbitrary strings
- [x] 4.2 Write a hypothesis property test verifying serialized arrays contain no newline characters in any element
- [x] 4.3 Write a hypothesis property test verifying `_normalize_text_field` is idempotent (normalizing twice equals normalizing once)
- [x] 4.4 Write example tests for edge cases: empty string, None, empty array, single-element array, trailing newlines, whitespace-only lines

## Task 5: Write integration test for full deck round-trip

- [x] 5.1 Write a test that creates a deck with string-format text fields, saves it, reloads it, and verifies all text content is preserved and the on-disk format uses arrays
- [x] 5.2 Write a test that creates a mixed-format deck (some slides array, some string), loads it, and verifies all fields are normalized to strings

## Task 6: Verify existing functionality is unaffected

- [x] 6.1 Run the PPTX export (`generate_slides.py`) against the converted deck and verify it produces output without errors
- [x] 6.2 Verify `slide_editor.py` imports and the deck load path work correctly with the new format
