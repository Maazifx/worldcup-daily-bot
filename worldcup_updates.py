import feedparser
import requests
import os
import re
import time
import random

from io import BytesIO
from PIL import Image

from graphics import create_graphic

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

POSTED_FILE = "posted_articles.txt"

FEEDS = {
    "BBC Sport": "https://feeds.bbci.co.uk/sport/football/rss.xml",
    "Sky Sports": "https://www.skysports.com/rss/12040",
    "ESPN FC": "https://www.espn.com/espn/rss/soccer/news",
    "The Guardian": "https://www.theguardian.com/football/rss",
    "90Min": "https://www.90min.com/posts.rss"
}

SOURCE_PRIORITY = [
    "BBC Sport",
    "Sky Sports",
    "ESPN FC",
    "The Guardian",
    "90Min"
]

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
    "world cup qualifier",
    "world cup qualifying",
    "group stage",
    "round of 16",
    "quarter-final",
    "quarterfinal",
    "semi-final",
    "semifinal",
    "final",
    "knockout",
    "international",
    "national team",
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
    "audio",
    "betting",
    "odds",
    "transfer rumours",
    "transfer rumor",
    "kit leaked",
    "home kit",
    "away kit",
    "third kit",
    "jersey leak"
]

def get_fallback_image():

    backgrounds = [
        "backgrounds/bg1.jpg",
        "backgrounds/bg2.jpg",
        "backgrounds/bg3.jpg",
        "backgrounds/bg4.jpg",
        "backgrounds/bg5.jpg",
        "backgrounds/bg6.jpg"
    ]

    return random.choice(backgrounds)

def get_best_image(image_url):

    if image_url == "BBC_FALLBACK":
        return get_fallback_image()

    try:

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(
            image_url,
            headers=headers,
            timeout=20
        )

        if response.status_code != 200:
            return get_fallback_image()

        image = Image.open(
            BytesIO(response.content)
        )

        width, height = image.size

        if width < 400:
            return get_fallback_image()

        with open("article.jpg", "wb") as f:
            f.write(response.content)

        return "article.jpg"

    except Exception:
        return get_fallback_image()

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

for source in SOURCE_PRIORITY:

    feed = feedparser.parse(FEEDS[source])

    if not hasattr(feed, "entries"):
        continue

    source_count = 0

    for article in feed.entries[:50]:

        if source_count >= 2:
            break

        title = getattr(article, "title", "").strip()
        link = getattr(article, "link", "").strip()
        summary = getattr(article, "summary", "").strip()

        if not title or not link:
            continue

        if link in posted_articles:
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
            banned in article_text
            for banned in BANNED_WORDS
        ):
            continue

        if not any(
            keyword in article_text
            for keyword in WORLD_CUP_KEYWORDS
        ):
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
            image_url = "BBC_FALLBACK"

        new_posts.append({
            "source": source,
            "title": title,
            "summary": clean_summary[:350],
            "link": link,
            "image": image_url
        })

        posted_articles.add(link)

        source_count += 1

if not new_posts:
    print("No World Cup news found.")
    raise SystemExit

posts_sent = 0

for post in new_posts:

    if posts_sent >= 3:
        break

    image_file = get_best_image(
        post["image"]
    )

    if not image_file:
        continue

    try:

        graphic_file = create_graphic(
            image_file,
            post["title"]
        )

        caption = (
            f"🚨 BREAKING\n\n"
            f"{post['title']}\n\n"
            f"{post['summary']}\n\n"
            f"🏆 Source: {post['source']}\n"
            f"📲 @wcupdates2026"
        )

        with open(graphic_file, "rb") as img:

            response = requests.post(
    f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
    data={
        "chat_id": CHAT_ID,
        "caption": caption[:1024],
        "reply_markup": f'''{{
            "inline_keyboard":[[
                {{
                    "text":"📰 Read Full Story",
                    "url":"{post["link"]}"
                }}
            ]]
        }}'''
    },
    files={
        "photo": img
    }
            )
        print(response.status_code)

        if response.status_code == 200:
            posts_sent += 1

        time.sleep(4)

    except Exception as e:
        print(e)

with open(POSTED_FILE, "w", encoding="utf-8") as f:

    for item in posted_articles:
        f.write(item + "\n")

print(f"Posted {posts_sent} World Cup articles.")
