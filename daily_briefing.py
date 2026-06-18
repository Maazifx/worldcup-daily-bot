import os
import requests
import datetime
import logging
import sys
import re
import feedparser
import urllib3
from zoneinfo import ZoneInfo

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    logger.error("BOT_TOKEN or CHAT_ID missing.")
    sys.exit(1)

STATE_FILE = "daily_briefing_state.txt"

# ---------- WORLD CUP 2026 TEAMS ----------
WORLD_CUP_TEAMS = {
    "Argentina", "Algeria", "Australia", "Austria", "Belgium", "Bosnia", "Brazil",
    "Canada", "Cape Verde", "Colombia", "Croatia", "Curacao", "Czechia", "DR Congo",
    "Ecuador", "Egypt", "England", "France", "Germany", "Ghana", "Haiti", "Iran",
    "Iraq", "Ivory Coast", "Japan", "Mexico", "Morocco", "Netherlands", "New Zealand",
    "Norway", "Panama", "Paraguay", "Portugal", "Qatar", "Saudi Arabia", "Scotland",
    "Senegal", "South Africa", "South Korea", "Spain", "Sweden", "Switzerland",
    "Tunisia", "Turkiye", "Uruguay", "USA", "Uzbekistan", "Wales"
}

FLAG_MAP = {
    "Argentina": "🇦🇷", "Algeria": "🇩🇿", "Australia": "🇦🇺", "Austria": "🇦🇹",
    "Belgium": "🇧🇪", "Bosnia": "🇧🇦", "Brazil": "🇧🇷", "Canada": "🇨🇦",
    "Cape Verde": "🇨🇻", "Colombia": "🇨🇴", "Croatia": "🇭🇷", "Curacao": "🇨🇼",
    "Czechia": "🇨🇿", "DR Congo": "🇨🇩", "Ecuador": "🇪🇨", "Egypt": "🇪🇬",
    "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "France": "🇫🇷", "Germany": "🇩🇪", "Ghana": "🇬🇭",
    "Haiti": "🇭🇹", "Iran": "🇮🇷", "Iraq": "🇮🇶", "Ivory Coast": "🇨🇮",
    "Japan": "🇯🇵", "Mexico": "🇲🇽", "Morocco": "🇲🇦", "Netherlands": "🇳🇱",
    "New Zealand": "🇳🇿", "Norway": "🇳🇴", "Panama": "🇵🇦", "Paraguay": "🇵🇾",
    "Portugal": "🇵🇹", "Qatar": "🇶🇦", "Saudi Arabia": "🇸🇦", "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    "Senegal": "🇸🇳", "South Africa": "🇿🇦", "South Korea": "🇰🇷", "Spain": "🇪🇸",
    "Sweden": "🇸🇪", "Switzerland": "🇨🇭", "Tunisia": "🇹🇳", "Turkiye": "🇹🇷",
    "Uruguay": "🇺🇾", "USA": "🇺🇸", "Uzbekistan": "🇺🇿", "Wales": "🏴󠁧󠁢󠁷󠁬󠁳󠁿"
}

def get_flag(country):
    return FLAG_MAP.get(country, "🏳️")

def utc_to_wat(utc_time_str):
    try:
        if ":" not in utc_time_str:
            return utc_time_str
        dt_utc = datetime.datetime.strptime(utc_time_str, "%H:%M").replace(tzinfo=ZoneInfo("UTC"))
        dt_wat = dt_utc.astimezone(ZoneInfo("Africa/Lagos"))
        return f"{dt_wat.strftime('%H:%M')} WAT"
    except:
        return utc_time_str

# ---------- API ----------
WC_API_BASE = "https://worldcup26.ir"

def get_today_matches():
    try:
        resp = requests.get(f"{WC_API_BASE}/get/games", timeout=15, verify=False)
        if resp.status_code != 200:
            return []
        data = resp.json()
        today = datetime.datetime.now(ZoneInfo("Africa/Lagos")).strftime("%Y-%m-%d")
        all_games = data.get("games", [])
        today_matches = []
        for g in all_games:
            local_date = g.get("local_date", "")
            if today in local_date:
                today_matches.append(g)
        return today_matches
    except Exception as e:
        logger.warning(f"API failed: {e}")
        return []

# ---------- RSS SOURCES ----------
RSS_FEEDS = {
    "Flashscore": "https://www.flashscore.com/rss/livescore.xml",
    "BBC Sport": "https://feeds.bbci.co.uk/sport/football/rss.xml",
    "Sky Sports": "https://www.skysports.com/rss/12040",
}

def fetch_rss_entries(url):
    try:
        feed = feedparser.parse(url, request_headers={"User-Agent": "Mozilla/5.0"})
        return feed.entries[:50]
    except Exception as e:
        logger.error(f"RSS failed for {url}: {e}")
        return []

def normalize_team(name):
    name = name.strip()
    fixes = {
        "USA": "USA",
        "United States": "USA",
        "South Korea": "South Korea",
        "Korea Republic": "South Korea",
        "Czech Republic": "Czechia",
        "Turkey": "Turkiye",
        "Congo DR": "DR Congo",
        "DR Congo": "DR Congo",
    }
    return fixes.get(name, name)

def parse_match_from_text(text):
    text = re.sub(r'<[^>]+>', ' ', text)  # strip HTML

    # Pattern 1: Team 2-1 Team FT / 67' / LIVE
    pattern = r'([A-Za-z\s\.]+?)\s+(\d+)[-:]\s*(\d+)\s+([A-Za-z\s\.]+?)\s*(FT|LIVE|HT|(\d+)\'|Penalty)?'
    matches = re.findall(pattern, text, re.IGNORECASE)
    for home, hg, ag, away, status, minute, _ in matches:
        home = normalize_team(home.strip())
        away = normalize_team(away.strip())
        if home in WORLD_CUP_TEAMS and away in WORLD_CUP_TEAMS:
            return {"home": home, "away": away, "score": f"{hg}-{ag}", "status": status.strip() if status else None}

    # Pattern 2: Team vs Team 14:00 kickoff
    pattern2 = r'([A-Za-z\s\.]+?)\s+v[s]?\.\s+([A-Za-z\s\.]+?)\s+(\d{1,2}:\d{2})'
    matches2 = re.findall(pattern2, text, re.IGNORECASE)
    for home, away, time_str in matches2:
        home = normalize_team(home.strip())
        away = normalize_team(away.strip())
        if home in WORLD_CUP_TEAMS and away in WORLD_CUP_TEAMS:
            return {"home": home, "away": away, "score": None, "time": time_str, "status": "upcoming"}

    return None

def get_today_from_rss():
    results, live, upcoming = [], [], []
    seen = set()

    for source, url in RSS_FEEDS.items():
        entries = fetch_rss_entries(url)
        for entry in entries:
            title = getattr(entry, "title", "")
            summary = getattr(entry, "summary", "")
            text = f"{title} {summary}"  # fixed syntax
            match = parse_match_from_text(text)
            if not match:
                continue
            key = f"{match['home']}_{match['away']}"
            if key in seen:
                continue
            seen.add(key)

            status = match.get("status", "").lower()
            if "ft" in status or "final" in text.lower():
                results.append({"home": match["home"], "away": match["away"], "score": match["score"], "source": source})
            elif "live" in status or re.search(r'\d+\'', status):
                live.append({"home": match["home"], "away": match["away"], "score": match["score"], "minute": status, "source": source})
            else:
                time_str = match.get("time")
                if time_str:
                    time_str = utc_to_wat(time_str)
                upcoming.append({"home": match["home"], "away": match["away"], "time": time_str, "source": source})

    return {"results": results[:8], "live": live[:5], "upcoming": upcoming[:8]}

def format_match_line(home, away, score=None, time=None, extra=""):
    flag_home = get_flag(home)
    flag_away = get_flag(away)
    score_part = f" {score}" if score else ""
    time_part = f" 🕒 {time}" if time else ""
    return f"{flag_home} {home}{score_part} {flag_away} {away}{time_part}{extra}"

def build_briefing():
    now_wat = datetime.datetime.now(ZoneInfo("Africa/Lagos"))
    today_str = now_wat.strftime("%d %B %Y")
    time_wat = now_wat.strftime("%H:%M WAT")

    lines = [
        "🌎 **FIFA WORLD CUP 2026 DAILY BRIEFING**",
        "",
        f"📅 {today_str}",
        f"🕒 {time_wat}",
        "━━━━━━━━━━━━━━"
    ]

    matches = get_today_matches()
    if matches:
        data_source = "API"
        completed = [m for m in matches if m.get("finished") == "TRUE"]
        live_now = [m for m in matches if m.get("status") == "live"]
        upcoming = [m for m in matches if m.get("finished") != "TRUE" and m.get("status") != "live"]
    else:
        logger.info("API empty, using RSS fallback")
        data_source = "RSS"
        rss_data = get_today_from_rss()
        completed = rss_data["results"]
        live_now = rss_data["live"]
        upcoming = rss_data["upcoming"]

    if completed:
        lines.append("🏁 **RESULTS**")
        for m in completed[:6]:
            if data_source == "API":
                home = m.get("home_team_name_en", "TBD")
                away = m.get("away_team_name_en", "TBD")
                hg = m.get("home_score", 0)
                ag = m.get("away_score", 0)
                lines.append(format_match_line(home, away, score=f"{hg}-{ag}"))
            else:
                lines.append(format_match_line(m["home"], m["away"], score=m["score"]))
        lines.append("━━━━━━━━━━━━━━")

    if live_now:
        lines.append("🔴 **LIVE NOW**")
        for m in live_now[:4]:
            if data_source == "API":
                home = m.get("home_team_name_en", "TBD")
                away = m.get("away_team_name_en", "TBD")
                hg = m.get("home_score", 0)
                ag = m.get("away_score", 0)
                minute = m.get("minute", "")
                extra = f" ({minute}')" if minute else " (LIVE)"
                lines.append(format_match_line(home, away, score=f"{hg}-{ag}", extra=extra))
            else:
                minute = m.get("minute", "LIVE")
                lines.append(format_match_line(m["home"], m["away"], score=m["score"], extra=f" ({minute})"))
        lines.append("━━━━━━━━━━━━━━")

    if upcoming:
        lines.append("📅 **UPCOMING TODAY**")
        for m in upcoming[:6]:
            if data_source == "API":
                home = m.get("home_team_name_en", "TBD")
                away = m.get("away_team_name_en", "TBD")
                time_str = m.get("local_date", "").split(" ")[-1] if " " in m.get("local_date", "") else ""
                time_str = utc_to_wat(time_str) if time_str else ""
                lines.append(format_match_line(home, away, time=time_str))
            else:
                lines.append(format_match_line(m["home"], m["away"], time=m.get("time")))
        lines.append("━━━━━━━━━━━━━━")

    if not completed and not live_now and not upcoming:
        lines.append("No World Cup 2026 matches scheduled for today.")

    lines.append(f"⚽ *Data source: {data_source}*")
    lines.append("🏆 **FIFA WORLD CUP 2026**")
    lines.append("📲 @wcupdates2026")
    return "\n".join(lines)

def send_briefing():
    today_wat = datetime.datetime.now(ZoneInfo("Africa/Lagos")).strftime("%Y-%m-%d")
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            if f.read().strip() == today_wat:
                logger.info("Already sent today – skipping.")
                return

    text = build_briefing()
    if not text:
        logger.warning("No text to send.")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            logger.info("✅ Briefing sent successfully!")
            with open(STATE_FILE, "w") as f:
                f.write(today_wat)
        else:
            logger.error(f"Telegram failed: {resp.text}")
    except Exception as e:
        logger.error(f"Send error: {e}")

if __name__ == "__main__":
    send_briefing()
