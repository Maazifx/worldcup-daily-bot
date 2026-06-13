import requests
import os

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

POSTED_FILE = "posted_matches.txt"

if not os.path.exists(POSTED_FILE):
    with open(POSTED_FILE, "w", encoding="utf-8"):
        pass

with open(POSTED_FILE, "r", encoding="utf-8") as f:
    posted_updates = set(
        line.strip()
        for line in f
        if line.strip()
    )

url = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"

response = requests.get(url)

data = response.json()

events = data.get("events", [])

if not events:
    print("No World Cup matches found.")
    exit()

new_updates = []

for event in events:

    competition = event["competitions"][0]

    home = competition["competitors"][0]["team"]["displayName"]
    away = competition["competitors"][1]["team"]["displayName"]

    home_score = competition["competitors"][0]["score"]
    away_score = competition["competitors"][1]["score"]

    status = competition["status"]["type"]["description"]

    update_key = (
        f"{home}|{away}|"
        f"{home_score}|{away_score}|"
        f"{status}"
    )

    if update_key not in posted_updates:

        new_updates.append({
            "home": home,
            "away": away,
            "home_score": home_score,
            "away_score": away_score,
            "status": status,
            "key": update_key
        })

        posted_updates.add(update_key)

if not new_updates:
    print("No new match updates.")

else:

    for match in new_updates:

        message = f"""
⚽ WORLD CUP UPDATE

{match['home']} {match['home_score']} - {match['away_score']} {match['away']}

⏱ {match['status']}
"""

        telegram_url = (
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        )

        response = requests.post(
            telegram_url,
            data={
                "chat_id": CHAT_ID,
                "text": message
            }
        )

        print(response.status_code)

    with open(POSTED_FILE, "w", encoding="utf-8") as f:

        for update in posted_updates:
            f.write(update + "\n")

    print(f"Posted {len(new_updates)} new updates.")
