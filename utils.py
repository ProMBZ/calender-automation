import re
import aiohttp
import logging

# --- Logging Setup ---
logging.basicConfig(filename='logs/automation.log', level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(message)s')

# --- Extract Name and Phone ---
def extract_name_phone(description):
    if not description:
        return None, None
    name_match = re.search(r'Name:\s*(.*)', description)
    phone_match = re.search(r'Phone:\s*(.*)', description)
    name = name_match.group(1).strip() if name_match else None
    phone = phone_match.group(1).strip() if phone_match else None
    return name, phone

# --- Async API Call ---
async def make_async_api_call(name, phone, api_url):
    payload = {"name": name, "phone": phone}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload) as resp:
                status = resp.status
                text = await resp.text()
                logging.info(f"✅ API Call for {name} ({phone}) - Status {status}")
                return status, text
    except Exception as e:
        logging.error(f"❌ API Call Failed for {name} ({phone}): {str(e)}")
        return 500, str(e)
