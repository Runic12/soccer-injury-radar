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
        # 1. Fetch official Team Names
        team_names = {}
        conn.request("GET", f"/v1/teams?league={meta['id']}", headers=headers)
        res_t = conn.getresponse()
        t_data = json.loads(res_t.read().decode("utf-8"))
        
        # Safely extract teams regardless of list/dict structure
        t_results = []
        if isinstance(t_data, list):
            t_results = t_data
        elif isinstance(t_data, dict):
            data_node = t_data.get("data", [])
            if isinstance(data_node, list):
                t_results = data_node
            elif isinstance(data_node, dict):
                t_results = data_node.get("teams", {}).get("value", []) if isinstance(data_node.get("teams"), dict) else []
                
        for t in t_results:
            t_id = t.get("id")
            t_name = t.get("display_name") or t.get("full_name") or t.get("name")
            if t_id and t_name:
                team_names[t_id] = t_name

        # 2. Fetch live injuries
        conn.request("GET", f"/v1/injuries?league={meta['id']}", headers=headers)
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))
        
        # Safely extract injuries
        results = []
        if isinstance(data, list):
            results = data
        elif isinstance(data, dict):
            data_node = data.get("data", [])
            if isinstance(data_node, list):
                results = data_node
            elif isinstance(data_node, dict):
                results = data_node.get("injuries", {}).get("value", []) if isinstance(data_node.get("injuries"), dict) else []
                
        print(f"Found {len(results)} active casualty reports.")
        
        teams_map = {}
        
        for entry in results:
            t_id = entry.get("current_team_id", "Unknown")
            
            # Map the raw ID to the real club name
            t_name = team_names.get(t_id, f"Club Unit {t_id[-5:].upper()}" if "bb_team" in t_id else t_id)
            
            p_name = entry.get("display_name") or entry.get("full_name", "Unknown Athlete")
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

        # Format JSON structure
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
            "teams": sorted(final_team_list, key=lambda x: x["name"])
        }
        print(f"Active sidelined players recorded: {sum(len(t['injured']) for t in final_team_list)}")

    except Exception as e:
        print(f"Error processing {meta['name']}: {e}")

with open("data.json", "w") as f:
    json.dump(output_database, f, indent=2)

print("\nWrite complete: Live direct casualty sheets with Club Names saved to data.json.")
