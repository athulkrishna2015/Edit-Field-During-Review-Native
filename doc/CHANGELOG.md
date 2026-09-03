# Changelog

All notable changes to **Edit Field During Review Native** are documented in this file.

## 7.4.6 - 2026-09-03

- **Config UI**: Added scroll areas to all config tabs (Settings, Support, Log) for better usability on small windows.
- **Config UI**: Added tooltips to all settings in the Settings, Support, and Log tabs for clearer documentation.
- **Config UI**: Fixed Log tab to fill the entire tab area with the log display.
- **Config UI**: Removed redundant explanatory text labels now that tooltips provide the documentation.

## 7.4.5 - 2026-09-03

- **Documentation**: Moved `CHANGELOG.md` from `addon/` to `doc/` to keep the addon package lean and exclude non-runtime files from the `.ankiaddon` build. Added `CHANGELOG.md` to `make_ankiaddon.py` exclusion list and referenced it in `doc/README.md`.

## 7.4.4 - 2026-09-03

- **Performance**: Optimized review screen card content loading speed. When pressing "Study Now" or moving between cards, the Add Cards window and card content are now preloaded proactively with reduced delays (50ms for AddCards, 100ms for card content), making the review experience feel snappier.
- **Refactored Preload Logic**: Added `on_reviewer_did_show_question` hook that triggers when a new question card is shown, canceling any pending editor preload and scheduling faster preloading of the Add Cards window and card content.
- **Throttled Reviewer Refresh**: Added a defer counter to `should_defer_reviewer_refresh` that limits consecutive deferrals (max 3), preventing unnecessary refresh suppression while editing.
- **New Methods**: Added `_preload_add_window_fast` and `_preload_card_content_fast` for faster content availability.

## 7.4.3 - 2026-09-02

- **Stability**: Hardened reviewer refresh and save-reload paths to recover cleanly when a card is deleted during editing or another refresh path hits a missing card.
- **Robustness**: Tightened editor bridge handling, config fallback logic, log signal initialization, and template wrapping safeguards to avoid avoidable runtime failures on newer Anki versions.

## 7.4.2 - 2026-08-18

- **Stability**: Fixed a crash when the card being edited is deleted during a note save (e.g., when changing card type removes the current card). The reviewer now detects the missing card and advances to the next card instead of raising a `NotFoundError`.

## 7.4.1 - 2026-06-26

- **Note Type Deck Fix**: Fixed an issue where changing the card or note type in the Add Cards window during review would trigger a deck change to the note type's default deck, resetting it from the currently reviewed card's deck.
- **Default Behavior Preservation**: Ensured Anki's default behavior for deck selection and note type changes is preserved when not in review mode (e.g., from the deck browser or overview screen).

## 7.4.0 - 2026-06-25

- **Preloading Add Cards**: Added a configuration option to preload the Add Cards window in the background, making it open instantaneously.
- **Deck Selection Preservation**: Fixed Anki defaulting to a preloaded deck on startup. The addon now preserves and restores the last opened deck when preloading in the background.
- **Smart Deck/Subdeck Selection**: Opening the Add Cards window from the deck browser list or deck overview screen now correctly selects the active deck or subdeck.

## 7.3.1 - 2026-05-18

- **Fix**: Resolved AttributeError regarding `addon_path` on older AddonManager versions.
- **Log Tab**: Added a "Copy" button to easily export logs for troubleshooting.
- **Stability**: Improved path resolution logic to be more cross-version compatible.

## 7.3.0 - 2026-05-18

- **Log Tab**: Added a dedicated Log tab in the configuration dialog for real-time activity tracking and easier troubleshooting.
- **Support Tab Auto-Open**: The Support tab now opens automatically once after an update to highlight new changes (respecting the "I have supported this addon" checkbox).
- **Live Updates**: Log entries now update in real-time as they are generated.
- **Image Fix**: Resolved an "Image not found" error that occurred when loading donation QR codes in certain installation environments.
- **Stability**: Refactored module loading and dynamic package resolution for better compatibility with development environments.
- **Compatibility**: Fixed compatibility with the AI-Hints add-on.

## 7.2.8 - 2026-04-10

- **Visual Fix**: Replaced the field box wrapper with a compliant standard HTML `<abbr>` tag to prevent the blue dashed editing outline from prematurely cutting off mid-sentence or failing to wrap block elements (like tables) when encountering stray HTML tags.
- **Unified Config Dialog**: The add-on's Config button now opens the same custom EFDRN Configuration dialog instead of showing a raw JSON editor.

## 7.2.6 - 2026-04-05

- **Crash Fix**: Resolved a `RuntimeError` regarding C++ object deletion when interacting with the hidden editor widget (e.g., jumping between cards or using the `N` shortcut).

## 7.2.5 - 2026-04-02

- **Crash Fix**: Resolved a `RuntimeError` that occurred when closing the profile, improving shutdown stability.

## 7.2.3 - 2026-04-02

- **Cloze Bug Fix**: Fixed a critical issue where Anki would incorrectly default to displaying Cloze 1 deletions for Cloze 2 and above when using the embedded editor.
- **Native Config GUI**: Enabled standard HTML-based configuration from Anki's Add-on manager through a new `config.md` fallback, while safely maintaining the advanced Qt GUI dialog.

## 7.2.1 - 2026-03-27

- Docs consolidation (removed FAQ, added Support tab assets).

## 7.2.0 - 2026-03-25

- Docs and known-issues updates.

## 7.1.3 - 2026-03-25

- Documentation updates.

## 7.1.2 - 2026-03-25

- Documentation and known-issues updates.

## 7.1.1 - 2026-03-25

- **Flicker Fix**: The embedded editor no longer causes the review screen to flicker or blank out while saving or redrawing the current card.
- **Review Screen Native Button**: Added an optional **Edit (N)** button and **N** shortcut on the review screen to open the embedded editor directly. The button is disabled by default and can be enabled in config.
- **Multiple Undo Styles**: Ctrl+Z now supports configurable undo behavior with three styles:
  - **Per-Field Revert** (default): reverts only the currently focused field
  - **Full Snapshot Revert**: reverts all fields to when editing started
  - **In-Editor Only**: standard Ctrl+Z in-editor undo
- **Enable/Disable Undo**: New "Enable Custom Undo (Ctrl+Z)" toggle in config (disabled by default). When enabled, Ctrl+Z uses the chosen style.
- **Config UI**: Undo Style dropdown in settings with descriptive help text.
- **Fixed No-Setup Editing**: Rendered reviewer fields are now auto-wrapped correctly, so Auto-enable works without manually adding `edit:` to templates.
- **Exclusions Hardened**: Disabled note types, templates, and fields now apply to explicit `{{edit:...}}` usage too, and exclusion settings survive renames by using stable internal IDs.
- **Toolbar Simplified**: The embedded editor now focuses on the native editing flow with **Done**, native undo/redo instead of a separate restore button.
- **Documentation Cleanup**: Updated the README, development notes, and config wording to match the current reviewer workflow.

## 7.1.0 - 2026-03-24

- **Eliminated Flicker**: The review screen now remains visible during the save transition, removing the "blank screen" jump when finishing an edit.
- **Image Occlusion Support**: Added review-screen support for opening the embedded editor on Image Occlusion cards.
- **Architectural Cleanup**: Refactored the internal code into specialized modules (`editor`, `utils`, `config`) for better stability and faster loading on newer Anki versions.
- **Added to Tools Menu**: Quick access to configuration via `Tools > EFDRN Configuration`.
- **README Refresh**: Updated installation info, screenshots, and repository links.

## 7.0.1 - 2026-03-23

- **Config Persistence Fix**: Configuration now resolves consistently through the base add-on name.
- **Empty Field Triggering**: Empty editable fields now expose a visible placeholder so they can still be clicked during review.
- **Undo/Redo Reliability**: Improved reviewer editing behavior and documentation around native undo/redo handling.

## 7.0.0 - 2026-03-23

- **Major Architectural Update**: Refactored to embed the native Anki editor.
- **Image Occlusion Support**: Ctrl+Click support and improved reliability.
- **UI Improvements**: Comprehensive configuration GUI and global field activation.
- Customizable trigger mechanism and performance optimizations.
- Isolated reviewer editor preferences and a support tab.
- Allow triggering the editor on empty fields via placeholder.
- Fix configuration persistence by using the base addon name.

## 6.23 - 2025-08-04

- Update bundled `ankiaddonconfig` library.

## 6.22 - 2025-04-20

- Add config option to disable autoplay after editing.

## 6.21 - 2024-11-16

- Ensure the reviewer is reloaded after a note is modified.
- Fix the previewer not refreshing when a note is modified too quickly.
- Replace optional chaining (`?.`) syntax for compatibility with older Anki/Chromium versions (Fixes #126).

## 6.20 - 2024-11-14

- Fix a compatibility issue with other add-ons caused by the custom `SemiEditor`.
- Make the previewer editable.

## 6.19 - 2024-08-28

- Support conditional replacements.

## 6.18 - 2024-01-03

- Update Note is fixed for Anki 23.10+ and remains compatible with 2.1.45+ (Closes #113, Fixes #107).

## 6.17 - 2023-11-01

- Fix Qt enum values (must be namespaced; direct value access no longer supported). Fixes #109, #110.
- Update `ankiaddonconfig`.

## 6.16 - 2023-10-09

- Escape field names when using them in regex.
- Don't use `ankiversion` (format changed in Anki 23.10); use try/except to check for valid APIs.

## 6.15 - 2023-07-31

- Update `ankiaddonconfig`: fix dropdown.

## 6.14 - 2023-07-11

- Update `ankiaddonconfig` to latest.

## 6.13 - 2022-06-27

- Serve the card at the end to improve rendering order.

## 6.12 - 2022-05-21

- Refactor HTML filtering into a dedicated `html-filter` module.
- Fix `wrapCloze` when the editable field is inside a shadow DOM.
- Update TypeScript files to Anki 2.1.53.

## 6.11 - 2022-02-09

- Use inline event handlers so editing still works on note types that modify card innerHTML (which removes previously attached listeners).
- Move JS code out of Python `showRawField`.
- Call `ctrlLinkEnable` only when `ctrl_click` is false.

## 6.10 - 2022-01-12

- Attach event listeners to EFDRC divs (fixes #63).
- Only send the `EFDRC!paste` signal when pasting non-plain-text or non-empty content.

## 6.9 - 2021-12-18

- Fix shortcuts not working when editing: listeners attached to `window` are no longer triggered by events bubbling from `contenteditable` elements.
- Update shortcut string parsing to use special characters.

## 6.8 - 2021-12-18

- Ignore key events while editing to avoid accidentally triggering shortcuts (fixes #44).
- Parse special characters in shortcuts and access PyQt enums through their enum type (Qt 6 compat).
- Make the "check every fields" button smaller.

## 6.7 - 2021-07-31

- Minor cleanup.

## 6.6 - 2021-07-31

- Anki 2.1.45 compatibility.
- Update `ankiaddonconfig` and reformat code with Black.

## 6.5 - 2021-07-30

- Fix a race condition with media (fixes #53).
- Fix an int/string version comparison bug.

## 6.4 - 2021-06-25

- Fix the version comparison methods and a debugging artifact.

## 6.3 - 2021-06-22

- Show a tutorial on first install.
- Improve the config fields tab aesthetics.

## 6.2 - 2021-04-27

- Support HTML text in config values.

## 6.1 - 2021-04-27

- Expose `registerShortcut`.
- Add `mypy.ini` for type checking.
- Declare a conflict with the original Edit Field During Review add-on in the manifest.

## 6.0 - 2021-04-05

- Require Anki v2.1.32+ (canonify/normalize done in Rust; null byte removed in `mungeHTML`).
- Add compatibility for updating from before v6.0.
- Use the manifest's `human_version` instead of a custom VERSION file.
