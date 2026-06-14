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

if response.status_code != 200:
    print("Could not fetch scoreboard.")
    exit()

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

    telegram_url = (
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    )

    # MATCH STARTED

    if status.lower() in ["first half", "second half"]:

        alert_key = f"START-{match_id}"

        if alert_key not in posted:

            message = f"""
⚽ MATCH STARTED

{home} vs {away}

🌎 FIFA WORLD CUP 2026
"""

            requests.post(
                telegram_url,
                data={
                    "chat_id": CHAT_ID,
                    "text": message
                }
            )

            posted.add(alert_key)

    # HALF TIME

    if status.lower() == "halftime":

        alert_key = f"HT-{match_id}"

        if alert_key not in posted:

            message = f"""
⏸ HALF TIME

{home} {home_score}-{away_score} {away}

🌎 FIFA WORLD CUP 2026
"""

            requests.post(
                telegram_url,
                data={
                    "chat_id": CHAT_ID,
                    "text": message
                }
            )

            posted.add(alert_key)

    # FULL TIME

    if status.lower() == "final":

        alert_key = f"FT-{match_id}"

        if alert_key not in posted:

            message = f"""
🏁 FULL TIME

{home} {home_score}-{away_score} {away}

🌎 FIFA WORLD CUP 2026
"""

            requests.post(
                telegram_url,
                data={
                    "chat_id": CHAT_ID,
                    "text": message
                }
            )

            posted.add(alert_key)

with open(POSTED_FILE, "w", encoding="utf-8") as f:
    for item in posted:
        f.write(item + "\n")

print("Finished checking matches.")
