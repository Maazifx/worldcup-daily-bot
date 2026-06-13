import feedparser
import requests

BOT_TOKEN = "8805510514:AAGIgIviJztRvh0iEXCRAQH-L8NtROciG2s"
CHAT_ID = "@wcupdates2026"

feed = feedparser.parse(
    "https://feeds.bbci.co.uk/sport/football/rss.xml"
)

latest = feed.entries[0]

message = f"""
🚨 {latest.title}

{latest.link}
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
