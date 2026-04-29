# Requirements Document

## Introduction

Remove all legacy migration code from the codebase to ship a clean v1. The project originally supported importing slides from markdown files and migrating numbered image filenames (`00.png`, `01.png`, …) to UUID-based filenames (`{slide_id}.png`). These migration paths are no longer needed — all decks now use the canonical `keynote.json` format with UUID-keyed images. This cleanup removes dead code, simplifies the public API surface, and eliminates confusing legacy references from documentation.

## Glossary

- **Deck**: The canonical slide data structure stored as `keynote.json`, containing a `slides[]` array with UUID-identified slide objects.
- **Keynote_Deck_Module**: The Python module `keynote_deck.py` that provides deck load/save operations and deck-level defaults.
- **Generate_Slides_Module**: The Python module `generate_slides.py` that builds PowerPoint files from a deck.
- **Generator_Module**: The Python module `generator.py` that provides image generation, LLM interaction, and global style loading.
- **Legacy_Import_Functions**: The functions `slides_chunks_from_markdown()`, `import_keynote_md_to_deck()`, and the CLI `import` subcommand that converted `keynote.md` files into `keynote.json` decks.
- **Legacy_Migration_Function**: The function `migrate_indexed_images_to_ids()` and the CLI `migrate-images` subcommand that copied numbered image files to UUID-named files.
- **Legacy_Image_Fallback**: The code path in `add_slide_image_column()` that tries `{slide_index:02d}.ext` filenames when no `{slide_id}.ext` image is found.
- **Legacy_Style_Fallback**: The code path in `load_global_style()` that reads `deck["style_prompt"]` when the style file is empty or missing.
- **UUID_Image_Convention**: The current convention where slide images are stored as `slide_images/{slide_id}.png`, keyed by the slide's UUID.

## Requirements

### Requirement 1: Remove Legacy Import Functions from Keynote_Deck_Module

**User Story:** As a maintainer, I want the markdown import functions removed from `keynote_deck.py`, so that the module only contains the canonical deck load/save API.

#### Acceptance Criteria

1. WHEN the Keynote_Deck_Module is loaded, THE Keynote_Deck_Module SHALL NOT define the function `slides_chunks_from_markdown`.
2. WHEN the Keynote_Deck_Module is loaded, THE Keynote_Deck_Module SHALL NOT define the function `import_keynote_md_to_deck`.
3. WHEN the Keynote_Deck_Module is loaded, THE Keynote_Deck_Module SHALL NOT import `keynote_slides_metadata`, `parse_frontmatter`, or `split_slides` from the Generator_Module.
4. WHEN the Keynote_Deck_Module is loaded, THE Keynote_Deck_Module SHALL NOT import the `uuid` module.
5. THE Keynote_Deck_Module SHALL continue to import `DEFAULT_MODEL` and `SCRIPT_DIR` from the Generator_Module.
6. THE Keynote_Deck_Module SHALL continue to provide the `default_deck_shell`, `load_deck`, `save_deck`, and `ensure_deck_defaults` functions with unchanged behavior.

### Requirement 2: Remove Legacy Migration Function from Keynote_Deck_Module

**User Story:** As a maintainer, I want the image migration function removed from `keynote_deck.py`, so that there is no dead code for converting numbered images to UUID filenames.

#### Acceptance Criteria

1. WHEN the Keynote_Deck_Module is loaded, THE Keynote_Deck_Module SHALL NOT define the function `migrate_indexed_images_to_ids`.
2. WHEN the Keynote_Deck_Module is loaded, THE Keynote_Deck_Module SHALL NOT import the `shutil` module.

### Requirement 3: Remove CLI Entry Point from Keynote_Deck_Module

**User Story:** As a maintainer, I want the CLI entry point removed from `keynote_deck.py`, so that the module is a pure library with no script behavior.

#### Acceptance Criteria

1. WHEN the Keynote_Deck_Module is loaded, THE Keynote_Deck_Module SHALL NOT define a `main` function.
2. WHEN the Keynote_Deck_Module is loaded, THE Keynote_Deck_Module SHALL NOT contain an `if __name__ == "__main__"` block.
3. WHEN the Keynote_Deck_Module is loaded, THE Keynote_Deck_Module SHALL NOT import the `argparse` module.
4. THE Keynote_Deck_Module module docstring SHALL NOT reference the `import` or `migrate-images` CLI commands.

### Requirement 4: Remove Legacy Image Fallback from Generate_Slides_Module

**User Story:** As a maintainer, I want the numbered-image fallback removed from `generate_slides.py`, so that image lookup uses only the UUID convention.

#### Acceptance Criteria

1. WHEN `add_slide_image_column` is called with a valid `slide_id`, THE Generate_Slides_Module SHALL look up images using only `{slide_id}.ext` filenames.
2. WHEN `add_slide_image_column` is called, THE Generate_Slides_Module SHALL NOT attempt to look up images using `{slide_index:02d}.ext` filenames.
3. WHEN no `{slide_id}.ext` image file exists, THE Generate_Slides_Module SHALL render a gray placeholder shape.
4. THE `add_slide_image_column` docstring SHALL describe only UUID-based image lookup.

### Requirement 5: Remove Legacy Style Fallback from Generator_Module

**User Story:** As a maintainer, I want the `style_prompt` fallback removed from `generator.py`, so that style loading uses only the style file or the built-in default.

#### Acceptance Criteria

1. WHEN the style file exists and contains text, THE Generator_Module `load_global_style` function SHALL return that text.
2. WHEN the style file is empty or missing, THE Generator_Module `load_global_style` function SHALL return `DEFAULT_STYLE_FALLBACK`.
3. WHEN the style file is empty or missing, THE Generator_Module `load_global_style` function SHALL NOT read `deck["style_prompt"]`.
4. THE `load_global_style` docstring SHALL NOT reference `style_prompt` or legacy fallback behavior.

### Requirement 6: Remove Legacy References from README

**User Story:** As a maintainer, I want all migration and legacy import references removed from the README, so that documentation reflects only the current v1 workflow.

#### Acceptance Criteria

1. THE README SHALL NOT contain the "Migrate numbered images to UUID filenames" section.
2. THE README SHALL NOT reference the `python keynote_deck.py import` command.
3. THE README SHALL NOT reference the `python keynote_deck.py migrate-images` command.
4. THE README SHALL NOT mention numbered image filenames (`00.png`, `01.png`, etc.) as a supported format.
5. THE README SHALL continue to document the `slide_images/{id}.png` UUID image convention.

### Requirement 7: No Remaining References to Removed Code

**User Story:** As a maintainer, I want to verify that no file in the codebase still references the removed functions or legacy patterns, so that the cleanup is complete.

#### Acceptance Criteria

1. WHEN a text search is performed across all Python files, THE codebase SHALL contain zero references to `slides_chunks_from_markdown`.
2. WHEN a text search is performed across all Python files, THE codebase SHALL contain zero references to `import_keynote_md_to_deck`.
3. WHEN a text search is performed across all Python files, THE codebase SHALL contain zero references to `migrate_indexed_images_to_ids`.
4. WHEN a text search is performed across all Python files, THE codebase SHALL contain zero call-site references to the removed `main` function in `keynote_deck.py`.
