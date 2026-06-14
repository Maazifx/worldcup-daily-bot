import feedparser
import requests
import os
import re

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

POSTED_FILE = "posted_articles.txt"

FEEDS = {
    "BBC Sport": "https://feeds.bbci.co.uk/sport/football/rss.xml",
    "Sky Sports": "https://www.skysports.com/rss/12040",
    "90Min": "https://www.90min.com/posts.rss"
}

WORLD_CUP_KEYWORDS = [
    "world cup",
    "fifa",
    "usa 2026",
    "canada 2026",
    "mexico 2026",
    "international",
    "national team",
    "qualification",
    "qualifier",
    "group stage",
    "round of 16",
    "quarter-final",
    "quarterfinal",
    "semi-final",
    "semifinal",
    "final",
    "argentina",
    "brazil",
    "england",
    "france",
    "germany",
    "spain",
    "portugal",
    "netherlands",
    "usa",
    "mexico",
    "canada"
]

if not os.path.exists(POSTED_FILE):
    open(POSTED_FILE, "w").close()

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

    for article in feed.entries[:20]:

        link = getattr(article, "link", "")
        title = getattr(article, "title", "")

        summary = getattr(article, "summary", "")

        if not link or not title:
            continue

        text_to_check = (
            title.lower() + " " +
            re.sub("<.*?>", "", summary).lower()
        )

        if not any(
            keyword in text_to_check
            for keyword in WORLD_CUP_KEYWORDS
        ):
            continue

        if link in posted_links:
            continue

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

        clean_summary = re.sub(
            "<.*?>",
            "",
            summary
        ).strip()

        clean_summary = clean_summary[:350]

        new_posts.append({
            "source": source,
            "title": title,
            "summary": clean_summary,
            "link": link,
            "image": image_url
        })

        posted_links.add(link)

if not new_posts:
    print("No World Cup news found.")

else:

    for post in new_posts:

        caption = f"""
🌎 WORLD CUP NEWS

📰 {post['title']}

📖 {post['summary']}

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

    with open(POSTED_FILE, "w", encoding="utf-8") as f:
        for link in posted_links:
            f.write(link + "\n")

    print(f"Posted {len(new_posts)} World Cup articles.")
