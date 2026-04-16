# Woordenlijst-checker door Black Kite (blackkite.nl)

# Vereiste bibliotheken
import time
import requests
import keyboard
import pyperclip
import threading
from urllib.parse import quote
import tkinter as tk
from tkinter import messagebox
import warnings
import configparser
import os
from collections import deque
import re
import sys
import html
import ctypes
import pystray
from PIL import Image

# Onderdruk waarschuwingen
warnings.filterwarnings("ignore", category=UserWarning)

VERSION = "1.5.5"

# URL naar version.txt in de publieke repository (voor updatecontrole)
UPDATE_CHECK_URL = "https://raw.githubusercontent.com/ErwinVanWouw/Woordenlijst-checker/master/version.txt"

# Woordsoort-prefixen voor popup-weergave (geordend van specifiek naar algemeen; eerste match wint)
# None = genus/artikel uit label parsen (zelfstandig naamwoord)
# 'RAW' = toon label ongewijzigd (voornaamwoord/voegwoord subtypes)
WOORDSOORT_PREFIXES = [
    ('bijvoeglijk naamwoord / bijwoord', 'bijvoeglijk naamwoord / bijwoord'),
    ('bijvoeglijk naamwoord',            'bijvoeglijk naamwoord'),   # defensief, nooit gezien
    ('zelfstandignaamwoordgroep',         'zelfstandignaamwoordgroep'),
    ('zelfstandig naamwoord',            None),
    ('naam',                             'naam'),
    ('hoofdwerkwoord',                   'werkwoord'),
    ('bijwoord',                         'bijwoord'),                # vangt ook '(afkorting)'
    ('voorzetsel / achterzetsel',        'voorzetsel / achterzetsel'),
    ('voorzetsel',                       'voorzetsel'),
    ('nevenschikkend voegwoord',         'RAW'),
    ('onderschikkend voegwoord',         'RAW'),
    ('persoonlijk voornaamwoord',        'RAW'),
    ('bezittelijk voornaamwoord',        'RAW'),
    ('aanwijzend voornaamwoord',         'RAW'),
    ('betrekkelijk voornaamwoord',       'RAW'),
    ('vragend voornaamwoord',            'RAW'),
    ('onbepaald voornaamwoord',          'RAW'),
    ('wederkerend voornaamwoord',        'RAW'),
    ('hoofdtelwoord',                    'telwoord'),
    ('rangtelwoord',                     'telwoord'),                # defensief
    ('tussenwerpsel',                    'tussenwerpsel'),           # vangt subtype-suffix
    ('symbool',                          'symbool'),
]

# Woordsoort-afkortingen voor popup-weergave
# Sleutels zijn de display-waarden die WOORDSOORT_PREFIXES produceert (of de RAW-labels)
POS_AFKORTINGEN = {
    'werkwoord':                          'ww.',
    'zelfstandignaamwoordgroep':          'znw. groep',
    'zelfstandig naamwoord':              'znw.',
    'bijvoeglijk naamwoord / bijwoord':   'bnw./bw.',
    'bijvoeglijk naamwoord':              'bnw.',
    'bijwoord':                           'bw.',
    'voorzetsel / achterzetsel':          'vz./az.',
    'voorzetsel':                         'vz.',
    'nevenschikkend voegwoord':           'nevensch. vw.',
    'onderschikkend voegwoord':           'ondersch. vw.',
    'persoonlijk voornaamwoord':          'pers. vnw.',
    'bezittelijk voornaamwoord':          'bez. vnw.',
    'aanwijzend voornaamwoord':           'aanw. vnw.',
    'betrekkelijk voornaamwoord':         'betr. vnw.',
    'vragend voornaamwoord':              'vr. vnw.',
    'onbepaald voornaamwoord':            'onbep. vnw.',
    'wederkerend voornaamwoord':          'wederk. vnw.',
    'telwoord':                           'telw.',
    'tussenwerpsel':                      'tw.',
    'symbool':                            'symb.',
}

# Eén permanente verborgen Tk-root voor alle popups (voorkomt flikkering bij aanmaken)
_popup_root = None

# --- SYSTEEMVAK (pystray) ---
_tray_icon = None


def _laad_tray_icoon_image():
    """Laad favicon.ico of val terug op een blauw vlak."""
    if hasattr(sys, '_MEIPASS'):
        icon_path = os.path.join(sys._MEIPASS, 'favicon.ico')
    else:
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'favicon.ico')
    try:
        return Image.open(icon_path).resize((32, 32))
    except Exception:
        return Image.new('RGBA', (32, 32), (0, 120, 215, 255))


def _on_tray_over(icon, item):
    if _popup_root:
        _popup_root.after(0, lambda: threading.Thread(target=show_over_popup).start())



def _on_tray_help(icon, item):
    if _popup_root:
        _popup_root.after(0, lambda: threading.Thread(target=show_help_popup).start())


def _on_tray_instellingen(icon, item):
    if _popup_root:
        _popup_root.after(0, lambda: threading.Thread(target=show_config_popup).start())


def _on_tray_afsluiten(icon, item):
    if _popup_root:
        _popup_root.after(0, _sluit_af)


def _sluit_af():
    """Sluit de applicatie netjes af vanuit de hoofdthread."""
    try:
        keyboard.unhook_all()
    except Exception:
        pass
    if _tray_icon:
        _tray_icon.stop()
    _popup_root.quit()


def _start_tray():
    """Maak het systeemvakicoon aan en start het in een aparte thread."""
    global _tray_icon
    menu = pystray.Menu(
        pystray.MenuItem('Over', _on_tray_over),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem('Help', _on_tray_help),
        pystray.MenuItem('Instellingen...', _on_tray_instellingen),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem('Afsluiten', _on_tray_afsluiten),
    )
    _tray_icon = pystray.Icon(
        'woordenlijstchecker',
        _laad_tray_icoon_image(),
        'Woordenlijst-checker',
        menu,
    )
    threading.Thread(target=_tray_icon.run, daemon=True).start()

# --- GEBRUIKSLIMIET ---
# Track laatste requests
request_history = deque(maxlen=100)
MAX_REQUESTS_PER_MINUTE = 30

def check_rate_limit():
    """Check of we niet te veel requests doen"""
    now = time.time()
    request_history.append(now)

    # Tel requests in laatste minuut
    recent = sum(1 for t in request_history if now - t < 60)

    if recent > MAX_REQUESTS_PER_MINUTE:
        print("[Waarschuwing] Te veel aanvragen (max. 30/minuut), wacht even...")
        done = threading.Event()
        def _toon_ratelimit():
            messagebox.showwarning("Rate Limit",
                                  "Maximum aantal controles bereikt.\nWacht even voordat u doorgaat.\n(Max. 30 controles per minuut)")
            done.set()
        _popup_root.after(0, _toon_ratelimit)
        done.wait()
        return False
    return True

# --- INVOERFILTER ---
def is_geldig_invoer(word):
    """Controleert of de invoer eruitziet als een geldig Nederlands woord of woordgroep."""
    if len(word) > 60:
        return False, "De geselecteerde tekst is te lang voor een woordcontrole."
    if not re.search(r'[a-zA-ZÀ-öø-ÿ]', word):
        return False, "De geselecteerde tekst bevat geen letters."
    if not re.fullmatch(r"[a-zA-ZÀ-öø-ÿ0-9 \-'\/\u00B9\u00B2\u00B3\u2070-\u2079\u2080-\u2089]+", word):
        return False, "De geselecteerde tekst bevat tekens die normaal niet in een Nederlands woord voorkomen."
    if len(re.findall(r'[a-zà-öø-ÿ][A-ZÀ-ÖØ-Þ]', re.sub(r'[0-9]', '', word))) >= 2:
        return False, "De geselecteerde tekst lijkt camelCase te bevatten, wat geen normaal woordpatroon is."
    return True, None

# --- CONFIGURATIE ---
def load_config():
    """Laad configuratie uit ini bestand of maak standaard aan"""
    config = configparser.ConfigParser()
    if hasattr(sys, '_MEIPASS'):
        _config_dir = os.path.dirname(sys.executable)
    else:
        _config_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(_config_dir, 'config.ini')

    # Check of config-bestand bestaat
    if os.path.exists(config_file):
        config.read(config_file)
        hotkey = config.get('Settings', 'hotkey', fallback='f9')
        # Laad opgeslagen sneltoets en pop-uppositie
        popup_x = config.getint('Settings', 'popup_x', fallback=-1)
        popup_y = config.getint('Settings', 'popup_y', fallback=-1)
        print(f"[Config] Sneltoets geladen: '{hotkey}'")
        if popup_x != -1 and popup_y != -1:
            print(f"[Config] Pop-uppositie geladen: {popup_x}, {popup_y}")
    else:
        # Maak nieuw configuratiebestand met standaardwaarden
        config['Settings'] = {
            'hotkey': 'f9',
            'popup_x': '-1',
            'popup_y': '-1'
        }
        try:
            with open(config_file, 'w') as f:
                config.write(f)
        except OSError as e:
            print(f"[Waarschuwing] Kon config.ini niet aanmaken: {e}")
        hotkey = 'f9'
        popup_x = popup_y = -1
        print(f"[Config] Nieuw config.ini bestand aangemaakt met standaard sneltoets: 'f9'")
        print(f"[Config] Pas het bestand aan om de sneltoets te wijzigen en herstart de tool")
        print(f"[Config] Pop-uppositie wordt onthouden na verslepen")

    return hotkey, popup_x, popup_y, config_file

# Laad de configuratie
HOTKEY, POPUP_X, POPUP_Y, CONFIG_FILE = load_config()

def save_popup_position(x, y):
    """Sla pop-uppositie op in configuratiebestand"""
    global POPUP_X, POPUP_Y

    # Update globale variabelen
    POPUP_X = x
    POPUP_Y = y

    # Schrijf naar configuratiebestand
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)

    if 'Settings' not in config:
        config['Settings'] = {}

    config['Settings']['popup_x'] = str(x)
    config['Settings']['popup_y'] = str(y)

    with open(CONFIG_FILE, 'w') as f:
        config.write(f)

def get_popup_position(width, height):
    """Bepaal pop-uppositie; valt terug op schermcentrum als opgeslagen positie onbereikbaar is"""
    def center():
        try:
            x = int(_popup_root.winfo_screenwidth()/2 - width/2)
            y = int(_popup_root.winfo_screenheight()/2 - height/2)
            return x, y
        except Exception as e:
            print(f"[Waarschuwing] Kon centrumpositie niet bepalen: {e}")
            return 100, 100

    if POPUP_X == -1 or POPUP_Y == -1:
        return center()

    # Valideer of opgeslagen positie zichtbaar is op de virtuele schermruimte (alle monitoren).
    # Minimaal de helft van de popup breedte én hoogte moet binnen het schermgebied vallen.
    try:
        u32 = ctypes.windll.user32
        virt_x = u32.GetSystemMetrics(76)   # SM_XVIRTUALSCREEN
        virt_y = u32.GetSystemMetrics(77)   # SM_YVIRTUALSCREEN
        virt_w = u32.GetSystemMetrics(78)   # SM_CXVIRTUALSCREEN
        virt_h = u32.GetSystemMetrics(79)   # SM_CYVIRTUALSCREEN
        # Popup is zichtbaar als het middelpunt binnen de virtuele schermruimte valt
        popup_cx = POPUP_X + width  // 2
        popup_cy = POPUP_Y + height // 2
        if (popup_cx < virt_x or popup_cx > virt_x + virt_w or
                popup_cy < virt_y or popup_cy > virt_y + virt_h):
            print("[Info] Opgeslagen positie niet bereikbaar, gebruik centrum")
            return center()
        return POPUP_X, POPUP_Y

    except Exception as e:
        print(f"[Waarschuwing] Kon pop-uppositie niet valideren: {e}")
        return POPUP_X, POPUP_Y

def _extract_woordsoort_entries(xml, word):
    """Extraheert alle woordsoort-entries uit de API-XML voor een geldig woord.

    Werkwijze:
    1. Splits XML in <found_lemmata>-blokken
    2. Per blok: strip <paradigm>-subblokken (labels daarin niet meenemen)
    3. Pak de eerste <label> → woordsoort op lemma-niveau
    4. Match via WOORDSOORT_PREFIXES (specifiek → algemeen)
    5. Voor zelfstandig naamwoord: artikel+genus uit de label-string parsen
    6. Voor werkwoord: pak <lemma> uit hetzelfde blok (= infinitief)
    7. Dedupliceer op display-string

    Retourneert geordende lijst van dicts met sleutels:
      display, article, gender, lemma
    """
    blocks = re.findall(r'<found_lemmata>.*?</found_lemmata>', xml, re.DOTALL)
    seen_displays = set()
    entries = []

    for block in blocks:
        # Strip paradigm-blokken zodat labels daarin niet meekomen
        clean_block = re.sub(r'<paradigm>.*?</paradigm>', '', block, flags=re.DOTALL)

        # Eerste <label> in het blok is de woordsoort op lemma-niveau.
        # Meerdere labels in hetzelfde blok zijn genus-varianten van hetzelfde lemma
        # (bijv. zn(m) én zn(o)) — we nemen alleen de eerste, anders dubbele entries.
        labels_in_block = re.findall(r'<label>(.*?)</label>', clean_block)
        if not labels_in_block or not labels_in_block[0]:
            continue
        label = labels_in_block[0]

        # Lemma voor dit blok
        lemma_match = re.search(r'<lemma>(.*?)</lemma>', clean_block)
        entry_lemma = lemma_match.group(1) if lemma_match else word

        # Bepaal display en artikel/genus via WOORDSOORT_PREFIXES
        display = None
        article = None
        gender = None

        matched = False
        for prefix, mapping in WOORDSOORT_PREFIXES:
            if label.startswith(prefix):
                matched = True
                if mapping is None:
                    # Zelfstandig naamwoord: genus uit label parsen
                    genus_match = re.search(r'\(([^)]+)\)', label)
                    genus_raw = genus_match.group(1) if genus_match else ''
                    genus_core = re.sub(r',.*', '', genus_raw).strip()  # 'm' uit 'm, afkorting'
                    if genus_core == 'o':
                        article = 'het'
                    elif '/' in genus_core and 'o' in genus_core:
                        article = 'de/het'
                    else:
                        article = 'de'
                    gender = genus_core if genus_core else None
                    display = "zelfstandig naamwoord"
                elif mapping == 'zelfstandignaamwoordgroep':
                    display = mapping
                    # Genus uit lemma_part_of_speech (bijv. NOU-C(gender=f,number=sg))
                    pos_m = re.search(r'<lemma_part_of_speech>(.*?)</lemma_part_of_speech>', clean_block)
                    lemma_pos = pos_m.group(1) if pos_m else ''
                    gc_m = re.search(r'gender=([^,)]+)', lemma_pos)
                    if gc_m:
                        _G = {'f': 'v', 'm': 'm', 'n': 'o'}
                        gc = gc_m.group(1)
                        gender = '/'.join(_G.get(c, c) for c in gc.split('/'))
                        article = 'het' if gender == 'o' else ('de/het' if 'o' in gender else 'de')
                elif mapping == 'RAW':
                    display = label
                else:
                    display = mapping
                break

        if not matched:
            # Fallback: toon raw label
            display = label

        # Vervang volledige naam door afkorting (indien beschikbaar)
        # Exacte match, anders prefix-match (bijv. 'persoonlijk voornaamwoord (1e persoon enkelvoud)')
        if display in POS_AFKORTINGEN:
            display = POS_AFKORTINGEN[display]
        else:
            for key, short in POS_AFKORTINGEN.items():
                if display.startswith(key):
                    display = short + display[len(key):]
                    break

        # Strip persoonsvorm-subtype van voornaamwoorden (bijv. 'pers. vnw. (1e persoon enkelvoud)' → 'pers. vnw.')
        if 'vnw.' in display:
            display = re.sub(r'\s*\(.*\)$', '', display).strip()

        # Meervoud-vlag: naamwoord waarvan het lemma afwijkt van het gezochte woord
        is_meervoud = (display == 'znw.' and entry_lemma.lower() != word.lower())

        # Dedupliceer — meervoud-entries samenvoegen tot één regel;
        # lemma meenemen zodat 'weegschaal' en 'Weegschaal' als aparte entries gelden,
        # maar twee identieke 'Weegschaal'-blokken met zelfde genus wél dedupliceren.
        dedup_key = "znw.|mv." if is_meervoud else f"{display}|{article}|{gender}|{entry_lemma}"
        if dedup_key in seen_displays:
            continue
        seen_displays.add(dedup_key)

        entries.append({
            'display': display,
            'article': article,
            'gender': gender,
            'lemma': entry_lemma,
            'is_meervoud': is_meervoud,
        })

    return entries


# --- KERNFUNCTIE: WOORDCONTROLE VIA API ---
def check_word_online(word):
    """Strikte controle, alleen lemma's - retourneert (is_valid, word, error_message, article, word_info, gender, gender_info_list).
    Verwacht een al-genormaliseerd woord (apostrofs zijn al omgezet door perform_check)."""
    if not word or not word.strip():
        print("[Info] Klembord is leeg, actie geannuleerd.")
        return False, word, None, None, None, None, None

    word_normalized = word

    api_url = "https://woordenlijst.org/MolexServe/lexicon/find_wordform"

    params = {
        "database": "gig_pro_wrdlst",
        "wordform": word_normalized.strip(),
        "part_of_speech": "",
        "paradigm": "true",
        "diminutive": "true",
        "onlyvalid": "true",
        "regex": "false",
        "dummy": str(int(time.time() * 1000))
    }

    print(f"[Check] Bezig met controleren van '{word_normalized}'...")

    try:
        response = requests.get(api_url, params=params, timeout=5)
        response.raise_for_status()

        xml_content = response.text

        if "<found_lemmata>" in xml_content:
            # Vind alle wordforms en lemma's
            wordforms = re.findall(r'<wordform>(.*?)</wordform>', xml_content)
            lemmas = [l for l in re.findall(r'<lemma>(.*?)</lemma>', xml_content) if l]

            # Extraheer alle woordsoort-entries via de nieuwe helperfunctie
            entries = _extract_woordsoort_entries(xml_content, word_normalized)

            # Bepaal article en gender voor backward-compat. (enkelvoudig naamwoord)
            article = None
            gender = None
            gender_info_list = None  # niet meer in gebruik; popup leest word_info['entries']

            noun_entries = [e for e in entries if e.get('article')]
            if noun_entries:
                article = noun_entries[0]['article']
                gender = noun_entries[0]['gender']

            # Sla alle entries op in word_info
            word_info = {'entries': entries} if entries else None

            # Meervoud-detectie (case-insensitief: API retourneert altijd kleine letters)
            wn_lower = re.escape(word_normalized.lower())
            paradigm_blocks = re.findall(r'<paradigm>.*?</paradigm>', xml_content, re.DOTALL)

            # Breed (over volledige XML): voor de artikel-override bij pure meervoudsvormen
            is_plural = bool(re.search(
                r'<label>meervoud</label>.*?<wordform>' + wn_lower + r'</wordform>',
                xml_content, re.DOTALL
            ))

            # Per-blok: woord als meervoud binnen één paradigmablock (voor invariant naamwoord)
            is_meervoud_in_block = any(
                re.search(r'<label>meervoud</label>', block) and
                re.search(r'<wordform>' + wn_lower + r'</wordform>', block)
                for block in paradigm_blocks
            )

            # Per-blok: woord ook als enkelvoud binnen één paradigmablock
            is_also_singular = any(
                re.search(r'<label>enkelvoud</label>', block) and
                re.search(r'<wordform>' + wn_lower + r'</wordform>', block)
                for block in paradigm_blocks
            )

            if is_plural and not is_also_singular:
                article = 'de'
                gender = None
                print(f"[Info] Meervoudsvorm - lidwoord is altijd 'de'")
                # Markeer znw. groep-entries ook als meervoud (bijv. 'happy few', 'ins en outs')
                for e in entries:
                    if e.get('display') == 'znw. groep':
                        e['is_meervoud'] = True

            # Invariant naamwoord (bijv. chassis): per-blok zowel enkelvoud als meervoud
            # Niet toevoegen als er al een meervoud-entry is (bijv. 'kussen' = mv. van 'kus')
            already_has_meervoud = any(e.get('is_meervoud') for e in entries)
            if is_meervoud_in_block and is_also_singular and entries and not already_has_meervoud:
                entries.append({
                    'display': 'znw.',
                    'article': None,
                    'gender': entries[0].get('gender'),
                    'lemma': entries[0].get('lemma', word_normalized),
                    'is_meervoud': True,
                })
                word_info = {'entries': entries}
                print(f"[Info] Invariant naamwoord - ook meervoud toegevoegd")

            # Finale output
            if entries:
                print(f"[Info] {len(entries)} woordsoort-entr{'y' if len(entries)==1 else 'ies'} gevonden")
                for e in entries:
                    if e.get('article') and e.get('gender'):
                        print(f"  - {e['display']}: {e['article']} ({e['gender']})")
                    else:
                        print(f"  - {e['display']}")
            else:
                print("[Info] Geen woordsoort-entries gevonden")

            # NIEUWE CHECK: is het ingevoerde woord zelf een lemma?
            if word_normalized in lemmas:
                print(f"[Resultaat] '{word}' is GEVONDEN (officiële spelling).")
                return True, word, None, article, word_info, gender, gender_info_list

            # CHECK 1: zijn er lemma's met interne hoofdletters?
            has_internal_caps_lemma = any(
                any(c.isupper() for c in lemma[1:])
                for lemma in lemmas
            )

            if has_internal_caps_lemma:
                # STRIKTE MODUS: alleen lemma's EN correcte wordforms met juiste hoofdletters
                if word_normalized in wordforms:
                    # Vind een vergelijkbaar lemma om het patroon te checken
                    base_lemma = None
                    for lemma in lemmas:
                        if any(c.isupper() for c in lemma[1:]):
                            # Dit lemma heeft interne hoofdletters
                            if word_normalized.lower().startswith(lemma.lower()[:5]):
                                base_lemma = lemma
                                break

                    if base_lemma:
                        # Check of ALLE hoofdletters exact overeenkomen
                        min_len = min(len(base_lemma), len(word_normalized))

                        # Vergelijk ALLE karakters op hoofdletter/kleine letter
                        exact_match = True
                        for i in range(min_len):
                            if base_lemma[i].isupper() != word_normalized[i].isupper():
                                exact_match = False
                                break

                        if exact_match:
                            print(f"[Resultaat] '{word}' is GEVONDEN.")
                            return True, word, None, article, word_info, gender, gender_info_list

                # Niet goedgekeurd - geef feedback
                relevant_lemmas = [l for l in lemmas if any(c.isupper() for c in l[1:])]
                if relevant_lemmas:
                    error_msg = f"Gebruik '{relevant_lemmas[0]}'"
                    print(f"[Resultaat] '{word}' is NIET correct ({error_msg}).")
                    return False, word, error_msg, None, None, None, None
                else:
                    print(f"[Resultaat] '{word}' is NIET correct gespeld.")
                    return False, word, "Controleer de spelling", None, None, None, None

            # CHECK 2: hoofdlettergevoelige woorden (pH, mkb, etc.)
            for lemma in lemmas:
                if lemma.lower() == word_normalized.lower() and lemma != word_normalized:
                    lowercase_versions = [l for l in lemmas if l == word_normalized.lower()]
                    uppercase_versions = [l for l in lemmas if l[0].isupper() and l.lower() == word_normalized.lower()]

                    if lowercase_versions and uppercase_versions:
                        continue

                    # Zin-beginwoord (bijv. 'Fiets'): alleen eerste letter is hoofdletter, rest klein.
                    # Laat de UITZONDERING-check hieronder dit geval afhandelen.
                    is_sentence_caps = (
                        len(word_normalized) > 1 and
                        word_normalized[0].isupper() and
                        word_normalized[1:].islower() and
                        ' ' not in word_normalized
                    )
                    if is_sentence_caps:
                        continue

                    error_msg = f"Gebruik '{lemma}'"
                    print(f"[Resultaat] '{word}' is NIET correct ({error_msg}).")
                    return False, word, error_msg, None, None, None, None

            # UITZONDERING: enkelvoudig woord met alleen eerste hoofdletter (Fiets)
            if (len(word_normalized) > 1 and
                word_normalized[0].isupper() and
                word_normalized[1:].islower() and
                ' ' not in word_normalized): # Enkelvoudige woorden

                if word_normalized.lower() in wordforms or word_normalized.lower() in lemmas:
                    print(f"[Resultaat] '{word}' is GEVONDEN (hoofdletter toegestaan).")
                    return True, word, None, article, word_info, gender, gender_info_list

            # NORMALE MODUS: geen speciale hoofdletters, accepteer wordforms
            if word_normalized in wordforms or word_normalized in lemmas:
                print(f"[Resultaat] '{word}' is GEVONDEN.")
                return True, word, None, article, word_info, gender, gender_info_list

            print(f"[Resultaat] '{word}' is NIET correct gespeld.")
            return False, word, "Controleer de spelling", None, None, None, None
        else:
            # WOORD NIET GEVONDEN - VRAAG SUGGESTIES OP
            print(f"[Resultaat] '{word}' is NIET gevonden.")

            # Haal suggesties op via spellcheck API
            suggestions = get_spelling_suggestions(word_normalized)

            if suggestions:
                error_msg = f"Bedoelde u: {suggestions}"
                return False, word, error_msg, None, None, None, None
            else:
                return False, word, None, None, None, None, None

    except requests.exceptions.RequestException as e:
        print(f"[Fout] Netwerkfout bij API-aanroep: {e}")
        return False, word, "Netwerkfout - controleer uw verbinding", None, None, None, None
    except Exception as e:
        print(f"[Fout] Onverwachte fout tijdens controle: {e}")
        return False, word, "Er is een fout opgetreden", None, None, None, None

def get_spelling_suggestions(word):
    """Haal spellingsuggesties op via de spellcheck API"""
    try:
        spellcheck_url = "https://woordenlijst.org/MolexServe/lexicon/spellcheck"

        params = {
            "database": "gig_pro_wrdlst",
            "word": word,
            "part_of_speech": "",
            "dummy": str(int(time.time() * 1000))
        }

        response = requests.get(spellcheck_url, params=params, timeout=5)
        response.raise_for_status()

        xml_content = response.text

        # Zoek naar corrections (meerdere suggesties gescheiden door |)
        corrections_match = re.search(r'<corrections>(.*?)</corrections>', xml_content)
        if corrections_match:
            corrections = corrections_match.group(1)
            if corrections:
                # Splits op | en maak het netjes; dedupliceer met behoud van volgorde
                seen = set()
                suggestions = []
                for s in corrections.split('|'):
                    s = s.strip()
                    if s and s not in seen:
                        seen.add(s)
                        suggestions.append(s)
                return ' / '.join(suggestions[:3])  # Max 3 suggesties

        # Als geen corrections, probeer best_guess
        best_guess_match = re.search(r'<best_guess>(.*?)</best_guess>', xml_content)
        if best_guess_match:
            best_guess = best_guess_match.group(1)
            if best_guess:
                return best_guess

        return None

    except Exception as e:
        print(f"[Waarschuwing] Kon geen suggesties ophalen: {e}")
        return None

# --- PRISMA ALTERNATIEVE SPELLING ---
def check_prisma_alternatief(word):
    """Controleer of een woord een alternatieve spelling is op spelling.prisma.nl.
    Retourneert (alternatief_woord, officiele_spelling, url) of None als er geen alternatief is."""
    try:
        base = "https://spelling.prisma.nl"
        sess = requests.Session()
        sess.headers.update({
            "User-Agent": "Mozilla/5.0",
            "Referer": base + "/",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        })
        sess.get(base + "/", timeout=5)

        r = sess.get(f"{base}/?id=-827&unitsearch={quote(word)}", timeout=5)
        r.raise_for_status()

        unitname_match = re.search(
            r'<div class="unitname"[^>]*id="U(\d+)"[^>]*>(.*?)</div>',
            r.text, re.DOTALL
        )
        if not unitname_match:
            return None

        cid = unitname_match.group(1)
        unitname_html = unitname_match.group(2)

        # Type A: 'alternatief' label staat in de unitname div zelf (unitname = witte, lref = groene)
        # Type B: 'alternatief' label staat elders op de pagina (unitname = groene, lref = witte)
        type_a = '<span class="la">alternatief</span>' in unitname_html
        type_b = not type_a and '<span class="la">alternatief</span>' in r.text

        if not type_a and not type_b:
            return None

        lref_match = re.search(r'<a href="[^"]+" class="lref">([^<]+)</a>', r.text)

        if type_a:
            # Type A: unitname = witte spelling, lref = groene spelling
            # Verwijder eerst het volledige <span class="la">alternatief</span> element
            # (inclusief tekst) vóór de overige tags worden gestript.
            cleaned_unitname = re.sub(r'<span class="la">alternatief</span>', '', unitname_html)
            alt_word = html.unescape(re.sub(r'<[^>]*>', '', cleaned_unitname).strip())
            officiele_spelling = html.unescape(lref_match.group(1)) if lref_match else None
        else:
            # Type B: lref = witte spelling, unitname = groene spelling
            alt_word = html.unescape(lref_match.group(1)) if lref_match else None
            officiele_spelling = html.unescape(re.sub(r'<[^>]*>', '', unitname_html).strip())

        if not alt_word:
            return None

        url = f"{base}/?id=-827&cid={cid}&unitsearch={quote(word)}"
        print(f"[Prisma] Alternatief gevonden: '{alt_word}' (officieel: {officiele_spelling})")
        return alt_word, officiele_spelling, url

    except Exception as e:
        print(f"[Waarschuwing] Kon Prisma niet raadplegen: {e}")
        return None

# --- GEDEELDE POPUP HULPFUNCTIES ---
def _set_icon(window):
    """Stel favicon.ico in op een tkinter-venster (werkt zowel als .py als .exe)"""
    try:
        icon_path = os.path.join(sys._MEIPASS, "favicon.ico") if hasattr(sys, '_MEIPASS') else "favicon.ico"
        if os.path.exists(icon_path):
            window.iconbitmap(icon_path)
    except Exception as e:
        print(f"[Info] Kon icoon niet laden: {e}")

def _bind_drag_save(window):
    """Sla pop-uppositie op zodra het venster wordt verplaatst.

    <Configure> vuurt bij elke pixelbeweging; de drempel van 5 px voorkomt
    onnodige schrijfacties. POPUP_X/POPUP_Y zijn globals die door
    save_popup_position() worden bijgewerkt, zodat de vergelijking altijd
    tegen de meest recent opgeslagen positie werkt.
    """
    def on_drag_end(event):
        if event.widget == window:
            new_x = window.winfo_x()
            new_y = window.winfo_y()
            if abs(new_x - POPUP_X) > 5 or abs(new_y - POPUP_Y) > 5:
                save_popup_position(new_x, new_y)
                print(f"[Info] Nieuwe pop-uppositie opgeslagen: {new_x}, {new_y}")
    window.bind('<Configure>', on_drag_end)


def _get_readme_path():
    """Retourneert het pad naar README.md (werkt zowel als .py als .exe)."""
    base = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, 'README.md')


def _get_over_path():
    """Retourneert het pad naar over.md (werkt zowel als .py als .exe)."""
    base = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, 'over.md')


def _render_inline(text_widget, line, link_counter):
    """Render een tekstregel met inline markdown-links naar een tkinter Text-widget."""
    pattern = r'\[([^\]]+)\]\(([^)]+)\)|(https?://\S+)'
    last_end = 0
    for m in re.finditer(pattern, line):
        if m.start() > last_end:
            text_widget.insert('end', line[last_end:m.start()], 'normal')
        tag = f'link_{link_counter[0]}'
        link_counter[0] += 1
        if m.group(1):
            link_text, link_url = m.group(1), m.group(2)
        else:
            link_url = m.group(3).rstrip()
            link_text = link_url
        text_widget.tag_configure(tag, foreground='blue', underline=True)
        text_widget.insert('end', link_text, tag)
        text_widget.tag_bind(tag, '<Button-1>', lambda e, u=link_url: os.startfile(u))
        last_end = m.end()
    if last_end < len(line):
        text_widget.insert('end', line[last_end:], 'normal')


def show_help_popup():
    """Toon een scrollbaar help-venster op basis van README.md."""
    if threading.current_thread() is not threading.main_thread():
        done = threading.Event()
        def _dispatch():
            show_help_popup()
            done.set()
        _popup_root.after(0, _dispatch)
        done.wait()
        return
    try:
        popup = tk.Toplevel(_popup_root)
        popup.title("Help – Woordenlijst-checker")
        popup.resizable(True, True)
        popup.attributes('-topmost', True)
        _set_icon(popup)
        popup_width, popup_height = 540, 460
        x = int(_popup_root.winfo_screenwidth() / 2 - popup_width / 2)
        y = int(_popup_root.winfo_screenheight() / 2 - popup_height / 2)
        popup.geometry(f"{popup_width}x{popup_height}+{x}+{y}")

        close_frame = tk.Frame(popup)
        close_frame.pack(side='bottom', fill='x', pady=(10, 10))
        tk.Button(close_frame, text="Sluiten", command=popup.destroy, width=10).pack(side='right', padx=15)

        frame = tk.Frame(popup)
        frame.pack(fill='both', expand=True, padx=10, pady=(10, 5))
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side='right', fill='y')
        text = tk.Text(
            frame, wrap='word', yscrollcommand=scrollbar.set,
            font=("Arial", 10), padx=10, pady=5,
            cursor='arrow', state='normal', relief='flat', borderwidth=0
        )
        text.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=text.yview)

        text.tag_configure('h1', font=("Arial", 14, "bold"), spacing1=10, spacing3=4)
        text.tag_configure('h2', font=("Arial", 11, "bold"), spacing1=8, spacing3=2)
        text.tag_configure('normal', font=("Arial", 10))

        readme_path = _get_readme_path()
        if os.path.exists(readme_path):
            with open(readme_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            link_counter = [0]
            for line in lines:
                stripped = line.rstrip('\n').rstrip()
                if stripped.startswith('# '):
                    text.insert('end', stripped[2:] + '\n', 'h1')
                elif stripped.startswith('## '):
                    text.insert('end', stripped[3:] + '\n', 'h2')
                elif stripped.startswith('- '):
                    _render_inline(text, '•  ' + stripped[2:] + '\n', link_counter)
                elif stripped == '':
                    text.insert('end', '\n', 'normal')
                else:
                    _render_inline(text, stripped + '\n', link_counter)
        else:
            text.insert('end', 'README.md niet gevonden.', 'normal')

        text.config(state='disabled')
        popup.bind('<Escape>', lambda e: popup.destroy())
        _popup_root.wait_window(popup)
    except Exception as e:
        print(f"[Fout] Kon helppop-up niet tonen: {e}")


def show_over_popup():
    """Toon een 'Over'-venster op basis van over.md met ondersteuning voor klikbare links."""
    if threading.current_thread() is not threading.main_thread():
        done = threading.Event()
        def _dispatch():
            show_over_popup()
            done.set()
        _popup_root.after(0, _dispatch)
        done.wait()
        return
    try:
        popup = tk.Toplevel(_popup_root)
        popup.title("Over – Woordenlijst-checker")
        popup.resizable(False, False)
        popup.attributes('-topmost', True)
        _set_icon(popup)
        popup_width, popup_height = 400, 300
        x = int(_popup_root.winfo_screenwidth() / 2 - popup_width / 2)
        y = int(_popup_root.winfo_screenheight() / 2 - popup_height / 2)
        popup.geometry(f"{popup_width}x{popup_height}+{x}+{y}")

        btn_frame = tk.Frame(popup)
        btn_frame.pack(side='bottom', fill='x', pady=(10, 10))
        tk.Button(btn_frame, text="Controleer op updates", command=lambda: threading.Thread(target=controleer_op_updates).start()).pack(side='left', padx=15)
        tk.Button(btn_frame, text="Sluiten", command=popup.destroy, width=10).pack(side='right', padx=15)

        text = tk.Text(
            popup, wrap='word',
            font=("Arial", 10), padx=15, pady=10,
            cursor='arrow', state='normal', relief='flat', borderwidth=0
        )
        text.pack(fill='both', expand=True)

        text.tag_configure('h1', font=("Arial", 13, "bold"), spacing1=6, spacing3=4)
        text.tag_configure('normal', font=("Arial", 10))

        over_path = _get_over_path()
        if os.path.exists(over_path):
            with open(over_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            link_counter = [0]
            for line in lines:
                stripped = line.rstrip('\n').rstrip()
                if stripped.startswith('# '):
                    text.insert('end', stripped[2:] + '\n', 'h1')
                elif stripped == '':
                    text.insert('end', '\n', 'normal')
                else:
                    _render_inline(text, stripped + '\n', link_counter)
        else:
            text.insert('end', f"Woordenlijst-checker v{VERSION}\n\nover.md niet gevonden.", 'normal')

        text.config(state='disabled')
        popup.bind('<Escape>', lambda e: popup.destroy())
        _popup_root.wait_window(popup)
    except Exception as e:
        print(f"[Fout] Kon over-pop-up niet tonen: {e}")


def controleer_op_updates():
    """Haal het versienummer op uit version.txt in de repository en vergelijk met VERSION."""
    try:
        response = requests.get(UPDATE_CHECK_URL, timeout=5)
        response.raise_for_status()
        nieuwste = response.text.strip()
        try:
            nieuwste_tuple = tuple(int(x) for x in nieuwste.split('.'))
            huidig_tuple  = tuple(int(x) for x in VERSION.split('.'))
        except ValueError:
            nieuwste_tuple = (0,)
            huidig_tuple   = (1,)
        if nieuwste_tuple <= huidig_tuple:
            bericht = f"U gebruikt de nieuwste versie ({VERSION})."
            titel = "Geen updates beschikbaar"
            def _toon():
                ouder = tk.Toplevel(_popup_root)
                ouder.withdraw()
                ouder.attributes('-topmost', True)
                messagebox.showinfo(titel, bericht, parent=ouder)
                ouder.destroy()
            _popup_root.after(0, _toon)
        else:
            RELEASES_URL = "https://github.com/ErwinVanWouw/Woordenlijst-checker/releases"
            def _toon():
                popup = tk.Toplevel(_popup_root)
                popup.title("Update beschikbaar")
                popup.configure(bg='white')
                popup.resizable(False, False)
                popup.attributes('-topmost', True)
                _set_icon(popup)

                frame = tk.Frame(popup, bg='white', padx=20, pady=16)
                frame.pack(fill='both', expand=True)

                tk.Label(frame,
                         text=f"Er is een nieuwe versie beschikbaar: {nieuwste}",
                         font=("Arial", 11), bg='white').pack(anchor='w')
                tk.Label(frame,
                         text=f"U heeft versie {VERSION}.",
                         font=("Arial", 11), bg='white').pack(anchor='w', pady=(2, 10))

                link = tk.Label(frame, text="Download van GitHub Releases",
                                font=("Arial", 11, "underline"), fg='blue',
                                cursor='hand2', bg='white')
                link.pack(anchor='w')
                link.bind('<Button-1>', lambda e: os.startfile(RELEASES_URL))

                tk.Button(frame, text="Sluiten", command=popup.destroy,
                          font=("Arial", 10)).pack(anchor='e', pady=(14, 0))

                popup.update_idletasks()
                w, h = popup.winfo_reqwidth(), popup.winfo_reqheight()
                x, y = get_center_position(w, h)
                popup.geometry(f"{w}x{h}+{x}+{y}")
            _popup_root.after(0, _toon)
    except Exception as e:
        print(f"[Fout] Updatecontrole mislukt: {e}")
        def _toon_fout():
            ouder = tk.Toplevel(_popup_root)
            ouder.withdraw()
            ouder.attributes('-topmost', True)
            messagebox.showwarning(
                "Updatecontrole mislukt",
                "Kon de updateserver niet bereiken.\nControleer uw internetverbinding.",
                parent=ouder
            )
            ouder.destroy()
        _popup_root.after(0, _toon_fout)


def show_config_popup():
    """Toon instellingenvenster voor sneltoets en pop-uppositie."""
    if threading.current_thread() is not threading.main_thread():
        done = threading.Event()
        def _dispatch():
            show_config_popup()
            done.set()
        _popup_root.after(0, _dispatch)
        done.wait()
        return
    try:
        global HOTKEY, POPUP_X, POPUP_Y
        popup = tk.Toplevel(_popup_root)
        popup.title("Instellingen")
        popup.resizable(False, False)
        popup.attributes('-topmost', True)
        _set_icon(popup)
        popup_width, popup_height = 380, 230
        x = int(_popup_root.winfo_screenwidth() / 2 - popup_width / 2)
        y = int(_popup_root.winfo_screenheight() / 2 - popup_height / 2)
        popup.geometry(f"{popup_width}x{popup_height}+{x}+{y}")

        close_frame = tk.Frame(popup)
        close_frame.pack(side='bottom', fill='x', pady=(10, 10))
        tk.Button(close_frame, text="Sluiten", command=popup.destroy, width=10).pack(side='right', padx=15)

        content = tk.Frame(popup)
        content.pack(fill='both', expand=True, padx=15, pady=(15, 0))

        sneltoets_frame = tk.Frame(content)
        sneltoets_frame.pack(anchor='w', pady=(5, 0))
        tk.Label(sneltoets_frame, text="Sneltoets:", font=("Arial", 10)).pack(side='left')
        hotkey_var = tk.StringVar(value=HOTKEY)
        hotkey_entry = tk.Entry(sneltoets_frame, textvariable=hotkey_var, width=20, font=("Arial", 10))
        hotkey_entry.pack(side='left', padx=(8, 0))

        tk.Button(content, text="Wijzig", command=lambda: sla_hotkey_op(), width=12).pack(anchor='w', pady=(8, 0))

        status_label = tk.Label(content, text="", font=("Arial", 9), fg='gray')
        status_label.pack(anchor='w', pady=(4, 0))

        def sla_hotkey_op():
            global HOTKEY
            new_hotkey = hotkey_var.get().strip().lower()
            if not new_hotkey:
                status_label.config(text="Sneltoets mag niet leeg zijn.", fg='red')
                return
            old_hotkey = HOTKEY  # Bewaar huidige waarde voor eventuele herstelactie
            try:
                keyboard.unhook_all()  # Ruimt ook een eventueel defecte hook op
            except Exception:
                pass
            try:
                keyboard.add_hotkey(new_hotkey, lambda: threading.Thread(target=perform_check).start())
                HOTKEY = new_hotkey  # Pas global pas aan na succesvolle registratie
                config = configparser.ConfigParser()
                config.read(CONFIG_FILE)
                if 'Settings' not in config:
                    config['Settings'] = {}
                config['Settings']['hotkey'] = new_hotkey
                with open(CONFIG_FILE, 'w') as f:
                    config.write(f)
                status_label.config(text=f"Opgeslagen: '{new_hotkey}'", fg='green')
                print(f"[Config] Sneltoets gewijzigd naar: '{new_hotkey}'")
            except Exception as e:
                status_label.config(text="Ongeldige sneltoets.", fg='red')
                print(f"[Config] Ongeldige sneltoets '{new_hotkey}': {e}")
                try:
                    keyboard.unhook_all()
                    keyboard.add_hotkey(old_hotkey, lambda: threading.Thread(target=perform_check).start())
                except Exception:
                    pass

        def reset_positie():
            global POPUP_X, POPUP_Y
            POPUP_X = -1
            POPUP_Y = -1
            config = configparser.ConfigParser()
            config.read(CONFIG_FILE)
            if 'Settings' not in config:
                config['Settings'] = {}
            config['Settings']['popup_x'] = '-1'
            config['Settings']['popup_y'] = '-1'
            with open(CONFIG_FILE, 'w') as f:
                config.write(f)
            status_label.config(text="Pop-uppositie gereset naar centrum.", fg='green')
            print("[Config] Pop-uppositie gereset")

        tk.Label(content, text="Positie van pop-ups opnieuw instellen.", font=("Arial", 10)).pack(anchor='w', pady=(15, 0))
        tk.Button(content, text="Reset positie", command=reset_positie, width=14).pack(anchor='w', pady=(4, 0))

        popup.bind('<Escape>', lambda e: popup.destroy())
        _popup_root.wait_window(popup)
    except Exception as e:
        print(f"[Fout] Kon instellingenpop-up niet tonen: {e}")


# --- NOTIFICATIE FUNCTIES ---
def show_success_popup(word, article=None, word_info=None, gender=None, gender_info_list=None):
    """Toon 3 seconden pop-up met groen vinkje en optioneel lidwoord met gender"""
    if threading.current_thread() is not threading.main_thread():
        done = threading.Event()
        def _dispatch():
            show_success_popup(word, article, word_info, gender, gender_info_list)
            done.set()
        _popup_root.after(0, _dispatch)
        done.wait()
        return
    try:
        root = _popup_root

        # Maak aangepast pop-upvenster
        popup = tk.Toplevel(root)
        popup.title("Gevonden")
        popup.configure(bg='white')

        _set_icon(popup)

        # Bepaal pop-upgrootte op basis van inhoud
        entries = word_info.get('entries', []) if word_info else []

        # Normaliseer beginhoofdletter naar onderkast voor weergave, maar alleen als
        # het lemma in de woordenlijst zelf ook met een onderkastletter begint.
        # Woorden als 'Excelfile' hebben een echt hoofdletter-lemma en worden niet aangepast.
        # Woorden met interne hoofdletters (NMa, CdK) vallen al buiten de is_sentence_caps-check.
        primary_lemma = entries[0].get('lemma', '') if entries else ''
        _is_sentence_caps = (len(word) > 1 and word[0].isupper() and word[1:].islower()
                             and not (primary_lemma and primary_lemma[0].isupper()))
        display_word = word.lower() if _is_sentence_caps else word

        def _entry_display_word(e):
            """Geeft het te tonen woord terug: lemma als dat alleen in beginkapitaal afwijkt."""
            lm = e.get('lemma', word)
            return lm if (lm and lm.lower() == word.lower()) else display_word

        def _entry_display_len(e):
            dw = _entry_display_word(e)
            disp = e.get('display', '')
            if e.get('is_meervoud'):
                g = e.get('gender')
                suffix = f" ({g})" if g else ""
                return len(f"'{dw}'  {disp} mv.{suffix}")
            elif e.get('article') and e.get('gender'):
                return len(f"'{dw}'  {e['article']} ({e['gender']})")
            elif e.get('article'):
                return len(f"'{dw}'  {e['article']}")
            elif disp:
                return len(f"'{dw}'  {disp}")
            return len(f"'{dw}'")

        if len(entries) > 1:
            popup_height = 150 + (len(entries) - 1) * 25 + 10
            max_line_len = max(_entry_display_len(e) for e in entries)
        else:
            popup_height = 160
            entry0 = entries[0] if entries else None
            if entry0 and entry0.get('is_meervoud'):
                disp0 = entry0.get('display', 'znw.')
                g = entry0.get('gender')
                suffix = f" ({g})" if g else ""
                first_line = f"'{display_word}'  {disp0} mv.{suffix}"
            elif entry0 and entry0.get('display') and not entry0.get('article'):
                # znw. groep zonder gender, of display-only entry (ww., bw., etc.)
                first_line = f"'{display_word}'  {entry0['display']}"
            elif article:
                first_line = (f"'{display_word}'  {article} ({gender})" if gender
                              else f"'{display_word}'  {article}")
            else:
                disp0 = entry0.get('display') if entry0 else None
                first_line = f"'{display_word}'  {disp0}" if disp0 else f"'{display_word}'"
            max_line_len = max(len(first_line), len("staat in Woordenlijst.org"))

        # Bereken benodigde breedte op basis van tekstlengte
        estimated_width = max_line_len * 8 + 200
        min_width = 350
        max_width = 600
        popup_width = max(min_width, min(estimated_width, max_width))

        # Positioneer pop-up (opgeslagen positie of centrum)
        x, y = get_popup_position(popup_width, popup_height)
        popup.geometry(f"{popup_width}x{popup_height}+{x}+{y}")

        # Geen resize en altijd bovenop
        popup.resizable(False, False)
        popup.attributes('-topmost', True)

        _bind_drag_save(popup)

        # Frame voor content
        frame = tk.Frame(popup, bg='white')
        frame.pack(expand=True, fill='both', padx=20, pady=20)

        # Groen vinkje
        check_label = tk.Label(frame, text="✓", font=("Arial", 48), fg='green', bg='white')
        check_label.pack(side='left', padx=10)

        # Woordlabels die klikbaar worden na een muisklik in de pop-up
        word_labels = []  # lijst van (label, url) tuples

        # Opmaak voor meerdere woordsoort-entries
        if len(entries) > 1:
            text_frame = tk.Frame(frame, bg='white')
            text_frame.pack(side='left', padx=10)

            # Maak regel voor elke entry (alleen eerste woord wordt klikbaar)
            for i, entry in enumerate(entries):
                line_frame = tk.Frame(text_frame, bg='white')
                line_frame.pack(anchor='w')

                # Toon lemma als het alleen in beginkapitaal afwijkt (bijv. 'Weegschaal')
                dw = _entry_display_word(entry)
                word_lbl = tk.Label(line_frame, text=f"'{dw}'", font=("Arial", 12), bg='white')
                word_lbl.pack(side='left')
                if i == 0:
                    word_labels.append((word_lbl, f"https://woordenlijst.org/zoeken/?q={quote(dw)}"))

                disp = entry.get('display', '')
                if entry.get('is_meervoud'):
                    # Meervoudsvorm van naamwoord
                    g = entry.get('gender')
                    suffix = f" ({g})" if g else ""
                    tk.Label(line_frame, text=f"  {disp} mv.{suffix}", font=("Arial", 12), bg='white').pack(side='left')
                elif entry.get('article') and entry.get('gender'):
                    # Enkelvoudig naamwoord met geslacht — 'znw.' weglaten, lidwoord+gender volstaat
                    tk.Label(line_frame, text=f"  {entry['article']}", font=("Arial", 12, "italic"), bg='white').pack(side='left')
                    tk.Label(line_frame, text=f" ({entry['gender']})", font=("Arial", 12), bg='white').pack(side='left')
                elif entry.get('article'):
                    # Naamwoord zonder geslacht
                    tk.Label(line_frame, text=f"  {entry['article']}", font=("Arial", 12, "italic"), bg='white').pack(side='left')
                elif disp:
                    # Werkwoord / bijwoord / voegwoord / etc.
                    tk.Label(line_frame, text=f"  {disp}", font=("Arial", 12), bg='white').pack(side='left')

            # "staat in Woordenlijst.org" regel
            tk.Label(text_frame, text="staat in Woordenlijst.org", font=("Arial", 12), bg='white').pack(anchor='w', pady=(10,0))

        elif article and gender:
            # Enkele naamwoord-entry
            text_frame = tk.Frame(frame, bg='white')
            text_frame.pack(side='left', padx=10)

            first_line_frame = tk.Frame(text_frame, bg='white')
            first_line_frame.pack(anchor='w')

            word_lbl = tk.Label(first_line_frame, text=f"'{display_word}'", font=("Arial", 12), bg='white')
            word_lbl.pack(side='left')
            word_labels.append((word_lbl, f"https://woordenlijst.org/zoeken/?q={quote(display_word)}"))
            tk.Label(first_line_frame, text=f"  {article}", font=("Arial", 12, "italic"), bg='white').pack(side='left')
            tk.Label(first_line_frame, text=f" ({gender})", font=("Arial", 12), bg='white').pack(side='left')

            tk.Label(text_frame, text="staat in Woordenlijst.org", font=("Arial", 12), bg='white').pack(anchor='w', pady=(10,0))

        elif len(entries) == 1 and not article:
            # Enkele niet-naamwoord entry (werkwoord, voegwoord, bijwoord, etc.)
            entry = entries[0]
            text_frame = tk.Frame(frame, bg='white')
            text_frame.pack(side='left', padx=10)

            first_line_frame = tk.Frame(text_frame, bg='white')
            first_line_frame.pack(anchor='w')

            word_lbl = tk.Label(first_line_frame, text=f"'{display_word}'", font=("Arial", 12), bg='white')
            word_lbl.pack(side='left')
            word_labels.append((word_lbl, f"https://woordenlijst.org/zoeken/?q={quote(display_word)}"))

            disp = entry.get('display') or ''
            if disp:
                tk.Label(first_line_frame, text=f"  {disp}", font=("Arial", 12), bg='white').pack(side='left')

            tk.Label(text_frame, text="staat in Woordenlijst.org", font=("Arial", 12), bg='white').pack(anchor='w', pady=(10, 0))

        else:
            # Fallback: woord zonder volledig gestructureerde woordsoort-info
            text_frame = tk.Frame(frame, bg='white')
            text_frame.pack(side='left', padx=10)

            first_line_frame = tk.Frame(text_frame, bg='white')
            first_line_frame.pack(anchor='w')
            word_lbl = tk.Label(first_line_frame, text=f"'{display_word}'", font=("Arial", 12), bg='white')
            word_lbl.pack(side='left')
            word_labels.append((word_lbl, f"https://woordenlijst.org/zoeken/?q={quote(display_word)}"))

            if entries and entries[0].get('is_meervoud'):
                disp0 = entries[0].get('display', 'znw.')
                g = entries[0].get('gender')
                suffix = f" ({g})" if g else ""
                tk.Label(first_line_frame, text=f"  {disp0} mv.{suffix}", font=("Arial", 12), bg='white').pack(side='left')
            elif entries and entries[0].get('display') and not entries[0].get('article'):
                # znw. groep zonder gender: toon alleen display-label (geen lidwoord)
                tk.Label(first_line_frame, text=f"  {entries[0]['display']}", font=("Arial", 12), bg='white').pack(side='left')
            elif article:
                tk.Label(first_line_frame, text=f"  ({article})", font=("Arial", 12, "italic"), bg='white').pack(side='left')

            tk.Label(text_frame, text="staat in Woordenlijst.org", font=("Arial", 12), bg='white').pack(anchor='w', pady=(10, 0))

        # Automatisch sluiten na 3 seconden (annuleerbaar via linkermuisklik)
        auto_close = [None]

        def cancel_auto_close(event=None):
            if auto_close[0] is not None:
                popup.after_cancel(auto_close[0])
                auto_close[0] = None
                # Maak woordlabels klikbaar als hyperlink
                for lbl, url in word_labels:
                    lbl.config(fg='blue', cursor='hand2', font=("Arial", 12, "underline"))
                    lbl.bind('<Button-1>', lambda e, u=url: [os.startfile(u), popup.destroy()])
                # Zet focus op pop-up zodat Enter het venster sluit
                popup.focus_set()
                popup.bind('<Return>', lambda e: popup.destroy())

        auto_close[0] = popup.after(3000, popup.destroy)

        # Bind linkermuisklik op pop-up en alle child-widgets om timer te annuleren
        def bind_click_to_cancel(widget):
            widget.bind('<Button-1>', cancel_auto_close, add=True)
            for child in widget.winfo_children():
                bind_click_to_cancel(child)

        bind_click_to_cancel(popup)

        # Start de GUI-loop
        root.wait_window(popup)

    except Exception as e:
        print(f"[Fout] Kon succespop-up niet tonen: {e}")

def show_failure_popup(word, error_message=None, alternatief_info=None):
    """Toon pop-up voor niet-gevonden woord met Ja/Nee-knoppen en klikbare suggesties"""
    if threading.current_thread() is not threading.main_thread():
        done = threading.Event()
        def _dispatch():
            show_failure_popup(word, error_message, alternatief_info)
            done.set()
        _popup_root.after(0, _dispatch)
        done.wait()
        return
    try:
        url_to_open = f"https://woordenlijst.org/zoeken/?q={quote(word)}"

        root = _popup_root

        # Custom dialog
        dialog = tk.Toplevel(root)
        dialog.title("Niet gevonden")
        dialog.resizable(False, False)
        dialog.attributes('-topmost', True)

        _set_icon(dialog)

        # Invoervak tonen tenzij het een 'Gebruik ...' bericht is
        show_entry = not (error_message and error_message.startswith("Gebruik "))

        # Bepaal hoogte op basis van inhoud
        base_height = 180  # Basishoogte voor titel, knoppen en footer

        # Check of er suggesties zijn
        has_suggestions = error_message and error_message.startswith("Bedoelde u:")
        if has_suggestions:
            # Tel aantal suggesties
            suggestions_text = error_message.replace("Bedoelde u:", "").strip()
            suggestions = [s.strip() for s in suggestions_text.split('/')]
            num_suggestions = min(len(suggestions), 3)  # Max 3
            # Voeg 30 pixels per suggestie toe + 30 voor label "Bedoelde u:"
            extra_height = 30 + (num_suggestions * 30)
        elif error_message:
            # Voor normale foutmelding zoals "Gebruik 'pH'"
            extra_height = 30
        else:
            # Bij geen foutmelding
            extra_height = 0

        if alternatief_info:
            extra_height += 50

        if show_entry:
            extra_height += 55  # Invoervak + Zoek opnieuw-knop

        total_height = base_height + extra_height

        # Positioneer pop-up (opgeslagen positie of centrum)
        x, y = get_popup_position(450, total_height)
        dialog.geometry(f"450x{total_height}+{x}+{y}")

        _bind_drag_save(dialog)

        # Hoofdtekst
        if show_entry:
            main_text = "staat niet in Woordenlijst.org."
        else:
            main_text = f"'{word}'\nstaat niet in Woordenlijst.org."
        tk.Label(dialog, text=main_text, pady=10).pack()

        # Bewerkbaar invoervak met zoekknop
        if show_entry:
            entry_var = tk.StringVar(value=word)
            entry_frame = tk.Frame(dialog)
            entry_frame.pack(pady=(0, 8))

            entry_widget = tk.Entry(entry_frame, textvariable=entry_var, width=20, font=("Arial", 10))
            entry_widget.pack(side='left', padx=(0, 5))

            def zoek_opnieuw(event=None):
                new_word = entry_var.get().strip()
                if not new_word:
                    return
                new_word = re.sub(r"[\u2019\u2018\u0060\u00B4\u02BC]", "'", new_word)
                dialog.destroy()
                def _do_search():
                    if not check_rate_limit():
                        return
                    prisma_result = [None]
                    prisma_thread = threading.Thread(
                        target=lambda: prisma_result.__setitem__(0, check_prisma_alternatief(new_word))
                    )
                    prisma_thread.start()
                    is_valid, checked_word, error_msg, article, word_info, gender, gender_info_list = check_word_online(new_word)
                    if is_valid:
                        show_success_popup(checked_word, article, word_info, gender, gender_info_list)
                    else:
                        prisma_thread.join(timeout=6)
                        prisma_data = None if prisma_thread.is_alive() else prisma_result[0]
                        if checked_word:
                            show_failure_popup(checked_word, error_msg, prisma_data)
                threading.Thread(target=_do_search, daemon=True).start()

            tk.Button(entry_frame, text="Zoek opnieuw", command=zoek_opnieuw).pack(side='left')
            entry_widget.bind('<Return>', zoek_opnieuw)

        # Suggesties of foutmelding
        if error_message:
            # Check of het suggesties zijn (begint met "Bedoelde u:")
            if error_message.startswith("Bedoelde u:"):
                # Toon label "Bedoelde u:"
                tk.Label(dialog, text="Bedoelde u:", font=("Arial", 10, "italic")).pack(pady=(5, 2))

                # Frame voor suggestielinks
                suggestions_frame = tk.Frame(dialog)
                suggestions_frame.pack(pady=5)

                # Haal suggesties uit de foutmelding
                suggestions_text = error_message.replace("Bedoelde u:", "").strip()
                suggestions = [s.strip() for s in suggestions_text.split('/')]

                def open_suggestion_and_close(suggestion):
                    """Open suggestielink en sluit pop-up"""
                    os.startfile(f"https://woordenlijst.org/zoeken/?q={quote(suggestion)}")
                    dialog.destroy()

                for suggestion in suggestions[:3]:
                    link = tk.Label(
                        suggestions_frame,
                        text=suggestion,
                        fg="blue",
                        cursor="hand2",
                        font=("Arial", 10, "underline")
                    )
                    link.pack(pady=2)
                    link.bind("<Button-1>", lambda e, s=suggestion: open_suggestion_and_close(s))
            else:
                # Normale foutmelding (zoals "Gebruik 'pH'")
                tk.Label(dialog, text=error_message, font=("Arial", 10, "italic"), pady=5).pack()

        # Alternatieve witte spelling (Prisma)
        if alternatief_info:
            alt_word, _, alt_url = alternatief_info
            tk.Label(dialog, text="Alternatieve witte spelling:", font=("Arial", 10, "italic")).pack(pady=(5, 0))
            alt_link = tk.Label(
                dialog, text=alt_word,
                fg="blue", cursor="hand2", font=("Arial", 10, "underline")
            )
            alt_link.pack(pady=(0, 5))
            alt_link.bind("<Button-1>", lambda e: [os.startfile(alt_url), dialog.destroy()])

        # Vraag om website te openen
        tk.Label(dialog, text="\nWilt u het oorspronkelijke woord opzoeken?", pady=5).pack()

        # Buttonsframe
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)

        def yes_action():
            os.startfile(url_to_open)
            dialog.destroy()

        def no_action():
            dialog.destroy()

        yes_button = tk.Button(button_frame, text="Ja", command=yes_action, width=8)
        yes_button.pack(side='left', padx=5)

        # Maak Nee de default button
        no_button = tk.Button(button_frame, text="Nee", command=no_action, width=8, default='active')
        no_button.pack(side='left', padx=5)

        # Focus
        dialog.after(100, lambda: no_button.focus_force())

        # Bindings
        no_button.bind('<Return>', lambda e: no_action())
        yes_button.bind('<Return>', lambda e: yes_action())
        dialog.bind('<Escape>', lambda e: no_action())

        root.wait_window(dialog)

    except Exception as e:
        print(f"[Fout] Kon foutpop-up niet tonen: {e}")

def show_invoerfilter_popup(word, reden):
    """Toon waarschuwingspop-up voor ongeldige invoer; retourneert True als gebruiker toch wil opzoeken."""
    if threading.current_thread() is not threading.main_thread():
        result = [True]
        done = threading.Event()
        def _dispatch():
            result[0] = show_invoerfilter_popup(word, reden)
            done.set()
        _popup_root.after(0, _dispatch)
        done.wait()
        return result[0]
    try:
        doorgaan = [False]

        root = _popup_root

        dialog = tk.Toplevel(root)
        dialog.title("Ongebruikelijke invoer")
        dialog.resizable(False, False)
        dialog.attributes('-topmost', True)

        _set_icon(dialog)

        x, y = get_popup_position(420, 200)
        dialog.geometry(f"420x200+{x}+{y}")

        _bind_drag_save(dialog)

        tk.Label(dialog, text=f"'{word}'", font=("Arial", 11, "bold"), pady=8).pack()
        tk.Label(dialog, text=reden, font=("Arial", 10), wraplength=380, pady=4).pack()
        tk.Label(dialog, text="Wilt u de term toch opzoeken?", pady=5).pack()

        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)

        def ja_action():
            doorgaan[0] = True
            dialog.destroy()

        def nee_action():
            dialog.destroy()

        ja_button = tk.Button(button_frame, text="Toch opzoeken", command=ja_action, width=14)
        ja_button.pack(side='left', padx=5)

        nee_button = tk.Button(button_frame, text="Annuleren", command=nee_action, width=10, default='active')
        nee_button.pack(side='left', padx=5)

        dialog.after(100, lambda: nee_button.focus_force())

        nee_button.bind('<Return>', lambda e: nee_action())
        ja_button.bind('<Return>', lambda e: ja_action())
        dialog.bind('<Escape>', lambda e: nee_action())

        root.wait_window(dialog)
        return doorgaan[0]

    except Exception as e:
        print(f"[Fout] Kon invoerfilterpop-up niet tonen: {e}")
        return True  # Bij fout toch doorgaan

# --- ACTIE DIE WORDT UITGEVOERD BIJ INDRUKKEN SNELTOETS ---
def perform_check():
    """De volledige actie: kopieer, lees klembord, start de controle en geef feedback."""

    # CONTROLEER VERBRUIKSLIMIET VOORAF
    if not check_rate_limit():
        return

    try:
        # Bewaar huidige klembordinhoud
        original_clipboard = pyperclip.paste()

        # Wis klembord eerst (belangrijk voor Word)
        pyperclip.copy('')

        # Kopieer geselecteerde tekst
        keyboard.send('ctrl+c')
        time.sleep(0.1)  # Langere wachttijd voor Word

        # Haal nieuwe klembordinhoud op
        selected_word = pyperclip.paste().strip()

        # Als klembord nog steeds leeg is, probeer alternatief
        if not selected_word:
            keyboard.send('ctrl+ins')  # Alternatieve kopieercombinatie
            time.sleep(0.2)
            selected_word = pyperclip.paste().strip()

        # Als klembord nog steeds leeg is, herstel origineel en stop
        if not selected_word:
            pyperclip.copy(original_clipboard)
            print("[Waarschuwing] Geen tekst geselecteerd of kopiëren mislukt")
            return
    except Exception as e:
        print(f"[Fout] Klembord kon niet worden gelezen: {e}")
        return

    # Normaliseer typografische apostrofs voordat de filter en API worden aangeroepen
    selected_word_norm = re.sub(r"[\u2019\u2018\u0060\u00B4\u02BC]", "'", selected_word)
    if selected_word_norm != selected_word:
        print(f"[Info] Apostrof genormaliseerd: '{selected_word}' → '{selected_word_norm}'")
        selected_word = selected_word_norm

    # Normaliseer typografische streepjes en speciale spaties
    selected_word = re.sub(r"[\u00AD\u2010\u2011\u2012\u2013]", "-", selected_word)
    selected_word = re.sub(r"[\u00A0\u202F\u2009]", " ", selected_word)

    # Controleer of invoer eruitziet als een geldig woord of woordgroep
    geldig, reden = is_geldig_invoer(selected_word)
    if not geldig:
        print(f"[Info] Invoerfilter: {reden}")
        if not show_invoerfilter_popup(selected_word, reden):
            return

    # Start Prisma-check parallel met woordenlijst.org-check
    prisma_result = [None]
    prisma_thread = threading.Thread(
        target=lambda: prisma_result.__setitem__(0, check_prisma_alternatief(selected_word))
    )
    prisma_thread.start()

    # Voer de online check uit (nu met 7 returnwaarden)
    is_valid, checked_word, error_message, article, word_info, gender, gender_info_list = check_word_online(selected_word)

    # Geef feedback op basis van het resultaat
    if is_valid:
        show_success_popup(checked_word, article, word_info, gender, gender_info_list)
    else:
        prisma_thread.join(timeout=6)  # Wacht max 6 seconden op Prisma
        # Kopieer resultaat alleen als de thread daadwerkelijk klaar is; voorkomt race bij timeout
        prisma_data = None if prisma_thread.is_alive() else prisma_result[0]
        if checked_word:
            show_failure_popup(checked_word, error_message, prisma_data)

# --- HOOFDFUNCTIE ---
def main():
    global _popup_root
    print(f"--- Woordenlijst-checker v{VERSION} ---")
    print(f"Druk op '{HOTKEY}' om het geselecteerde woord te controleren.")
    print(f"Rechtsklik op het systeemvakicoon voor alle opties.")
    print(f"Configuratie: {os.path.abspath('config.ini')}")
    print("----------------------------------------------------------")

    # Maak één permanente verborgen Tk-root aan vóór de hotkey-listener start.
    # Door dit in de hoofdthread te doen en nooit te vernietigen, verdwijnt het
    # flikkerende lege venster dat eerder bij elke popup even zichtbaar was.
    _popup_root = tk.Tk()
    _popup_root.attributes('-alpha', 0)
    _popup_root.withdraw()

    _start_tray()

    keyboard.add_hotkey(HOTKEY, lambda: threading.Thread(target=perform_check).start())

    # Periodieke herregistratie van de sneltoets (elke 5 minuten) als bescherming tegen
    # het stilzwijgend intrekken van de WH_KEYBOARD_LL hook door Windows na slaapstand,
    # schermvergrendeling of hervatting.
    _HERREGISTREER_INTERVAL_MS = 5 * 60 * 1000  # 5 minuten

    def _herregistreer_sneltoets():
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        try:
            keyboard.add_hotkey(HOTKEY, lambda: threading.Thread(target=perform_check).start())
            print("[Info] Sneltoets herregistreerd (periodieke refresh)")
        except Exception as e:
            print(f"[Waarschuwing] Periodieke herregistratie mislukt: {e}")
        _popup_root.after(_HERREGISTREER_INTERVAL_MS, _herregistreer_sneltoets)

    _popup_root.after(_HERREGISTREER_INTERVAL_MS, _herregistreer_sneltoets)

    _popup_root.mainloop()  # Tk-event loop draait in hoofdthread; after()-callbacks verwerken popups

if __name__ == "__main__":
    main()
