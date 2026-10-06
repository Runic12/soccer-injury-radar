import os
import http.client
import json

API_KEY = os.environ.get("RAPIDAPI_KEY", "").strip()
conn = http.client.HTTPSConnection("api.bigballsdata.com")

headers = {
    'x-api-key': API_KEY,
    'Accept': 'application/json'
}

LEAGUES = {
    "epl": {"id": "EPL", "name": "Premier League"},
    "laliga": {"id": "LALIGA", "name": "La Liga"},
    "seriea": {"id": "SERIE_A", "name": "Serie A"},
    "bundesliga": {"id": "BUNDESLIGA", "name": "Bundesliga"},
    "mls": {"id": "MLS", "name": "MLS"}
}

output_database = {}

for key, meta in LEAGUES.items():
    print(f"\n--- Fetching live injury sheets for {meta['name']} ---")
    
    try:
        conn.request("GET", f"/v1/injuries?league={meta['id']}", headers=headers)
        res = conn.getresponse()
        raw = res.read().decode("utf-8")
        data = json.loads(raw)
        
        # Navigate the exact JSON path revealed by your diagnostic test
        results = data.get("data", {}).get("injuries", {}).get("value", [])
        print(f"Found {len(results)} active casualty reports.")
        
        teams_map = {}
        
        for entry in results:
            # Group by Team ID since the free tier omits the full club string
            t_id = entry.get("current_team_id", "Unknown")
            t_name = f"Club Unit {t_id[-5:].upper()}" if "bb_team" in t_id else t_id
            
            p_name = entry.get("display_name") or entry.get("full_name", "Unknown Athlete")
            
            # Since the aggregator omits exact medicals, we apply safe fallbacks for the dashboard
            raw_reason = entry.get("injury_type", "Undisclosed Outage") 
            raw_status = entry.get("status", "out").lower()
            return_date = entry.get("return_date", "Pending Assessment")

            # Status Mapping
            if raw_status in ["day-to-day", "questionable", "doubtful"]:
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
                    "injured": []
                }

            teams_map[t_id]["injured"].append({
                "name": p_name,
                "pos": "First Team Squad",
                "type": raw_reason,
                "cat": cat,
                "status": availability,
                "return": return_date,
                "daysLost": 7,
                "durability": "Active Casualty",
                "history": [raw_reason]
            })

        # Format JSON structure for your frontend
        final_team_list = []
        for t_id, t_data in teams_map.items():
            if t_data["injured"]:
                final_team_list.append({
                    "id": t_id,
                    "name": t_data["name"],
                    "injured": t_data["injured"]
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

print("\nWrite complete: Live direct casualty sheets saved to data.json.")
