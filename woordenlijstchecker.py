# Woordenlijst-checker v1.2.6 door Black Kite (blackkite.nl)

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
from datetime import datetime, timedelta
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
    now = datetime.now()
    request_history.append(now)

    # Tel requests in laatste minuut
    recent = sum(1 for t in request_history if now - t < timedelta(minutes=1))

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
    """Bepaal pop-uppositie met robuuste validatie"""
    if POPUP_X == -1 or POPUP_Y == -1:
        return get_center_position(width, height)

    # Test of positie werkelijk zichtbaar is
    try:
        test = tk.Tk()
        test.withdraw()
        test.geometry(f"1x1+{POPUP_X}+{POPUP_Y}")
        test.update()

        # Check of window op gevraagde positie staat
        actual_x = test.winfo_x()
        actual_y = test.winfo_y()
        test.destroy()

        # Als Windows positie heeft aangepast (>100px verschil)
        if abs(actual_x - POPUP_X) > 100 or abs(actual_y - POPUP_Y) > 100:
            print("[Info] Opgeslagen positie niet bereikbaar, gebruik centrum")
            return get_center_position(width, height)

        return POPUP_X, POPUP_Y

    except Exception as e:
        print(f"[Waarschuwing] Kon pop-uppositie niet valideren: {e}")
        return get_center_position(width, height)

def get_center_position(width, height):
    """Bereken centrumpositie van primaire monitor"""
    try:
        temp_root = tk.Tk()
        temp_root.withdraw()
        x = int(temp_root.winfo_screenwidth()/2 - width/2)
        y = int(temp_root.winfo_screenheight()/2 - height/2)
        temp_root.destroy()
        return x, y
    except Exception as e:
        print(f"[Waarschuwing] Kon centrumpositie niet bepalen: {e}")
        return 100, 100  # Fallback positie

# --- KERNFUNCTIE: WOORDCONTROLE VIA API ---
def check_word_online(word):
    """Strikte controle, alleen lemma's - retourneert (is_valid, word, error_message, article)"""
    if not word or not word.strip():
        print("[Info] Klembord is leeg, actie geannuleerd.")
        return False, word, None, None

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

            # LIDWOORDEXTRACTIE - gebaseerd op part_of_speech
            articles = set()

            # Check of het gezochte woord in de paradigm staat met een "meervoud" label
            is_plural = False
            paradigm_blocks = re.findall(r'<paradigm>.*?</paradigm>', xml_content, re.DOTALL)
            for block in paradigm_blocks:
                if '<wordform>' + word_normalized + '</wordform>' in block:
                    if '<label>meervoud</label>' in block:
                        is_plural = True
                        break

            # Als het een meervoud is, is het lidwoord altijd "de"
            if is_plural:
                article = 'de'
                print(f"[Info] Meervoudsvorm - lidwoord is altijd 'de'")
            else:
                # Voor enkelvoud: verzamel alle genders van de relevante lemma's
                for lemma in lemmas:
                    # Skip lemma's die niet exact overeenkomen (behalve hoofdletters)
                    if lemma.lower() != word_normalized.lower():
                        continue

                    # Zoek gender in lemma_part_of_speech
                    pos_pattern = r'<lemma>' + re.escape(lemma) + r'</lemma>.*?<lemma_part_of_speech>.*?gender=([^,\)]+)'
                    pos_matches = re.findall(pos_pattern, xml_content, re.DOTALL)

                    for gender in pos_matches:
                        # Verwerk alle mogelijke gendercombinaties
                        if 'n' in gender:  # neuter (onzijdig)
                            articles.add('het')
                        if any(x in gender for x in ['m', 'f', 'c']):  # mannelijk, vrouwelijk of common
                            articles.add('de')

                if not articles:
                    for lemma in lemmas:
                        pos_pattern = r'<lemma>' + re.escape(lemma) + r'</lemma>.*?<lemma_part_of_speech>.*?gender=([^,\)]+)'
                        pos_match = re.search(pos_pattern, xml_content, re.DOTALL)
                        if pos_match:
                            gender = pos_match.group(1)
                            if 'n' in gender:
                                articles.add('het')
                            if any(x in gender for x in ['m', 'f', 'c']):
                                articles.add('de')

                # Format enkelvoud lidwoorden
                if len(articles) == 1:
                    article = articles.pop()
                elif len(articles) > 1:
                    article = "/".join(sorted(articles))
                else:
                    article = None

            # Finale output
            if article:
                print(f"[Info] Lidwoord: {article}")
            else:
                print("[Info] Geen lidwoord gevonden")

            # NIEUWE CHECK: is het ingevoerde woord zelf een lemma?
            if word_normalized in lemmas:
                print(f"[Resultaat] '{word}' is GEVONDEN (officiële spelling).")
                return True, word, None, article

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
                            return True, word, None, article

                # Niet goedgekeurd - geef feedback
                relevant_lemmas = [l for l in lemmas if any(c.isupper() for c in l[1:])]
                if relevant_lemmas:
                    error_msg = f"Gebruik '{relevant_lemmas[0]}'"
                    print(f"[Resultaat] '{word}' is NIET correct ({error_msg}).")
                    return False, word, error_msg, None
                else:
                    print(f"[Resultaat] '{word}' is NIET correct gespeld.")
                    return False, word, "Controleer de spelling", None

            # CHECK 2: hoofdlettergevoelige woorden (pH, mkb, etc.)
            for lemma in lemmas:
                if lemma.lower() == word_normalized.lower() and lemma != word_normalized:
                    lowercase_versions = [l for l in lemmas if l == word_normalized.lower()]
                    uppercase_versions = [l for l in lemmas if l[0].isupper() and l.lower() == word_normalized.lower()]

                    if lowercase_versions and uppercase_versions:
                        continue

                    error_msg = f"Gebruik '{lemma}'"
                    print(f"[Resultaat] '{word}' is NIET correct ({error_msg}).")
                    return False, word, error_msg, None

            # UITZONDERING: enkelvoudig woord met alleen eerste hoofdletter (Fiets)
            if (len(word_normalized) > 1 and
                word_normalized[0].isupper() and
                word_normalized[1:].islower() and
                ' ' not in word_normalized): # Enkelvoudige woorden

                if word_normalized.lower() in wordforms or word_normalized.lower() in lemmas:
                    print(f"[Resultaat] '{word}' is GEVONDEN (hoofdletter toegestaan).")
                    return True, word, None, article

            # NORMALE MODUS: geen speciale hoofdletters, accepteer wordforms
            if word_normalized in wordforms or word_normalized in lemmas:
                print(f"[Resultaat] '{word}' is GEVONDEN.")
                return True, word, None, article

            print(f"[Resultaat] '{word}' is NIET correct gespeld.")
            return False, word, "Controleer de spelling", None
        else:
            # WOORD NIET GEVONDEN - VRAAG SUGGESTIES OP
            print(f"[Resultaat] '{word}' is NIET gevonden.")

            # Haal suggesties op via spellcheck API
            suggestions = get_spelling_suggestions(word_normalized)

            if suggestions:
                error_msg = f"Bedoelde u: {suggestions}"
                return False, word, error_msg, None
            else:
                return False, word, None, None

    except requests.exceptions.RequestException as e:
        print(f"[Fout] Netwerkfout bij API-aanroep: {e}")
        return False, word, "Netwerkfout - controleer uw verbinding", None
    except Exception as e:
        print(f"[Fout] Onverwachte fout tijdens controle: {e}")
        return False, word, "Er is een fout opgetreden", None

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

# --- NOTIFICATIE FUNCTIES ---
def show_success_popup(word, article=None):
    """Toon 3 seconden pop-up met groen vinkje en optioneel lidwoord"""
    try:
        root = tk.Tk()
        root.withdraw()

        # Maak aangepast pop-upvenster
        popup = tk.Toplevel(root)
        popup.title("Gevonden")
        popup.configure(bg='white')

        try:
            # ICO-bestand in dezelfde map als het script
            if hasattr(sys, '_MEIPASS'):
                # Running als .exe
                icon_path = os.path.join(sys._MEIPASS, "favicon.ico")
            else:
                # Running als .py script
                icon_path = "favicon.ico"

            if os.path.exists(icon_path):
                popup.iconbitmap(icon_path)
        except Exception as e:
            print(f"[Info] Kon icoon niet laden: {e}")

        # Bereken benodigde breedte op basis van tekstlengte
        if article:
            display_text = f"'{word}' ({article})"
        else:
            display_text = f"'{word}'"

        # Schat de benodigde breedte (ongeveer 8 pixels per karakter + marges)
        estimated_width = len(display_text) * 8 + 200  # 200 voor vinkje en marges
        min_width = 350
        max_width = 600
        popup_width = max(min_width, min(estimated_width, max_width))
        popup_height = 150

        # Positioneer pop-up (opgeslagen positie of centrum)
        x, y = get_popup_position(popup_width, popup_height)
        popup.geometry(f"{popup_width}x{popup_height}+{x}+{y}")

        # Geen resize en altijd bovenop
        popup.resizable(False, False)
        popup.attributes('-topmost', True)

        # Detecteer wanneer pop-up wordt verplaatst
        def on_drag_end(event):
            if event.widget == popup:
                new_x = popup.winfo_x()
                new_y = popup.winfo_y()
                # Alleen opslaan als positie echt veranderd is (niet bij andere events)
                if abs(new_x - POPUP_X) > 5 or abs(new_y - POPUP_Y) > 5:
                    save_popup_position(new_x, new_y)
                    print(f"[Info] Nieuwe popup positie opgeslagen: {new_x}, {new_y}")

        popup.bind('<Configure>', on_drag_end)

        # Frame voor content
        frame = tk.Frame(popup, bg='white')
        frame.pack(expand=True, fill='both', padx=20, pady=20)

        # Groen vinkje
        check_label = tk.Label(frame, text="✓", font=("Arial", 48), fg='green', bg='white')
        check_label.pack(side='left', padx=10)

        # Tekst met optioneel lidwoord
        full_display_text = display_text + "\nstaat in Woordenlijst.org"

        text_label = tk.Label(frame,
                             text=full_display_text,
                             font=("Arial", 12),
                             bg='white',
                             justify='left')
        text_label.pack(side='left', padx=10)

        # Automatisch sluiten na 3 seconden
        popup.after(3000, lambda: [popup.destroy(), root.destroy()])

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

        try:
            # ICO-bestand in dezelfde map als het script
            if hasattr(sys, '_MEIPASS'):
                # Running als .exe
                icon_path = os.path.join(sys._MEIPASS, "favicon.ico")
            else:
                # Running als .py script
                icon_path = "favicon.ico"

            if os.path.exists(icon_path):
                dialog.iconbitmap(icon_path)
        except Exception as e:
            print(f"[Info] Kon icoon niet laden: {e}")

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

        # Detecteer wanneer pop-up wordt verplaatst
        def on_drag_end(event):
            if event.widget == dialog:
                new_x = dialog.winfo_x()
                new_y = dialog.winfo_y()
                # Alleen opslaan als positie echt veranderd is
                if abs(new_x - POPUP_X) > 5 or abs(new_y - POPUP_Y) > 5:
                    save_popup_position(new_x, new_y)
                    print(f"[Info] Nieuwe pop-uppositie opgeslagen: {new_x}, {new_y}")

        dialog.bind('<Configure>', on_drag_end)

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
    # Voer de online check uit (nu met 4 returnwaarden)
    is_valid, checked_word, error_message, article = check_word_online(selected_word)

    # Geef feedback op basis van het resultaat
    if is_valid:
        # Toon pop-up met groen vinkje en optioneel lidwoord
        show_success_popup(checked_word, article)
    else:
        # Toon pop-up met Ja/Nee-opties en specifieke foutmelding
        if checked_word:
            show_failure_popup(checked_word, error_message)

# --- HOOFDFUNCTIE ---
def main():
    print("--- Woordenlijstchecker v1.2.6 ---")
    print(f"Druk op '{HOTKEY}' om het geselecteerde woord te controleren.")
    print("Druk op 'Esc' om het script te stoppen.")
    print(f"Configuratie: {os.path.abspath('config.ini')}")
    print("----------------------------------------------------------")

    keyboard.add_hotkey(HOTKEY, lambda: threading.Thread(target=perform_check).start())
    keyboard.wait('esc')
    print("\n--- Script gestopt. ---")

if __name__ == "__main__":
    main()
