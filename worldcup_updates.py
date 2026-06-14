import feedparser
import requests
import os
import re
import time

from graphics import create_graphic

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

POSTED_FILE = "posted_articles.txt"

FEEDS = {
    "Sky Sports": "https://www.skysports.com/rss/12040",
    "90Min": "https://www.90min.com/posts.rss",
    "BBC Sport": "https://feeds.bbci.co.uk/sport/football/rss.xml"
}

WORLD_CUP_KEYWORDS = [
    "world cup",
    "fifa",
    "fifa world cup",
    "world cup 2026",
    "usa 2026",
    "canada 2026",
    "mexico 2026",
    "qualification",
    "qualifier",
    "group stage",
    "round of 16",
    "quarter-final",
    "quarterfinal",
    "semi-final",
    "semifinal",
    "final",
    "knockout",
    "international football",
    "national team",
    "soccer",
    "football",
    "argentina",
    "brazil",
    "england",
    "france",
    "germany",
    "spain",
    "portugal",
    "netherlands",
    "belgium",
    "croatia",
    "morocco",
    "usa",
    "mexico",
    "canada",
    "scotland",
    "australia",
    "japan",
    "ecuador",
    "tunisia",
    "ivory coast",
    "turkiye"
]

BANNED_WORDS = [
    "darts",
    "rugby",
    "cricket",
    "golf",
    "tennis",
    "formula 1",
    "f1",
    "motogp",
    "boxing",
    "ufc",
    "mma",
    "snooker",
    "basketball",
    "nba",
    "nfl",
    "baseball",
    "mlb",
    "horse racing",
    "cycling",
    "podcast",
    "football daily",
    "audio"
]

if not os.path.exists(POSTED_FILE):
    with open(POSTED_FILE, "w", encoding="utf-8"):
        pass

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

    source_post_count = 0

    for article in feed.entries[:25]:

        if source_post_count >= 1:
            break

        title = getattr(article, "title", "").strip()
        link = getattr(article, "link", "").strip()
        summary = getattr(article, "summary", "").strip()

        if not title or not link:
            continue

        if "sounds/play" in link:
            continue

        clean_summary = re.sub(
            "<.*?>",
            "",
            summary
        ).strip()

        article_text = (
            title.lower()
            + " "
            + clean_summary.lower()
        )

        if any(
            word in article_text
            for word in BANNED_WORDS
        ):
            continue

        if not any(
            keyword.lower() in article_text
            for keyword in WORLD_CUP_KEYWORDS
        ):
            continue

        article_key = link

        if article_key in posted_articles:
            print(f"Skipping duplicate: {title}")
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

        if not image_url:
            continue

        new_posts.append({
            "key": article_key,
            "source": source,
            "title": title,
            "summary": clean_summary[:350],
            "link": link,
            "image": image_url
        })

        posted_articles.add(article_key)
        source_post_count += 1

if not new_posts:
    print("No World Cup news found.")
    exit()

for post in new_posts[:3]:

    caption = (
        f"🚨 BREAKING\n\n"
        f"{post['title']}\n\n"
        f"{post['summary']}\n\n"
        f"📲 @wcupdates2026"
    )

    try:

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        image_response = requests.get(
            post["image"],
            headers=headers,
            timeout=20
        )

        if image_response.status_code != 200:
            continue

        with open("article.jpg", "wb") as img:
            img.write(image_response.content)

        graphic_file = create_graphic(
            "article.jpg",
            post["title"]
        )

        with open(graphic_file, "rb") as img:

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

        print(response.status_code)

        time.sleep(4)

    except Exception as e:
        print(e)

with open(POSTED_FILE, "w", encoding="utf-8") as f:
    for item in posted_articles:
        f.write(item + "\n")

print(
    f"Posted {min(len(new_posts), 3)} World Cup articles."
)
