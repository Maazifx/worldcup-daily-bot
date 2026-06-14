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
    "canada",
    "scotland",
    "australia",
    "japan",
    "curaçao",
    "ecuador",
    "tunisia"
]

if not os.path.exists(POSTED_FILE):
    open(POSTED_FILE, "w").close()

with open(POSTED_FILE, "r", encoding="utf-8") as f:
    posted_articles = set(
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

        title = getattr(article, "title", "").strip()
        link = getattr(article, "link", "").strip()
        summary = getattr(article, "summary", "").strip()

        if not title or not link:
            continue

        # Skip podcasts and audio content
        if "sounds/play" in link:
            continue

        if "football daily" in title.lower():
            continue

        if "podcast" in title.lower():
            continue

        if "audio" in title.lower():
            continue

        clean_summary = re.sub("<.*?>", "", summary)

        article_text = (
            title.lower() +
            " " +
            clean_summary.lower()
        )

        if not any(
            keyword.lower() in article_text
            for keyword in WORLD_CUP_KEYWORDS
        ):
            continue

        article_key = f"{title}|{link}"

        if article_key in posted_articles:
            continue

        image_url = None

        if hasattr(article, "media_content"):
            try:
                image_url = article.media_content[0]["url"]
            except Exception:
                pass

        if not image_url and hasattr(article, "media_thumbnail"):
            try:
                image_url = article.media_thumbnail[0]["url"]
            except Exception:
                pass

        clean_summary = clean_summary[:350]

        new_posts.append({
            "key": article_key,
            "source": source,
            "title": title,
            "summary": clean_summary,
            "link": link,
            "image": image_url
        })

        posted_articles.add(article_key)

if not new_posts:
    print("No World Cup news found.")

else:

    for post in new_posts:

        caption = (
            f"🌎 WORLD CUP NEWS\n\n"
"
            f"📖 {post['summary']}\n\n"
            f"🏆 Source: {post['source']}\n\n"
            f"🔗 {post['link']}"
        )

        try:

            if post["image"]:

    try:

        image_response = requests.get(
            post["image"],
            timeout=20
        )

        with open("temp.jpg", "wb") as img:
            img.write(image_response.content)

        with open("temp.jpg", "rb") as img:

            response = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                data={
                    "chat_id": CHAT_ID,
                    "caption": caption[:1024]
                },
                files={
                    "photo": img
                }
            )

    except Exception as e:

        print(e)

        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": caption
            }
    )
            print(response.status_code)

        except Exception as e:
            print(e)

    with open(POSTED_FILE, "w", encoding="utf-8") as f:
        for item in posted_articles:
            f.write(item + "\n")

    print(f"Posted {len(new_posts)} World Cup articles.")
