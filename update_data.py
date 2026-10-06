import os
import http.client
import json
import time

API_KEY = os.environ.get("RAPIDAPI_KEY", "").strip()

conn = http.client.HTTPSConnection("v3.football.api-sports.io")

headers = {
    'x-rapidapi-host': "v3.football.api-sports.io",
    'x-rapidapi-key': API_KEY,
    'x-apisports-key': API_KEY
}

# Pulling the last matchday (covers 1 match per team)
LEAGUES = {
    "epl": {"id": 39, "name": "Premier League", "matches": 10},
    "laliga": {"id": 140, "name": "La Liga", "matches": 10},
    "seriea": {"id": 135, "name": "Serie A", "matches": 10},
    "bundesliga": {"id": 78, "name": "Bundesliga", "matches": 9},
    "mls": {"id": 253, "name": "MLS", "matches": 14}
}

ACTIVE_SEASON = 2026
output_database = {}

for key, meta in LEAGUES.items():
    print(f"\n--- Fetching latest matchday fixtures for {meta['name']} ---")
    
    try:
        # 1. Fetch the most recent matchday fixtures
        conn.request("GET", f"/fixtures?league={meta['id']}&season={ACTIVE_SEASON}&last={meta['matches']}", headers=headers)
        res = conn.getresponse()
        raw = res.read().decode("utf-8")
        data = json.loads(raw)
        
        fixtures = data.get("response", [])
        fixture_ids = [str(f["fixture"]["id"]) for f in fixtures if "fixture" in f]
        
        print(f"Found {len(fixture_ids)} recent fixtures. Pulling active injury sheets...")
        
        teams_map = {}
        
        # 2. Pull the exact injury sheet for each recent fixture
        for fid in fixture_ids:
            conn.request("GET", f"/injuries?fixture={fid}", headers=headers)
            res_inj = conn.getresponse()
            inj_data = json.loads(res_inj.read().decode("utf-8"))
            results = inj_data.get("response", [])
            
            for entry in results:
                team_info = entry.get("team", {})
                t_id = str(team_info.get("id", ""))
                t_name = team_info.get("name", "Unknown Squad")

                player_info = entry.get("player", {})
                p_id = str(player_info.get("id", ""))
                p_name = player_info.get("name", "Unknown Athlete")
                raw_reason = player_info.get("reason") or "Undisclosed Strain"
                raw_type = player_info.get("type") or "Missing Fixture"

                # Availability Status
                combined_text = (raw_type + " " + raw_reason).lower()
                if any(term in combined_text for term in ["doubtful", "questionable", "late test", "doubt"]):
                    availability = "Doubtful (Late Fitness Assessment)"
                else:
                    availability = "Sidelined (Ruled Out)"

                # Category Mapping
                lower_r = raw_reason.lower()
                if any(w in lower_r for w in ["hamstring", "muscle", "groin", "adductor", "thigh", "calf"]):
                    cat = "Soft-Tissue"
                elif any(w in lower_r for w in ["acl", "cruciate", "ligament", "meniscus", "fracture", "ankle", "knee"]):
                    cat = "Structural"
                else:
                    cat = "Trauma/Impact"

                if t_id not in teams_map:
                    teams_map[t_id] = {
                        "id": t_id,
                        "name": t_name,
                        "injured": {}
                    }

                # Dictionary prevents duplicates of the same player
                teams_map[t_id]["injured"][p_id] = {
                    "name": p_name,
                    "pos": "First Team Squad",
                    "type": raw_reason,
                    "cat": cat,
                    "status": availability,
                    "return": "Evaluated Weekly",
                    "daysLost": 7,
                    "durability": "Active Casualty",
                    "history": [raw_reason]
                }
                
            # Brief pause to prevent hitting API rate limits (10 calls/sec)
            time.sleep(0.3) 

        # 3. Format JSON structure
        final_team_list = []
        for t_id, t_data in teams_map.items():
            injured_list = list(t_data["injured"].values())
            if injured_list:
                final_team_list.append({
                    "id": t_id,
                    "name": t_data["name"],
                    "injured": injured_list
                })

        output_database[key] = {
            "name": meta["name"],
            "teams": sorted(final_team_list, key=lambda x: len(x["injured"]), reverse=True)
        }
        print(f"Active sidelined players recorded: {sum(len(t['injured']) for t in final_team_list)}")

    except Exception as e:
        print(f"Error processing {meta['name']}: {e}")

with open("data.json", "w") as f:
    json.dump(output_database, f, indent=2)

print("\nWrite complete: Matchday casualty sheets saved to data.json.")
