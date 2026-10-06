import os
import http.client
import json

API_KEY = os.environ.get("RAPIDAPI_KEY", "").strip()
conn = http.client.HTTPSConnection("api.bigballsdata.com")

headers = {
    'x-api-key': API_KEY,
    'Accept': 'application/json'
}

print("\n--- Big Balls Data API Diagnostic (Teams Endpoint) ---")
try:
    conn.request("GET", "/v1/teams?league=EPL", headers=headers)
    res = conn.getresponse()
    raw = res.read().decode("utf-8")
    
    print(f"HTTP Status: {res.status}")
    print(f"Raw Response Body (First 1000 characters):\n{raw[:1000]}")
except Exception as e:
    print(f"Connection Failed: {e}")
