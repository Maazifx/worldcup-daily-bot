import requests
import os

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

url = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/standings"

response = requests.get(url)

if response.status_code != 200:
    print("Failed to fetch standings.")
    exit()

data = response.json()

groups = data.get("children", [])

if not groups:
    print("No standings found.")
    exit()

for group in groups:

    group_name = group.get("name", "Unknown Group")

    entries = (
        group.get("standings", {})
             .get("entries", [])
    )

    message = f"📊 {group_name.upper()}\n\n"

    for team in entries:

        team_name = team["team"]["displayName"]

        stats = {
            stat["name"]: stat["value"]
            for stat in team["stats"]
        }

        points = stats.get("points", 0)
        played = stats.get("gamesPlayed", 0)
        gd = stats.get("pointDifferential", 0)

        message += (
            f"{team_name}\n"
            f"Pts: {points} | "
            f"P: {played} | "
            f"GD: {gd}\n\n"
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

    print(
        group_name,
        telegram_response.status_code
    )
