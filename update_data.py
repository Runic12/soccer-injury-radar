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
        
        player_latest_records = {}
        team_latest_date = {}
        
        # 1. Track the most recent fixture date per club and latest missed match per player
        for entry in results:
            p_info = entry.get("player") or {}
            p_name = p_info.get("name")
            
            t_info = entry.get("team") or {}
            t_name = t_info.get("name") or "Unknown Club"
            t_id = t_name.lower().replace(" ", "_")
            
            f_info = entry.get("fixture") or {}
            f_date = str(f_info.get("date", ""))[:10]
            
            if not p_name or not f_date or not t_id:
                continue
                
            if t_id not in team_latest_date or f_date > team_latest_date[t_id]:
                team_latest_date[t_id] = f_date
                
            if p_name not in player_latest_records or f_date > player_latest_records[p_name]["date"]:
                player_latest_records[p_name] = {
                    "date": f_date,
                    "entry": entry,
                    "t_name": t_name,
                    "t_id": t_id
                }

        teams_map = {}
        active_injuries = 0
        
        # 2. Filter active injuries dynamically and estimate return windows
        for p_name, record in player_latest_records.items():
            t_id = record["t_id"]
            p_date_str = record["date"]
            t_latest_str = team_latest_date[t_id]
            
            p_dt = datetime.strptime(p_date_str, "%Y-%m-%d")
            t_dt = datetime.strptime(t_latest_str, "%Y-%m-%d")
            
            # Sidelined if player's latest missed game is within 14 days of team's most recent fixture
            if (t_dt - p_dt).days <= 14:
                entry = record["entry"]
                
                p_pos = (entry.get("player") or {}).get("position") or "First Team Squad"
                injury_type = (entry.get("player") or {}).get("type") or "Undisclosed"
                injury_reason = (entry.get("player") or {}).get("reason") or "Medical Absence"
                
                full_desc = f"{injury_type}: {injury_reason}"
                lower_r = full_desc.lower()
                
                # Dynamic clinical categorization and recovery window estimator
                if any(w in lower_r for w in ["acl", "cruciate"]):
                    cat = "Structural"
                    expected_return = "6-9 Months"
                elif any(w in lower_r for w in ["ligament", "meniscus", "fracture", "surgery", "ankle", "knee"]):
                    cat = "Structural"
                    expected_return = "2-4 Months"
                elif any(w in lower_r for w in ["hamstring", "muscle", "groin", "adductor", "thigh", "calf", "strain"]):
                    cat = "Soft-Tissue"
                    expected_return = "3-4 Weeks"
                elif any(w in lower_r for w in ["knock", "impact", "dead leg", "contusion"]):
                    cat = "Trauma/Impact"
                    expected_return = "Day-to-Day"
                else:
                    cat = "Trauma/Impact"
                    expected_return = "Pending Assessment"

                if t_id not in teams_map:
                    teams_map[t_id] = {
                        "id": t_id,
                        "name": record["t_name"],
                        "injured": []
                    }

                teams_map[t_id]["injured"].append({
                    "name": p_name,
                    "pos": p_pos,
                    "type": full_desc.title(),
                    "cat": cat,
                    "status": "Sidelined",
                    "return": expected_return,
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
