import os
import http.client
import json

API_KEY = os.environ.get("RAPIDAPI_KEY")

if not API_KEY:
    print("Warning: RAPIDAPI_KEY secret not found in environment.")

conn = http.client.HTTPSConnection("v3.football.api-sports.io")

headers = {
    'x-rapidapi-host': "v3.football.api-sports.io",
    'x-rapidapi-key': API_KEY or ""
}

# Major D1 Leagues: Premier League (39), La Liga (140), Serie A (135), Bundesliga (78), MLS (253)
LEAGUES = {
    "epl": {"id": 39, "name": "Premier League"},
    "laliga": {"id": 140, "name": "La Liga"},
    "seriea": {"id": 135, "name": "Serie A"},
    "bundesliga": {"id": 78, "name": "Bundesliga"},
    "mls": {"id": 253, "name": "MLS"}
}

output_database = {}
CURRENT_SEASON = 2026

for key, meta in LEAGUES.items():
    print(f"Fetching injury telemetry for {meta['name']}...")
    endpoint = f"/injuries?league={meta['id']}&season={CURRENT_SEASON}"
    
    try:
        conn.request("GET", endpoint, headers=headers)
        res = conn.getresponse()
        raw = res.read().decode("utf-8")
        data = json.loads(raw)
        
        teams_map = {}
        for entry in data.get("response", []):
            team_info = entry.get("team", {})
            t_name = team_info.get("name", "Unknown")
            t_id = str(team_info.get("id", ""))
            
            player_info = entry.get("player", {})
            reason = player_info.get("reason", "Undisclosed Strain")
            
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
        print(f"Error fetching {meta['name']}: {e}")

with open("data.json", "w") as f:
    json.dump(output_database, f, indent=2)

print("Telemetry sync complete. Written to data.json.")