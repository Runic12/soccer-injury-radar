import os
import http.client
import json
from datetime import datetime, timezone, timedelta

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

# Active campaign year
CURRENT_SEASON = 2026
NOW = datetime.now(timezone.utc)
# Look back up to 10 days (captures immediate prior match/international window) through any upcoming fixtures
ACTIVE_WINDOW_START = NOW - timedelta(days=10)

output_database = {}

for key, meta in LEAGUES.items():
    endpoint = f"/injuries?league={meta['id']}&season={CURRENT_SEASON}"
    print(f"\nProcessing active live casualties for {meta['name']} (Season {CURRENT_SEASON})...")
    
    try:
        conn.request("GET", endpoint, headers=headers)
        res = conn.getresponse()
        raw = res.read().decode("utf-8")
        data = json.loads(raw)
        
        results = data.get("response", [])
        
        # If the newly kicked-off season has sparse logs yet, gracefully fall back to transition data
        if not results:
            print(f"Notice: No active telemetry under {CURRENT_SEASON}, checking current cycle fallback...")
            conn.request("GET", f"/injuries?league={meta['id']}&season={CURRENT_SEASON - 1}", headers=headers)
            res = conn.getresponse()
            data = json.loads(res.read().decode("utf-8"))
            results = data.get("response", [])

        teams_map = {}
        for entry in results:
            team_info = entry.get("team", {})
            t_id = str(team_info.get("id", ""))
            t_name = team_info.get("name", "Unknown Squad")

            player_info = entry.get("player", {})
            p_id = str(player_info.get("id", ""))
            p_name = player_info.get("name", "Unknown Athlete")
            raw_reason = player_info.get("reason") or "Undisclosed Outage"
            raw_type = player_info.get("type") or "Missing Fixture"

            fixture = entry.get("fixture", {})
            f_date_str = fixture.get("date")
            entry_date = None
            if f_date_str:
                try:
                    entry_date = datetime.fromisoformat(f_date_str.replace("Z", "+00:00"))
                except Exception:
                    pass

            # Classify Status: Out vs Doubtful
            lower_type = (raw_type + " " + raw_reason).lower()
            if any(term in lower_type for term in ["doubtful", "questionable", "late test"]):
                availability = "Doubtful (Late Fitness Assessment)"
            else:
                availability = "Sidelined (Ruled Out)"

            # Root Cause Mechanism
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
                    "players": {}
                }

            if p_id not in teams_map[t_id]["players"]:
                teams_map[t_id]["players"][p_id] = {
                    "name": p_name,
                    "pos": "First Team Squad",
                    "type": raw_reason,
                    "cat": cat,
                    "status": availability,
                    "return": "Evaluated Ahead of Next Match",
                    "daysLost": 7,
                    "durability": "Under Surveillance",
                    "history": [],
                    "latest_date": entry_date,
                    "is_active_now": False
                }

            p_entry = teams_map[t_id]["players"][p_id]
            if raw_reason not in p_entry["history"]:
                p_entry["history"].append(raw_reason)

            # Check if this injury applies to current/upcoming match window
            if entry_date:
                if not p_entry["latest_date"] or entry_date >= p_entry["latest_date"]:
                    p_entry["latest_date"] = entry_date
                    p_entry["type"] = raw_reason
                    p_entry["cat"] = cat
                    p_entry["status"] = availability
                
                # Active if scheduled in an upcoming fixture or missed a game in the last 10 days
                if entry_date >= ACTIVE_WINDOW_START:
                    p_entry["is_active_now"] = True

        # Assemble strictly active squads
        final_team_list = []
        for t_id, t_data in teams_map.items():
            active_injured = []
            for p_id, p_stats in t_data["players"].items():
                if p_stats["is_active_now"]:
                    outage_count = len(p_stats["history"])
                    if outage_count >= 3:
                        p_stats["durability"] = "High Risk (Chronic / Recurrent)"
                    elif outage_count == 2:
                        p_stats["durability"] = "Moderate Risk (Secondary Outage)"
                    else:
                        p_stats["durability"] = "Acute (Isolated Absence)"

                    # Clean internal date fields
                    del p_stats["latest_date"]
                    del p_stats["is_active_now"]
                    active_injured.append(p_stats)

            if active_injured:
                final_team_list.append({
                    "id": t_id,
                    "name": t_data["name"],
                    "injured": active_injured
                })

        output_database[key] = {
            "name": meta["name"],
            "teams": sorted(final_team_list, key=lambda x: len(x["injured"]), reverse=True)
        }
        print(f"Total current sidelined players in {meta['name']}: {sum(len(t['injured']) for t in final_team_list)}")

    except Exception as e:
        print(f"Pipeline error on {meta['name']}: {e}")

with open("data.json", "w") as f:
    json.dump(output_database, f, indent=2)

print("\nWrite complete: Live active roster synced to data.json.")
