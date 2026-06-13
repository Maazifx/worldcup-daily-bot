import feedparser
import requests
import os

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

POSTED_FILE = "posted_articles.txt"

if not os.path.exists(POSTED_FILE):
    open(POSTED_FILE, "w").close()

with open(POSTED_FILE, "r", encoding="utf-8") as f:
    posted_links = set(line.strip() for line in f)

feed = feedparser.parse(
    "https://feeds.bbci.co.uk/sport/football/rss.xml"
)

latest = feed.entries[0]

if latest.link not in posted_links:

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

    print(response.text)

    with open(POSTED_FILE, "a", encoding="utf-8") as f:
        f.write(latest.link + "\n")

else:
    print("Already posted.")
