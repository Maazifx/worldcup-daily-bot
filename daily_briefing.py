import os
import requests
import feedparser
import re
import datetime
import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    logger.error("BOT_TOKEN or CHAT_ID missing.")
    sys.exit(1)

STATE_FILE = "daily_briefing_state.txt"

# RSS feeds – same as your news bot
FEEDS = {
    "BBC Sport": "https://feeds.bbci.co.uk/sport/football/rss.xml",
    "Sky Sports": "https://www.skysports.com/rss/12040",
    "Guardian": "https://www.theguardian.com/football/rss",
    "90Min": "https://www.90min.com/posts.rss"
}

def fetch_articles_from_feed(url):
    try:
        feed = feedparser.parse(url, request_headers={"User-Agent": "Mozilla/5.0"})
        return feed.entries[:30]
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return []

def extract_match_info(text):
    """Try to extract team names and scores from text."""
    # Patterns: "Team A 2-1 Team B", "Team A 2:1 Team B", "Team A vs Team B"
    patterns = [
        r'([A-Za-z ]+)\s+(\d+)\s*[-–:;]\s*(\d+)\s+([A-Za-z ]+)',  # score
        r'([A-Za-z ]+)\s+v(?:s)?\.?\s+([A-Za-z ]+)',  # vs
        r'([A-Za-z ]+)\s+[-–]\s+([A-Za-z ]+)',  # dash
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            groups = m.groups()
            if len(groups) == 4:
                home, hg, ag, away = groups
                return (home.strip(), away.strip(), f"{hg}-{ag}")
            elif len(groups) == 2:
                return (groups[0].strip(), groups[1].strip(), None)
    return (None, None, None)

def is_result(text):
    return any(kw in text.lower() for kw in ["full-time", "result", "final", "wins", "beat", "defeat"])

def is_live(text):
    return any(kw in text.lower() for kw in ["live", "minute", "half-time", "updates"])

def is_preview(text):
    return any(kw in text.lower() for kw in ["preview", "ahead of", "set to face", "clash"])

def build_briefing():
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            if f.read().strip() == today:
                logger.info("Briefing already sent today – skipping.")
                return None

    all_articles = []
    for source, url in FEEDS.items():
        entries = fetch_articles_from_feed(url)
        for entry in entries:
            title = getattr(entry, "title", "").strip()
            summary = getattr(entry, "summary", "").strip()
            summary = re.sub("<.*?>", "", summary)
            if title:
                all_articles.append({
                    "source": source,
                    "title": title,
                    "summary": summary,
                    "link": getattr(entry, "link", "")
                })

    if not all_articles:
        return "No football news found today."

    results = []
    live = []
    upcoming = []

    for article in all_articles:
        text = article["title"] + " " + article["summary"]
        home, away, score = extract_match_info(text)
        if not home or not away:
            continue
        if is_result(text) and score:
            results.append(f"{home} {score} {away}")
        elif is_live(text):
            live.append(f"{home} vs {away} (LIVE)")
        elif is_preview(text):
            upcoming.append(f"{home} vs {away}")

    # If we got nothing, fallback to raw headlines that mention matches
    if not results and not live and not upcoming:
        for article in all_articles:
            text = article["title"]
            if " vs " in text or " v " in text or "–" in text:
                upcoming.append(text)

    lines = []
    if results:
        lines.append("🏁 RESULTS")
        lines.extend(results[:5])
        lines.append("")
    if live:
        lines.append("🔴 LIVE")
        lines.extend(live[:3])
        lines.append("")
    if upcoming:
        lines.append("🔥 NEXT MATCH")
        lines.append(upcoming[0])
    else:
        lines.append("🔥 No upcoming matches found.")

    if not lines or len(lines) == 1:
        return "No match information available today."

    lines.append("\n🏆 FIFA WORLD CUP 2026")
    lines.append("📲 @wcupdates2026")
    return "\n".join(lines)

def send_briefing():
    try:
        text = build_briefing()
        if text is None:
            return
        if not text:
            return
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": True}
        resp = requests.post(url, json=payload)
        if resp.status_code == 200:
            logger.info("Briefing sent.")
            with open(STATE_FILE, "w") as f:
                f.write(datetime.datetime.utcnow().strftime("%Y-%m-%d"))
        else:
            logger.error(f"Failed: {resp.text}")
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    send_briefing()
