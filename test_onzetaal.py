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

print("\n=== Result endpoint (standby) ===")
try:
    r2 = session.get(
        BASE + "/?id=-827&unitsearch=standby",
        timeout=5
    )
    print(f"Status: {r2.status_code}")
    print(f"Content-Type: {r2.headers.get('Content-Type')}")
    hits = re.findall(r'<div class="unitname"[^>]*>.*?</div>', r2.text, re.DOTALL)
    if hits:
        print(f"\nGevonden unitname divs ({len(hits)}):")
        for h in hits:
            print(h)
    else:
        print("\nGeen unitname divs gevonden. Eerste 2000 tekens:")
        print(r2.text[:2000])
except Exception as e:
    print(f"Fout: {e}")
