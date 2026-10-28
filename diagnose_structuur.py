"""
Diagnostisch script: toont de XML-labelstructuur per woord.

Beantwoordt drie vragen:
  1. Staan labels BINNEN <found_lemmata>-blokken?
  2. Staan labels BINNEN <paradigm>-blokken (genest)?
  3. Wat vindt _extract_woordsoort_entries (strip-aanpak per blok)?

Uitvoeren: python diagnose_structuur.py
Verwijderen daarna: het script is tijdelijk.
"""
import requests, re, time

TESTWOORDEN = [
    'groot',    # bijvoeglijk naamwoord
    'lopen',    # werkwoord
    'fiets',    # zelfstandig naamwoord
    'hoewel',   # onderschikkend voegwoord
    'in',       # voorzetsel / bijwoord / werkwoord / symbool
    'die',      # voornaamwoord
    'want',     # nevenschikkend voegwoord
    'snel',     # bijv.nw./bijwoord
    'echt',     # bijv.nw./bijwoord
]

def haal_xml(woord):
    r = requests.get(
        "https://woordenlijst.org/MolexServe/lexicon/find_wordform",
        params={
            "database": "gig_pro_wrdlst", "wordform": woord,
            "paradigm": "true", "diminutive": "true",
            "onlyvalid": "true", "regex": "false",
            "dummy": str(int(time.time() * 1000))
        }, timeout=5)
    return r.text

def analyseer(woord, xml):
    gevonden = "<found_lemmata>" in xml
    print(f"\n{'='*60}")
    print(f"  Woord: {woord!r}   {'[GEVONDEN]' if gevonden else '[NIET GEVONDEN]'}")
    print(f"{'='*60}")

    if not gevonden:
        return

    # --- 1. Labels in VOLLEDIGE XML (inclusief paradigm) ---
    alle_labels = re.findall(r'<label>(.*?)</label>', xml)
    print(f"\n[1] Alle labels in volledige XML ({len(alle_labels)} stuks):")
    for l in alle_labels:
        print(f"      {l!r}")

    # --- 2. Labels na GLOBAAL strippen van paradigm ---
    xml_gestript = re.sub(r'<paradigm>.*?</paradigm>', '', xml, flags=re.DOTALL)
    globale_labels = re.findall(r'<label>(.*?)</label>', xml_gestript)
    print(f"\n[2] Labels na globaal paradigm-strippen ({len(globale_labels)} stuks):")
    for l in globale_labels:
        print(f"      {l!r}")

    # --- 3. Per <found_lemmata>-blok: labels voor en na strip ---
    blokken = re.findall(r'<found_lemmata>.*?</found_lemmata>', xml, re.DOTALL)
    print(f"\n[3] Per <found_lemmata>-blok ({len(blokken)} blokken):")
    for i, blok in enumerate(blokken):
        labels_heel = re.findall(r'<label>(.*?)</label>', blok)
        clean = re.sub(r'<paradigm>.*?</paradigm>', '', blok, flags=re.DOTALL)
        labels_gestript = re.findall(r'<label>(.*?)</label>', clean)
        lemmas = re.findall(r'<lemma>(.*?)</lemma>', clean)
        print(f"  blok {i}:  lemma(s): {lemmas}")
        print(f"          labels (heel blok): {labels_heel}")
        print(f"          labels (na strip):  {labels_gestript}")
        if len(labels_heel) != len(labels_gestript):
            print(f"          *** {len(labels_heel) - len(labels_gestript)} label(s) zitten BINNEN <paradigm> ***")

for woord in TESTWOORDEN:
    try:
        xml = haal_xml(woord)
        analyseer(woord, xml)
    except Exception as e:
        print(f"\n[FOUT] {woord!r}: {e}")
    time.sleep(0.4)

print("\n\nKlaar.")
