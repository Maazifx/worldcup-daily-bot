import feedparser
import requests
import os

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

POSTED_FILE = "posted_articles.txt"

FEEDS = {
    "BBC Sport": "https://feeds.bbci.co.uk/sport/football/rss.xml",
    "FIFA": "https://inside.fifa.com/rss-feed",
    "UEFA": "https://www.uefa.com/rssfeed/news/rss.xml"
}

if not os.path.exists(POSTED_FILE):
    open(POSTED_FILE, "w").close()

with open(POSTED_FILE, "r", encoding="utf-8") as f:
    posted_links = set(line.strip() for line in f)

new_posts = []

for source, url in FEEDS.items():

    feed = feedparser.parse(url)

    for article in feed.entries[:5]:

        if article.link not in posted_links:

            new_posts.append({
                "source": source,
                "title": article.title,
                "link": article.link
            })

            posted_links.add(article.link)

if not new_posts:
    print("No new articles found.")

else:

    for post in new_posts:

        message = f"""
🚨 BREAKING NEWS

📰 {post['title']}

🏆 Source: {post['source']}

🔗 {post['link']}
"""

        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": message
            }
        )

        print(response.status_code)

    with open(POSTED_FILE, "w", encoding="utf-8") as f:
        for link in posted_links:
            f.write(link + "\n")
