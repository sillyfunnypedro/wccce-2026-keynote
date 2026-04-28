# Requirements Document

## Introduction

The keynote slide deck editor stores slide text fields (`markdown`, `body`, `title`) as single strings with embedded `\n` characters in `keynote.json`. This makes hand-editing the JSON file difficult because multi-line content appears as one long escaped string. This feature changes the JSON storage format so that these text fields are stored as arrays of strings (one element per line), while keeping the in-memory representation as plain newline-joined strings for all consuming code.

## Glossary

- **Deck_Loader**: The module (`keynote_deck.py`) responsible for reading `keynote.json` from disk and returning an in-memory deck dictionary.
- **Deck_Saver**: The module (`keynote_deck.py`) responsible for writing the in-memory deck dictionary back to `keynote.json` on disk.
- **Text_Field**: Any of the `markdown`, `body`, or `title` fields on a slide object in the deck.
- **Array_Format**: A JSON array of strings where each element represents one line of text (no embedded newline characters within elements).
- **String_Format**: The legacy format where a text field is a single JSON string with embedded `\n` characters representing line breaks.
- **Slide_Editor**: The Tk-based GUI application (`slide_editor.py`) that reads and writes slide content.
- **PPTX_Exporter**: The PowerPoint export module (`generate_slides.py`) that reads slide markdown to produce `.pptx` files.
- **LLM_Generator**: The module (`generator.py`) that produces text content via LLM API calls and writes results back to the deck.

## Requirements

### Requirement 1: Normalize Text Fields on Load

**User Story:** As a developer, I want the deck loader to accept both array and string formats for text fields, so that existing decks continue to work without manual migration.

#### Acceptance Criteria

1. WHEN a Text_Field value is a JSON array of strings, THE Deck_Loader SHALL join the array elements with newline characters and return the result as a single string.
2. WHEN a Text_Field value is a JSON string, THE Deck_Loader SHALL return it unchanged as a single string.
3. WHEN a Text_Field value is null or missing, THE Deck_Loader SHALL return an empty string.
4. FOR ALL valid deck files, loading then accessing a Text_Field SHALL yield a plain Python string regardless of the on-disk format (round-trip normalization property).

### Requirement 2: Serialize Text Fields as Arrays on Save

**User Story:** As a user who hand-edits JSON, I want text fields saved as arrays of strings (one line per element), so that I can read and modify slide content directly in a text editor.

#### Acceptance Criteria

1. WHEN the Deck_Saver writes a Text_Field to disk, THE Deck_Saver SHALL split the string on newline characters and write the result as a JSON array of strings.
2. WHEN a Text_Field is an empty string, THE Deck_Saver SHALL write it as an empty JSON array `[]`.
3. WHEN a Text_Field contains a single line with no newline, THE Deck_Saver SHALL write it as a JSON array with one element.
4. THE Deck_Saver SHALL produce Array_Format for the `markdown`, `body`, and `title` fields of every slide in the `slides[]` array.

### Requirement 3: Round-Trip Integrity

**User Story:** As a developer, I want loading and saving a deck to preserve all text content exactly, so that no data is lost during format conversion.

#### Acceptance Criteria

1. FOR ALL Text_Field values, loading a deck then saving it SHALL produce a file that, when loaded again, yields identical in-memory string values (round-trip property).
2. WHEN a Text_Field contains trailing newlines or empty lines, THE Deck_Loader and Deck_Saver SHALL preserve them through the round-trip.
3. WHEN a Text_Field contains only whitespace lines, THE Deck_Loader and Deck_Saver SHALL preserve the exact whitespace content through the round-trip.

### Requirement 4: Transparent Consumption by Downstream Modules

**User Story:** As a developer, I want the format change to be invisible to the slide editor, PPTX exporter, and LLM generator, so that no changes are needed in those modules.

#### Acceptance Criteria

1. THE Slide_Editor SHALL continue to read and write Text_Field values as plain strings without modification.
2. THE PPTX_Exporter SHALL continue to receive Text_Field values as plain strings from the loaded deck.
3. THE LLM_Generator SHALL continue to receive and produce Text_Field values as plain strings.
4. IF a downstream module writes a plain string to a Text_Field in memory, THEN THE Deck_Saver SHALL convert it to Array_Format when persisting.

### Requirement 5: Migration of Existing Decks

**User Story:** As a user with an existing `keynote.json` in string format, I want the first save operation to automatically convert all text fields to array format, so that I do not need a separate migration step.

#### Acceptance Criteria

1. WHEN an existing deck in String_Format is loaded and then saved, THE Deck_Saver SHALL write all Text_Field values in Array_Format.
2. THE Deck_Loader SHALL handle a mixed deck where some slides use Array_Format and others use String_Format within the same file.
3. WHEN migration occurs, THE Deck_Saver SHALL not alter any non-text-field data in the deck (frontmatter, ids, image_prompt, credits, models, paths).
