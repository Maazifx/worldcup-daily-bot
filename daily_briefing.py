import requests
import os
from datetime import datetime

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

STATE_FILE = "daily_briefing_state.txt"

today = datetime.utcnow().strftime("%Y-%m-%d")

# Check if already sent today
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        last_sent = f.read().strip()
    if last_sent == today:
        print("Briefing already sent today.")
        exit()

# Fetch data from ESPN
url = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
response = requests.get(url)
if response.status_code != 200:
    print("Failed to fetch World Cup data.")
    exit()

data = response.json()
events = data.get("events", [])

# Build the message
message = f"🌎 WORLD CUP DAILY BRIEFING\n\n📅 {today}\n\n"

# --- RESULTS (completed matches) ---
message += "🏁 LATEST RESULTS\n\n"
results_found = False
for event in events:
    try:
        comp = event["competitions"][0]
        status = comp["status"]["type"]["description"].lower()
        if "final" not in status and "complete" not in status and "finished" not in status:
            continue
        home = comp["competitors"][0]["team"]["displayName"]
        away = comp["competitors"][1]["team"]["displayName"]
        home_score = comp["competitors"][0]["score"]
        away_score = comp["competitors"][1]["score"]
        message += f"⚽ {home} {home_score}-{away_score} {away}\n"
        results_found = True
    except:
        continue
if not results_found:
    message += "No completed matches available.\n"

# --- MATCH TO WATCH (first upcoming fixture) ---
message += "\n🔥 MATCH TO WATCH\n\n"
watch_found = False
for event in events:
    try:
        comp = event["competitions"][0]
        status = comp["status"]["type"]["description"].lower()
        if "scheduled" in status or "pre" in status:
            home = comp["competitors"][0]["team"]["displayName"]
            away = comp["competitors"][1]["team"]["displayName"]
            match_time = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
            message += f"{home} vs {away}\n🕒 {match_time.strftime('%H:%M UTC')}\n"
            watch_found = True
            break
    except:
        continue
if not watch_found:
    message += "No upcoming matches scheduled.\n"

# --- TOURNAMENT UPDATE (static text) ---
message += """

📊 TOURNAMENT UPDATE

Group-stage battles continue as nations compete for qualification into the knockout rounds.

🏆 FIFA WORLD CUP 2026
"""

# Send to Telegram
telegram_response = requests.post(
    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
    data={"chat_id": CHAT_ID, "text": message}
)
print(telegram_response.status_code)

# Mark as sent
with open(STATE_FILE, "w", encoding="utf-8") as f:
    f.write(today)

print("Daily briefing sent.")
