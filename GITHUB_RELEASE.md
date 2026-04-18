# Darc's Visual Pickit V0.2.02

Build-Date: 2026-03-26T07:28:00-07:00

This release focuses on updater reliability and release safety. It keeps the `V0.2.00` project structure improvements, while adding stronger completion and timeout handling so the Update Center no longer gets stuck on `Checking for updates...` when a check fails or stalls.

## Highlights

- Fixed updater asset selection so it prefers the installer that matches the latest GitHub release version.
- Prevents stale attached installers from being chosen when a release has more than one `.exe` asset.
- Fixed the updater install handoff so `Download & Install` more reliably launches the installer after the app closes.
- Added fail-safe completion and timeout handling so update checks clear cleanly instead of leaving the Update Center stuck.
- Much faster rule browsing, paging, searching, and mode switching.
- Standard mode has been tuned heavily so it stays full-featured while feeling much more responsive.
- Performance mode and standard mode now switch more reliably without losing the visible entries.
- The updater has been expanded into a full Update Center instead of a simple prompt.
- Child windows now use the proper app icon more consistently.
- The project has been reorganized into a cleaner multi-file structure for easier maintenance and future updates.
- Internal release filenames are now stable, so future bumps only need the folder version and centralized metadata updated.

## What's Improved

- Improved updater robustness when GitHub releases contain multiple installer assets.
- Improved updater completion handling when a background check errors, hangs, or returns unexpectedly.
- Improved standard-mode responsiveness with lighter inactive cards, faster hydration, and card reuse across paging and searching.
- Improved performance-mode rendering and paging behavior for larger files.
- Reduced startup and render overhead across the editor.
- Reworked action handling in standard mode with a better active-card tools tray.
- Improved build and packaging flow with the one-folder release layout.

## Fixes

- Fixed a real updater bug where the app could launch an older attached installer instead of the installer matching the latest release version.
- Fixed a real updater issue where `Download & Install` could close the app without successfully handing off to the installer.
- Fixed the Update Center getting stuck on `Checking for updates...` instead of clearing to a real result or timeout.
- Fixed weird symbol/button fallback issues showing up in packaged builds.
- Fixed standard mode sometimes failing to show the full editable stats area correctly.
- Fixed switching from standard mode back to performance mode leaving the page empty or stale.
- Fixed paging cases where page 2 or later could show a blank screen even when entries existed.
- Fixed `Actions` / `Hide Tools` behavior so the tray actually appears and hides correctly.
- Fixed updater messaging so local builds newer than the published GitHub release are described correctly.
- Fixed child dialog windows more consistently using the app icon.

## Update Center

- Added a dedicated Update Center window.
- Shows current build, latest release, publish date, installer name, and release notes.
- Supports auto-check toggle and check interval settings.
- Supports `Check Now`, `Open Release Page`, `Skip This Version`, `Clear Skipped Version`, and `Download & Install`.

## Internal Refactor

- Split the old monolithic app into focused support modules for parser logic, runtime wiring, paging, compact UI, widgets, dialogs, and controller logic.
- Cleaned out old ghost wrappers, redundant patch chains, and versioned monkey-patch layers.
- Simplified the active runtime path so the live behavior is easier to reason about and maintain.

## Release Assets

- `DarcsVisualPickit-Setup-v0.2.02.exe`
- `DarcsVisualPickit.exe` in the one-folder build output

## Notes

- This version is packaged as a one-folder build for better startup behavior and easier asset handling.
- If you are updating from an older build, the installer is the recommended distribution path.
