import os
import json
import time
import requests
from datetime import datetime

# Pulls your direct API-Sports key from your updated RAPIDAPI_KEY secret
API_KEY = os.environ.get("RAPIDAPI_KEY", "").strip()
URL = "https://v3.football.api-sports.io/injuries"

headers = {
    'x-apisports-key': API_KEY,
    'Accept': 'application/json'
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

# Capture today's date to filter out past (healed) injuries
today_str = datetime.now().strftime("%Y-%m-%d")

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
        
        active_injuries = 0
        
        for entry in results:
            # 1. Filter out past fixtures to remove healed players
            fixture_info = entry.get("fixture") or {}
            fixture_date = str(fixture_info.get("date", ""))[:10]
            
            if fixture_date and fixture_date < today_str:
                continue
                
            # 2. Use 'or' fallbacks to prevent NoneType crashes
            team_info = entry.get("team") or {}
            t_name = team_info.get("name") or "Unknown Club"
            t_id = t_name.lower().replace(" ", "_")
            
            player_info = entry.get("player") or {}
            p_name = player_info.get("name") or "Unknown Athlete"
            p_pos = player_info.get("position") or "First Team Squad"
            
            injury_type = player_info.get("type") or "Undisclosed"
            injury_reason = player_info.get("reason") or "Medical Absence"
            
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
                    "injured": {}
                }

            # 3. Use a dictionary keyed by player name to prevent duplicate entries 
            # if a player is scheduled to miss multiple future matches
            if p_name not in teams_map[t_id]["injured"]:
                active_injuries += 1
                teams_map[t_id]["injured"][p_name] = {
                    "name": p_name,
                    "pos": p_pos,
                    "type": full_desc.title(),
                    "cat": cat,
                    "status": "Sidelined",
                    "return": "Pending Assessment",
                    "daysLost": "N/A",
                    "durability": "Active Casualty",
                    "history": [injury_type]
                }

        # Convert the dictionary of players back to a standard list
        final_team_list = []
        for t_id, t_data in teams_map.items():
            t_data["injured"] = list(t_data["injured"].values())
            final_team_list.append(t_data)
            
        print(f"Success! Filtered down to {active_injuries} currently active injuries for {meta['name']}.")
        
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
                    "daysLost": "0",
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
