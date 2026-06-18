import feedparser
import requests
import os
import re
import time
import json
import logging
import hashlib
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

POSTED_FILE = "worldcup_posted_articles.json"

FEEDS = {
    "BBC Sport": "https://feeds.bbci.co.uk/sport/football/rss.xml",
    "Sky Sports": "https://www.skysports.com/rss/12040",
    "ESPN FC": "https://www.espn.com/espn/rss/soccer/news",
    "The Guardian": "https://www.theguardian.com/football/rss",
    "90Min": "https://www.90min.com/posts.rss"
}

SOURCE_PRIORITY = ["BBC Sport", "Sky Sports", "ESPN FC", "The Guardian", "90Min"]

# ---------- FLEXIBLE TOURNAMENT COMPETITOR DICTIONARY ----------
WORLD_CUP_TEAMS = {
    "argentina", "algeria", "australia", "austria", "belgium", "bosnia", "brazil",
    "canada", "cape verde", "colombia", "croatia", "curacao", "czechia", "dr congo",
    "ecuador", "egypt", "england", "france", "germany", "ghana", "haiti", "iran",
    "iraq", "ivory coast", "japan", "mexico", "morocco", "netherlands", "new zealand",
    "norway", "panama", "paraguay", "portugal", "qatar", "saudi arabia", "scotland",
    "senegal", "south africa", "south korea", "spain", "sweden", "switzerland",
    "tunisia", "turkiye", "uruguay", "usa", "uzbekistan", "wales"
}

REQUIRED_TERMS = ["world cup", "worldcup", "fifa", "wc2026", "wc 2026"]

EXCLUDE_TERMS = [
    "women's", "woman", "female", "lionesses", "wsl",
    "super league", "sarina wiegman", "wiegman",
    "euro 2025", "euro 2026", "u17", "u20", "u23",
    "youth", "paralympic", "olympic", "futsal", "beach soccer",
    "2027 world cup", "world cup 2027", "2027 women's",
    "predictor", "game", "quiz", "competition", "prize", "signed",
    "how to play", "final whistle", "round score"
]

FOOTBALL_TERMS = ["football", "soccer", "fifa", "world cup", "goal", "manager", "midfielder", "defender", "striker"]

BANNED_WORDS = [
    "darts", "rugby", "cricket", "golf", "tennis", "formula 1", "f1",
    "motogp", "boxing", "ufc", "mma", "snooker", "basketball", "nba",
    "nfl", "baseball", "mlb", "horse racing", "cycling", "podcast",
    "audio", "betting", "odds", "transfer rumours", "transfer rumor",
    "kit leaked", "home kit", "away kit", "ashes", "test match",
    "one day international", "odi", "t20", "county championship",
    "premiership rugby", "six nations", "wimbledon", "atp", "wta",
    "third kit", "jersey leak", "scores & fixtures", "predictor"
]

# ----------------------------------------------------------------------
# Image helpers
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
        return None
    except Exception as e:
        logger.debug(f"Scraping error: {e}")
        return None

def get_best_image(article_link, feed_image_url):
    scraped_url = scrape_article_image(article_link)
    if scraped_url:
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(scraped_url, headers=headers, timeout=20)
            if resp.status_code == 200:
                img = Image.open(BytesIO(resp.content))
                width, height = img.size
                if width >= 600 and height >= 350:
                    with open("article.jpg", "wb") as f:
                        f.write(resp.content)
                    return "article.jpg"
        except Exception as e:
            logger.debug(f"Scraped image download failed: {e}")
    if feed_image_url and feed_image_url != "BBC_FALLBACK":
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(feed_image_url, headers=headers, timeout=20)
            if resp.status_code == 200:
                with open("article.jpg", "wb") as f:
                    f.write(resp.content)
                return "article.jpg"
        except Exception as e:
            logger.debug(f"RSS image download failed: {e}")
    return create_placeholder_image()

def normalise_title(title):
    title = title.lower()
    title = re.sub(r'[^\w\s]', '', title)
    return re.sub(r'\s+', ' ', title).strip()

def get_title_hash(title):
    norm = normalise_title(title)
    return hashlib.sha1(norm.encode('utf-8')).hexdigest()

# ----------------------------------------------------------------------
# Cleaned Evaluation Filters
# ----------------------------------------------------------------------
def is_men_world_cup_article(title, summary, link):
    text = (title + " " + summary).lower()

    if any(excl in text for excl in EXCLUDE_TERMS):
        return False

    # Check that it involves tournament elements or active qualified nations
    contains_req = any(req in text for req in REQUIRED_TERMS) or "world-cup" in link.lower()
    contains_team = any(team in text for team in WORLD_CUP_TEAMS)

    return contains_req and contains_team

# ----------------------------------------------------------------------
# JSON Load / Save Functions
# ----------------------------------------------------------------------
def load_posted_state():
    if os.path.exists(POSTED_FILE):
        try:
            with open(POSTED_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read JSON file registry: {e}")
            return []
    return []

def save_posted_state(state_list):
    try:
        with open(POSTED_FILE, "w", encoding="utf-8") as f:
            json.dump(state_list, f, indent=2, ensure_ascii=False)
        logger.info(f"Database sync successful. Tracked collection length: {len(state_list)}")
    except Exception as e:
        logger.error(f"Failed to write out state modifications: {e}")

# ----------------------------------------------------------------------
# Execution Engine
# ----------------------------------------------------------------------
def main():
    history_log = load_posted_state()
    posted_links = {entry["link"] for entry in history_log}
    posted_hashes = {entry["title_hash"] for entry in history_log}
    
    new_posts = []

    for source in SOURCE_PRIORITY:
        feed = feedparser.parse(FEEDS[source])
        if not hasattr(feed, "entries"):
            continue
        source_count = 0
        for article in feed.entries[:30]:
            if source_count >= 2:
                break
            title = getattr(article, "title", "").strip()
            link = getattr(article, "link", "").strip()
            summary = getattr(article, "summary", "").strip()
            if not title or not link:
                continue

            title_hash = get_title_hash(title)
            if link in posted_links or title_hash in posted_hashes:
                continue

            clean_summary = re.sub("<.*?>", "", summary).strip()

            if not is_men_world_cup_article(title, clean_summary, link):
                continue

            article_text = title.lower() + " " + clean_summary.lower()
            if not any(term in article_text for term in FOOTBALL_TERMS) or any(banned in article_text for banned in BANNED_WORDS):
                continue

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
                "feed_image": feed_image,
                "title_hash": title_hash
            })
            source_count += 1
            logger.info(f"Staged article item matching criteria: {title[:50]}")

    if not new_posts:
        logger.info("No fresh articles found on this sweep execution cycle.")
        return

    posts_sent = 0
    for post in new_posts:
        if posts_sent >= 3:
            break
        image_file = get_best_image(post["link"], post["feed_image"])
        if not image_file or not os.path.exists(image_file):
            continue
        try:
            caption = (
                f"🚨 *BREAKING NEWS*\n\n"
                f"*{post['title']}*\n\n"
                f"{post['summary']}...\n\n"
                f"🏆 *Source:* {post['source']}\n"
                f"📲 @wcupdates2026"
            )
            reply_markup = {"inline_keyboard": [[{"text": "📰 Read Full Story", "url": post["link"]}]]}
            with open(image_file, "rb") as img:
                resp = requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                    data={
                        "chat_id": CHAT_ID,
                        "caption": caption[:1024],
                        "parse_mode": "Markdown",
                        "reply_markup": json.dumps(reply_markup)
                    },
                    files={"photo": img}
                )
            if resp.status_code == 200:
                posts_sent += 1
                posted_links.add(post["link"])
                posted_hashes.add(post["title_hash"])
                
                # Append structured dictionary profile item seamlessly
                history_log.append({"link": post["link"], "title_hash": post["title_hash"]})
                save_posted_state(history_log)
                logger.info(f"Pushed update channel update notification: {post['title']}")
            else:
                logger.error(f"Telegram processing failure context trace: {resp.text}")
            time.sleep(5)
        except Exception as e:
            logger.error(f"Fatal error handling channel push: {e}")

    logger.info(f"Successfully processed {posts_sent} updates during this lifecycle validation run.")

if __name__ == "__main__":
    main()
