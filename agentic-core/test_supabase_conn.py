# c:\Users\HP\Desktop\JOB-HUNTER-AGENT\01-projects\job-hunting-agent\agentic-core\test_supabase_conn.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "") or os.environ.get("SUPABASE_KEY", "")

def test_conn():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Supabase environment variables missing!")
        return

    print(f"Connecting to: {SUPABASE_URL}")
    url = f"{SUPABASE_URL}/rest/v1/jobs?select=*&limit=1"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    try:
        resp = requests.get(url, headers=headers)
        if resp.ok:
            print("✅ Supabase connection successful!")
            data = resp.json()
            if data:
                print("Found an existing job row. Columns available:")
                for k, v in data[0].items():
                    print(f"  - {k}: {type(v).__name__}")
            else:
                print("No rows found in 'jobs' table.")
        else:
            print(f"❌ Connection failed: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_conn()
