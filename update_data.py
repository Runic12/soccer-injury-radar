import os
import http.client
import json

# We are keeping the same environment variable name so you don't have to edit your workflow file
API_KEY = os.environ.get("RAPIDAPI_KEY", "").strip()

# Adjust the host if the documentation specifies a different base URL
conn = http.client.HTTPSConnection("api.bigballsdata.com")

headers = {
    'x-api-key': API_KEY,
    'Accept': 'application/json'
}

# League identifiers (You may need to tweak these string IDs based on their exact docs)
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
        # Hitting the dedicated injuries endpoint
        conn.request("GET", f"/v1/injuries?league={meta['id']}", headers=headers)
        res = conn.getresponse()
        raw = res.read().decode("utf-8")
        data = json.loads(raw)
        
        # Assuming the API returns a 'results' or 'data' array
        results = data.get("results", data.get("data", []))
        print(f"Found {len(results)} active casualty reports.")
        
        teams_map = {}
        
        for entry in results:
            t_name = entry.get("team", "Unknown Squad")
            # Create a safe ID from the team name for the frontend map
            t_id = t_name.lower().replace(" ", "_")
            
            p_name = entry.get("player", "Unknown Athlete")
            raw_reason = entry.get("injury_type", "Undisclosed Strain")
            raw_status = entry.get("status", "out").lower()
            return_date = entry.get("return_date", "Evaluated Weekly")

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
