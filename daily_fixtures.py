import requests
import os
from datetime import datetime

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

STATE_FILE = "daily_fixtures_state.txt"

today = datetime.utcnow().strftime("%Y-%m-%d")

# Check if already sent today
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        last_sent = f.read().strip()
    if last_sent == today:
        print("Fixtures already sent today.")
        exit()

# Fetch data from ESPN
url = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
response = requests.get(url)
if response.status_code != 200:
    print("Failed to fetch World Cup data.")
    exit()

data = response.json()
events = data.get("events", [])

# Build message
message = f"📅 WORLD CUP FIXTURES – {today}\n\n"

fixtures_found = False
for event in events:
    try:
        comp = event["competitions"][0]
        status = comp["status"]["type"]["description"].lower()
        # Only show scheduled or pre-match (not started yet)
        if "scheduled" not in status and "pre" not in status:
            continue
        home = comp["competitors"][0]["team"]["displayName"]
        away = comp["competitors"][1]["team"]["displayName"]
        match_time = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
        message += f"⚽ {home} vs {away}\n🕒 {match_time.strftime('%H:%M UTC')}\n\n"
        fixtures_found = True
    except:
        continue

if not fixtures_found:
    message += "No fixtures scheduled for today.\n"

# Optional: add a footer
message += "🏆 FIFA WORLD CUP 2026"

# Send to Telegram
telegram_response = requests.post(
    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
    data={"chat_id": CHAT_ID, "text": message}
)
print(telegram_response.status_code)

# Mark as sent
with open(STATE_FILE, "w", encoding="utf-8") as f:
    f.write(today)

print("Daily fixtures sent.")
