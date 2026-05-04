# CLAUDE.md — Woordenlijst-checker

This file provides guidance for AI assistants working in this repository.

## Project Overview

**Woordenlijst-checker** is a Windows desktop utility (v1.6) that lets editors, proofreaders, and translators instantly verify Dutch spelling against the official [woordenlijst.org](https://woordenlijst.org/) database without leaving their active application. A global hotkey (default: F9) triggers a lookup of the selected word via clipboard, and a pop-up reports the result within seconds.

**License:** GNU General Public License v3
**Author:** Black Kite (blackkite.nl)
**Language:** Python 3 (single-file script, no package structure)
**Platform:** Windows only (uses `keyboard` for global hotkeys and Windows clipboard conventions)

---

## Repository Structure

```
Woordenlijst-checker/
├── woordenlijstchecker.py   # Entire application — ~1896 lines, single file
├── README.md                # End-user documentation
├── LICENSE                  # GNU GPLv3
├── over.md                  # App info shown in the "Over" popup (supports markdown links)
├── version.txt              # Current version number (used for update checks)
├── version_info.txt         # PyInstaller Windows version metadata (VERSIONINFO resource)
├── test_woorden.py          # CLI tester for problematic input words (no GUI, no hotkey)
├── verificatie_woorden.py   # Automated verifier comparing app output against Excel expectations
└── config.ini               # Auto-generated at runtime (NOT in repo)
```

There are **no subdirectories and no CI/CD configuration.**

---

## Architecture

The application is a **monolithic single-file Python script**. All logic lives in `woordenlijstchecker.py`. There is no package structure, no class hierarchy, and no module separation. This is intentional for easy distribution as a standalone executable.

### Execution Model

```
main()
 ├─ _start_tray()                    ← starts pystray tray icon in separate thread
 ├─ keyboard.add_hotkey(HOTKEY, ...) ← registers global hotkey (default: F9)
 │     └─ threading.Thread(target=perform_check).start()
 │           ├─ check_rate_limit()           ← max 30 requests/minute
 │           ├─ clipboard read (Ctrl+C / Ctrl+Ins fallback)
 │           ├─ check_prisma_alternatief()   ← parallel thread (spelling.prisma.nl)
 │           ├─ check_word_online(word)       ← API call to woordenlijst.org
 │           └─ show_success_popup() OR show_failure_popup(alternatief_info=...)
 └─ _herregistreer_sneltoets()       ← periodic hotkey re-registration every 5 min
```

The main thread blocks on `keyboard.wait('esc')`. Each hotkey press spawns a new thread for non-blocking UI. The tray icon runs in its own thread and dispatches menu actions back to the tkinter thread via `_popup_root.after()`.

**Hotkey auto-recovery:** Windows silently removes `WH_KEYBOARD_LL` hooks after sleep or screen lock. `_herregistreer_sneltoets()` runs via `_popup_root.after()` every 5 minutes, calling `keyboard.unhook_all()` + `keyboard.add_hotkey()` to keep the hook alive. The same `unhook_all` call is made before every manual hotkey change in `sla_hotkey_op()`.

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
| `_extract_woordsoort_entries(found_lemmata_block)` | Parses a single `<found_lemmata>` block and returns a list of entry dicts with `display`, `article`, `gender`, `lemma`, and optionally `is_meervoud` |
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
| `show_success_popup(word, article, word_info, gender, gender_info_list)` | Green checkmark popup, auto-closes after 3 seconds; supports homonyms, plurals, ambiguous words; shows part-of-speech abbreviation per entry |
| `show_failure_popup(word, error_message, alternatief_info)` | Error dialog with clickable suggestion links, optional "witte spelling" result from Prisma, editable re-search field, and Yes/No buttons to open woordenlijst.org |
| `show_over_popup()` | "Over" dialog — reads and displays `over.md` with inline link rendering |
| `show_help_popup()` | Help dialog — reads and displays `README.md` with inline link rendering |
| `show_config_popup()` | Settings dialog — lets user change hotkey and reset popup position |
| `show_invoerfilter_popup(word, reden)` | Warning dialog shown when input is filtered (e.g. too short, non-word) |
| `controleer_op_updates()` | Fetches `version.txt` via `UPDATE_CHECK_URL`; compares version tuples (not strings); shows custom popup with a clickable link to the GitHub Releases page when an update is available |

### Helper Functions
| Function | Purpose |
|---|---|
| `_get_readme_path()` | Returns path to `README.md` (works for `.py` and `.exe`) |
| `_get_over_path()` | Returns path to `over.md` (works for `.py` and `.exe`) |
| `_set_icon(window)` | Sets the app icon on a tkinter window |
| `_render_inline(text_widget, line, link_counter)` | Renders markdown inline links in a `Text` widget |
| `_entry_display_word(entry)` | Returns the display word for a homonym entry, using the lemma's own capitalisation |
| `_herregistreer_sneltoets()` | Inner function in `main()` — periodically re-registers the hotkey to recover from sleep/lock |

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
- `<label>` — word type tags (`hoofdwerkwoord`, `meervoud`, `enkelvoud`, `zelfstandig naamwoord`, etc.); all labels per `<found_lemmata>` block are processed and mapped via `WOORDSOORT_PREFIXES`

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
| Standard library: `tkinter`, `threading`, `configparser`, `os`, `re`, `sys`, `time`, `urllib.parse`, `warnings`, `collections.deque`, `html`, `ctypes` | Various built-in functionality |

To install third-party dependencies manually:
```bash
pip install requests keyboard pyperclip pystray Pillow
```

The distributed `.exe` bundles all dependencies via PyInstaller (referenced by `sys._MEIPASS` checks in the code).

---

## Word Checking Logic — Key Rules

Understanding the checking logic is essential before modifying `check_word_online`:

1. **Typographic character normalization**: Before the input filter runs, `perform_check()` normalizes typographic hyphens (U+00AD, U+2010–U+2013) to plain hyphens (`-`) and special spaces (U+00A0, U+202F, U+2009) to plain spaces. This prevents false "invalid characters" warnings when text is pasted from Word, InDesign, or web pages.

2. **Apostrophe normalization**: Typographic apostrophes (`'`, `` ` ``, `´`, `ʼ`) are normalized to straight apostrophes (`'`) before API queries.

3. **Lemma vs. wordform**: A word is valid if it appears as a `<lemma>` (preferred) or as a `<wordform>` under certain conditions.

4. **Internal capitals (strict mode)**: Words where the API returns lemmas with internal uppercase letters (e.g., compound proper nouns) are validated strictly — the input capitalization must exactly match the lemma's capitalization pattern.

5. **Case-sensitive lemmas** (e.g., `pH`, `mkb`): If the lowercase variant of the input matches a lemma but with different casing, an error is returned with the correct form suggested.

6. **Sentence-initial capitals**: A word like `Fiets` (first letter uppercase, rest lowercase) is accepted and shown in lowercase in the popup — **unless** the primary lemma itself starts with a capital (e.g. `Excelfile`), in which case the original capitalisation is preserved.

7. **Plural nouns**: Words found only as `<label>meervoud</label>` (plural) always get article `de`. Gender from the underlying singular lemma is propagated to the plural entry and shown in the popup as `znw. mv. (m)`, `znw. mv. (o)`, etc.

8. **Word groups** (`znw. groep`): Multi-word noun-group entries (e.g. *ziekte van Parkinson*, *ins en outs*) are extracted and displayed with their own article and gender where available. Plural word groups are marked with `is_meervoud=True` and displayed as `znw. groep mv.` with no article.

9. **Homonyms**: When multiple lemma entries are found for the same word, `gender_info_list` is populated as a list of dicts and the popup renders each variant on a separate line. Each entry carries its own `lemma` key so that differing capitalisations (e.g. `weegschaal` vs. `Weegschaal`) are displayed correctly via `_entry_display_word()`.

10. **Part-of-speech abbreviations**: Each entry is mapped to a short Dutch label (e.g. *znw.*, *bnw.*, *ww.*, *vnw.*, *naam*, *znw. groep*) via the `WOORDSOORT_PREFIXES` lookup table. Noun entries for plain singular nouns omit the *znw.* prefix to keep the popup clean.

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
| plural | de | propagated from singular entry, shown as e.g. `znw. mv. (o)` |
| proper noun (`NOU-P`) | de | *naam* (no gender shown) |
| `znw. groep` singular | de / het | shown when available |
| `znw. groep` plural | — | no article; shown as `znw. groep mv.` |

---

## Development Conventions

- **Language**: Code comments and print statements are in Dutch. Variable names and function names are in Dutch or English (mixed).
- **Single-file design**: Do not split into multiple files or add a package structure without explicit user request. The monolithic design is intentional for distribution simplicity.
- **No type hints**: The codebase does not use Python type annotations. Do not add them unless requested.
- **Test script**: `test_woorden.py` is a lightweight CLI tester for specific problematic words (no GUI, no hotkey, no clipboard). Run it directly with `python test_woorden.py`. It calls `check_word_online()` directly and prints results. Add words to the `TESTWOORDEN` list inside the file.
- **No linter config**: No `.flake8`, `.pylintrc`, or `pyproject.toml` exist. Follow PEP 8 style.
- **Error handling**: All network calls are wrapped in try-except. Errors are printed to stdout using `[Tag]` prefix format (e.g., `[Fout]`, `[Info]`, `[Waarschuwing]`, `[Resultaat]`).
- **GUI**: Uses `tkinter` only. Do not introduce other GUI frameworks.
- **Opening URLs**: Use `os.startfile(url)` to open URLs in the user's default browser. Do **not** use `webbrowser.open()` — on Windows this can ignore the configured default browser and open Edge instead.
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

## Testing

There is **no automated test suite** and **no CI/CD pipeline**.

`test_woorden.py` is a manual CLI helper: it calls `check_word_online()` directly for a predefined list of words and prints the results. Useful for quickly verifying API parsing changes. Run with:

```bash
python test_woorden.py
```

Most functions depend on tkinter GUI, live network access, or the system clipboard — integration/manual testing remains the primary validation method.

---

## Release Notes

### v1.6
- **Hyphenation in success popup**: syllabification now shows both the base form and the diminutive side by side, separated by a bold `|` (e.g. *mar·shal·low | mar·shal·low·tje*). For words with variant spellings (e.g. with/without trema), alternatives are shown with a bold `of` instead of the raw `#` separator from the API.
- **Hyphenation placement**: in multi-entry popups (words with multiple word types, e.g. *bal*), syllabification appears directly under the noun entry rather than at the bottom of the popup.
- **Hyphenation for word groups**: fixed — multi-word entries such as *ziekte van Parkinson* and *happy few* now show correct syllabification (previously the API's wordpart paradigms were matched instead of the group's own paradigm).
- **Hyphenation for plural and invariant nouns**: fixed — plural forms at position 10 (e.g. *kinderen*) and invariant nouns (e.g. *chassis*) now show syllabification.
- **Failure popup redesign**: red cross icon (✗, Arial 48, #cc0000) added on the left, mirroring the success popup's green checkmark. All content is now left-aligned. "Wilt u het oorspronkelijke woord opzoeken?" and the Ja/Nee buttons sit below the icon block.

### v1.5.9
- **Right-click context menu on suggestions**: suggestions in the "not found" popup now respond to right-click with a menu offering "Kopiëren" (copies to clipboard, closes popup) and "Openen in Woordenlijst.org" (opens browser, closes popup). Left-click continues to open the browser directly. Applies to both spelling suggestion links ("Bedoelde u:"), the correct-form link ("Gebruik 'term'"), and the alternative white spelling link ("Alternatieve witte spelling:").

### v1.5.8
- **Variant spellings** ("Zie ook:"): the success popup now shows co-equal variant spellings when the API reports them — e.g. searching *stuken* shows *Zie ook: stuccen*. Variants are clickable links. Only shown when the searched word itself appears in the API's `<parent>` field, preventing false positives.
- **Abbreviations allowed**: period (`.`) added to the input filter whitelist, so abbreviations such as *etc.* and *enz.* no longer trigger the "unusual characters" warning.

### v1.5.7
- **Compound word suggestions**: when a word is not found and the spellcheck API returns no corrections, the app now falls back to a regex prefix search (`find_wordform` with `regex=true`). This surfaces compound words built on the input — e.g. searching *doe-het-zelf* now suggests *doe-het-zelfafdeling* and similar entries.
- **Failure popup layout**: the word is now shown in the header of the "not found" dialog for both popup types, ensuring the message always has a clear subject and starts with a capital.

### v1.5.6
- **Deduplicate spelling suggestions**: when the spellcheck API returns the same correction multiple times (e.g. for multi-word input like *spoiler alerts*), duplicates are now collapsed so each suggestion appears only once. Order is preserved; the cap of 3 suggestions still applies after deduplication.

### v1.5.5
- Normalize typographic hyphens (non-breaking, soft, en-dash variants) and special spaces (non-breaking, narrow no-break, thin) to their plain equivalents before the input filter runs — prevents false "invalid characters" warnings when pasting from Word, InDesign, or web browsers.

### v1.5.4
- **Gender on plural nouns**: gender is now propagated from the singular lemma entry to its plural and shown in the popup — e.g. `znw. mv. (o)` for a neuter noun.
- **Word groups** (`znw. groep`): singular groups (e.g. *ziekte van Parkinson*) now show the correct article and gender extracted from `<lemma_part_of_speech>`; plural groups (e.g. *ins en outs*, *happy few*) are shown as `znw. groep mv.` without an article.
- **Capitalised lemmas** (e.g. *Excelfile*): words whose primary lemma is itself capitalised are no longer lowercased in the popup; the sentence-initial-capital normalisation now checks the lemma before lowercasing.

### v1.5.3
- **Update check**: version comparison now uses integer tuples instead of string equality, preventing false "new version" notifications (e.g. remote 1.5.2 no longer appears newer than local 1.5.3).
- **Update notification popup**: the "new version available" dialog now includes a clickable link directly to the GitHub Releases page.

---

## Git Workflow

- **Main branch:** `master`
- **Feature branches:** Use descriptive names; the project has no enforced branch naming convention beyond what may be imposed by the development environment.
- Commit messages are in English (based on existing commit history: `Update woordenlijstchecker.py`, `v1.2.x`).
