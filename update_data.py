import os
import http.client
import json
from datetime import datetime

API_KEY = os.environ.get("RAPIDAPI_KEY", "").strip()

conn = http.client.HTTPSConnection("v3.football.api-sports.io")

headers = {
    'x-rapidapi-host': "v3.football.api-sports.io",
    'x-rapidapi-key': API_KEY,
    'x-apisports-key': API_KEY
}

# Major D1 Leagues
LEAGUES = {
    "epl": {"id": 39, "name": "Premier League"},
    "laliga": {"id": 140, "name": "La Liga"},
    "seriea": {"id": 135, "name": "Serie A"},
    "bundesliga": {"id": 78, "name": "Bundesliga"},
    "mls": {"id": 253, "name": "MLS"}
}

SEASON = 2024
output_database = {}

for key, meta in LEAGUES.items():
    endpoint = f"/injuries?league={meta['id']}&season={SEASON}"
    print(f"\nProcessing active injury roster for {meta['name']}...")
    
    try:
        conn.request("GET", endpoint, headers=headers)
        res = conn.getresponse()
        raw = res.read().decode("utf-8")
        data = json.loads(raw)
        
        results = data.get("response", [])
        
        # 1. Identify each team's most recent fixture that has injury records logged
        team_latest_fixture_date = {}
        for entry in results:
            t_id = str(entry.get("team", {}).get("id", ""))
            f_date_str = entry.get("fixture", {}).get("date")
            if t_id and f_date_str:
                try:
                    f_date = datetime.fromisoformat(f_date_str.replace("Z", "+00:00")).replace(tzinfo=None)
                    if t_id not in team_latest_fixture_date or f_date > team_latest_fixture_date[t_id]:
                        team_latest_fixture_date[t_id] = f_date
                except Exception:
                    pass

        # 2. Track players: build their career history, but flag them as 'currently_injured'
        #    ONLY if their latest missed fixture matches the team's latest fixture window (within 7 days).
        teams_map = {}
        for entry in results:
            team_info = entry.get("team", {})
            t_id = str(team_info.get("id", ""))
            t_name = team_info.get("name", "Unknown")

            player_info = entry.get("player", {})
            p_id = str(player_info.get("id", ""))
            p_name = player_info.get("name", "Unknown")
            reason = player_info.get("reason", "Undisclosed Outage")

            fixture = entry.get("fixture", {})
            f_date_str = fixture.get("date")
            entry_date = None
            if f_date_str:
                try:
                    entry_date = datetime.fromisoformat(f_date_str.replace("Z", "+00:00")).replace(tzinfo=None)
                except Exception:
                    pass

            # Classify mechanism
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
                    "players": {}
                }

            if p_id not in teams_map[t_id]["players"]:
                teams_map[t_id]["players"][p_id] = {
                    "name": p_name,
                    "pos": player_info.get("type", "Squad Member"),
                    "type": reason,
                    "cat": cat,
                    "return": "Current Outage",
                    "daysLost": 0,
                    "durability": "Under Surveillance",
                    "history": [],
                    "latest_entry_date": entry_date or datetime.min
                }

            p_entry = teams_map[t_id]["players"][p_id]
            p_entry["daysLost"] += 7  # 1 fixture missed ≈ 1 week outage
            
            if reason not in p_entry["history"]:
                p_entry["history"].append(reason)

            if entry_date and entry_date >= p_entry["latest_entry_date"]:
                p_entry["latest_entry_date"] = entry_date
                p_entry["type"] = reason
                p_entry["cat"] = cat

        # 3. Filter out all cured players:
        # A player is ONLY included if their latest injury is from the team's most recent fixture cycle (last 7 days)
        final_team_list = []
        for t_id, t_data in teams_map.items():
            active_squad_injured = []
            latest_ref_date = team_latest_fixture_date.get(t_id, datetime.min)

            for p_id, p_stats in t_data["players"].items():
                player_latest = p_stats["latest_entry_date"]
                
                # Check if the player missed the squad's latest fixture (within 7 days of the team's latest fixture report)
                delta_days = (latest_ref_date - player_latest).total_seconds() / 86400.0
                
                if delta_days <= 7.0:
                    # Player is CURRENTLY sidelined (missed the latest match/week)
                    outage_count = len(p_stats["history"])
                    if outage_count >= 3:
                        p_stats["durability"] = "High Risk (Chronic / Recurrent)"
                    elif outage_count == 2:
                        p_stats["durability"] = "Moderate Risk (Secondary Strain)"
                    else:
                        p_stats["durability"] = "Acute / Short-Term Outage"

                    del p_stats["latest_entry_date"]
                    active_squad_injured.append(p_stats)

            if active_squad_injured:
                final_team_list.append({
                    "id": t_id,
                    "name": t_data["name"],
                    "injured": active_squad_injured
                })

        output_database[key] = {
            "name": meta["name"],
            "teams": sorted(final_team_list, key=lambda x: len(x["injured"]), reverse=True)
        }
        print(f"Verified current active casualties in {meta['name']}: {sum(len(t['injured']) for t in final_team_list)}")

    except Exception as e:
        print(f"Error processing {meta['name']}: {e}")

with open("data.json", "w") as f:
    json.dump(output_database, f, indent=2)

print("\nSync complete: Strictly current injuries saved to data.json.")
