# Requirements Document

## Introduction

The WCCCE 2026 keynote slide editor repository is being released publicly as part of a keynote lecture on conversational programming. The repository currently has no README. This feature creates a comprehensive, image-documented `README.md` that serves two purposes: (1) a practical user guide for anyone who discovers the repo, and (2) a showcase of the conversational programming methodology used to build the tool. Screenshots will be stored in a `documentation_images/` directory and captured by the user at specific points during the task workflow.

## Glossary

- **README**: The `README.md` file at the repository root that documents the project.
- **Documentation_Images**: The `documentation_images/` directory at the repository root that stores screenshot PNG files referenced by the README.
- **Slide_Editor**: The Tk-based GUI application (`slide_editor.py`) used to edit keynote decks.
- **Presenter_Mode**: The read-only fullscreen or windowed presentation view within `slide_editor.py` that displays slides with markdown and optional images.
- **Deck_Format**: The `keynote.json` file structure containing frontmatter, slides array, model configuration, and output paths.
- **Slide_Card**: The always-visible portion of a slide row in the editor showing the title, body preview, and image thumbnail.
- **Content_Editor**: The expandable right-column panel on each slide row containing title input, credits checkbox, and markdown body editor.
- **Image_Prompt_Area**: The text area below each slide card where the user writes or edits the image generation prompt.
- **Action_Buttons**: The 2×5 grid of buttons next to the image prompt area (Suggest, Image prompt, Preview render, Render, Paste image, Delete image, Present from here, Copy AI locator, Insert above, Delete).
- **Toolbar**: The top section of the editor window containing deck path, Browse, Reload, Save, Present buttons, model selectors, credits timing controls, and API key status.
- **Credits_Slide**: A slide with `credits: true` that scrolls markdown upward during presentation with configurable delay and speed.
- **OpenRouter_Integration**: The image generation pipeline that sends prompts to OpenRouter API models and saves rendered PNG images.

## Requirements

### Requirement 1: Project Overview Section

**User Story:** As a visitor finding this repo, I want to immediately understand what this project is and why it exists, so that I can decide whether it is relevant to me.

#### Acceptance Criteria

1. THE README SHALL contain a project overview section that identifies the tool as a keynote slide editor built for the WCCCE 2026 conference.
2. THE README SHALL explain that the tool was built using conversational programming methodology.
3. THE README SHALL include a screenshot of the full editor window in the overview section, referenced from Documentation_Images.
4. THE README SHALL list the core capabilities of the Slide_Editor: editing slides, generating images via AI, and presenting.

### Requirement 2: Installation and Setup Section

**User Story:** As a new user, I want clear setup instructions, so that I can get the editor running on my machine.

#### Acceptance Criteria

1. THE README SHALL list all Python package dependencies required to run the Slide_Editor (Pillow, python-pptx, and any others imported).
2. THE README SHALL document how to configure the OpenRouter API key using either the `OPENROUTER_API_KEY` environment variable or a key file in the `.env/` directory.
3. THE README SHALL provide the exact command to launch the editor: `python slide_editor.py --deck keynote.json`.
4. THE README SHALL provide the exact command to launch standalone presenter mode: `python slide_editor.py --present --deck keynote.json`.
5. THE README SHALL document optional CLI flags: `--present-windowed`, `--debug`, `--profile-startup`.

### Requirement 3: Deck Format Documentation Section

**User Story:** As a user who wants to hand-edit or create decks, I want to understand the JSON structure, so that I can work with `keynote.json` directly.

#### Acceptance Criteria

1. THE README SHALL document the top-level Deck_Format keys: `version`, `frontmatter`, `slides`, `text_model`, `model`, `output_directory`, `global_style_file`, `width`, `height`, `credits_start_delay_seconds`, `credits_scroll_pixels_per_second`.
2. THE README SHALL document the slide object fields: `id`, `kind`, `markdown`, `title`, `body`, `image_prompt`, `credits`.
3. THE README SHALL explain the array-of-strings text format where `markdown`, `title`, and `body` are stored as JSON arrays with one element per line.
4. THE README SHALL include a representative JSON code example showing a single slide object.
5. THE README SHALL explain that slide images are stored as `slide_images/{id}.png` so reordering slides in the JSON array does not break image references.

### Requirement 4: Editor UI Walkthrough Section

**User Story:** As a new user, I want a visual walkthrough of the editor interface, so that I can understand each part of the UI before using it.

#### Acceptance Criteria

1. THE README SHALL include a screenshot of a single Slide_Card showing the title preview, body preview, and image thumbnail, referenced from Documentation_Images.
2. THE README SHALL include a screenshot of the Content_Editor panel showing the title input, credits checkbox, and markdown body editor, referenced from Documentation_Images.
3. THE README SHALL include a screenshot of the Image_Prompt_Area and Action_Buttons, referenced from Documentation_Images.
4. THE README SHALL describe each Action_Button and its function: Suggest, Image prompt, Preview render, Render, Paste image, Delete image, Present from here, Copy AI locator, Insert above, Delete.
5. THE README SHALL include a screenshot of the Toolbar showing model selectors, credits timing controls, and Present button, referenced from Documentation_Images.

### Requirement 5: Presenter Mode Section

**User Story:** As a presenter, I want to understand how to use presentation mode and its keyboard shortcuts, so that I can deliver my talk smoothly.

#### Acceptance Criteria

1. THE README SHALL document all Presenter_Mode keyboard shortcuts: Left/PgUp (previous), Right/Space/PgDn (next), Home (first), End (last), F5 (reload from disk), Escape (exit fullscreen or quit), minus/plus (text size).
2. THE README SHALL include a screenshot of Presenter_Mode showing a slide with both markdown text and an image side by side, referenced from Documentation_Images.
3. THE README SHALL include a screenshot of Presenter_Mode showing a text-only slide with no image (full-width markdown), referenced from Documentation_Images.
4. THE README SHALL explain that font size is adjustable with minus/plus keys and persisted across sessions in `settings.json`.

### Requirement 6: Image Generation Section

**User Story:** As a user, I want to understand how AI image generation works in this tool, so that I can create and manage slide images.

#### Acceptance Criteria

1. THE README SHALL explain the image generation workflow: write prompt, optionally use Suggest for LLM-generated prompts, Preview render for a quick check, then Render for the final image.
2. THE README SHALL document that images are generated via OpenRouter_Integration using configurable models.
3. THE README SHALL explain the `global_style.md` file and its role in prepending style instructions to every image prompt.
4. THE README SHALL document the Paste image feature for importing images from the clipboard.
5. THE README SHALL explain that thumbnail caches are stored in `slide_images/.thumbs/` and regenerated automatically.

### Requirement 7: Slide Management Section

**User Story:** As a user, I want to understand how to add, remove, and reorder slides, so that I can build my deck.

#### Acceptance Criteria

1. THE README SHALL document how to insert a new slide using the Insert above button.
2. THE README SHALL document how to delete a slide using the Delete button.
3. THE README SHALL explain that slides can be reordered by editing the `slides[]` array in `keynote.json` directly, and that images remain linked by UUID.
4. THE README SHALL document the autosave behavior and the external-change detection that reloads the deck when modified outside the editor.

### Requirement 8: Credits Feature Section

**User Story:** As a user, I want to understand the credits slide feature, so that I can create scrolling credits for my presentation.

#### Acceptance Criteria

1. THE README SHALL explain how to enable credits on a slide by checking the credits checkbox in the Content_Editor or setting `credits: true` in JSON.
2. THE README SHALL document the credits scroll timing configuration: `credits_start_delay_seconds` and `credits_scroll_pixels_per_second` with their valid ranges.
3. THE README SHALL include a screenshot of Presenter_Mode showing a Credits_Slide with scrolling markdown, referenced from Documentation_Images.
4. THE README SHALL explain that credits slides display full-width markdown with no side image in Presenter_Mode.

### Requirement 9: Conversational Programming Story Section

**User Story:** As a conference attendee or curious developer, I want to understand how this tool was built using conversational programming, so that I can appreciate the methodology being demonstrated.

#### Acceptance Criteria

1. THE README SHALL contain a section explaining that the entire tool was built through conversational programming with AI assistants.
2. THE README SHALL describe the iterative development process: describing features in conversation, reviewing generated code, and refining through dialogue.
3. THE README SHALL position this repository as a companion artifact to the WCCCE 2026 keynote lecture.

### Requirement 10: Contributing and Forking Guidance Section

**User Story:** As a developer who wants to adapt this tool, I want guidance on how to fork and modify it, so that I can build my own slide editor.

#### Acceptance Criteria

1. THE README SHALL explain how to create a new deck by starting with a fresh `keynote.json` following the documented Deck_Format.
2. THE README SHALL explain how to customize the visual style by editing `global_style.md`.
3. THE README SHALL document the PowerPoint export capability via `generate_slides.py`.

### Requirement 11: Screenshot Capture Tasks

**User Story:** As the repository maintainer, I want specific screenshot capture instructions in the task plan, so that I can provide the exact images needed for the README.

#### Acceptance Criteria

1. THE task plan SHALL include a task for the user to capture a screenshot of the full Slide_Editor window and save it to Documentation_Images.
2. THE task plan SHALL include a task for the user to capture a screenshot of a single Slide_Card and save it to Documentation_Images.
3. THE task plan SHALL include a task for the user to capture a screenshot of the Content_Editor panel and save it to Documentation_Images.
4. THE task plan SHALL include a task for the user to capture a screenshot of the Image_Prompt_Area and Action_Buttons and save it to Documentation_Images.
5. THE task plan SHALL include a task for the user to capture a screenshot of Presenter_Mode with a slide image and save it to Documentation_Images.
6. THE task plan SHALL include a task for the user to capture a screenshot of Presenter_Mode showing credits scrolling and save it to Documentation_Images.
7. THE task plan SHALL include a task for the user to capture a screenshot of the Toolbar and save it to Documentation_Images.
8. THE task plan SHALL include a task for the user to capture a screenshot of a text-only slide in Presenter_Mode and save it to Documentation_Images.
