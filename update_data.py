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

# We no longer need to hardcode match counts; the script will find every team dynamically
LEAGUES = {
    "epl": {"id": 39, "name": "Premier League"},
    "laliga": {"id": 140, "name": "La Liga"},
    "seriea": {"id": 135, "name": "Serie A"},
    "bundesliga": {"id": 78, "name": "Bundesliga"},
    "mls": {"id": 253, "name": "MLS"}
}

ACTIVE_SEASON = 2026
output_database = {}

for key, meta in LEAGUES.items():
    print(f"\n--- Fetching full season schedule for {meta['name']} ---")
    
    try:
        # 1. Fetch the entire season schedule (Allowed on Free Plan)
        conn.request("GET", f"/fixtures?league={meta['id']}&season={ACTIVE_SEASON}", headers=headers)
        res = conn.getresponse()
        raw = res.read().decode("utf-8")
        data = json.loads(raw)
        
        if data.get("errors"):
            print(f"API Error (Fixtures): {data['errors']}")
            
        fixtures = data.get("response", [])
        
        # 2. Filter for matches that have already finished (Full Time, Extra Time, Penalties)
        past_fixtures = [f for f in fixtures if f["fixture"]["status"]["short"] in ["FT", "AET", "PEN"]]
        
        # 3. Find the absolute most recent completed match for EVERY team
        team_latest_fixture = {}
        for f in past_fixtures:
            fid = str(f["fixture"]["id"])
            timestamp = f["fixture"]["timestamp"]
            t_home = str(f["teams"]["home"]["id"])
            t_away = str(f["teams"]["away"]["id"])
            
            if t_home not in team_latest_fixture or timestamp > team_latest_fixture[t_home]["ts"]:
                team_latest_fixture[t_home] = {"fid": fid, "ts": timestamp}
            if t_away not in team_latest_fixture or timestamp > team_latest_fixture[t_away]["ts"]:
                team_latest_fixture[t_away] = {"fid": fid, "ts": timestamp}
                
        # 4. Extract the unique list of fixture IDs to query
        unique_fids = list(set([data["fid"] for data in team_latest_fixture.values()]))
        
        print(f"Found {len(unique_fids)} latest unique fixtures. Pulling active injury sheets...")
        
        teams_map = {}
        
        # 5. Pull the exact injury sheet for each recent fixture
        for fid in unique_fids:
            conn.request("GET", f"/injuries?fixture={fid}", headers=headers)
            res_inj = conn.getresponse()
            inj_data = json.loads(res_inj.read().decode("utf-8"))
            
            if inj_data.get("errors"):
                print(f"API Error (Injuries for Fixture {fid}): {inj_data['errors']}")
                
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
                
            # Brief pause to prevent hitting API rate limits (10 calls/sec max)
            time.sleep(0.3) 

        # 6. Format JSON structure
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

print("\nWrite complete: Live matchday casualty sheets saved to data.json.")
