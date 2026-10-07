import os
import json
import requests

# Retrieve your API key securely from GitHub Actions secrets
API_KEY = os.environ.get("API_FOOTBALL_KEY", "").strip()
BASE_URL = "https://v3.football.api-sports.io/injuries"

headers = {
    'x-apisports-key': API_KEY,
    'Accept': 'application/json'
}

# Target leagues mapping
LEAGUES = {
    "epl": {"id": 39, "name": "Premier League", "season": "2026"},
    "laliga": {"id": 140, "name": "La Liga", "season": "2026"},
    "seriea": {"id": 135, "name": "Serie A", "season": "2026"},
    "bundesliga": {"id": 78, "name": "Bundesliga", "season": "2026"},
    "mls": {"id": 253, "name": "MLS", "season": "2026"}
}

output_database = {}

for key, meta in LEAGUES.items():
    print(f"\nFetching live injuries for {meta['name']}...")
    teams_map = {}
    
    try:
        url = f"{BASE_URL}?league={meta['id']}&season={meta['season']}"
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"API Error for {meta['name']}: Status {response.status_code}")
            continue
            
        data = response.json()
        results = data.get("response", [])
        print(f"Found {len(results)} active injury records.")
        
        for entry in results:
            team_info = entry.get("team", {})
            t_name = team_info.get("name", "Unknown Club")
            t_id = t_name.lower().replace(" ", "_")
            
            player_info = entry.get("player", {})
            p_name = player_info.get("name", "Unknown Athlete")
            p_pos = player_info.get("position", "First Team Squad")
            
            # API-Football fixture/injury attributes
            injury_type = player_info.get("type", "Undisclosed Injury")
            injury_reason = player_info.get("reason", "Medical Absence")
            
            full_desc = f"{injury_type}: {injury_reason}"
            lower_r = full_desc.lower()
            
            # Categorization logic for your dashboard metrics
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
                "status": "Sidelined (Active)",
                "return": "Pending Assessment",
                "daysLost": 10,
                "durability": "Active Casualty",
                "history": [injury_type]
            })

        final_team_list = list(teams_map.values())
        
        # Fallback safeguard if a league returns empty array during off-seasons
        if not final_team_list:
            final_team_list = [{
                "id": "squad_sync",
                "name": f"{meta['name']} Club",
                "injured": [{
                    "name": "No Active Injuries Reported",
                    "pos": "Squad",
                    "type": "Clearance",
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
        print(f"Successfully processed {meta['name']}.")

    except Exception as e:
        print(f"Error connecting to API for {meta['name']}: {e}")

# Write structured database to data.json for your frontend
with open("data.json", "w") as f:
    json.dump(output_database, f, indent=2)

print("\nWrite complete: Live API data saved to data.json.")
