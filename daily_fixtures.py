import requests
import os
from datetime import datetime

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

STATE_FILE = "daily_fixtures_state.txt"

today = datetime.utcnow().strftime("%Y-%m-%d")

last_posted = ""

if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        last_posted = f.read().strip()

if last_posted == today:
    print("Today's fixtures already posted.")
    exit()

url = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"

response = requests.get(url)

if response.status_code != 200:
    print("Could not fetch fixtures.")
    exit()

data = response.json()

events = data.get("events", [])

if not events:
    print("No fixtures found.")
    exit()

message = "📅 TODAY'S WORLD CUP MATCHES\n\n"

for event in events:

    competition = event["competitions"][0]

    home = competition["competitors"][0]["team"]["displayName"]
    away = competition["competitors"][1]["team"]["displayName"]

    match_date = event["date"]

    try:
        dt = datetime.fromisoformat(
            match_date.replace("Z", "+00:00")
        )

        time_string = dt.strftime("%H:%M UTC")

    except:
        time_string = "TBA"

    message += (
        f"⚽ {home} vs {away}\n"
        f"🕒 {time_string}\n\n"
    )

telegram_url = (
    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
)

telegram_response = requests.post(
    telegram_url,
    data={
        "chat_id": CHAT_ID,
        "text": message
    }
)

print(telegram_response.status_code)

with open(STATE_FILE, "w", encoding="utf-8") as f:
    f.write(today)

print("Fixtures posted.")
