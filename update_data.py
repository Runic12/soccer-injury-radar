import os
import http.client

API_KEY = os.environ.get("RAPIDAPI_KEY", "").strip()

print(f"Debug: Key loaded. Length = {len(API_KEY)} characters.")

conn = http.client.HTTPSConnection("api.bigballsdata.com")
headers = {
    'x-api-key': API_KEY,
    'Accept': 'application/json'
}

print("\n--- Big Balls Data API Diagnostic ---")
try:
    conn.request("GET", "/v1/injuries?league=EPL", headers=headers)
    res = conn.getresponse()
    raw = res.read().decode("utf-8")
    
    print(f"HTTP Status: {res.status}")
    print(f"Raw Response Body:\n{raw}")
except Exception as e:
    print(f"Connection Failed: {e}")
