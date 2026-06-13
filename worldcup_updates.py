import requests
import os

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

POSTED_FILE = "posted_matches.txt"

if not os.path.exists(POSTED_FILE):
    open(POSTED_FILE, "w").close()

with open(POSTED_FILE, "r", encoding="utf-8") as f:
    posted = set(
        line.strip()
        for line in f
        if line.strip()
    )

url = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"

response = requests.get(url)
data = response.json()

events = data.get("events", [])

for event in events:

    competition = event["competitions"][0]

    home = competition["competitors"][0]["team"]["displayName"]
    away = competition["competitors"][1]["team"]["displayName"]

    home_score = competition["competitors"][0]["score"]
    away_score = competition["competitors"][1]["score"]

    status = competition["status"]["type"]["description"]

    match_id = event["id"]

    # FULL TIME ALERT
    if status.lower() == "final":

        alert_key = f"FT-{match_id}"

        if alert_key not in posted:

            message = f"""
🏁 FULL TIME

{home} {home_score}-{away_score} {away}

🌎 FIFA WORLD CUP 2026
"""

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

            posted.add(alert_key)

with open(POSTED_FILE, "w", encoding="utf-8") as f:
    for item in posted:
        f.write(item + "\n")

print("Finished checking matches.")
