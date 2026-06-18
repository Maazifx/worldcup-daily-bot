import feedparser
import requests
import os
import re
import time
import random
import json
import logging
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from bs4 import BeautifulSoup

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

SOURCE_PRIORITY = ["BBC Sport", "Sky Sports", "ESPN FC", "The Guardian", "90Min"]

# ---------- STRICT FILTERS ----------
# 1. Must contain at least one of these (men's World Cup specific)
REQUIRED_TERMS = [
    "world cup 2026",
    "fifa world cup",
    "men's world cup",
    "world cup qualifier",
    "world cup qualifying",
    "world cup group",
    "world cup knockout",
    "world cup final",
    "world cup semi-final",
    "world cup quarter-final",
    "world cup round of 16"
]

# 2. If any of these appear, skip (women's, other sports, non-football)
EXCLUDE_TERMS = [
    "women's",
    "woman",
    "female",
    "lionesses",
    "wsl",
    "super league",
    "euro 2025",
    "u17",
    "u20",
    "u23",
    "youth",
    "paralympic",
    "olympic",
    "futsal",
    "beach soccer"
]

# Also keep the original football terms and banned words (but we can relax football terms)
FOOTBALL_TERMS = ["football", "soccer", "fifa", "world cup", "goal", "manager", "midfielder", "defender", "striker"]
BANNED_WORDS = ["darts", "rugby", "cricket", "golf", "tennis", "formula 1", "f1", "motogp", "boxing", "ufc", "mma", "snooker", "basketball", "nba", "nfl", "baseball", "mlb", "horse racing", "cycling", "podcast", "audio", "betting", "odds", "transfer rumours", "transfer rumor", "kit leaked", "home kit", "away kit", "ashes", "test match", "one day international", "odi", "t20", "county championship", "premiership rugby", "six nations", "wimbledon", "atp", "wta", "third kit", "jersey leak"]

# ----------------------------------------------------------------------
# Helper: create a placeholder image (only as last resort)
# ----------------------------------------------------------------------
def create_placeholder_image(text="World Cup News"):
    img = Image.new('RGB', (1200, 800), color=(30, 30, 50))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
    except:
        font = ImageFont.load_default()
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    x = (1200 - text_width) // 2
    y = (800 - text_height) // 2
    draw.text((x, y), text, fill=(255, 255, 255), font=font)
    subtext = "FIFA World Cup 2026"
    try:
        font2 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
    except:
        font2 = ImageFont.load_default()
    draw.text((x, y + 100), subtext, fill=(200, 200, 200), font=font2)
    filename = "placeholder.jpg"
    img.save(filename, "JPEG", quality=85)
    return filename

# ----------------------------------------------------------------------
# Scrape the article page to find the best image
# ----------------------------------------------------------------------
def scrape_article_image(article_url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(article_url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, 'lxml')
        og_tag = soup.find('meta', property='og:image')
        if og_tag and og_tag.get('content'):
            image_url = og_tag['content']
            if image_url.startswith('//'):
                image_url = 'https:' + image_url
            elif image_url.startswith('/'):
                from urllib.parse import urlparse
                parsed = urlparse(article_url)
                base = f"{parsed.scheme}://{parsed.netloc}"
                image_url = base + image_url
            return image_url
        twitter_tag = soup.find('meta', attrs={'name': 'twitter:image'})
        if twitter_tag and twitter_tag.get('content'):
            return twitter_tag['content']
        images = soup.find_all('img')
        for img in images:
            src = img.get('src')
            if not src:
                continue
            width = img.get('width')
            if width and int(width) > 400:
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    from urllib.parse import urlparse
                    parsed = urlparse(article_url)
                    base = f"{parsed.scheme}://{parsed.netloc}"
                    src = base + src
                return src
        if images:
            src = images[0].get('src')
            if src:
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    from urllib.parse import urlparse
                    parsed = urlparse(article_url)
                    base = f"{parsed.scheme}://{parsed.netloc}"
                    src = base + src
                return src
        return None
    except Exception as e:
        logger.debug(f"Scraping error: {e}")
        return None

# ----------------------------------------------------------------------
# Get the best image for an article
# ----------------------------------------------------------------------
def get_best_image(article_link, feed_image_url):
    scraped_url = scrape_article_image(article_link)
    if scraped_url:
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(scraped_url, headers=headers, timeout=20)
            if resp.status_code == 200:
                img = Image.open(BytesIO(resp.content))
                width, height = img.size
                if width >= 800 and height >= 450:
                    with open("article.jpg", "wb") as f:
                        f.write(resp.content)
                    logger.info("Used scraped image.")
                    return "article.jpg"
        except Exception as e:
            logger.debug(f"Scraped image download failed: {e}")
    if feed_image_url and feed_image_url != "BBC_FALLBACK":
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(feed_image_url, headers=headers, timeout=20)
            if resp.status_code == 200:
                img = Image.open(BytesIO(resp.content))
                width, height = img.size
                if width >= 400:
                    with open("article.jpg", "wb") as f:
                        f.write(resp.content)
                    logger.info("Used RSS feed image.")
                    return "article.jpg"
        except Exception as e:
            logger.debug(f"RSS image download failed: {e}")
    logger.info("Using placeholder image.")
    return create_placeholder_image()

# ----------------------------------------------------------------------
# Filtering function
# ----------------------------------------------------------------------
def is_men_world_cup_article(title, summary, link):
    """Return True only if this is a men's FIFA World Cup article."""
    text = (title + " " + summary).lower()
    link_lower = link.lower()

    # Exclude women's or other non-men's topics
    if any(excl in text for excl in EXCLUDE_TERMS):
        return False

    # Must contain one of the required men's World Cup phrases
    if not any(req in text for req in REQUIRED_TERMS):
        # Also check the URL for clues
        if not ("world-cup" in link_lower or "worldcup" in link_lower or "fifa" in link_lower):
            return False
        # If URL has "worldcup" but doesn't contain specific phrase, still accept if it mentions "world cup" and not excluded
        if "world cup" not in text and "worldcup" not in text:
            return False

    # Additional check: ensure it's about men's by not having women's terms (already excluded)
    return True

# ----------------------------------------------------------------------
# Load posted articles, fetch and filter, send
# ----------------------------------------------------------------------
if not os.path.exists(POSTED_FILE):
    with open(POSTED_FILE, "w", encoding="utf-8") as f:
        pass

with open(POSTED_FILE, "r", encoding="utf-8") as f:
    posted_articles = set(line.strip() for line in f if line.strip())

new_posts = []

for source in SOURCE_PRIORITY:
    feed = feedparser.parse(FEEDS[source])
    if not hasattr(feed, "entries"):
        logger.warning(f"No entries from {source}")
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
        clean_summary = re.sub("<.*?>", "", summary).strip()

        # --- Apply strict filter ---
        if not is_men_world_cup_article(title, clean_summary, link):
            logger.debug(f"Skipped (not men's WC): {title[:50]}")
            continue

        # Also ensure football terms (just as safety)
        article_text = title.lower() + " " + clean_summary.lower()
        if not any(term in article_text for term in FOOTBALL_TERMS):
            continue
        if any(banned in article_text for banned in BANNED_WORDS):
            continue

        # Get RSS image if any
        feed_image = None
        if hasattr(article, "media_content"):
            try: feed_image = article.media_content[0]["url"]
            except: pass
        if not feed_image and hasattr(article, "media_thumbnail"):
            try: feed_image = article.media_thumbnail[0]["url"]
            except: pass
        if not feed_image:
            feed_image = "BBC_FALLBACK"

        new_posts.append({
            "source": source,
            "title": title,
            "summary": clean_summary[:350],
            "link": link,
            "feed_image": feed_image
        })
        source_count += 1
        logger.info(f"Found article: {title[:60]}")

if not new_posts:
    logger.warning("No men's World Cup news found.")
    raise SystemExit

posts_sent = 0
for post in new_posts:
    if posts_sent >= 3:
        break

    image_file = get_best_image(post["link"], post["feed_image"])
    if not image_file or not os.path.exists(image_file):
        continue

    try:
        caption = (
            f"🚨 BREAKING\n\n"
            f"{post['title']}\n\n"
            f"{post['summary']}\n\n"
            f"🏆 Source: {post['source']}\n"
            f"📲 @wcupdates2026"
        )
        reply_markup = {"inline_keyboard": [[{"text": "📰 Read Full Story", "url": post["link"]}]]}

        with open(image_file, "rb") as img:
            resp = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                data={
                    "chat_id": CHAT_ID,
                    "caption": caption[:1024],
                    "reply_markup": json.dumps(reply_markup)
                },
                files={"photo": img}
            )
        if resp.status_code == 200:
            posts_sent += 1
            posted_articles.add(post["link"])
            logger.info(f"Posted: {post['title']}")
        else:
            logger.error(f"Failed to post: {resp.text}")
        time.sleep(4)

    except Exception as e:
        logger.error(f"Error posting: {e}")

with open(POSTED_FILE, "w", encoding="utf-8") as f:
    for item in posted_articles:
        f.write(item + "\n")

logger.info(f"Posted {posts_sent} World Cup articles.")
