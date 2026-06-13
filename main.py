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

if not os.path.exists(POSTED_FILE):
    with open(POSTED_FILE, "w", encoding="utf-8"):
        pass

with open(POSTED_FILE, "r", encoding="utf-8") as f:
    posted_links = set(
        line.strip()
        for line in f
        if line.strip()
    )

new_posts = []

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

            image_url = None

            if "media_content" in article:
                try:
                    image_url = article.media_content[0]["url"]
                except:
                    pass

            if not image_url and "media_thumbnail" in article:
                try:
                    image_url = article.media_thumbnail[0]["url"]
                except:
                    pass

            new_posts.append({
                "source": source,
                "title": title,
                "link": link,
                "image": image_url
            })

            posted_links.add(link)

if not new_posts:
    print("No new articles found.")

else:

    for post in new_posts:

        caption = f"""
🚨 BREAKING NEWS

📰 {post['title']}

🏆 Source: {post['source']}

🔗 {post['link']}
"""

        if post["image"]:

            response = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                data={
                    "chat_id": CHAT_ID,
                    "photo": post["image"],
                    "caption": caption[:1024]
                }
            )

        else:

            response = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                data={
                    "chat_id": CHAT_ID,
                    "text": caption
                }
            )

        print(response.status_code)
        print(response.text)

    with open(POSTED_FILE, "w", encoding="utf-8") as f:
        for link in posted_links:
            f.write(link + "\n")

    print(f"Posted {len(new_posts)} new articles.")
