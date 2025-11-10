# Woordenlijst-checker v1.2.3 door Black Kite (blackkite.nl)
# Gebruikslimiet
from collections import deque
from datetime import datetime, timedelta

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
        print("[Waarschuwing] Te veel aanvragen, wacht even...")
        time.sleep(5)
        return False
    return True

# Vereiste bibliotheken
import requests
import keyboard
import pyperclip
import time
import threading
import webbrowser
from urllib.parse import quote
import tkinter as tk
from tkinter import messagebox
import warnings
# NIEUWE IMPORTS voor configuratie
import configparser
import os

# Onderdruk waarschuwingen
warnings.filterwarnings("ignore", category=UserWarning)

# --- CONFIGURATIE ---
def load_config():
    """Laad configuratie uit ini bestand of maak standaard aan"""
    config = configparser.ConfigParser()
    config_file = 'config.ini'

    # Check of config bestand bestaat
    if os.path.exists(config_file):
        config.read(config_file)
        hotkey = config.get('Settings', 'hotkey', fallback='f9')
        print(f"[Config] Sneltoets geladen uit config.ini: '{hotkey}'")
    else:
        # Maak nieuw config bestand met standaard waarden
        config['Settings'] = {
            'hotkey': 'f9'
        }
        with open(config_file, 'w') as f:
            config.write(f)
        hotkey = 'f9'
        print(f"[Config] Nieuw config.ini bestand aangemaakt met standaard sneltoets: 'f9'")
        print(f"[Config] Pas het bestand aan om de sneltoets te wijzigen en herstart de tool")

    return hotkey

# Laad de configuratie
HOTKEY = load_config()

# --- KERNFUNCTIE: WOORDCONTROLE VIA API ---
def check_word_online(word):
    """Strikte controle, alleen lemma's - retourneert (is_valid, word, error_message)"""
    if not word or not word.strip():
        print("[Info] Klembord is leeg, actie geannuleerd.")
        return False, word, None

    # Normaliseer alle typografische apostrofs naar rechte apostrof
    import re
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

            # NIEUWE CHECK: is het ingevoerde woord zelf een lemma?
            if word_normalized in lemmas:
                print(f"[Resultaat] '{word}' is GEVONDEN (officiële spelling).")
                return True, word, None

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
                            return True, word, None

                # Niet goedgekeurd - geef feedback
                relevant_lemmas = [l for l in lemmas if any(c.isupper() for c in l[1:])]
                if relevant_lemmas:
                    error_msg = f"Gebruik '{relevant_lemmas[0]}'"
                    print(f"[Resultaat] '{word}' is NIET correct ({error_msg}).")
                    return False, word, error_msg
                else:
                    print(f"[Resultaat] '{word}' is NIET correct gespeld.")
                    return False, word, "Controleer de spelling"

            # CHECK 2: hoofdlettergevoelige woorden (pH, mkb, etc.)
            for lemma in lemmas:
                if lemma.lower() == word_normalized.lower() and lemma != word_normalized:
                    lowercase_versions = [l for l in lemmas if l == word_normalized.lower()]
                    uppercase_versions = [l for l in lemmas if l[0].isupper() and l.lower() == word_normalized.lower()]

                    if lowercase_versions and uppercase_versions:
                        continue

                    error_msg = f"Gebruik '{lemma}'"
                    print(f"[Resultaat] '{word}' is NIET correct ({error_msg}).")
                    return False, word, error_msg

            # UITZONDERING: enkelvoudig woord met alleen eerste hoofdletter (Fiets)
            if (len(word_normalized) > 1 and 
                word_normalized[0].isupper() and 
                word_normalized[1:].islower() and 
                ' ' not in word_normalized): # Enkelvoudige woorden

                if word_normalized.lower() in wordforms or word_normalized.lower() in lemmas:
                    print(f"[Resultaat] '{word}' is GEVONDEN (hoofdletter toegestaan).")
                    return True, word, None

            # NORMALE MODUS: geen speciale hoofdletters, accepteer wordforms
            if word_normalized in wordforms or word_normalized in lemmas:
                print(f"[Resultaat] '{word}' is GEVONDEN.")
                return True, word, None

            print(f"[Resultaat] '{word}' is NIET correct gespeld.")
            return False, word, "Controleer de spelling"
        else:
            # WOORD NIET GEVONDEN - VRAAG SUGGESTIES OP
            print(f"[Resultaat] '{word}' is NIET gevonden.")

            # Haal suggesties op via spellcheck API
            suggestions = get_spelling_suggestions(word_normalized)

            if suggestions:
                error_msg = f"Bedoelde u: {suggestions}"
                return False, word, error_msg
            else:
                return False, word, None

    except Exception as e:
        print(f"[Fout] Er is een fout opgetreden: {e}")
        return False, word, "Er is een fout opgetreden"

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

        # Parse suggesties
        import re

        # Zoek naar corrections (meerdere suggesties gescheiden door |)
        corrections_match = re.search(r'<corrections>(.*?)</corrections>', xml_content)
        if corrections_match:
            corrections = corrections_match.group(1)
            if corrections:
                # Split op | en maak het netjes
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
def show_success_popup(word):
    """Toon 3 seconden pop-up met groen vinkje"""
    root = tk.Tk()
    root.withdraw()

    # Maak aangepast pop-upvenster
    popup = tk.Toplevel(root)
    popup.title("Gevonden")
    popup.configure(bg='white')

    try:
        # ICO-bestand in dezelfde map als het script
        import sys
        if hasattr(sys, '_MEIPASS'):
            # Running als .exe
            icon_path = os.path.join(sys._MEIPASS, "favicon.ico")
        else:
            # Running als .py script
            icon_path = "favicon.ico"

        if os.path.exists(icon_path):
            popup.iconbitmap(icon_path)
    except:
        pass  # Gebruik standaard icoon als bestand niet bestaat

    # Centreer het venster
    popup.geometry("350x150+{}+{}".format(
        int(popup.winfo_screenwidth()/2 - 175),
        int(popup.winfo_screenheight()/2 - 75)
    ))

    # Geen resize en altijd bovenop
    popup.resizable(False, False)
    popup.attributes('-topmost', True)

    # Frame voor content
    frame = tk.Frame(popup, bg='white')
    frame.pack(expand=True, fill='both', padx=20, pady=20)

    # Groen vinkje
    check_label = tk.Label(frame, text="✓", font=("Arial", 48), fg='green', bg='white')
    check_label.pack(side='left', padx=10)

    # Tekst
    text_label = tk.Label(frame, 
                         text=f"'{word}'\nstaat in Woordenlijst.org", 
                         font=("Arial", 12), 
                         bg='white',
                         justify='left')
    text_label.pack(side='left', padx=10)

    # Automatisch sluiten na 3 seconden
    popup.after(3000, lambda: [popup.destroy(), root.destroy()])

    # Start de GUI-loop
    popup.mainloop()

def show_failure_popup(word, error_message=None):
    """Toon pop-up voor niet-gevonden woord met Ja/Nee-knoppen en klikbare suggesties"""
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
        import sys
        if hasattr(sys, '_MEIPASS'):
            # Running als .exe
            icon_path = os.path.join(sys._MEIPASS, "favicon.ico")
        else:
            # Running als .py script
            icon_path = "favicon.ico"

        if os.path.exists(icon_path):
            dialog.iconbitmap(icon_path)
    except:
        pass  # Gebruik standaard icoon als bestand niet bestaat

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

    # Stel geometrie in met dynamische hoogte
    dialog.geometry("450x{}+{}+{}".format(
        total_height,
        int(dialog.winfo_screenwidth()/2 - 225),
        int(dialog.winfo_screenheight()/2 - total_height//2)
    ))

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

            # Maak klikbare links voor elke suggestie
            for suggestion in suggestions[:3]:  # Max 3 suggesties
                link = tk.Label(
                    suggestions_frame,
                    text=suggestion,
                    fg="blue",
                    cursor="hand2",
                    font=("Arial", 10, "underline")
                )
                link.pack(pady=2)
                # Open direct de website met deze suggestie
                link.bind("<Button-1>", lambda e, s=suggestion: webbrowser.open_new_tab(
                    f"https://woordenlijst.org/zoeken/?q={quote(s)}"
                ))
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

    tk.Button(button_frame, text="Ja", command=yes_action, width=8).pack(side='left', padx=5)
    tk.Button(button_frame, text="Nee", command=no_action, width=8).pack(side='left', padx=5)

    # Footercredit
    tk.Label(dialog, 
             text="blackkite.nl", 
             fg='#808080', 
             font=('Arial', 7),
             anchor='w').pack(side='bottom', anchor='w', padx=10, pady=2)

    # Focus op Ja-knop
    button_frame.winfo_children()[0].focus()

    # Enter = Ja, Escape = Nee
    dialog.bind('<Return>', lambda e: yes_action())
    dialog.bind('<Escape>', lambda e: no_action())

    dialog.mainloop()
    
# --- ACTIE DIE WORDT UITGEVOERD BIJ INDRUKKEN SNELTOETS ---
def perform_check():
    """De volledige actie: kopieer, lees klembord, start de controle en geef feedback."""
    try:
        # Bewaar huidige klembordinhoud
        original_clipboard = pyperclip.paste()

        # Wis klembord eerst (belangrijk voor Word)
        pyperclip.copy('')

        # Kopieer geselecteerde tekst
        keyboard.send('ctrl+c')
        time.sleep(0.2)  # Langere wachttijd voor Word

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

    # Voer de online check uit (nu met 3 returnwaarden)
    is_valid, checked_word, error_message = check_word_online(selected_word)

    # Geef feedback op basis van het resultaat
    if is_valid:
        # Toon pop-up met groen vinkje
        show_success_popup(checked_word)
    else:
        # Toon pop-up met Ja/Nee-opties en specifieke foutmelding
        if checked_word:
            show_failure_popup(checked_word, error_message)

# --- HOOFDFUNCTIE ---
def main():
    print("--- Woordenlijst Checker ---")
    print(f"Druk op '{HOTKEY}' om het geselecteerde woord te controleren.")
    print("Druk op 'Esc' om het script volledig te stoppen.")
    print(f"Configuratie: {os.path.abspath('config.ini')}")
    print("----------------------------------------------------------")

    keyboard.add_hotkey(HOTKEY, lambda: threading.Thread(target=perform_check).start())
    keyboard.wait('esc')
    print("\n--- Script gestopt. ---")

if __name__ == "__main__":
    main()
