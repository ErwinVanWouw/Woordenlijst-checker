# Woordenlijst-checker  v1.2.1 door Black Kite (blackkite.nl)
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

# Onderdruk waarschuwingen
warnings.filterwarnings("ignore", category=UserWarning)

# --- CONFIGURATIE ---
HOTKEY = 'F9'

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

            # CHECK 1: Zijn er lemma's met interne hoofdletters?
            has_internal_caps_lemma = any(
                any(c.isupper() for c in lemma[1:]) 
                for lemma in lemmas
            )

            if has_internal_caps_lemma:
                # STRIKTE MODUS: alleen lemma's EN correcte wordforms met juiste hoofdletters

                # Optie 1: is het een exact lemma?
                if word_normalized in lemmas:
                    print(f"[Resultaat] '{word}' is GEVONDEN (officiële spelling).")
                    return True, word, None

                # Optie 2: is het een wordform met de JUISTE hoofdletters?
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
                            print(f"[Resultaat] '{word}' is GEVONDEN (correcte vervoeging).")
                            return True, word, None

                # Niet goedgekeurd - geef feedback
                relevant_lemmas = [l for l in lemmas if any(c.isupper() for c in l[1:])]
                if relevant_lemmas:
                    error_msg = f"Gebruik '{relevant_lemmas[0]}' of correcte vervoeging"
                    print(f"[Resultaat] '{word}' is NIET correct ({error_msg}).")
                    return False, word, error_msg
                else:
                    print(f"[Resultaat] '{word}' is NIET correct gespeld.")
                    return False, word, "Controleer de spelling"

            # CHECK 2: Hoofdlettergevoelige woorden (pH, mkb, etc.)
            for lemma in lemmas:
                if lemma.lower() == word_normalized.lower() and lemma != word_normalized:
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
            print(f"[Resultaat] '{word}' is NIET gevonden.")
            return False, word, None

    except Exception as e:
        print(f"[Fout] Er is een fout opgetreden: {e}")
        return False, word, "Er is een fout opgetreden"

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
        popup.iconbitmap("favicon.ico")
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
    """Toon pop-up voor niet-gevonden woord met Ja/Nee-knoppen"""
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
        dialog.iconbitmap("favicon.ico")
    except:
        pass  # Gebruik standaard icoon als bestand niet bestaat

    # Centreer het venster (maak groter voor langere tekst)
    dialog.geometry("400x180+{}+{}".format(
        int(dialog.winfo_screenwidth()/2 - 200),
        int(dialog.winfo_screenheight()/2 - 90)
    ))

    # Hoofdtekst - gebruik specifieke foutmelding of standaard
    if error_message:
        message_text = f"'{word}'\nstaat niet in Woordenlijst.org.\n\n{error_message}\n\nWilt u de website openen?"
    else:
        message_text = f"'{word}'\nstaat niet in Woordenlijst.org.\n\nWilt u de website openen?"

    tk.Label(dialog, 
             text=message_text,
             pady=15,
             wraplength=350).pack()

    # Buttons frame
    button_frame = tk.Frame(dialog)
    button_frame.pack(pady=5)

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
        # Bewaar huidige klembord inhoud
        original_clipboard = pyperclip.paste()

        # Wis klembord eerst (belangrijk voor Word)
        pyperclip.copy('')

        # Kopieer geselecteerde tekst
        keyboard.send('ctrl+c')
        time.sleep(0.5)  # Langere wachttijd voor Word

        # Haal nieuwe klembord inhoud op
        selected_word = pyperclip.paste().strip()

        # Als klembord nog steeds leeg is, probeer alternatief
        if not selected_word:
            keyboard.send('ctrl+ins')  # Alternatieve kopieer-combinatie
            time.sleep(0.5)
            selected_word = pyperclip.paste().strip()

        # Als klembord nog steeds leeg is, herstel origineel en stop
        if not selected_word:
            pyperclip.copy(original_clipboard)
            print("[Waarschuwing] Geen tekst geselecteerd of kopiëren mislukt")
            return

    except Exception as e:
        print(f"[Fout] Klembord kon niet worden gelezen: {e}")
        return

    # Voer de online check uit (nu met 3 return waarden)
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
    print("----------------------------------------------------------")

    keyboard.add_hotkey(HOTKEY, lambda: threading.Thread(target=perform_check).start())
    keyboard.wait('esc')
    print("\n--- Script gestopt. ---")

if __name__ == "__main__":
    main()

