import urllib.request
import json

def fetch_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode('utf-8'))

print("\n--- ESPN Roster Structure Diagnostic ---")
try:
    # Fetch Arsenal's internal roster directly
    url = "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/teams/359/roster"
    data = fetch_json(url)
    
    # We will search the JSON to find the actual list of athletes
    athletes = data.get("athletes", [])
    if not athletes:
        # Sometimes it's nested under another athletes array
        athletes = data.get("athletes", [{}])[0].get("items", [])
        
    if athletes:
        print("Successfully found the roster! Here is the exact JSON for one player:\n")
        print(json.dumps(athletes[0], indent=2))
    else:
        print("Could not locate the athletes array. Here is the top-level structure:")
        print(json.dumps(list(data.keys()), indent=2))

except Exception as e:
    print(f"Connection Failed: {e}")
