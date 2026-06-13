import feedparser
import requests
import os

# Read secrets from GitHub
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

# BBC Football RSS
feed = feedparser.parse(
    "https://feeds.bbci.co.uk/sport/football/rss.xml"
)

latest = feed.entries[0]

message = f"""
🚨 BREAKING NEWS

📰 {latest.title}

🔗 {latest.link}
"""

response = requests.post(
    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
    data={
        "chat_id": CHAT_ID,
        "text": message
    }
)

print(response.status_code)
print(response.text)
