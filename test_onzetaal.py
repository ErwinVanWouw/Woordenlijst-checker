import requests

headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://onzetaal.nl/"
}

print("=== Autocomplete endpoint ===")
try:
    r1 = requests.get(
        "https://onzetaal.nl/?id=-940&contentonly=true&addroot=false&d=standby",
        headers=headers, timeout=5
    )
    print(f"Status: {r1.status_code}")
    print(f"Content-Type: {r1.headers.get('Content-Type')}")
    print(r1.text[:1000])
except Exception as e:
    print(f"Fout: {e}")

print("\n=== Result endpoint ===")
try:
    r2 = requests.get(
        "https://onzetaal.nl/?id=-827&unitsearch=standby",
        headers=headers, timeout=5
    )
    print(f"Status: {r2.status_code}")
    print(f"Content-Type: {r2.headers.get('Content-Type')}")
    # Zoek naar de relevante HTML-structuur
    import re
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
