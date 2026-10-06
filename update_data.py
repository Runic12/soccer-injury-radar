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

# Major D1 Leagues: Premier League (39), La Liga (140), Serie A (135), Bundesliga (78), MLS (253)
LEAGUES = {
    "epl": {"id": 39, "name": "Premier League"},
    "laliga": {"id": 140, "name": "La Liga"},
    "seriea": {"id": 135, "name": "Serie A"},
    "bundesliga": {"id": 78, "name": "Bundesliga"},
    "mls": {"id": 253, "name": "MLS"}
}

# The active 2026–2027 campaign
ACTIVE_SEASON = 2026

output_database = {}

for key, meta in LEAGUES.items():
    endpoint = f"/injuries?league={meta['id']}&season={ACTIVE_SEASON}"
    print(f"\nFetching live 2026/27 campaign data for {meta['name']} (Season {ACTIVE_SEASON})...")
    
    try:
        conn.request("GET", endpoint, headers=headers)
        res = conn.getresponse()
        raw = res.read().decode("utf-8")
        data = json.loads(raw)
        
        results = data.get("response", [])
        print(f"Total season-to-date casualty reports for {meta['name']}: {len(results)}")

        if not results:
            print(f"No records returned for {meta['name']} under {ACTIVE_SEASON}.")
            output_database[key] = {"name": meta["name"], "teams": []}
            continue

        # 1. Identify the most recent fixture date recorded for each club in the active season
        club_latest_fixture = {}
        for entry in results:
            t_id = str(entry.get("team", {}).get("id", ""))
            f_date_str = entry.get("fixture", {}).get("date")
            if t_id and f_date_str:
                try:
                    f_date = datetime.fromisoformat(f_date_str.replace("Z", "+00:00")).replace(tzinfo=None)
                    if t_id not in club_latest_fixture or f_date > club_latest_fixture[t_id]:
                        club_latest_fixture[t_id] = f_date
                except Exception:
                    pass

        # 2. Map players: track cumulative campaign history, but check current availability
        teams_map = {}
        for entry in results:
            team_info = entry.get("team", {})
            t_id = str(team_info.get("id", ""))
            t_name = team_info.get("name", "Unknown Squad")

            player_info = entry.get("player", {})
            p_id = str(player_info.get("id", ""))
            p_name = player_info.get("name", "Unknown Athlete")
            raw_reason = player_info.get("reason") or "Undisclosed Strain"
            raw_type = player_info.get("type") or "Missing Fixture"

            fixture = entry.get("fixture", {})
            f_date_str = fixture.get("date")
            entry_date = None
            if f_date_str:
                try:
                    entry_date = datetime.fromisoformat(f_date_str.replace("Z", "+00:00")).replace(tzinfo=None)
                except Exception:
                    pass

            # Availability: Doubtful vs Ruled Out
            combined_text = (raw_type + " " + raw_reason).lower()
            if any(term in combined_text for term in ["doubtful", "questionable", "late test", "doubt"]):
                availability = "Doubtful (Late Fitness Assessment)"
            else:
                availability = "Sidelined (Ruled Out)"

            # Mechanism categorization
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
                    "return": "Evaluated Ahead of Upcoming Fixture",
                    "daysLost": 0,
                    "durability": "Under Surveillance",
                    "history": [],
                    "latest_date": entry_date or datetime.min
                }

            p_entry = teams_map[t_id]["players"][p_id]
            p_entry["daysLost"] += 7
            if raw_reason not in p_entry["history"]:
                p_entry["history"].append(raw_reason)

            if entry_date and entry_date >= p_entry["latest_date"]:
                p_entry["latest_date"] = entry_date
                p_entry["type"] = raw_reason
                p_entry["cat"] = cat
                p_entry["status"] = availability

        # 3. Active filter: Keep player ONLY if their latest absence was on the club's most recent fixture cycle
        final_team_list = []
        for t_id, t_data in teams_map.items():
            active_injured = []
            latest_match_time = club_latest_fixture.get(t_id, datetime.min)

            for p_id, p_stats in t_data["players"].items():
                # Days elapsed between the team's latest logged match and the player's last recorded outage
                delta_days = (latest_match_time - p_stats["latest_date"]).total_seconds() / 86400.0

                # If the player missed the club's most recent match cycle (within 8 days of the team's latest report)
                if delta_days <= 8.0:
                    history_count = len(p_stats["history"])
                    if history_count >= 3:
                        p_stats["durability"] = "High Risk (Chronic / Recurrent)"
                    elif history_count == 2:
                        p_stats["durability"] = "Moderate Risk (Secondary Outage)"
                    else:
                        p_stats["durability"] = "Acute (Isolated Absence)"

                    del p_stats["latest_date"]
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
        print(f"Verified active casualties for {meta['name']}: {sum(len(t['injured']) for t in final_team_list)}")

    except Exception as e:
        print(f"Error resolving {meta['name']}: {e}")

with open("data.json", "w") as f:
    json.dump(output_database, f, indent=2)

print("\nWrite complete: 2026/27 active roster saved to data.json.")
