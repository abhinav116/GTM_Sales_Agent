import os, json, urllib.request
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")

if not url or not key:
    print("ERROR: SUPABASE_URL or SUPABASE_SERVICE_KEY not found in .env")
    exit(1)

print(f"Testing: {url}")

# Test insert
payload = json.dumps({
    "run_id": "test_connection_001",
    "prospect_company": "Test Company",
    "avg_confidence": 0.88,
    "human_review_required": False,
    "flags_count": 0,
    "pain_points_count": 2,
}).encode("utf-8")

req = urllib.request.Request(
    f"{url}/rest/v1/runs",
    data=payload,
    method="POST",
    headers={
        "Content-Type":  "application/json",
        "apikey":        key,
        "Authorization": f"Bearer {key}",
        "Prefer":        "resolution=ignore-duplicates",
    }
)

try:
    with urllib.request.urlopen(req) as resp:
        print(f"INSERT status: {resp.status}")
    print("SUCCESS: Row inserted into Supabase.")
except urllib.error.HTTPError as e:
    print(f"HTTP ERROR {e.code}: {e.read().decode()}")
except Exception as e:
    print(f"ERROR: {e}")
