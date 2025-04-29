import streamlit as st
import base64
import asyncio
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timezone
import os

from utils import extract_name_phone, make_async_api_call

st.set_page_config(page_title="NextAxion Automation", page_icon="📅")  # ✅ FIRST


# --- Logo + Password Protection ---
def add_logo(logo_path):
    with open(logo_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode()
    st.markdown(
        f"""
        <div style="text-align:center;">
            <img src="data:image/png;base64,{encoded}" width="140" style="margin-bottom:10px"/>
            <h2 style="margin-top:0; font-family:Arial">NextAxion_ Automation</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

# --- Password Gate ---
def check_password():
    add_logo("nextaxion.jpeg")  # ✅ Show logo at login screen too
    def password_entered():
        if st.session_state["password"] == "NextAxion_":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("🔐 Enter App Password", type="password", on_change=password_entered, key="password")
        st.stop()
    elif not st.session_state["password_correct"]:
        st.error("❌ Incorrect password")
        st.stop()

# 🔐 Require password before app runs
check_password()

# --- Calendar Automation Config ---
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
API_ENDPOINT = "https://your-api-endpoint.com/add_client"  # ✅ Replace with your real API
CHECK_INTERVAL_MINUTES = 5

# --- Connect to Google Calendar ---
def get_calendar_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    else:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)

# --- Fetch Events ---
def get_upcoming_events(service):
    now = datetime.utcnow().isoformat() + 'Z'
    events_result = service.events().list(
        calendarId='primary', timeMin=now,
        maxResults=20, singleEvents=True,
        orderBy='startTime').execute()
    return events_result.get('items', [])

# --- Check 24-hour rule (fixed timezone-safe) ---
def is_event_24_hours_away(event_start_time):
    try:
        event_time = datetime.fromisoformat(event_start_time.replace('Z', '+00:00')).astimezone(timezone.utc)
        now = datetime.now(timezone.utc)
        diff = event_time - now
        return 23 <= diff.total_seconds() / 3600 <= 25
    except Exception as e:
        print(f"⛔ Error in time comparison: {e}")
        return False

# --- Scheduled Task ---
async def scheduled_job():
    service = get_calendar_service()
    events = get_upcoming_events(service)

    for event in events:
        start_time = event['start'].get('dateTime', event['start'].get('date'))
        description = event.get('description', '')
        summary = event.get('summary', 'No Title')

        if start_time and is_event_24_hours_away(start_time):
            name, phone = extract_name_phone(description)
            if name and phone:
                status, response = await make_async_api_call(name, phone, API_ENDPOINT)
                print(f"✅ {summary}: API Response [{status}]")
            else:
                print(f"⚠️ Skipped: {summary} - Missing name or phone.")
        else:
            print(f"🕓 Skipped: {summary} - Not within 24h.")

st.title("📅 Google Calendar Automation")

if st.button("🔄 Run Manual Check"):
    asyncio.run(scheduled_job())
    st.success("Manual trigger completed!")

st.caption("Automation checks every 5 minutes. Leave this tab open or run on a server.")

# --- Background Scheduler ---
scheduler = BackgroundScheduler()
scheduler.add_job(lambda: asyncio.run(scheduled_job()), 'interval', minutes=CHECK_INTERVAL_MINUTES)
scheduler.start()
