# Browser Automation Tools Usage Guidelines

This document provides rules for the OpenClaw agent planner on when and how to use the semantic browser tools.

## Session Management & Stateful Navigation
- All tools accept an optional `session` string key parameter (defaults to `'default'`).
- Using distinct session names (e.g. `'amazon'`, `'gmail'`) isolates cookies, session tokens, and localStorage. This allows you to stay signed in to multiple websites simultaneously.
- Always use `browser.close(session="...")` when a workflow is complete to release browser processes and save resources.

## Element Targeting (Visual IDs)
- All element-interacting tools (`click`, `type`, `clear`, `hover`, `select`, `upload_file`, `download_file`) accept a semantic `element_id` (e.g. `btn_login`, `lnk_categories`, `inp_search_products`) rather than raw CSS or XPath.
- The element IDs are generated dynamically by the extractor. Always consult the returned `PageState` or `StateDiff` to find the correct `element_id` before invoking an action on it.

## Available Tools List

1. **`browser.open`**
   - **Usage**: Starts the browser session (if offline) and loads the page URL.
   - **Parameters**: `url`, `session`.

2. **`browser.click`**
   - **Usage**: Click a button, link, checkbox, or option.
   - **Parameters**: `element_id`, `session`.

3. **`browser.type`**
   - **Usage**: Fill in input text boxes, search fields, textareas. Focuses and clears existing values automatically.
   - **Parameters**: `element_id`, `text`, `session`.

4. **`browser.clear`**
   - **Usage**: Wipe input values.
   - **Parameters**: `element_id`, `session`.

5. **`browser.hover`**
   - **Usage**: Hover mouse cursor focus to trigger hidden tooltips, dropdown flyouts, or interactive CSS menus.
   - **Parameters**: `element_id`, `session`.

6. **`browser.select`**
   - **Usage**: Choose value from select/dropdown lists.
   - **Parameters**: `element_id`, `value`, `session`.

7. **`browser.scroll`**
   - **Usage**: Scroll down to load infinite scroll items (products, posts) or scroll up to navigate home.
   - **Parameters**: `direction` ('up' or 'down'), `amount` (offset in pixels), `session`.

8. **`browser.wait`**
   - **Usage**: Wait a specific duration for loading, background sync, or transitions.
   - **Parameters**: `seconds`, `session`.

9. **`browser.back` / `browser.forward` / `browser.reload`**
   - **Usage**: Standard history navigation and refresh operations.
   - **Parameters**: `session`.

10. **`browser.upload_file`**
    - **Usage**: Upload local documents (e.g. resumes, photos, reports) to file input selectors.
    - **Parameters**: `element_id`, `file_path`, `session`.

11. **`browser.download_file`**
    - **Usage**: Clicks a download trigger (like a PDF link or export button) and blocks until the file has completed downloading locally.
    - **Parameters**: `element_id`, `output_dir` (local download folder), `session`.

12. **`browser.close`**
    - **Usage**: Closes the context of the named session.
    - **Parameters**: `session`.

---

## Stabilization & Guardrails
- **Auto-Stabilization**: You do NOT need to wait after click or type actions. The tool executor uses a MutationObserver to delay return until page changes settle.
- **Safety Reviews**: Click/submit actions containing high-risk keywords (e.g., place order, delete repo, pay) trigger a safety review, prompting the user for approval before continuing.
