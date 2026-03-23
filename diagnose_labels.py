import requests, re, time

testwoorden = [
    # Klassieke woordsoorten
    'in', 'groot', 'snel', 'ik', 'twee', 'oef', 'en', 'van', 'lopen', 'fiets',
    # Mogelijke 'overig'-gevallen
    'anti-', 'bv.', 'aids', 'laser', 'pre-', 'on-',
]

alle_labels = set()

for woord in testwoorden:
    try:
        r = requests.get("https://woordenlijst.org/MolexServe/lexicon/find_wordform", params={
            "database": "gig_pro_wrdlst", "wordform": woord, "paradigm": "true",
            "diminutive": "true", "onlyvalid": "true", "regex": "false",
            "dummy": str(int(time.time() * 1000))
        }, timeout=5)
        # Strip paradigm-blokken zodat alleen top-level <label> overblijven
        xml = re.sub(r'<paradigm>.*?</paradigm>', '', r.text, flags=re.DOTALL)
        labels = re.findall(r'<label>(.*?)</label>', xml)
        alle_labels.update(labels)
        status = "GEVONDEN" if "<found_lemmata>" in r.text else "niet gevonden"
        print(f"  {woord!r:20} [{status}]  labels: {labels}")
    except Exception as e:
        print(f"  {woord!r:20} [FOUT] {e}")
    time.sleep(0.4)

print("\n--- Alle unieke top-level labels ---")
for lbl in sorted(alle_labels):
    print(f"  {lbl!r}")
