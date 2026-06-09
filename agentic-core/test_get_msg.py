# c:\Users\HP\Desktop\JOB-HUNTER-AGENT\01-projects\job-hunting-agent\agentic-core\test_get_msg.py
import asyncio
import os
from dotenv import load_dotenv
from telethon import TelegramClient

load_dotenv()

api_id = int(os.getenv("TELEGRAM_API_ID"))
api_hash = os.getenv("TELEGRAM_API_HASH")

async def main():
    client = TelegramClient("job_agent_session", api_id, api_hash)
    await client.start()
    entity = await client.get_entity("@TechJobsOccean")
    msg = await client.get_messages(entity, ids=1435)
    print("=== RAW TEXT ===")
    print(msg.text)
    print("================")
    await client.disconnect()

asyncio.run(main())
