# Darc's Visual Pickit

A modern, visual Graphical User Interface (GUI) for editing and managing Diablo NIP (Pickit) files. Built with Python and CustomTkinter, this tool replaces tedious text-editing with an interactive, visually distinct card-based system.

## 🌟 Key Features

* **Visual Rule Cards:** Items are represented as distinct, collapsible cards with quality-based color coding.
* **Stat & Skill Libraries:** Easily search and append attributes and skills using built-in, searchable catalogs.
* **Live Syntax Checking:** Automatically detects unbalanced brackets, missing operators, and invalid formatting to prevent bot errors.
* **Auto-Backup System:** Safely archives your `.nip` files before saving, with configurable retention limits.
* **Rapid Templating:** Generate standard rules for High Runes, Caster Basics, Rares, and more with a single click.
* **Custom Keybinds:** Fully map application actions to your preferred keyboard shortcuts.
* **Segmented Loading:** Optimized background loading ensures the UI remains highly responsive even with massive `.nip` files.
* **Update Center:** Built-in updater checks GitHub releases and handles download and installation automatically.

## 🛠️ Installation & Usage

### Option 1 — Installer (Recommended)

Download the latest `DarcsVisualPickit-Setup-*.exe` from the [Releases page](https://github.com/KolbotForever/darcs-visual-pickit/releases) and run it.

### Option 2 — Portable EXE

Download `DarcsVisualPickit.exe` from the latest release and run it directly — no installation required.

### Option 3 — Running from Source

#### Prerequisites
* Python 3.10+
* `customtkinter`
* `Pillow`

1. Clone the repository:
   ```bash
   git clone https://github.com/Kolbotforever/darcs-visual-pickit.git
   cd darcs-visual-pickit
   ```

2. Install dependencies:
   ```bash
   pip install customtkinter Pillow
   ```

3. Launch the app:
   ```bash
   python app_main.py
   ```

## 🔄 Auto-Updater

Darc's Visual Pickit includes a built-in **Update Center** that checks GitHub releases automatically at startup.

* On launch the app silently checks for a newer release (at most once per 24 hours by default).
* If an update is found, the **Update Center** window opens automatically.
* Click **Download & Install** to download the latest installer and launch it. The app will close itself so the installer can run cleanly.
* After installation completes the app relaunches automatically.

### Updater Troubleshooting

| Symptom | Solution |
|---|---|
| Update Center stays on "Checking for updates..." | The check will time out automatically after 20 seconds. Click **Check Now** to retry. |
| "Download & Install" shows "Launch Failed" | Download the installer manually from the [Releases page](https://github.com/KolbotForever/darcs-visual-pickit/releases) and run it. |
| App did not close after clicking OK on "Updater Started" | Close the app manually — the installer is already waiting and will launch once the app exits. |
| App reopened to old version after update | Re-run the downloaded installer from `%TEMP%\DarcsVisualPickit\updates\`. |
| Auto-check is annoying | Open the Update Center and disable **Enable automatic update checks**, or increase the check interval. |

## 📁 Project Structure

| File | Purpose |
|---|---|
| `app_main.py` | Main application, UI, and updater logic |
| `release_metadata.py` | Version constants used by builds and the updater |
| `nip_parser.py` | `.nip` rule parsing and validation |
| `paged_core.py` | Core paging helpers |
| `paged_cache_runtime.py` | Paging and cache runtime |
| `paged_validation.py` | Validation helpers for paged rules |
| `runtime_controller.py` | Runtime controller (performance/standard modes) |
| `runtime_mutations.py` | Rule mutation operations |
| `runtime_wiring.py` | Runtime method wiring |
| `widget_cards.py` | Item rule card widgets |
| `compact_card_runtime.py` | Compact card rendering runtime |
| `compact_model_cache.py` | Compact mode model cache |
| `compact_ui_runtime.py` | Compact UI runtime |
| `profile_runtime.py` | Profile/session runtime |
| `editor_dialogs.py` | Editor dialog windows |
| `advanced_clause_ui.py` | Advanced clause editor UI |
| `sidebar_filters.py` | Sidebar filter logic |

## 📄 License

See [LICENSE](LICENSE) for details.
