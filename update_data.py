import os
import json
import time
import requests

# Pulls your direct API-Sports key from your updated RAPIDAPI_KEY secret
API_KEY = os.environ.get("RAPIDAPI_KEY", "").strip()

HEADERS = {
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
    print(f"\n[{meta['name']}] Fetching list of all active clubs...")
    
    try:
        # 1. Fetch all teams in this specific league
        teams_url = "https://v3.football.api-sports.io/teams"
        teams_resp = requests.get(teams_url, headers=HEADERS, params={"league": meta["id"], "season": meta["season"]}, timeout=15)
        teams_data = teams_resp.json().get("response", [])
        
        final_team_list = []
        league_active_injuries = 0
        
        # 2. Loop through every single team
        for t_data in teams_data:
            team_info = t_data.get("team", {})
            t_id_num = team_info.get("id")
            t_name = team_info.get("name", "Unknown Club")
            t_id_str = t_name.lower().replace(" ", "_")
            
            if not t_id_num:
                continue
                
            print(f"  -> Scanning multi-competition injury reports for {t_name}...")
            
            inj_url = "https://v3.football.api-sports.io/injuries"
            # NOTE: We omit 'league' to catch all competitions (Champions League, Cups, etc)
            inj_resp = requests.get(inj_url, headers=HEADERS, params={"team": t_id_num, "season": meta["season"]}, timeout=15)
            inj_records = inj_resp.json().get("response", [])
            
            player_latest_records = {}
            all_team_dates = set()
            
            # Track the absolute latest missed match for each player AND all dates the team had an injury report
            for entry in inj_records:
                p_name = (entry.get("player") or {}).get("name")
                f_date = str((entry.get("fixture") or {}).get("date", ""))[:10]
                
                if not p_name or not f_date:
                    continue
                    
                all_team_dates.add(f_date)
                
                if p_name not in player_latest_records or f_date > player_latest_records[p_name]["date"]:
                    player_latest_records[p_name] = {
                        "date": f_date,
                        "entry": entry
                    }
            
            # Sort all dates to find the most recent ones
            sorted_dates = sorted(list(all_team_dates), reverse=True)
            # We take the top 2 most recent dates. This covers the "next" match and the "just played" match.
            valid_active_dates = sorted_dates[:2]
            
            team_injured_list = []
            
            for p_name, record in player_latest_records.items():
                
                # TRUE IF: The player was on the injury report for the team's most recent or upcoming match
                if record["date"] in valid_active_dates:
                    entry = record["entry"]
                    
                    p_photo = (entry.get("player") or {}).get("photo")
                    p_pos = (entry.get("player") or {}).get("position") or "First Team Squad"
                    injury_type = (entry.get("player") or {}).get("type") or "Undisclosed"
                    injury_reason = (entry.get("player") or {}).get("reason") or "Medical Absence"
                    
                    full_desc = f"{injury_type}: {injury_reason}"
                    lower_r = full_desc.lower()
                    
                    # Ignore players who transferred or are out on loan
                    if "transfer" in lower_r or "loan" in lower_r:
                        continue
                    
                    # Categorize the injury
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
                        
                    team_injured_list.append({
                        "name": p_name,
                        "photo": p_photo,
                        "pos": p_pos,
                        "type": full_desc.title(),
                        "cat": cat,
                        "status": "Sidelined",
                        "return": expected_return,
                        "daysLost": "N/A",
                        "durability": "Active Casualty",
                        "history": [injury_type]
                    })
                    league_active_injuries += 1
            
            # If the team has injured players, add them to the master list
            if team_injured_list:
                final_team_list.append({
                    "id": t_id_str,
                    "name": t_name,
                    "injured": sorted(team_injured_list, key=lambda x: x["name"])
                })
                
            # Sleep briefly to ensure we don't trip any API rate limits
            time.sleep(0.2)
            
        print(f"Success! {meta['name']} processed. {league_active_injuries} active injuries found.")
        
        # Fallback if an entire league is somehow 100% healthy
        if not final_team_list:
            final_team_list = [{
                "id": "squad_clear",
                "name": f"{meta['name']} Squad",
                "injured": [{
                    "name": "Full Squad Available",
                    "photo": "",
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

# Save the final compiled JSON
with open("data.json", "w") as f:
    json.dump(output_database, f, indent=2)

print("\nWrite complete: Premium multi-competition dataset saved to data.json.")
