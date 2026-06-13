import feedparser
import requests
import os

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

POSTED_FILE = "posted_articles.txt"

FEEDS = {
    "BBC Sport": "https://feeds.bbci.co.uk/sport/football/rss.xml",
    "Sky Sports": "https://www.skysports.com/rss/12040",
    "90Min": "https://www.90min.com/posts.rss"
}

# Create file if it doesn't exist
if not os.path.exists(POSTED_FILE):
    with open(POSTED_FILE, "w", encoding="utf-8"):
        pass

# Read previously posted links
with open(POSTED_FILE, "r", encoding="utf-8") as f:
    posted_links = set(
        line.strip()
        for line in f
        if line.strip()
    )

new_posts = []

# Scan all feeds
for source, url in FEEDS.items():

    feed = feedparser.parse(url)

    if not hasattr(feed, "entries"):
        continue

    for article in feed.entries[:10]:

        link = getattr(article, "link", None)
        title = getattr(article, "title", None)

        if not link or not title:
            continue

        if link not in posted_links:

            new_posts.append({
                "source": source,
                "title": title,
                "link": link
            })

            posted_links.add(link)

# Nothing new
if not new_posts:
    print("No new articles found.")

# Send new articles
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
        print(response.text)

    # Save updated links
    with open(POSTED_FILE, "w", encoding="utf-8") as f:
        for link in posted_links:
            f.write(link + "\n")

    print(f"Posted {len(new_posts)} new articles.")
