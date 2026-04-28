# Design Document

## Overview

This feature creates a comprehensive `README.md` at the repository root and a `documentation_images/` directory for screenshots. The README is a pure documentation artifact — no application code changes are needed. The design focuses on document structure, image references, and the workflow for the user to capture screenshots.

## Architecture

### File Structure

```
repo-root/
├── README.md                          # New — the comprehensive README
├── documentation_images/              # New — screenshot directory
│   ├── editor-full-window.png         # Full editor window
│   ├── slide-card.png                 # Single slide card (title + body + thumbnail)
│   ├── content-editor.png             # Content editor panel (title, credits, body)
│   ├── image-prompt-buttons.png       # Image prompt area + action buttons
│   ├── presenter-with-image.png       # Presenter mode: markdown + image
│   ├── presenter-text-only.png        # Presenter mode: text-only (no image)
│   ├── presenter-credits.png          # Presenter mode: credits scrolling
│   └── toolbar.png                    # Top toolbar (deck path, models, credits timing, Present)
├── slide_editor.py                    # Existing — no changes
├── keynote.json                       # Existing — no changes
└── ...
```

### README Structure

The README will be organized into the following sections in order:

1. **Title and Badges** — Project name, one-line description
2. **Hero Screenshot** — Full editor window screenshot
3. **What Is This?** — Project overview, WCCCE 2026 context, conversational programming mention
4. **Quick Start** — Installation, API key setup, launch commands
5. **The Deck Format** — `keynote.json` structure, slide object fields, array-of-strings format, image path convention
6. **Editor Walkthrough** — Visual tour with screenshots of slide card, content editor, image prompt area, action buttons, toolbar
7. **Presenter Mode** — Keyboard shortcuts, font sizing, screenshots of image slide and text-only slide
8. **Image Generation** — OpenRouter workflow, global style, Suggest/Preview/Render pipeline, paste image, thumbnails
9. **Slide Management** — Insert, delete, reorder, autosave, external change detection
10. **Credits Slides** — Credits checkbox, scroll timing, presenter behavior, screenshot
11. **The Conversational Programming Story** — How the tool was built, methodology, WCCCE 2026 keynote context
12. **Forking and Customization** — New decks, custom styles, PowerPoint export
13. **License / Acknowledgments** — Brief closing

### Image References

All images will use relative markdown image syntax:

```markdown
![Description](documentation_images/filename.png)
```

### Screenshot Naming Convention

Screenshots use kebab-case descriptive names:
- `editor-full-window.png`
- `slide-card.png`
- `content-editor.png`
- `image-prompt-buttons.png`
- `presenter-with-image.png`
- `presenter-text-only.png`
- `presenter-credits.png`
- `toolbar.png`

### Content Approach

- **Code examples** use fenced markdown code blocks with language hints (`json`, `bash`, `python`)
- **Keyboard shortcuts** are presented in a markdown table
- **Action buttons** are described in a definition-list style (bold name followed by description)
- **JSON examples** show realistic but minimal snippets from the actual `keynote.json` structure
- **Tone** is warm and practical — matching the conversational programming theme of the keynote

## Design Decisions

### Why a `documentation_images/` directory instead of inline or external hosting?

The repository will be made public on GitHub. Relative image paths in a committed directory ensure screenshots render in the GitHub README viewer without external dependencies. The directory name is explicit and won't conflict with `slide_images/` (which holds generated slide art).

### Why user-captured screenshots instead of automated screenshots?

The Tk GUI requires a running display and the visual state depends on the actual keynote deck content. User-captured screenshots will show the real deck being used for the WCCCE 2026 presentation, making the README authentic rather than showing placeholder content.

### Why array-of-strings format in the JSON example?

The deck already uses the array-of-strings storage format (implemented in the `markdown-array-storage` spec). The README should document the current format, not the legacy string format.

## Correctness Properties

This feature produces documentation files only. Correctness is verified by:

1. All image references in README.md point to files that will exist in `documentation_images/` after the user completes screenshot tasks.
2. All CLI commands documented in the README match the actual `argparse` definitions in `slide_editor.py`.
3. All JSON field names documented match the actual `keynote.json` schema and `keynote_deck.py` constants.
4. All keyboard shortcuts documented match the actual key bindings in `PresentModeApp._bind_present_keys()`.

These are verified by manual review during task execution, not by automated tests (documentation content is not suitable for property-based testing).
