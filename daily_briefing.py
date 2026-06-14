import requests
import os
from datetime import datetime

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

today = datetime.utcnow().strftime("%Y-%m-%d")

POSTED_FILE = f"fixtures_{today}.txt"

if os.path.exists(POSTED_FILE):
    print("Today's fixtures already posted.")
    exit()

url = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"

response = requests.get(url)
data = response.json()

events = data.get("events", [])

if not events:
    print("No fixtures found.")
    exit()

message = "📅 TODAY'S WORLD CUP MATCHES\n\n"

fixture_count = 0

for event in events:

    status = event["status"]["type"]["description"]

    if status.lower() == "final":
        continue

    competition = event["competitions"][0]

    home = competition["competitors"][0]["team"]["displayName"]
    away = competition["competitors"][1]["team"]["displayName"]

    date = event["date"]

    try:
        match_time = datetime.fromisoformat(
            date.replace("Z", "+00:00")
        )

        time_string = match_time.strftime("%H:%M UTC")

    except Exception:
        time_string = "TBA"

    fixture_count += 1

    message += (
        f"⚽ {home} vs {away}\n"
        f"🕒 {time_string}\n\n"
    )

if fixture_count == 0:
    print("No upcoming fixtures.")
    exit()

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

with open(POSTED_FILE, "w") as f:
    f.write("posted")
