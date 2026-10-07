import os
import json
import time
import requests
from datetime import datetime, timedelta

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

# Creates a 14-day rolling window to identify currently injured players
cutoff_date = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")

for key, meta in LEAGUES.items():
    print(f"\nFetching live injuries for {meta['name']} (Season {meta['season']})...")
    
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
        
        # 1. Find the absolute latest missed match for every individual player
        player_latest_records = {}
        for entry in results:
            p_info = entry.get("player") or {}
            p_name = p_info.get("name")
            
            f_info = entry.get("fixture") or {}
            f_date = str(f_info.get("date", ""))[:10]
            
            if not p_name or not f_date:
                continue
                
            if p_name not in player_latest_records:
                player_latest_records[p_name] = {"date": f_date, "entry": entry}
            else:
                if f_date > player_latest_records[p_name]["date"]:
                    player_latest_records[p_name] = {"date": f_date, "entry": entry}
        
        # 2. Filter active injuries based on the 14-day cutoff window
        teams_map = {}
        active_injuries = 0
        
        for p_name, record in player_latest_records.items():
            if record["date"] >= cutoff_date:
                entry = record["entry"]
                
                t_info = entry.get("team") or {}
                t_name = t_info.get("name") or "Unknown Club"
                t_id = t_name.lower().replace(" ", "_")
                
                p_pos = (entry.get("player") or {}).get("position") or "First Team Squad"
                injury_type = (entry.get("player") or {}).get("type") or "Undisclosed"
                injury_reason = (entry.get("player") or {}).get("reason") or "Medical Absence"
                
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
                    "return": "Pending Assessment",
                    "daysLost": "N/A",
                    "durability": "Active Casualty",
                    "history": [injury_type]
                })
                active_injuries += 1

        final_team_list = list(teams_map.values())
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
