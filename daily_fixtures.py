import requests
import os
from datetime import datetime, timezone

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

STATE_FILE = "daily_fixtures_state.txt"

today = datetime.now(timezone.utc).date()

last_posted = ""

if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        last_posted = f.read().strip()

today_string = today.strftime("%Y-%m-%d")

if last_posted == today_string:
    print("Today's fixtures already posted.")
    exit()

url = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"

response = requests.get(url)

if response.status_code != 200:
    print("Could not fetch fixtures.")
    exit()

data = response.json()

events = data.get("events", [])

message = "📅 TODAY'S WORLD CUP MATCHES\n\n"

fixture_count = 0

finished_statuses = [
    "final",
    "full time",
    "after extra time",
    "after penalties"
]

for event in events:
    for event in events:

    print(event["date"])
    print(event["status"]["type"]["description"])
    print(event["name"])
    print("----------------")

    competition = event["competitions"][0]
    
    match_date = event.get("date")

    if not match_date:
        continue

    try:
        match_time = datetime.fromisoformat(
            match_date.replace("Z", "+00:00")
        )

    except Exception:
        continue

    match_day = match_time.date()

    if match_day != today:
        continue

    status = (
        event.get("status", {})
        .get("type", {})
        .get("description", "")
        .lower()
    )

    if status in finished_statuses:
        continue

    competition = event["competitions"][0]

    home = competition["competitors"][0]["team"]["displayName"]
    away = competition["competitors"][1]["team"]["displayName"]

    time_string = match_time.strftime("%H:%M UTC")

    fixture_count += 1

    message += (
        f"⚽ {home} vs {away}\n"
        f"🕒 {time_string}\n\n"
    )

if fixture_count == 0:
    print("No upcoming fixtures today.")
    exit()

telegram_response = requests.post(
    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
    data={
        "chat_id": CHAT_ID,
        "text": message
    }
)

print(telegram_response.status_code)

with open(STATE_FILE, "w", encoding="utf-8") as f:
    f.write(today_string)

print("Today's fixtures posted.")
