import requests
import re

BASE = "https://spelling.prisma.nl"

# Stap 1: haal een sessie-cookie op
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": BASE + "/",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
})

print("=== Sessie ophalen ===")
try:
    r0 = session.get(BASE + "/", timeout=5)
    print(f"Status: {r0.status_code}")
    print(f"Cookies: {dict(session.cookies)}")
except Exception as e:
    print(f"Fout: {e}")

print("\n=== Autocomplete endpoint (term=stand) ===")
try:
    r1 = session.get(
        BASE + "/?id=-940&contentonly=true&addroot=false&d=&term=stand",
        timeout=5
    )
    print(f"Status: {r1.status_code}")
    print(f"Content-Type: {r1.headers.get('Content-Type')}")
    print(r1.text[:1000])
except Exception as e:
    print(f"Fout: {e}")

def test_result(woord):
    print(f"\n=== Result endpoint ({woord}) ===")
    try:
        r = session.get(BASE + f"/?id=-827&unitsearch={woord}", timeout=5)
        print(f"Status: {r.status_code}")
        hits = re.findall(r'<div class="unitname"[^>]*>.*?</div>', r.text, re.DOTALL)
        if hits:
            print(f"Gevonden unitname divs ({len(hits)}):")
            for h in hits:
                print(h)
            # Zoek ook naar officiële spelling (lref)
            lrefs = re.findall(r'<a href="([^"]+)" class="lref">([^<]+)</a>', r.text)
            if lrefs:
                print(f"Officiële spelling (lref): {lrefs}")
        else:
            print("Geen unitname divs gevonden — geen resultaat of ander formaat.")
            print(r.text[:500])
    except Exception as e:
        print(f"Fout: {e}")

test_result("standby")    # alternatief
test_result("fiets")      # gewoon woord
test_result("xyzqqqq")    # niet-bestaand woord
