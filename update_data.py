import os
import json
import time
import requests

API_KEY = os.environ.get("RAPIDAPI_KEY", "").strip()
URL = "https://api-football-v1.p.rapidapi.com/v3/injuries"

headers = {
    'x-rapidapi-key': API_KEY,
    'x-rapidapi-host': 'api-football-v1.p.rapidapi.com'
}

# Configured for the active 2026 campaign across all 5 leagues
LEAGUES = {
    "epl": {"id": 39, "name": "Premier League", "season": "2026"},
    "laliga": {"id": 140, "name": "La Liga", "season": "2026"},
    "seriea": {"id": 135, "name": "Serie A", "season": "2026"},
    "bundesliga": {"id": 78, "name": "Bundesliga", "season": "2026"},
    "mls": {"id": 253, "name": "MLS", "season": "2026"}
}

output_database = {}

for key, meta in LEAGUES.items():
    print(f"\nFetching live injuries for {meta['name']} (Season {meta['season']})...")
    teams_map = {}
    
    try:
        response = requests.get(
            URL, 
            headers=headers, 
            params={"league": meta["id"], "season": meta["season"]}, 
            timeout=15
        )
        
        if response.status_code != 200:
            print(f"API Error for {meta['name']}: Status {response.status_code}")
            continue
            
        data = response.json()
        results = data.get("response", [])
        print(f"Success! Found {len(results)} active injury records for {meta['name']}.")
        
        for entry in results:
            team_info = entry.get("team", {})
            t_name = team_info.get("name", "Unknown Club")
            t_id = t_name.lower().replace(" ", "_")
            
            player_info = entry.get("player", {})
            p_name = player_info.get("name", "Unknown Athlete")
            p_pos = player_info.get("position", "First Team Squad")
            
            injury_type = player_info.get("type", "Undisclosed")
            injury_reason = player_info.get("reason", "Medical Absence")
            
            full_desc = f"{injury_type}: {injury_reason}"
            lower_r = full_desc.lower()
            
            if any(w in lower_r for w in ["hamstring", "muscle", "groin", "adductor", "thigh", "calf", "strain"]):
                cat = "Soft-Tissue"
            elif any(w in lower_r for w in ["acl", "cruciate", "ligament", "meniscus", "fracture", "ankle", "knee", "surgery"]):
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
                "name": p_name,
                "pos": p_pos,
                "type": full_desc.title(),
                "cat": cat,
                "status": "Sidelined",
                "return": "Under Evaluation",
                "daysLost": 14,
5                "durability": "Active Casualty",
                "history": [injury_type]
            })

        final_team_list = list(teams_map.values())
        
        if not final_team_list:
            final_team_list = [{
                "id": "squad_clear",
                "name": f"{meta['name']} Squad",
                "injured": [{
                    "name": "Full Squad Available",
                    "pos": "First Team",
                    "type": "No Active Injuries",
                    "cat": "Soft-Tissue",
                    "status": "Active",
                    "return": "N/A",
                    "daysLost": 0,
                    "durability": "Available",
                    "history": ["None"]
                }]
            }]

        output_database[key] = {
            "name": meta["name"],
            "teams": sorted(final_team_list, key=lambda x: x["name"])
        }

    except Exception as e:
        print(f"Error connecting to Pro API for {meta['name']}: {e}")

    time.sleep(1)

with open("data.json", "w") as f:
    json.dump(output_database, f, indent=2)

print("\nWrite complete: Live Pro multi-league dataset saved to data.json.")
