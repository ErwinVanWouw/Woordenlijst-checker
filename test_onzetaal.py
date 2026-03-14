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
    print(r1.text[:500])
except Exception as e:
    print(f"Fout: {e}")

print("\n=== Result endpoint ===")
try:
    r2 = requests.get(
        "https://onzetaal.nl/?id=-827&unitsearch=standby",
        headers=headers, timeout=5
    )
    print(f"Status: {r2.status_code}")
    print(r2.text[:1000])
except Exception as e:
    print(f"Fout: {e}")
