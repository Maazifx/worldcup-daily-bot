import feedparser
import requests
import os
import re
import time
import json
import tempfile
import hashlib
import logging
from io import BytesIO
from PIL import Image

# ---------- CONFIG ----------
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

# ---------- LOGGING ----------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ---------- IMAGE DOWNLOAD (no overlay) ----------
def download_article_image(image_url):
    if not image_url:
        return None
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(image_url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return None
        # Quick validation
        try:
            img = Image.open(BytesIO(resp.content))
            if img.size[0] < 200:
                return None
        except:
            return None
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        tmp.write(resp.content)
        tmp.close()
        return tmp.name
    except Exception as e:
        logger.warning(f"Image download failed: {e}")
        return None

# ---------- DUPLICATE DETECTION ----------
def content_hash(title, summary):
    text = (title + " " + summary[:200]).lower()
    text = re.sub(r'\b(bbc|sky|espn|guardian|90min|sport|news)\b', '', text)
    return hashlib.md5(text.encode('utf-8')).hexdigest()

# ---------- TELEGRAM SENDERS ----------
def send_photo(image_path, caption, reply_markup):
    try:
        with open(image_path, "rb") as f:
            resp = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                data={
                    "chat_id": CHAT_ID,
                    "caption": caption[:1024],
                    "reply_markup": json.dumps(reply_markup)
                },
                files={"photo": f},
                timeout=30
            )
        result = resp.json()
        return result.get("ok", False)
    except Exception as e:
        logger.error(f"Send photo error: {e}")
        return False

def send_text(caption, reply_markup):
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": caption[:4096],
                "reply_markup": json.dumps(reply_markup)
            },
            timeout=30
        )
        result = resp.json()
        return result.get("ok", False)
    except Exception as e:
        logger.error(f"Send text error: {e}")
        return False

# ---------- PERSISTENCE HELPERS ----------
def load_posted():
    """Return a dict of {link: hash} for all previously posted articles."""
    posted = {}
    if os.path.exists(POSTED_FILE):
        with open(POSTED_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if '|' in line:
                    link, h = line.split('|', 1)
                    posted[link] = h
                else:
                    posted[line] = None   # old entries without hash
    return posted

def save_posted(posted_dict):
    """Save the dict as link|hash lines."""
    with open(POSTED_FILE, "w", encoding="utf-8") as f:
        for link, h in posted_dict.items():
            if h:
                f.write(f"{link}|{h}\n")
            else:
                f.write(f"{link}\n")

# ---------- MAIN ----------
def main():
    posted = load_posted()
    posted_links = set(posted.keys())
    posted_hashes = set(h for h in posted.values() if h is not None)
    logger.info(f"Loaded {len(posted_links)} entries, {len(posted_hashes)} with content hashes")

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
            if link in posted_links:
                continue

            clean_summary = re.sub("<.*?>", "", summary).strip()
            article_text = title.lower() + " " + clean_summary.lower()

            # Football filter
            football_terms = [
                "football", "soccer", "fifa", "world cup", "goal",
                "manager", "midfielder", "defender", "striker", "national team"
            ]
            if not any(term in article_text for term in football_terms):
                continue

            # Banned words
            if any(banned in article_text for banned in BANNED_WORDS):
                continue

            # World Cup keywords
            keyword_match = any(kw in article_text for kw in WORLD_CUP_KEYWORDS)
            url_match = (
                "world-cup" in link.lower()
                or "worldcup" in link.lower()
                or "fifa" in link.lower()
            )
            if not keyword_match and not url_match:
                continue

            # Duplicate content check
            h = content_hash(title, clean_summary)
            if h in posted_hashes:
                logger.info(f"Skipping duplicate content (hash {h[:8]}) for '{title[:50]}...'")
                continue

            # Extract image
            image_url = None
            if hasattr(article, "media_content"):
                try:
                    image_url = article.media_content[0]["url"]
                except:
                    pass
            if not image_url and hasattr(article, "media_thumbnail"):
                try:
                    image_url = article.media_thumbnail[0]["url"]
                except:
                    pass

            new_posts.append({
                "source": source,
                "title": title,
                "summary": clean_summary[:350],
                "link": link,
                "image_url": image_url,
                "content_hash": h
            })
            source_count += 1

    if not new_posts:
        logger.info("No new World Cup articles found.")
        return

    posts_sent = 0
    for post in new_posts:
        if posts_sent >= 3:
            break

        image_file = download_article_image(post["image_url"]) if post["image_url"] else None

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

        if image_file:
            success = send_photo(image_file, caption, reply_markup)
            try:
                os.unlink(image_file)
            except:
                pass
        else:
            success = send_text(caption, reply_markup)

        if success:
            posts_sent += 1
            posted[post["link"]] = post["content_hash"]   # store with hash
            posted_hashes.add(post["content_hash"])
            logger.info(f"Posted: {post['title'][:60]}...")
        else:
            logger.error(f"Failed to send post for {post['link']}")

        time.sleep(4)

    save_posted(posted)
    logger.info(f"Posted {posts_sent} new articles.")

if __name__ == "__main__":
    main()
