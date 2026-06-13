import feedparser
import requests
import os

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

POSTED_FILE = "posted_articles.txt"

feed = feedparser.parse(
    "https://feeds.bbci.co.uk/sport/football/rss.xml"
)

latest = feed.entries[0]

article_link = latest.link

posted = set()

if os.path.exists(POSTED_FILE):
    with open(POSTED_FILE, "r", encoding="utf-8") as f:
        posted = set(line.strip() for line in f)

if article_link not in posted:

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

    with open(POSTED_FILE, "a", encoding="utf-8") as f:
        f.write(article_link + "\n")

else:
    print("Article already posted.")
