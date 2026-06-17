import feedparser
import requests
import os
import re
import time
import random
import json
import logging
from io import BytesIO
from PIL import Image

# ------------------ Setup logging ------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

POSTED_FILE = "worldcup_posted_articles.txt"

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
    "world cup", "fifa world cup", "world cup 2026", "fifa",
    "world cup qualifier", "world cup qualifying", "qualification",
    "qualifier", "group stage", "round of 16", "quarter-final",
    "quarterfinal", "semi-final", "semifinal", "knockout stage",
    "world cup opener"
]

BANNED_WORDS = [
    "darts", "rugby", "cricket", "golf", "tennis", "formula 1", "f1",
    "motogp", "boxing", "ufc", "mma", "snooker", "basketball", "nba",
    "nfl", "baseball", "mlb", "horse racing", "cycling", "podcast",
    "football daily", "audio", "betting", "odds", "transfer rumours",
    "transfer rumor", "kit leaked", "home kit", "away kit", "ashes",
    "test match", "one day international", "odi", "t20",
    "county championship", "premiership rugby", "six nations",
    "wimbledon", "atp", "wta", "third kit", "jersey leak"
]

def get_fallback_image():
    backgrounds = [
        "background/1571741257821.jpeg",
        "background/64 qatar.jpg",
        "background/WC.jpg.webp",
        "background/gettyimages-1127374662-612x612.jpg",
        "background/gettyimages-1775210084-612x612.jpg",
        "background/gettyimages-469569148-612x612.jpg"
    ]
    return random.choice(backgrounds)

def get_best_image(image_url):
    if image_url == "BBC_FALLBACK":
        return get_fallback_image()

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(image_url, headers=headers, timeout=20)
        if response.status_code != 200:
            return get_fallback_image()

        img = Image.open(BytesIO(response.content))
        width, height = img.size
        if width < 800 or height < 450:
            logger.info(f"Image too small ({width}x{height}), using fallback")
            return get_fallback_image()

        # Save without recompression (original quality)
        with open("article.jpg", "wb") as f:
            f.write(response.content)
        return "article.jpg"

    except Exception as e:
        logger.error(f"Error downloading image: {e}")
        return get_fallback_image()

# ---------- Load posted articles ----------
if not os.path.exists(POSTED_FILE):
    with open(POSTED_FILE, "w", encoding="utf-8"):
        pass

with open(POSTED_FILE, "r", encoding="utf-8") as f:
    posted_articles = set(line.strip() for line in f if line.strip())

new_posts = []

# ---------- Fetch & filter feeds ----------
for source in SOURCE_PRIORITY:
    logger.info(f"Processing {source}...")
    try:
        feed = feedparser.parse(FEEDS[source], request_headers={"User-Agent": "Mozilla/5.0"})
    except Exception as e:
        logger.error(f"Failed to parse {source}: {e}")
        continue

    if not hasattr(feed, "entries") or not feed.entries:
        logger.warning(f"No entries from {source}")
        continue

    logger.info(f"Found {len(feed.entries)} entries in {source}")

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

        clean_summary = re.sub("<.*?>", "", summary).strip()
        article_text = (title.lower() + " " + clean_summary.lower())

        # ---- Football filter ----
        football_terms = [
            "football", "soccer", "fifa", "world cup", "goal",
            "manager", "midfielder", "defender", "striker", "national team"
        ]
        if not any(term in article_text for term in football_terms):
            continue

        # ---- Banned words ----
        if any(banned in article_text for banned in BANNED_WORDS):
            continue

        # ---- World Cup keywords ----
        keyword_match = any(kw in article_text for kw in WORLD_CUP_KEYWORDS)
        url_match = ("world-cup" in link.lower() or "worldcup" in link.lower() or "fifa" in link.lower())
        if not keyword_match and not url_match:
            continue

        # ---- Extract image ----
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
        source_count += 1
        logger.info(f"Added article from {source}: {title[:50]}...")

    logger.info(f"Added {source_count} articles from {source}")

if not new_posts:
    logger.info("No World Cup news found.")
    raise SystemExit

# ---------- Send posts ----------
posts_sent = 0
for post in new_posts:
    if posts_sent >= 3:
        break

    image_file = get_best_image(post["image"])
    if not image_file or not os.path.exists(image_file):
        logger.warning(f"Could not get image for {post['title']}")
        continue

    try:
        caption = (
            f"🚨 BREAKING\n\n"
            f"{post['title']}\n\n"
            f"{post['summary']}\n\n"
            f"🏆 Source: {post['source']}\n"
            f"📲 @wcupdates2026"
        )

        reply_markup = {
            "inline_keyboard": [[
                {"text": "📰 Read Full Story", "url": post["link"]}
            ]]
        }

        with open(image_file, "rb") as img:
            response = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                data={
                    "chat_id": CHAT_ID,
                    "caption": caption[:1024],
                    "reply_markup": json.dumps(reply_markup)
                },
                files={"photo": img}
            )

        if response.status_code == 200:
            posts_sent += 1
            posted_articles.add(post["link"])
            logger.info(f"Posted: {post['title']}")
        else:
            logger.error(f"Failed to post: {response.text}")

        time.sleep(4)

    except Exception as e:
        logger.error(f"Error posting: {e}")

# ---------- Save state ----------
logger.info(f"Saving {len(posted_articles)} posted articles")
with open(POSTED_FILE, "w", encoding="utf-8") as f:
    for item in posted_articles:
        f.write(item + "\n")

logger.info(f"Posted {posts_sent} World Cup articles.")
