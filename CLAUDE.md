# CLAUDE.md — Woordenlijst-checker

This file provides guidance for AI assistants working in this repository.

## Project Overview

**Woordenlijst-checker** is a Windows desktop utility (v1.5) that lets editors, proofreaders, and translators instantly verify Dutch spelling against the official [woordenlijst.org](https://woordenlijst.org/) database without leaving their active application. A global hotkey (default: F9) triggers a lookup of the selected word via clipboard, and a pop-up reports the result within seconds.

**License:** GNU General Public License v3
**Author:** Black Kite (blackkite.nl)
**Language:** Python 3 (single-file script, no package structure)
**Platform:** Windows only (uses `keyboard` for global hotkeys and Windows clipboard conventions)

---

## Repository Structure

```
Woordenlijst-checker/
├── woordenlijstchecker.py   # Entire application — ~1347 lines, single file
├── README.md                # End-user documentation
├── LICENSE                  # GNU GPLv3
├── over.md                  # App info shown in the "Over" popup (supports markdown links)
├── version.txt              # Current version number (used for update checks)
└── config.ini               # Auto-generated at runtime (NOT in repo)
```

There are **no subdirectories, no test files, and no CI/CD configuration.**

---

## Architecture

The application is a **monolithic single-file Python script**. All logic lives in `woordenlijstchecker.py`. There is no package structure, no class hierarchy, and no module separation. This is intentional for easy distribution as a standalone executable.

### Execution Model

```
main()
 ├─ _start_tray()                    ← starts pystray tray icon in separate thread
 └─ keyboard.add_hotkey(HOTKEY, ...) ← registers global hotkey (default: F9)
       └─ threading.Thread(target=perform_check).start()
             ├─ check_rate_limit()           ← max 30 requests/minute
             ├─ clipboard read (Ctrl+C / Ctrl+Ins fallback)
             ├─ check_prisma_alternatief()   ← parallel thread (spelling.prisma.nl)
             ├─ check_word_online(word)       ← API call to woordenlijst.org
             └─ show_success_popup() OR show_failure_popup(alternatief_info=...)
```

The main thread blocks on `keyboard.wait('esc')`. Each hotkey press spawns a new thread for non-blocking UI. The tray icon runs in its own thread and dispatches menu actions back to the tkinter thread via `_popup_root.after()`.

---

## Key Functions

### System Tray
The application runs as a system tray icon (via `pystray`) with the following menu items:
- **Over** — opens the "Over" popup (reads `over.md`)
- **Controleer op updates** — fetches `version.txt` from GitHub and compares with `VERSION`
- **Help** — opens the help popup (reads `README.md`)
- **Instellingen...** — opens the settings/config popup
- **Afsluiten** — quits the application

### Configuration
| Function | Purpose |
|---|---|
| `load_config()` | Reads or auto-creates `config.ini`; returns `(hotkey, popup_x, popup_y, config_file)` |
| `save_popup_position(x, y)` | Writes popup position to `config.ini` after user drags it |
| `get_popup_position(w, h)` | Returns saved position or falls back to center |
| `get_center_position(w, h)` | Calculates screen center using tkinter screen metrics |

### Rate Limiting
| Function | Purpose |
|---|---|
| `check_rate_limit()` | Enforces max 30 API requests/minute using a `deque`; shows warning dialog if exceeded |

### Core Word Checking
| Function | Purpose |
|---|---|
| `check_word_online(word)` | Main business logic — queries the API, parses XML, returns 7-tuple |
| `get_spelling_suggestions(word)` | Calls the spellcheck endpoint; returns up to 3 suggestions as a string |
| `check_prisma_alternatief(word)` | Queries `spelling.prisma.nl` for alternative (white-list) spellings; returns `(alt_word, officiele_spelling, url)` or `None` |

**Return signature of `check_word_online`:**
```python
(is_valid: bool, word: str, error_message: str|None, article: str|None,
 word_info: dict|None, gender: str|None, gender_info_list: list|None)
```

### UI / Popups
| Function | Purpose |
|---|---|
| `show_success_popup(word, article, word_info, gender, gender_info_list)` | Green checkmark popup, auto-closes after 3 seconds; supports homonyms, plurals, ambiguous words |
| `show_failure_popup(word, error_message, alternatief_info)` | Error dialog with clickable suggestion links, optional "witte spelling" result from Prisma, and Yes/No buttons to open woordenlijst.org |
| `show_over_popup()` | "Over" dialog — reads and displays `over.md` with inline link rendering |
| `show_help_popup()` | Help dialog — reads and displays `README.md` with inline link rendering |
| `show_config_popup()` | Settings dialog — lets user change hotkey and reset popup position |
| `show_invoerfilter_popup(word, reden)` | Warning dialog shown when input is filtered (e.g. too short, non-word) |
| `controleer_op_updates()` | Fetches `version.txt` via `UPDATE_CHECK_URL`; shows result dialog |

### Helper Functions
| Function | Purpose |
|---|---|
| `_get_readme_path()` | Returns path to `README.md` (works for `.py` and `.exe`) |
| `_get_over_path()` | Returns path to `over.md` (works for `.py` and `.exe`) |
| `_set_icon(window)` | Sets the app icon on a tkinter window |
| `_render_inline(text_widget, line, link_counter)` | Renders markdown inline links in a `Text` widget |

### Entry Points
| Function | Purpose |
|---|---|
| `perform_check()` | Orchestrates clipboard read → API check → popup display |
| `main()` | Registers global hotkey, starts tray icon, starts the blocking keyboard listener loop |

---

## External API Integration

The app integrates with two woordenlijst.org API endpoints:

### Word Validation
```
GET https://woordenlijst.org/MolexServe/lexicon/find_wordform
Params: database=gig_pro_wrdlst, wordform=<word>, paradigm=true,
        diminutive=true, onlyvalid=true, regex=false, dummy=<timestamp>
Response: XML with <found_lemmata>, <wordform>, <lemma>, <paradigm>, etc.
```

### Spelling Suggestions
```
GET https://woordenlijst.org/MolexServe/lexicon/spellcheck
Params: database=gig_pro_wrdlst, word=<word>, dummy=<timestamp>
Response: XML with <corrections> (pipe-separated) or <best_guess>
```

**Important:** The API returns XML but the code parses it with regex (not an XML parser library). Responses are parsed for:

- `<found_lemmata>` — presence indicates word exists in database
- `<wordform>` / `<lemma>` — matched forms
- `<paradigm>` blocks — inflection data (singular/plural, gender)
- `lemma_part_of_speech` attributes — extract gender (`m`, `f`, `n`, `c`)
- `<label>` — word type tags (`hoofdwerkwoord`, `meervoud`, `enkelvoud`, `zelfstandig naamwoord`)

### Prisma Alternative Spelling (spelling.prisma.nl)

When a word is **not found** in woordenlijst.org, the app simultaneously queries `spelling.prisma.nl` (the Prisma/onzetaal dictionary) to check whether the word exists as an alternative ("witte") spelling. This runs in a parallel thread alongside the main check.

```
GET https://spelling.prisma.nl/?id=-827&unitsearch=<word>
Response: HTML page parsed with regex for .unitname and .lref elements
```

Two response patterns are handled:
- **Type A**: the `unitname` div contains `<span class="la">alternatief</span>` → `unitname` = witte spelling, `lref` = groene (official) spelling
- **Type B**: the `alternatief` label appears elsewhere on the page → `lref` = witte spelling, `unitname` = groene spelling

If a result is found, `show_failure_popup` displays it as a clickable link labelled **"Alternatieve witte spelling:"**. The check times out after 6 seconds and never blocks the popup.

---

## Configuration System

A `config.ini` file is auto-created in the working directory on first run:

```ini
[Settings]
hotkey = f9
popup_x = -1
popup_y = -1
```

- `hotkey`: Any key or key combination supported by the `keyboard` library (e.g., `f9`, `ctrl+shift+f9`)
- `popup_x` / `popup_y`: Saved popup position; `-1` means "center of screen"
- The file is read-only at startup; popup position is updated live when the user drags the popup

**Note:** `config.ini` is not committed to the repository (it's user-specific runtime state).

---

## Dependencies

All dependencies are third-party Python packages. There is no `requirements.txt` or `pyproject.toml`; they are listed only as comments in the source file.

| Package | Purpose |
|---|---|
| `requests` | HTTP calls to woordenlijst.org API and update check |
| `keyboard` | Global hotkey registration and Ctrl+C simulation |
| `pyperclip` | Cross-platform clipboard read/write |
| `pystray` | System tray icon and menu |
| `Pillow` (`PIL`) | Tray icon image creation |
| Standard library: `tkinter`, `threading`, `configparser`, `os`, `re`, `sys`, `time`, `webbrowser`, `urllib.parse`, `warnings`, `collections.deque`, `html`, `ctypes` | Various built-in functionality |

To install third-party dependencies manually:
```bash
pip install requests keyboard pyperclip pystray Pillow
```

The distributed `.exe` bundles all dependencies via PyInstaller (referenced by `sys._MEIPASS` checks in the code).

---

## Word Checking Logic — Key Rules

Understanding the checking logic is essential before modifying `check_word_online`:

1. **Apostrophe normalization**: Typographic apostrophes (`'`, `` ` ``, `´`, `ʼ`) are normalized to straight apostrophes (`'`) before API queries.

2. **Lemma vs. wordform**: A word is valid if it appears as a `<lemma>` (preferred) or as a `<wordform>` under certain conditions.

3. **Internal capitals (strict mode)**: Words where the API returns lemmas with internal uppercase letters (e.g., compound proper nouns) are validated strictly — the input capitalization must exactly match the lemma's capitalization pattern.

4. **Case-sensitive lemmas** (e.g., `pH`, `mkb`): If the lowercase variant of the input matches a lemma but with different casing, an error is returned with the correct form suggested.

5. **Sentence-initial capitals**: A word like `Fiets` (first letter uppercase, rest lowercase) is accepted if its lowercase form exists in the database.

6. **Plural nouns**: Words found only as `<label>meervoud</label>` (plural) always get article `de`; their singular lemma may be shown for reference.

7. **Homonyms**: When multiple lemma entries with different gender/article combinations are found for the same word, `gender_info_list` is populated as a list of dicts, and the popup renders each variant on a separate line.

---

## Article and Gender Extraction

Dutch nouns have grammatical gender. The code extracts this from `lemma_part_of_speech` attributes in the XML:

| API gender code | Article | Displayed gender |
|---|---|---|
| `m` | de | m |
| `f` | de | v |
| `n` | het | o |
| `c` (common) | de | m/v |
| `m` + `f` combined | de | m/v |
| plural | de | (none shown) |

---

## Development Conventions

- **Language**: Code comments and print statements are in Dutch. Variable names and function names are in Dutch or English (mixed).
- **Single-file design**: Do not split into multiple files or add a package structure without explicit user request. The monolithic design is intentional for distribution simplicity.
- **No type hints**: The codebase does not use Python type annotations. Do not add them unless requested.
- **No test suite**: There are no tests. If adding tests, use `pytest` and create a `tests/` directory.
- **No linter config**: No `.flake8`, `.pylintrc`, or `pyproject.toml` exist. Follow PEP 8 style.
- **Error handling**: All network calls are wrapped in try-except. Errors are printed to stdout using `[Tag]` prefix format (e.g., `[Fout]`, `[Info]`, `[Waarschuwing]`, `[Resultaat]`).
- **GUI**: Uses `tkinter` only. Do not introduce other GUI frameworks.
- **Threading**: `perform_check()` always runs in a separate thread to keep the hotkey listener responsive. Any tkinter calls from threads should use `.after()` or be in the spawned thread's own mainloop.

---

## Running the Application

```bash
# Install dependencies (if not already installed)
pip install requests keyboard pyperclip

# Run the script (Windows, requires admin rights for global hotkeys)
python woordenlijstchecker.py
```

On startup, the script:
1. Reads or creates `config.ini` in the current working directory
2. Registers the configured hotkey (default F9)
3. Listens until Escape is pressed

**Note:** The `keyboard` library requires administrator/root privileges on most systems for global hotkey capture.

---

## No Tests, No CI/CD

- There are currently **no automated tests**.
- There is **no CI/CD pipeline** (no GitHub Actions, no pre-commit hooks, etc.).
- If adding tests, note that most functions depend on tkinter GUI, live network access, or system clipboard — integration/manual testing is the primary validation method.

---

## Git Workflow

- **Main branch:** `master`
- **Feature branches:** Use descriptive names; the project has no enforced branch naming convention beyond what may be imposed by the development environment.
- Commit messages are in English (based on existing commit history: `Update woordenlijstchecker.py`, `v1.2.x`).
