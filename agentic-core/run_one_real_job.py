# c:\Users\HP\Desktop\JOB-HUNTER-AGENT\01-projects\job-hunting-agent\agentic-core\run_one_real_job.py
import requests
import json

FASTAPI_URL = "http://localhost:8000/process-job"

post = """💬 Job title: Senior Full Stack & Automation Developer

🏢 Company: Namaa Agency

👨🏻‍💻 Technologies: React, Next.js, Python, Node.js, PostgreSQL, MySQL, REST APIs, Git, Vercel, n8n, Make, Zapier, Docker...

📍 Location: Staouali, Algiers

🌐 Remote: ❌

💰 Salary: 🤔

🔗 Apply: https://emploitic.com/entreprises/namaa-agency/offres-d-emploi/informatique-telecom-internet/senior-full-stack-automation-developer-w9ab3"""

def run():
    print("🚀 Sending a single real high-match job through the full end-to-end pipeline...")
    payload = {
        "raw_text": post,
        "source": "telegram",
        "source_channel": "@TechJobsOccean",
        "source_message_id": 1435
    }
    
    try:
        resp = requests.post(FASTAPI_URL, json=payload, timeout=300)
        print(f"Status Code: {resp.status_code}")
        if resp.ok:
            result = resp.json()
            print("\n=== PIPELINE RESULT ===")
            print(json.dumps(result, indent=2))
            print("========================")
        else:
            print(f"Error: {resp.text}")
    except Exception as e:
        print(f"Failed to connect or process: {e}")

if __name__ == "__main__":
    run()
