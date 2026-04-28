# Tasks

## Task 1: Create documentation_images directory and README skeleton

- [x] 1.1 Create the `documentation_images/` directory with a `.gitkeep` file so it is tracked by git before screenshots are added.
- [x] 1.2 Create `README.md` at the repository root with the title, one-line description, and placeholder section headers for all sections defined in the design document.
- [x] 1.3 Add `documentation_images/` to the project (ensure it is NOT in `.gitignore`).

## Task 2: Write the Project Overview and Quick Start sections

- [x] 2.1 Write the "What Is This?" section: identify the project as a WCCCE 2026 keynote slide editor built with conversational programming, list core capabilities (editing, AI image generation, presenting), and include an image reference to `documentation_images/editor-full-window.png`.
- [x] 2.2 Write the "Quick Start" section: Python 3 requirement, `pip install` command for dependencies (Pillow, python-pptx), API key setup (environment variable `OPENROUTER_API_KEY` or `.env/OpenRouter.md` key file), launch commands (`python slide_editor.py --deck keynote.json` and `python slide_editor.py --present --deck keynote.json`), and optional CLI flags (`--present-windowed`, `--debug`, `--profile-startup`).

## Task 3: Write the Deck Format section

- [x] 3.1 Document the top-level `keynote.json` keys: `version`, `frontmatter` (title, subtitle, author, footer), `slides[]`, `text_model`, `model`, `output_directory`, `global_style_file`, `width`, `height`, `credits_start_delay_seconds`, `credits_scroll_pixels_per_second`.
- [x] 3.2 Document the slide object fields: `id` (UUID), `kind` (content/title/quote), `markdown`, `title`, `body`, `image_prompt`, `credits` (boolean). Explain the array-of-strings storage format for text fields.
- [x] 3.3 Include a JSON code example showing a representative slide object with array-of-strings text fields.
- [x] 3.4 Explain the image path convention: images stored as `slide_images/{id}.png`, so reordering the `slides[]` array does not break image references.

## Task 4: Write the Editor UI Walkthrough section

- [x] 4.1 Write an introduction to the editor layout and include an image reference to `documentation_images/slide-card.png` with a description of the slide card components (title preview, markdown body preview, image thumbnail).
- [x] 4.2 Describe the Content Editor panel and include an image reference to `documentation_images/content-editor.png`. Cover the title input, credits checkbox, and markdown body editor.
- [x] 4.3 Describe the Image Prompt area and Action Buttons, include an image reference to `documentation_images/image-prompt-buttons.png`. Document each button: Suggest (LLM edit of slide content), Image prompt (LLM-generated image prompt), Preview render (quick render check), Render (final image generation), Paste image (clipboard import), Delete image (remove slide image), Present from here (open presenter at this slide), Copy AI locator (copy slide context for AI tools), Insert above (add new slide), Delete (remove slide).
- [x] 4.4 Describe the Toolbar and include an image reference to `documentation_images/toolbar.png`. Cover: deck path and Browse/Reload/Save buttons, Present button, text model selector (for Suggest), image model selector (for Render), API key status indicator, credits roll timing controls (delay and speed).

## Task 5: Write the Presenter Mode section

- [x] 5.1 Write the Presenter Mode section introduction explaining the two layouts: markdown + image side-by-side (for slides with images) and full-width markdown (for text-only or credits slides).
- [x] 5.2 Include a keyboard shortcuts table: Left/PgUp/Up → previous, Right/Space/PgDn/Down → next, Home → first slide, End → last slide, F5 → reload from disk, Escape → exit fullscreen or quit, minus/plus → adjust text size.
- [x] 5.3 Include image references to `documentation_images/presenter-with-image.png` and `documentation_images/presenter-text-only.png` with descriptions.
- [x] 5.4 Document font size adjustment (minus/plus keys, persisted in `settings.json`) and the reload-from-disk feature (F5 to pick up external edits without restarting).

## Task 6: Write the Image Generation and Slide Management sections

- [x] 6.1 Write the "Image Generation" section: explain the workflow (write prompt → Suggest for LLM help → Preview render → Render), OpenRouter integration, configurable models, `global_style.md` role, paste image from clipboard, and thumbnail cache in `slide_images/.thumbs/`.
- [x] 6.2 Write the "Slide Management" section: Insert above button, Delete button, reordering by editing `slides[]` in JSON (images stay linked by UUID), autosave behavior, and external change detection (editor reloads when `keynote.json` is modified by another tool).

## Task 7: Write the Credits, Story, and Forking sections

- [x] 7.1 Write the "Credits Slides" section: enabling credits (`credits: true` or checkbox), scroll timing configuration (`credits_start_delay_seconds` range 0–60, `credits_scroll_pixels_per_second` range 5–500), presenter behavior (full-width markdown, auto-scroll after delay). Include image reference to `documentation_images/presenter-credits.png`.
- [x] 7.2 Write the "The Conversational Programming Story" section: explain that the tool was built entirely through conversational programming with AI assistants, describe the iterative process (describe features → review code → refine through dialogue), position the repo as a companion artifact to the WCCCE 2026 keynote.
- [x] 7.3 Write the "Forking and Customization" section: creating a new deck (fresh `keynote.json`), customizing visual style (`global_style.md`), PowerPoint export (`python generate_slides.py`), and the `keynote_deck.py` CLI for importing markdown and migrating images.

## Task 8: User screenshot capture tasks

- [x] 8.1 **USER ACTION**: Launch the editor (`python slide_editor.py --deck keynote.json`), capture a screenshot of the full editor window showing multiple slide cards, and save it as `documentation_images/editor-full-window.png`.
- [x] 8.2 **USER ACTION**: In the editor, capture a screenshot of a single slide card showing the title preview, markdown body preview, and image thumbnail on the right, and save it as `documentation_images/slide-card.png`.
- [x] 8.3 **USER ACTION**: Click on a slide card to expand the content editor. Capture a screenshot of the Content Editor panel showing the title input field, credits checkbox, and markdown body editor, and save it as `documentation_images/content-editor.png`.
- [x] 8.4 **USER ACTION**: With a slide's editor expanded, capture a screenshot of the image prompt text area and the 2×5 action button grid (Suggest, Image prompt, Preview render, Render, Paste image, Delete image, Present from here, Copy AI locator, Insert above, Delete), and save it as `documentation_images/image-prompt-buttons.png`.
- [x] 8.5 **USER ACTION**: Open Presenter Mode (click Present or run `python slide_editor.py --present --deck keynote.json`). Navigate to a slide that has a generated image. Capture a screenshot showing the markdown text on the left and the image on the right, and save it as `documentation_images/presenter-with-image.png`.
- [x] 8.6 **USER ACTION**: In Presenter Mode, navigate to a slide that has no image (or a text-only slide). Capture a screenshot showing the full-width markdown layout, and save it as `documentation_images/presenter-text-only.png`.
- [x] 8.7 **USER ACTION**: In Presenter Mode, navigate to the credits slide (the one with `credits: true`). Wait for the scroll animation to begin, then capture a screenshot showing the credits text mid-scroll, and save it as `documentation_images/presenter-credits.png`.
- [x] 8.8 **USER ACTION**: In the editor, capture a screenshot of just the top toolbar area showing the deck path, Browse/Reload/Save/Present buttons, model selector fields, API key status, and credits timing controls, and save it as `documentation_images/toolbar.png`.

## Task 9: Final review and polish

- [x] 9.1 Review all image references in `README.md` to confirm they match the filenames in `documentation_images/`.
- [x] 9.2 Verify all CLI commands in the README match the actual `argparse` definitions in `slide_editor.py`.
- [x] 9.3 Verify all JSON field names match the actual `keynote.json` structure and `keynote_deck.py` constants.
- [x] 9.4 Verify all keyboard shortcuts match the bindings in `PresentModeApp._bind_present_keys()`.
- [x] 9.5 Read through the full README for tone, flow, and completeness. Ensure it works as both a user guide and a showcase of conversational programming.
