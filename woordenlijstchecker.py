# Woordenlijst-checker v1.2.8 door Black Kite (blackkite.nl)

# Vereiste bibliotheken
import time
import requests
import keyboard
import pyperclip
import threading
import webbrowser
from urllib.parse import quote
import tkinter as tk
from tkinter import messagebox
import warnings
import configparser
import os
from collections import deque
import re
import sys

# Onderdruk waarschuwingen
warnings.filterwarnings("ignore", category=UserWarning)

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
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning("Rate Limit",
                              "Maximum aantal controles bereikt.\nWacht even voordat u doorgaat.\n(Max. 30 controles per minuut)")
        root.destroy()
        return False
    return True

# --- CONFIGURATIE ---
def load_config():
    """Laad configuratie uit ini bestand of maak standaard aan"""
    config = configparser.ConfigParser()
    config_file = 'config.ini'

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
        with open(config_file, 'w') as f:
            config.write(f)
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
            temp = tk.Tk()
            temp.withdraw()
            x = int(temp.winfo_screenwidth()/2 - width/2)
            y = int(temp.winfo_screenheight()/2 - height/2)
            temp.destroy()
            return x, y
        except Exception as e:
            print(f"[Waarschuwing] Kon centrumpositie niet bepalen: {e}")
            return 100, 100

    if POPUP_X == -1 or POPUP_Y == -1:
        return center()

    # Test of positie werkelijk zichtbaar is
    try:
        test = tk.Tk()
        test.withdraw()
        test.geometry(f"1x1+{POPUP_X}+{POPUP_Y}")
        test.update()
        actual_x = test.winfo_x()
        actual_y = test.winfo_y()
        test.destroy()

        # Als Windows positie heeft aangepast (>100px verschil)
        if abs(actual_x - POPUP_X) > 100 or abs(actual_y - POPUP_Y) > 100:
            print("[Info] Opgeslagen positie niet bereikbaar, gebruik centrum")
            return center()

        return POPUP_X, POPUP_Y

    except Exception as e:
        print(f"[Waarschuwing] Kon pop-uppositie niet valideren: {e}")
        return center()

# --- KERNFUNCTIE: WOORDCONTROLE VIA API ---
def check_word_online(word):
    """Strikte controle, alleen lemma's - retourneert (is_valid, word, error_message, article, word_info, gender, gender_info_list)"""
    if not word or not word.strip():
        print("[Info] Klembord is leeg, actie geannuleerd.")
        return False, word, None, None, None, None, None

    # Normaliseer alle typografische apostrofs naar rechte apostrof
    word_normalized = re.sub(r"[\u2019\u2018\u0060\u00B4\u02BC]", "'", word)

    # Als er een wijziging was, toon dit
    if word != word_normalized:
        print(f"[Info] Apostrof genormaliseerd: '{word}' → '{word_normalized}'")

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

            # Detecteer woordsoorten
            is_verb = False
            is_plural_noun = False

            # Check of het een werkwoord is
            verb_pattern = r'<label>hoofdwerkwoord</label><lemma>' + re.escape(word_normalized) + r'</lemma>'
            if re.search(verb_pattern, xml_content):
                is_verb = True
                print(f"[Info] Werkwoord gedetecteerd: {word_normalized}")

            # LIDWOORDEXTRACTIE - gebaseerd op part_of_speech
            gender_info_list = []  # lijst van dicts met article/gender combinaties
            gender = None

            # Check of het gezochte woord ALLEEN als meervoud voorkomt
            is_plural = False
            is_also_singular = False

            paradigm_blocks = re.findall(r'<paradigm>.*?</paradigm>', xml_content, re.DOTALL)
            for block in paradigm_blocks:
                if '<wordform>' + word_normalized + '</wordform>' in block:
                    if '<label>meervoud</label>' in block:
                        is_plural = True
                    if '<label>enkelvoud</label>' in block:
                        is_also_singular = True

            # Het is alleen een meervoud als het niet ook als enkelvoud voorkomt
            if is_plural and not is_also_singular:
                is_plural_noun = True  # Voor de word_info
                article = 'de'
                gender = None
                gender_info_list = None
                print(f"[Info] Meervoudsvorm - lidwoord is altijd 'de'")
            else:
                # Voor enkelvoud: verzamel genders per lemma voorkomen
                lemma_entries = []

                # Verzamel unieke lemma's
                matching_lemmas = []

                for l in lemmas:
                    if l.lower() == word_normalized.lower():
                        # Voor elk uniek lemma, voeg het maar één keer toe
                        if l not in matching_lemmas:
                            matching_lemmas.append(l)

                # Vind voor elk matchend lemma de gender info
                for lemma in matching_lemmas:
                    # Zoek ALLE gevallen van dit lemma met gender info
                    pattern = r'<lemma>' + re.escape(lemma) + r'</lemma>.*?<lemma_id>\d+</lemma_id>.*?<lemma_part_of_speech>.*?gender=([^,\)]+)'
                    matches = re.findall(pattern, xml_content, re.DOTALL)

                    for gender_raw in matches:
                        entry_articles = set()
                        entry_genders = set()

                        # Parse de gender string (kan m, f, n, m/f, m/n, etc. zijn)
                        if 'n' in gender_raw:
                            entry_articles.add('het')
                            entry_genders.add('o')
                        if 'm' in gender_raw:
                            entry_articles.add('de')
                            entry_genders.add('m')
                        if 'f' in gender_raw:
                            entry_articles.add('de')
                            entry_genders.add('v')
                        if 'c' in gender_raw:  # common gender
                            entry_articles.add('de')
                            entry_genders.add('m/v')

                        # Maak article- en gender-strings
                        if entry_articles:
                            art_str = "/".join(sorted(entry_articles))

                            # Speciale gender formatting
                            if 'm' in entry_genders and 'v' in entry_genders and 'm/v' not in entry_genders:
                                gen_str = 'm/v'
                            elif 'm' in entry_genders and 'o' in entry_genders:
                                gen_str = 'm/o'
                            elif 'v' in entry_genders and 'o' in entry_genders:
                                gen_str = 'v/o'
                            else:
                                gen_str = "/".join(sorted(entry_genders))

                            # Voeg toe aan lijst met het ORIGINELE lemma (met hoofdletters)
                            entry = {'lemma': lemma, 'article': art_str, 'gender': gen_str}

                            # Check of deze exact combinatie nog niet bestaat
                            duplicate = False
                            for existing in lemma_entries:
                                if (existing['lemma'] == lemma and 
                                    existing['article'] == art_str and 
                                    existing['gender'] == gen_str):
                                    duplicate = True
                                    break

                            if not duplicate:
                                lemma_entries.append(entry)

                # Verwerk de resultaten
                if lemma_entries:
                    # Als er maar één unieke combinatie is
                    if len(lemma_entries) == 1:
                        article = lemma_entries[0]['article']
                        gender = lemma_entries[0]['gender']
                        gender_info_list = None  # Geen lijst nodig voor enkelvoudige entry
                    else:
                        # Meerdere combinaties (homoniemen)
                        gender_info_list = lemma_entries
                        article = "/".join(sorted({e['article'] for e in lemma_entries}))
                        gender = None  # Geen enkele gender, want we hebben een lijst
                else:
                    article = None
                    gender = None
                    gender_info_list = None

            # Maak word_info dictionary voor complexe gevallen
            word_info = None
            if is_verb and is_plural_noun:
                word_info = {'is_ambiguous': True}
                print(f"[Info] Ambigue woord: zowel werkwoord als meervoud zelfstandig naamwoord")

            # Update word_info met gender info
            if word_info:
                if gender_info_list:
                    word_info['gender_info_list'] = gender_info_list
                else:
                    word_info['gender'] = gender

            # Finale output
            if gender_info_list:
                print(f"[Info] Homoniemen gevonden: {len(gender_info_list)} varianten")
                for info in gender_info_list:
                    print(f"  - {info['article']} ({info['gender']})")
            elif article:
                if gender:
                    print(f"[Info] Lidwoord: {article} ({gender})")
                else:
                    print(f"[Info] Lidwoord: {article}")
            else:
                print("[Info] Geen lidwoord gevonden")

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
                # Splits op | en maak het netjes
                suggestions = [s.strip() for s in corrections.split('|')]
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
    """Sla pop-uppositie op zodra het venster wordt verplaatst"""
    def on_drag_end(event):
        if event.widget == window:
            new_x = window.winfo_x()
            new_y = window.winfo_y()
            if abs(new_x - POPUP_X) > 5 or abs(new_y - POPUP_Y) > 5:
                save_popup_position(new_x, new_y)
                print(f"[Info] Nieuwe pop-uppositie opgeslagen: {new_x}, {new_y}")
    window.bind('<Configure>', on_drag_end)

# --- NOTIFICATIE FUNCTIES ---
def show_success_popup(word, article=None, word_info=None, gender=None, gender_info_list=None):
    """Toon 3 seconden pop-up met groen vinkje en optioneel lidwoord met gender"""
    try:
        root = tk.Tk()
        root.withdraw()

        # Maak aangepast pop-upvenster
        popup = tk.Toplevel(root)
        popup.title("Gevonden")
        popup.configure(bg='white')

        _set_icon(popup)

        # Bepaal pop-upgrootte op basis van inhoud
        if gender_info_list and len(gender_info_list) > 1:
            popup_height = 150 + (len(gender_info_list) - 1) * 25 + 10
            max_line_len = max(
                len(f"'{info.get('lemma', word)}' {info['article']} ({info['gender']})")
                for info in gender_info_list
            )
        elif word_info and word_info.get('is_ambiguous'):
            popup_height = 190
            first_line = f"'{word}' {article} ({gender})" if gender else f"'{word}' ({article})"
            max_line_len = max(len(first_line), len("staat in Woordenlijst.org"), len("▶ tevens infinitief"))
        elif article:
            popup_height = 160
            first_line = f"'{word}' {article} ({gender})" if gender else f"'{word}' ({article})"
            max_line_len = max(len(first_line), len("staat in Woordenlijst.org"))
        else:
            popup_height = 160
            max_line_len = max(len(f"'{word}'"), len("staat in Woordenlijst.org"))

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

        # Opmaak voor homoniemen
        if gender_info_list and len(gender_info_list) > 1:
            text_frame = tk.Frame(frame, bg='white')
            text_frame.pack(side='left', padx=10)

            # Maak regel voor elke variant (alleen eerste woord wordt klikbaar)
            for i, info in enumerate(gender_info_list):
                line_frame = tk.Frame(text_frame, bg='white')
                line_frame.pack(anchor='w')

                display_word = info.get('lemma', word)  # Gebruik lemma met juiste hoofdletters
                word_lbl = tk.Label(line_frame, text=f"'{display_word}'", font=("Arial", 12), bg='white')
                word_lbl.pack(side='left')
                if i == 0:
                    word_labels.append((word_lbl, f"https://woordenlijst.org/zoeken/?q={quote(display_word)}"))
                tk.Label(line_frame, text=f" {info['article']}", font=("Arial", 12, "italic"), bg='white').pack(side='left')
                tk.Label(line_frame, text=f" ({info['gender']})", font=("Arial", 12), bg='white').pack(side='left')

            # "staat in Woordenlijst.org" regel
            tk.Label(text_frame, text="staat in Woordenlijst.org", font=("Arial", 12), bg='white').pack(anchor='w', pady=(10,0))

        elif article and gender:
            # Enkele entry met italics
            text_frame = tk.Frame(frame, bg='white')
            text_frame.pack(side='left', padx=10)

            first_line_frame = tk.Frame(text_frame, bg='white')
            first_line_frame.pack(anchor='w')

            word_lbl = tk.Label(first_line_frame, text=f"'{word}'", font=("Arial", 12), bg='white')
            word_lbl.pack(side='left')
            word_labels.append((word_lbl, f"https://woordenlijst.org/zoeken/?q={quote(word)}"))
            tk.Label(first_line_frame, text=f" {article}", font=("Arial", 12, "italic"), bg='white').pack(side='left')
            tk.Label(first_line_frame, text=f" ({gender})", font=("Arial", 12), bg='white').pack(side='left')

            tk.Label(text_frame, text="staat in Woordenlijst.org", font=("Arial", 12), bg='white').pack(anchor='w', pady=(10,0))

            # Eventuele ambigue notitie
            if word_info and word_info.get('is_ambiguous'):
                tk.Label(text_frame, text="", font=("Arial", 8), bg='white').pack()
                tk.Label(text_frame, text="▶ tevens infinitief", font=("Arial", 11), bg='white').pack(anchor='w')
        else:
            # Normale tekst: splits woord en overige tekst in aparte labels
            text_frame = tk.Frame(frame, bg='white')
            text_frame.pack(side='left', padx=10)

            first_line = f"'{word}' ({article})" if article else f"'{word}'"
            word_lbl = tk.Label(text_frame, text=first_line, font=("Arial", 12), bg='white')
            word_lbl.pack(anchor='w')
            word_labels.append((word_lbl, f"https://woordenlijst.org/zoeken/?q={quote(word)}"))

            tk.Label(text_frame, text="staat in Woordenlijst.org", font=("Arial", 12), bg='white').pack(anchor='w', pady=(10, 0))

            if word_info and word_info.get('is_ambiguous'):
                tk.Label(text_frame, text="", font=("Arial", 8), bg='white').pack()
                tk.Label(text_frame, text="▶ tevens infinitief", font=("Arial", 11), bg='white').pack(anchor='w')

        # Automatisch sluiten na 3 seconden (annuleerbaar via linkermuisklik)
        auto_close = [None]

        def cancel_auto_close(event=None):
            if auto_close[0] is not None:
                popup.after_cancel(auto_close[0])
                auto_close[0] = None
                # Maak woordlabels klikbaar als hyperlink
                for lbl, url in word_labels:
                    lbl.config(fg='blue', cursor='hand2', font=("Arial", 12, "underline"))
                    lbl.bind('<Button-1>', lambda e, u=url: [webbrowser.open_new_tab(u), popup.destroy(), root.destroy()])
                # Zet focus op pop-up zodat Enter het venster sluit
                popup.focus_set()
                popup.bind('<Return>', lambda e: [popup.destroy(), root.destroy()])

        auto_close[0] = popup.after(3000, lambda: [popup.destroy(), root.destroy()])

        # Bind linkermuisklik op pop-up en alle child-widgets om timer te annuleren
        def bind_click_to_cancel(widget):
            widget.bind('<Button-1>', cancel_auto_close, add=True)
            for child in widget.winfo_children():
                bind_click_to_cancel(child)

        bind_click_to_cancel(popup)

        # Start de GUI-loop
        popup.mainloop()

    except Exception as e:
        print(f"[Fout] Kon succespop-up niet tonen: {e}")

def show_failure_popup(word, error_message=None):
    """Toon pop-up voor niet-gevonden woord met Ja/Nee-knoppen en klikbare suggesties"""
    try:
        url_to_open = f"https://woordenlijst.org/zoeken/?q={quote(word)}"

        root = tk.Tk()
        root.withdraw()

        # Custom dialog
        dialog = tk.Toplevel(root)
        dialog.title("Niet gevonden")
        dialog.resizable(False, False)
        dialog.attributes('-topmost', True)

        _set_icon(dialog)

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

        total_height = base_height + extra_height

        # Positioneer pop-up (opgeslagen positie of centrum)
        x, y = get_popup_position(450, total_height)
        dialog.geometry(f"450x{total_height}+{x}+{y}")

        _bind_drag_save(dialog)

        # Hoofdtekst
        main_text = f"'{word}'\nstaat niet in Woordenlijst.org."
        tk.Label(dialog, text=main_text, pady=10).pack()

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
                    webbrowser.open_new_tab(f"https://woordenlijst.org/zoeken/?q={quote(suggestion)}")
                    dialog.destroy()
                    root.destroy()

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

        # Vraag om website te openen
        tk.Label(dialog, text="\nWilt u het oorspronkelijke woord opzoeken?", pady=5).pack()

        # Buttonsframe
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)

        def yes_action():
            webbrowser.open_new_tab(url_to_open)
            dialog.destroy()
            root.destroy()

        def no_action():
            dialog.destroy()
            root.destroy()

        yes_button = tk.Button(button_frame, text="Ja", command=yes_action, width=8)
        yes_button.pack(side='left', padx=5)

        # Maak Nee de default button
        no_button = tk.Button(button_frame, text="Nee", command=no_action, width=8, default='active')
        no_button.pack(side='left', padx=5)

        # Focus
        dialog.after(100, lambda: no_button.focus_force())  # Kleine delay voor zekerheid

        # Bindings
        no_button.bind('<Return>', lambda e: no_action())
        yes_button.bind('<Return>', lambda e: yes_action())
        dialog.bind('<Escape>', lambda e: no_action())

        dialog.mainloop()

    except Exception as e:
        print(f"[Fout] Kon foutpop-up niet tonen: {e}")

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

    # Voer de online check uit (nu met 7 returnwaarden)
    is_valid, checked_word, error_message, article, word_info, gender, gender_info_list = check_word_online(selected_word)

    # Geef feedback op basis van het resultaat
    if is_valid:
        # Toon pop-up met groen vinkje en optioneel lidwoord
        show_success_popup(checked_word, article, word_info, gender, gender_info_list)
    else:
        # Toon pop-up met Ja/Nee-opties en specifieke foutmelding
        if checked_word:
            show_failure_popup(checked_word, error_message)

# --- HOOFDFUNCTIE ---
def main():
    print("--- Woordenlijst-checker v1.2.8 ---")
    print(f"Druk op '{HOTKEY}' om het geselecteerde woord te controleren.")
    print(f"Configuratie: {os.path.abspath('config.ini')}")
    print("----------------------------------------------------------")

    keyboard.add_hotkey(HOTKEY, lambda: threading.Thread(target=perform_check).start())
    threading.Event().wait()

if __name__ == "__main__":
    main()
