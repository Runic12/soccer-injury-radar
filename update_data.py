import os
import http.client
import json

API_KEY = os.environ.get("RAPIDAPI_KEY", "").strip()

print(f"DEBUG: Key length detected: {len(API_KEY)}")
if not API_KEY:
    print("CRITICAL: RAPIDAPI_KEY secret is completely empty!")

conn = http.client.HTTPSConnection("v3.football.api-sports.io")

headers = {
    'x-rapidapi-host': "v3.football.api-sports.io",
    'x-rapidapi-key': API_KEY,
    'x-apisports-key': API_KEY
}

# Key D1 Leagues: Premier League (39), La Liga (140), Serie A (135), Bundesliga (78), MLS (253)
LEAGUES = {
    "epl": {"id": 39, "name": "Premier League"},
    "laliga": {"id": 140, "name": "La Liga"},
    "seriea": {"id": 135, "name": "Serie A"},
    "bundesliga": {"id": 78, "name": "Bundesliga"},
    "mls": {"id": 253, "name": "MLS"}
}

# The active European campaign year
SEASON = 2024

output_database = {}

for key, meta in LEAGUES.items():
    endpoint = f"/injuries?league={meta['id']}&season={SEASON}"
    print(f"\n--- Requesting {meta['name']} (ID: {meta['id']}, Season: {SEASON}) ---")
    
    try:
        conn.request("GET", endpoint, headers=headers)
        res = conn.getresponse()
        raw = res.read().decode("utf-8")
        data = json.loads(raw)
        
        if "errors" in data and data["errors"]:
            print(f"API Error details: {data['errors']}")
            
        results = data.get("response", [])
        print(f"Total entries found: {len(results)}")
        
        teams_map = {}
        for entry in results:
            team_info = entry.get("team", {})
            t_name = team_info.get("name", "Unknown")
            t_id = str(team_info.get("id", ""))
            
            player_info = entry.get("player", {})
            reason = player_info.get("reason", "Undisclosed Strain")
            
            # Categorize failure mechanism
            lower_r = reason.lower()
            if any(w in lower_r for w in ["hamstring", "muscle", "groin", "adductor", "thigh", "calf"]):
                cat = "Soft-Tissue"
            elif any(w in lower_r for w in ["acl", "cruciate", "ligament", "meniscus", "fracture", "ankle"]):
                cat = "Structural"
            else:
                cat = "Trauma/Impact"
                
            if t_id not in teams_map:
                teams_map[t_id] = {
                    "id": t_id,
                    "name": t_name,
                    "injured": []
                }
                
            teams_map[t_id]["injured"].append({
                "name": player_info.get("name", "Unknown"),
                "pos": player_info.get("type", "Player"),
                "type": reason,
                "cat": cat,
                "return": "Monitored Daily",
                "daysLost": 14,
                "durability": "Under Surveillance",
                "history": [reason]
            })
            
        output_database[key] = {
            "name": meta["name"],
            "teams": list(teams_map.values())
        }
    except Exception as e:
        print(f"Connection/JSON error on {meta['name']}: {e}")

with open("data.json", "w") as f:
    json.dump(output_database, f, indent=2)

print("\nWrite complete: data.json saved.")
