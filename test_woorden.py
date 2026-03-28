"""
test_woorden.py — Commandoregeltester voor Woordenlijst-checker
Simuleert exact dezelfde stappen als perform_check() + check_word_online(),
inclusief apostrof-normalisatie en invoerfilter, maar zonder GUI of klembord.

Gebruik:
    python test_woorden.py
"""

import re
import sys
import time
import requests

# ---------------------------------------------------------------------------
# Gekopieerde constanten uit woordenlijstchecker.py (synchroon houden)
# ---------------------------------------------------------------------------

WOORDSOORT_PREFIXES = [
    ('bijvoeglijk naamwoord / bijwoord', 'bijvoeglijk naamwoord / bijwoord'),
    ('bijvoeglijk naamwoord',            'bijvoeglijk naamwoord'),
    ('zelfstandignaamwoordgroep',         'zelfstandignaamwoordgroep'),
    ('zelfstandig naamwoord',            None),
    ('naam',                             'naam'),
    ('hoofdwerkwoord',                   'werkwoord'),
    ('bijwoord',                         'bijwoord'),
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
    ('rangtelwoord',                     'telwoord'),
    ('tussenwerpsel',                    'tussenwerpsel'),
    ('symbool',                          'symbool'),
]

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

# ---------------------------------------------------------------------------
# Gekopieerde functies uit woordenlijstchecker.py (synchroon houden)
# ---------------------------------------------------------------------------

def _extract_woordsoort_entries(xml, word):
    blocks = re.findall(r'<found_lemmata>.*?</found_lemmata>', xml, re.DOTALL)
    seen_displays = set()
    entries = []

    for block in blocks:
        clean_block = re.sub(r'<paradigm>.*?</paradigm>', '', block, flags=re.DOTALL)
        labels_in_block = re.findall(r'<label>(.*?)</label>', clean_block)
        if not labels_in_block or not labels_in_block[0]:
            continue
        label = labels_in_block[0]

        lemma_match = re.search(r'<lemma>(.*?)</lemma>', clean_block)
        entry_lemma = lemma_match.group(1) if lemma_match else word

        display = None
        article = None
        gender = None
        matched = False

        for prefix, mapping in WOORDSOORT_PREFIXES:
            if label.startswith(prefix):
                matched = True
                if mapping is None:
                    genus_match = re.search(r'\(([^)]+)\)', label)
                    genus_raw = genus_match.group(1) if genus_match else ''
                    genus_core = re.sub(r',.*', '', genus_raw).strip()
                    if genus_core == 'o':
                        article = 'het'
                    elif '/' in genus_core and 'o' in genus_core:
                        article = 'de/het'
                    else:
                        article = 'de'
                    gender = genus_core if genus_core else None
                    display = "zelfstandig naamwoord"
                elif mapping == 'RAW':
                    display = label
                else:
                    display = mapping
                break

        if not matched:
            display = label

        # Exacte match, anders prefix-match
        if display in POS_AFKORTINGEN:
            display = POS_AFKORTINGEN[display]
        else:
            for key, short in POS_AFKORTINGEN.items():
                if display.startswith(key):
                    display = short + display[len(key):]
                    break

        # Strip persoonsvorm-subtype van voornaamwoorden
        if 'vnw.' in display:
            display = re.sub(r'\s*\(.*\)$', '', display).strip()

        is_meervoud = (display == 'znw.' and entry_lemma.lower() != word.lower())
        dedup_key = "znw.|mv." if is_meervoud else f"{display}|{article}|{gender}"
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


def check_word_online(word):
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

    try:
        response = requests.get(api_url, params=params, timeout=5)
        response.raise_for_status()
        xml_content = response.text

        if "<found_lemmata>" in xml_content:
            wordforms = re.findall(r'<wordform>(.*?)</wordform>', xml_content)
            lemmas = [l for l in re.findall(r'<lemma>(.*?)</lemma>', xml_content) if l]
            entries = _extract_woordsoort_entries(xml_content, word_normalized)

            article = None
            gender = None
            gender_info_list = None

            noun_entries = [e for e in entries if e.get('article')]
            if noun_entries:
                article = noun_entries[0]['article']
                gender = noun_entries[0]['gender']

            word_info = {'entries': entries} if entries else None

            wn_lower = re.escape(word_normalized.lower())
            paradigm_blocks = re.findall(r'<paradigm>.*?</paradigm>', xml_content, re.DOTALL)

            is_plural = bool(re.search(
                r'<label>meervoud</label>.*?<wordform>' + wn_lower + r'</wordform>',
                xml_content, re.DOTALL
            ))
            is_meervoud_in_block = any(
                re.search(r'<label>meervoud</label>', block) and
                re.search(r'<wordform>' + wn_lower + r'</wordform>', block)
                for block in paradigm_blocks
            )
            is_also_singular = any(
                re.search(r'<label>enkelvoud</label>', block) and
                re.search(r'<wordform>' + wn_lower + r'</wordform>', block)
                for block in paradigm_blocks
            )

            if is_plural and not is_also_singular:
                article = 'de'
                gender = None

            already_has_meervoud = any(e.get('is_meervoud') for e in entries)
            if is_meervoud_in_block and is_also_singular and entries and not already_has_meervoud:
                entries.append({
                    'display': 'znw.',
                    'article': None,
                    'gender': None,
                    'lemma': entries[0].get('lemma', word_normalized),
                    'is_meervoud': True,
                })
                word_info = {'entries': entries}

            if word_normalized in lemmas:
                return True, word, None, article, word_info, gender, gender_info_list

            has_internal_caps_lemma = any(
                any(c.isupper() for c in lemma[1:]) for lemma in lemmas
            )

            if has_internal_caps_lemma:
                if word_normalized in wordforms:
                    base_lemma = None
                    for lemma in lemmas:
                        if any(c.isupper() for c in lemma[1:]):
                            if word_normalized.lower().startswith(lemma.lower()[:5]):
                                base_lemma = lemma
                                break
                    if base_lemma:
                        min_len = min(len(base_lemma), len(word_normalized))
                        exact_match = all(
                            base_lemma[i].isupper() == word_normalized[i].isupper()
                            for i in range(min_len)
                        )
                        if exact_match:
                            return True, word, None, article, word_info, gender, gender_info_list

                relevant_lemmas = [l for l in lemmas if any(c.isupper() for c in l[1:])]
                if relevant_lemmas:
                    return False, word, f"Gebruik '{relevant_lemmas[0]}'", None, None, None, None
                return False, word, "Controleer de spelling", None, None, None, None

            for lemma in lemmas:
                if lemma.lower() == word_normalized.lower() and lemma != word_normalized:
                    lowercase_versions = [l for l in lemmas if l == word_normalized.lower()]
                    uppercase_versions = [l for l in lemmas if l[0].isupper() and l.lower() == word_normalized.lower()]
                    if lowercase_versions and uppercase_versions:
                        continue
                    is_sentence_caps = (
                        len(word_normalized) > 1 and
                        word_normalized[0].isupper() and
                        word_normalized[1:].islower() and
                        ' ' not in word_normalized
                    )
                    if is_sentence_caps:
                        continue
                    return False, word, f"Gebruik '{lemma}'", None, None, None, None

            if (len(word_normalized) > 1 and
                    word_normalized[0].isupper() and
                    word_normalized[1:].islower() and
                    ' ' not in word_normalized):
                if word_normalized.lower() in wordforms or word_normalized.lower() in lemmas:
                    return True, word, None, article, word_info, gender, gender_info_list

            if word_normalized in wordforms or word_normalized in lemmas:
                return True, word, None, article, word_info, gender, gender_info_list

            return False, word, "Controleer de spelling", None, None, None, None

        else:
            suggestions = get_spelling_suggestions(word_normalized)
            if suggestions:
                return False, word, f"Bedoelde u: {suggestions}", None, None, None, None
            return False, word, None, None, None, None, None

    except requests.exceptions.RequestException as e:
        return False, word, f"Netwerkfout: {e}", None, None, None, None
    except Exception as e:
        return False, word, f"Fout: {e}", None, None, None, None


def get_spelling_suggestions(word):
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
        xml = response.text

        corrections_match = re.search(r'<corrections>(.*?)</corrections>', xml, re.DOTALL)
        if corrections_match:
            raw = corrections_match.group(1).strip()
            suggestions = [s.strip() for s in raw.split('|') if s.strip()][:3]
            if suggestions:
                return ', '.join(suggestions)

        best_guess_match = re.search(r'<best_guess>(.*?)</best_guess>', xml, re.DOTALL)
        if best_guess_match:
            return best_guess_match.group(1).strip()

        return None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Invoerfilter — identiek aan perform_check() in woordenlijstchecker.py
# ---------------------------------------------------------------------------

def normaliseer_apostrof(word):
    """Typografische apostrofs normaliseren, zoals perform_check() doet."""
    return re.sub(r"[\u2019\u2018\u0060\u00B4\u02BC]", "'", word)


def invoerfilter(word):
    """
    Simuleert de invoerfilter uit perform_check().
    Geeft (geblokkeerd: bool, reden: str|None) terug.
    """
    # Te kort
    if len(word.strip()) < 2:
        return True, "te kort (< 2 tekens)"

    # Alleen cijfers
    if word.strip().isdigit():
        return True, "alleen cijfers"

    # Bevat spaties maar ook niet-woord-tekens buiten woord+spatie
    # (De app controleert of het eruitziet als 'een geldig woord of woordgroep')
    # Eenvoudige benadering: blokkeer als het uitsluitend leestekens/symbolen is
    if not re.search(r'[A-Za-z\u00C0-\u024F]', word):
        return True, "geen letters"

    return False, None


# ---------------------------------------------------------------------------
# Popup-weergave simuleren
# ---------------------------------------------------------------------------

def formatteer_resultaat(word_in, is_valid, word_out, error_message, article, word_info, gender):
    """Geeft een tekstrepresentatie van wat de popup toont."""
    lines = []
    if is_valid:
        lines.append("✓  GEVONDEN")
        if word_info and word_info.get('entries'):
            for e in word_info['entries']:
                parts = []
                if e.get('article'):
                    parts.append(e['article'])
                parts.append(e['display'])
                if e.get('gender'):
                    parts.append(f"({e['gender']})")
                if e.get('is_meervoud'):
                    parts.append("[mv.]")
                lines.append("   " + "  ".join(parts))
        elif article:
            lines.append(f"   {article}  znw.  ({gender})" if gender else f"   {article}  znw.")
    else:
        lines.append("✗  NIET GEVONDEN")
        if error_message:
            lines.append(f"   {error_message}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Testwoorden
# ---------------------------------------------------------------------------

TESTWOORDEN = [
    # --- Ronde 2 ---
    # Voegwoorden
    'omdat', 'want', 'hoewel', 'maar', 'toch',
    # Voornaamwoorden (persoonlijk, bezittelijk, wederkerend)
    'ik', 'jij', 'wij', 'ons', 'jullie',
    'die', 'mijn', 'deze', 'wie', 'elk',
    # Bijv.nw. kandidaten zonder bijwoord-functie
    'zwanger', 'getrouwd', 'nuchter', 'leeg', 'rood',
    # Bijwoord-only
    'immers', 'echt', 'zelfs', 'bijna',

    # --- Ronde 3: hoofdlettergevoeligheid & samenstellingen ---
    'pH', 'ph', 'PH',
    'mkb', 'MKB',
    'ziekte van Parkinson', 'ziekte van parkinson',
    'Goede Vrijdag', 'goede vrijdag',
    'Dag van de Arbeid', 'dag van de arbeid',
    'Europees Parlementslid', 'europees parlementslid',
    'Europees Parlementsleden',
    'NMa', 'nma',
    'CdK', 'cdk',

    # --- Ronde 4: woordsoort en homoniemen ---
    'vrouw', 'man', 'kind', 'kinderen',
    'harken', 'bal', 'deksel', 'aas',
    'weegschaal', 'Weegschaal',

    # --- Ronde 4b: invariante naamwoorden (enkelvoud = meervoud) ---
    'chassis', 'Chassis',

    # --- Ronde 4c: meervoud met beginhoofdletter ---
    'features', 'Features',

    # --- Ronde 4d: meervoud + enkelvoud + werkwoord (homoniemen) ---
    'kussen', 'Kussen',

    # --- Ronde 4e: enkelvoud met beginhoofdletter (normalisatie) ---
    'liniaal', 'Liniaal',

    # --- Ronde 4f: tussenwerpsel ---
    'goedemorgen',

    # --- Ronde 5: apostrof-varianten ---
    "taxi\u2019s",   # rechts typografisch (')
    "taxi\u2018s",   # links typografisch (')
    "taxi`s",        # backtick
    "taxi\u00B4s",   # acuut accent (´)
    "taxi\u02BCs",   # modifier letter apostrophe (ʼ)
    "taxi's",        # standaard apostrof — correcte vorm

    # --- Ronde 6: randgevallen & invoerfilter ---
    'CO\u2082',      # subscript (CO₂)
    'm\u00B3',       # superscript (m³)
    'P@ssw0rd!',
    'MyS3cUr3P4ss',
    '112',
]


# ---------------------------------------------------------------------------
# Hoofd
# ---------------------------------------------------------------------------

def main():
    BREED = 60
    print("=" * BREED)
    print("  Woordenlijst-checker — testrun")
    print(f"  {len(TESTWOORDEN)} testwoorden")
    print("=" * BREED)

    for woord_orig in TESTWOORDEN:
        # Stap 1: apostrof-normalisatie (zoals perform_check doet)
        woord = normaliseer_apostrof(woord_orig)
        genorm = f" → genormaliseerd: '{woord}'" if woord != woord_orig else ""

        print(f"\n{'─' * BREED}")
        print(f"  Invoer: '{woord_orig}'{genorm}")

        # Stap 2: invoerfilter
        geblokkeerd, reden = invoerfilter(woord)
        if geblokkeerd:
            print(f"  [FILTER] Geblokkeerd: {reden}")
            continue

        # Stap 3: API-controle
        is_valid, word_out, error_message, article, word_info, gender, _ = check_word_online(woord)

        # Stap 4: resultaat zoals popup
        print(formatteer_resultaat(woord, is_valid, word_out, error_message, article, word_info, gender))

    print(f"\n{'=' * BREED}")
    print("  Klaar.")
    print("=" * BREED)


if __name__ == "__main__":
    main()
