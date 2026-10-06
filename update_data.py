import os
import http.client
import json

API_KEY = os.environ.get("RAPIDAPI_KEY", "").strip()

conn = http.client.HTTPSConnection("v3.football.api-sports.io")

headers = {
    'x-rapidapi-host': "v3.football.api-sports.io",
    'x-rapidapi-key': API_KEY,
    'x-apisports-key': API_KEY
}

conn.request("GET", "/leagues?id=39", headers=headers)
res = conn.getresponse()
data = json.loads(res.read().decode("utf-8"))

seasons = data["response"][0]["seasons"]
print("Recent Premier League Seasons Registered in API:")
for s in seasons[-4:]:
    print(f"Year: {s['year']}, Start: {s['start']}, End: {s['end']}, Current: {s['current']}")
