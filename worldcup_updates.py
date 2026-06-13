import requests
import os

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

url = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"

response = requests.get(url)

data = response.json()

events = data.get("events", [])

if not events:
    print("No World Cup matches found.")
    exit()

message = "📅 WORLD CUP MATCHES\n\n"

for event in events:

    competition = event["competitions"][0]

    home = competition["competitors"][0]["team"]["displayName"]
    away = competition["competitors"][1]["team"]["displayName"]

    status = competition["status"]["type"]["description"]

    home_score = competition["competitors"][0]["score"]
    away_score = competition["competitors"][1]["score"]

    message += (
        f"{home} {home_score}-{away_score} {away}\n"
        f"Status: {status}\n\n"
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
print(telegram_response.text)
