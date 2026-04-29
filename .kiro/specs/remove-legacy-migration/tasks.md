# Tasks

## Task 1: Clean up keynote_deck.py

- [x] 1.1 Remove unused imports: `import argparse`, `import shutil`, `import uuid`, and remove `keynote_slides_metadata`, `parse_frontmatter`, `split_slides` from the `from generator import (...)` statement (keep `DEFAULT_MODEL` and `SCRIPT_DIR`)
- [x] 1.2 Update the module docstring to remove the two CLI usage lines (`python keynote_deck.py import ...` and `python keynote_deck.py migrate-images ...`)
- [x] 1.3 Remove the `slides_chunks_from_markdown()` function
- [x] 1.4 Remove the `import_keynote_md_to_deck()` function
- [x] 1.5 Remove the `migrate_indexed_images_to_ids()` function
- [x] 1.6 Remove the `main()` function and the `if __name__ == "__main__":` block

## Task 2: Clean up generate_slides.py

- [x] 2.1 In `add_slide_image_column()`, remove the legacy `{slide_index:02d}.ext` fallback loop — keep only the `{slide_id}.ext` lookup
- [x] 2.2 Update the `add_slide_image_column()` docstring to describe only UUID-based image lookup
- [x] 2.3 Update the module-level docstring to remove the `00.png`, `01.png` fallback mention
- [x] 2.4 Update the `--images` argparse help text to remove the "else 00.png …" reference

## Task 3: Clean up generator.py

- [x] 3.1 In `load_global_style()`, remove the `style_prompt` legacy fallback block (the block that reads `deck.get("style_prompt")`)
- [x] 3.2 Update the `load_global_style()` docstring to remove the `style_prompt` legacy reference

## Task 4: Clean up README.md

- [x] 4.1 Remove the "Migrate numbered images to UUID filenames" subsection (heading, description, and code block)
- [x] 4.2 Remove the `python keynote_deck.py import` paragraph and code block from the "Create a new deck" section
- [x] 4.3 Update the `--images` help text description if it mentions numbered fallback

## Task 5: Verification and testing

- [x] 5.1 Verify `keynote_deck.py` has no syntax errors and the module imports cleanly
- [-] 5.2 Verify `load_deck()` and `save_deck()` round-trip works: load `keynote.json`, save to a temp file, load again, and confirm equivalence
- [ ] 5.3 Verify `generate_slides.py` has no syntax errors and can generate a PPTX from the existing deck
- [ ] 5.4 Verify `generator.py` has no syntax errors and `load_global_style()` returns the style file content (or fallback) without reading `style_prompt`
- [ ] 5.5 Grep all `.py` files for references to `slides_chunks_from_markdown`, `import_keynote_md_to_deck`, `migrate_indexed_images_to_ids`, and the removed `main` in `keynote_deck.py` — confirm zero matches
- [ ] 5.6 Verify README.md contains no references to `keynote_deck.py import`, `migrate-images`, or numbered image format as a supported workflow
