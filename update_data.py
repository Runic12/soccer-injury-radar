import os
import http.client
import json

API_KEY = os.environ.get("RAPIDAPI_KEY", "").strip()

conn = http.client.HTTPSConnection("v3.football.api-sports.io")

headers = {
    'x-rapidapi-host': "v3.football.api-sports.io",
    'x-rapidapi-key': API_KEY,
    'x-apisports-key': API_KEY
}

def test_endpoint(url):
    print(f"\n--- Checking: {url} ---")
    conn.request("GET", url, headers=headers)
    res = conn.getresponse()
    raw = res.read().decode("utf-8")
    data = json.loads(raw)
    errors = data.get("errors", {})
    results = data.get("response", [])
    print(f"Errors: {errors}")
    print(f"Count returned: {len(results)}")
    if results:
        # Print sample from first entry to inspect available fields
        print(f"Sample item: {json.dumps(results[0], indent=2)[:350]}...")
    return len(results)

# 1. Check if Premier League (39) has data for date queries
test_endpoint("/injuries?league=39&date=2026-10-05")

# 2. Check recent dates (past weekend matchday)
test_endpoint("/injuries?league=39&date=2026-10-04")
test_endpoint("/injuries?league=39&date=2026-10-03")

# 3. Check what seasons are formally registered for Premier League
test_endpoint("/leagues?id=39")
