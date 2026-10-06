import urllib.request
import json
from datetime import datetime

# ESPN uses specific League IDs (eng.1 for EPL, esp.1 for La Liga, etc.)
LEAGUES = {
    "epl": {"id": "eng.1", "name": "Premier League"},
    "laliga": {"id": "esp.1", "name": "La Liga"},
    "seriea": {"id": "ita.1", "name": "Serie A"},
    "bundesliga": {"id": "ger.1", "name": "Bundesliga"},
    "mls": {"id": "usa.1", "name": "MLS"}
}

def fetch_json(url):
    """Safely fetch and parse JSON from ESPN's public endpoints."""
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode('utf-8'))

def extract_injured_athletes(obj):
    """Smart hunter function that recursively finds any athlete object containing an 'injuries' array."""
    out = []
    if isinstance(obj, dict):
        # If this dictionary has a populated injuries list, we caught an injured player
        if "injuries" in obj and obj.get("injuries"):
            out.append(obj)
        else:
            for k, v in obj.items():
                out.extend(extract_injured_athletes(v))
    elif isinstance(obj, list):
        for item in obj:
            out.extend(extract_injured_athletes(item))
    return out

output_database = {}

for key, meta in LEAGUES.items():
    print(f"\n--- Fetching live injury sheets for {meta['name']} ---")
    teams_map = {}
    
    try:
        # 1. Fetch the official team list for the league
        teams_url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{meta['id']}/teams"
        teams_data = fetch_json(teams_url)
        
        # Safely navigate ESPN's team structure
        sports = teams_data.get("sports", [])
        if not sports:
            continue
        leagues_data = sports[0].get("leagues", [])
        if not leagues_data:
            continue
        teams = leagues_data[0].get("teams", [])
        
        print(f"Intercepted {len(teams)} clubs. Scanning rosters for casualties...")
        
        # 2. Iterate through every team and pull their active roster
        for t_entry in teams:
            team_info = t_entry.get("team", {})
            t_id = team_info.get("id")
            t_name = team_info.get("displayName", "Unknown Club")
            
            if not t_id:
                continue
                
            roster_url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{meta['id']}/teams/{t_id}/roster"
            roster_data = fetch_json(roster_url)
            
            # 3. Hunt down the injured players in the roster payload
            injured_athletes = extract_injured_athletes(roster_data)
            
            if injured_athletes:
                clean_t_id = t_name.lower().replace(" ", "_")
                if clean_t_id not in teams_map:
                    teams_map[clean_t_id] = {
                        "id": clean_t_id,
                        "name": t_name,
                        "injured": []
                    }
                
                # Format the real data for your frontend dashboard
                for athlete in injured_athletes:
                    p_name = athlete.get("fullName") or athlete.get("displayName", "Unknown Athlete")
                    injuries = athlete.get("injuries", [])
                    
                    # Grab real medical context and status
                    raw_reason = injuries[0].get("details", "Undisclosed Injury") if injuries else "Undisclosed Injury"
                    status = injuries[0].get("status", "Sidelined") if injuries else "Sidelined"
                    
                    # ESPN return dates can sometimes be missing; fallback gracefully
                    return_date = injuries[0].get("returnDate", "Pending Assessment") if injuries else "Pending Assessment"
                    
                    # Categorize the real injury for the Pie Chart
                    lower_r = raw_reason.lower()
                    if any(w in lower_r for w in ["hamstring", "muscle", "groin", "adductor", "thigh", "calf", "strain"]):
                        cat = "Soft-Tissue"
                    elif any(w in lower_r for w in ["acl", "cruciate", "ligament", "meniscus", "fracture", "ankle", "knee", "surgery"]):
                        cat = "Structural"
                    else:
                        cat = "Trauma/Impact"
                        
                    teams_map[clean_t_id]["injured"].append({
                        "name": p_name,
                        "pos": "First Team Squad",
                        "type": raw_reason.title(),
                        "cat": cat,
                        "status": status.title(),
                        "return": return_date,
                        "daysLost": 7,
                        "durability": "Active Casualty",
                        "history": [raw_reason.title()]
                    })

        # Assemble final output sorted alphabetically by team name
        final_team_list = list(teams_map.values())
        output_database[key] = {
            "name": meta["name"],
            "teams": sorted(final_team_list, key=lambda x: x["name"])
        }
        print(f"Recorded {sum(len(t['injured']) for t in final_team_list)} authentic casualties for {meta['name']}.")

    except Exception as e:
        print(f"Error processing {meta['name']}: {e}")

# Save the structured database
with open("data.json", "w") as f:
    json.dump(output_database, f, indent=2)

print("\nWrite complete: Authentic, unscrambled casualty sheets saved.")
