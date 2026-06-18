import os
import requests
import datetime
import logging
import sys
import re
import feedparser
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    logger.error("BOT_TOKEN or CHAT_ID missing.")
    sys.exit(1)

STATE_FILE = "daily_briefing_state.txt"

# ---------- PRIMARY API (with SSL bypass) ----------
WC_API_BASE = "https://worldcup26.ir"

def get_today_matches():
    try:
        resp = requests.get(f"{WC_API_BASE}/get/games", timeout=15, verify=False)
        if resp.status_code != 200:
            return []
        data = resp.json()
        today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        all_games = data.get("games", [])
        today_matches = []
        for g in all_games:
            local_date = g.get("local_date", "")
            if today in local_date or local_date.replace('/', '-')[:10] == today:
                today_matches.append(g)
        return today_matches
    except Exception as e:
        logger.warning(f"API failed: {e}")
        return []

def get_standings():
    try:
        resp = requests.get(f"{WC_API_BASE}/get/groups", timeout=10, verify=False)
        if resp.status_code == 200:
            return resp.json()
        return []
    except Exception as e:
        logger.warning(f"Standings failed: {e}")
        return []

# ---------- RSS FALLBACK (improved) ----------
RSS_FEEDS = {
    "BBC Sport": "https://feeds.bbci.co.uk/sport/football/rss.xml",
    "Sky Sports": "https://www.skysports.com/rss/12040",
    "Guardian": "https://www.theguardian.com/football/rss",
}

# List of known World Cup teams to validate matches
KNOWN_TEAMS = [
    "Argentina", "Algeria", "Australia", "Austria", "Belgium", "Bosnia", "Brazil",
    "Canada", "Cape Verde", "Colombia", "Croatia", "Curacao", "Czechia", "DR Congo",
    "Ecuador", "Egypt", "England", "France", "Germany", "Ghana", "Haiti", "Iran",
    "Iraq", "Ivory Coast", "Japan", "Mexico", "Morocco", "Netherlands", "New Zealand",
    "Norway", "Panama", "Paraguay", "Portugal", "Qatar", "Saudi Arabia", "Scotland",
    "Senegal", "South Africa", "South Korea", "Spain", "Sweden", "Switzerland",
    "Tunisia", "Turkiye", "Uruguay", "USA", "Uzbekistan", "Wales"
]
TEAM_SET = set(KNOWN_TEAMS)

def fetch_articles_from_feed(url):
    try:
        feed = feedparser.parse(url, request_headers={"User-Agent": "Mozilla/5.0"})
        return feed.entries[:30]
    except Exception as e:
        logger.error(f"RSS failed for {url}: {e}")
        return []

def is_valid_team(name):
    """Check if a name looks like a real team (starts with capital letter, not too short)."""
    name = name.strip()
    if len(name) < 2:
        return False
    # Check against known teams first
    if name in TEAM_SET:
        return True
    # Also accept if it starts with uppercase and is at least 3 chars
    if name[0].isupper() and len(name) >= 3:
        return True
    return False

def extract_match_info(text):
    """Extract home team, away team, and score with validation."""
    # Pattern: Team A 2-1 Team B
    pattern = r'([A-Za-z ]{2,30})\s+(\d+)\s*[-–:;]\s*(\d+)\s+([A-Za-z ]{2,30})'
    matches = re.findall(pattern, text, re.IGNORECASE)
    for home, hg, ag, away in matches:
        home = home.strip()
        away = away.strip()
        # Validate both are real team names
        if is_valid_team(home) and is_valid_team(away):
            return (home, away, f"{hg}-{ag}")
    
    # Pattern: Team A vs Team B (no score)
    pattern2 = r'([A-Za-z ]{2,30})\s+v(?:s)?\.?\s+([A-Za-z ]{2,30})'
    matches2 = re.findall(pattern2, text, re.IGNORECASE)
    for home, away in matches2:
        home = home.strip()
        away = away.strip()
        if is_valid_team(home) and is_valid_team(away):
            return (home, away, None)
    
    return (None, None, None)

def is_result(text):
    return any(kw in text.lower() for kw in ["full-time", "result", "final", "wins", "beat", "defeat", "draw", "win"])

def is_live(text):
    return any(kw in text.lower() for kw in ["live", "minute", "half-time", "updates", "breaking"])

def build_from_rss():
    all_articles = []
    for source, url in RSS_FEEDS.items():
        entries = fetch_articles_from_feed(url)
        for e in entries:
            title = getattr(e, "title", "").strip()
            summary = getattr(e, "summary", "").strip()
            summary = re.sub("<.*?>", "", summary)
            if title:
                all_articles.append({"title": title, "summary": summary, "source": source})
    
    if not all_articles:
        return [], [], []
    
    results, live, upcoming, seen = [], [], [], set()
    for art in all_articles:
        text = art["title"] + " " + art["summary"]
        home, away, score = extract_match_info(text)
        if not home or not away:
            continue
        key = f"{home}_{away}"
        if key in seen:
            continue
        seen.add(key)
        if score and is_result(text):
            results.append(f"{home} {score} {away}")
        elif is_live(text):
            live.append(f"{home} vs {away}")
        else:
            upcoming.append(f"{home} vs {away}")
    
    return results, live, upcoming

# ---------- FORMATTING ----------
def format_match(m):
    home = m.get("home_team_name_en", "TBD")
    away = m.get("away_team_name_en", "TBD")
    score = f"{m.get('home_score', 0)}-{m.get('away_score', 0)}" if m.get("finished") == "TRUE" else "vs"
    time_info = m.get("local_date", "TBD")
    status = "✅" if m.get("finished") == "TRUE" else "⏳"
    return f"{status} **{home}** {score} **{away}** — {time_info}"

def build_briefing():
    today_str = datetime.datetime.utcnow().strftime("%B %d, %Y")
    lines = [
        "🌍 **WORLD CUP 2026 DAILY BRIEFING**",
        f"📅 {today_str}\n"
    ]

    # Try primary API
    matches = get_today_matches()
    if matches:
        completed = [m for m in matches if m.get("finished") == "TRUE"]
        upcoming = [m for m in matches if m.get("finished") != "TRUE"]

        if completed:
            lines.append("🏁 **RESULTS**")
            for m in completed:
                lines.append(format_match(m))
            lines.append("")
        if upcoming:
            lines.append("⏳ **TODAY'S FIXTURES**")
            for m in upcoming:
                lines.append(format_match(m))
            lines.append("")

        standings = get_standings()
        if standings:
            lines.append("🏆 **CURRENT GROUP STANDINGS**")
            for group in standings[:4]:
                g_name = group.get("group", group.get("name", "Group"))
                lines.append(f"**{g_name}**")
                table = group.get("table", [])[:4]
                for team in table:
                    name = team.get("team_name_en", team.get("name", "TBD"))
                    pts = team.get("points", 0)
                    lines.append(f"  • {name} — {pts} pts")
            lines.append("")
        
        lines.append("⚽ **FIFA World Cup 2026** — Enjoy the games!")
    
    else:
        # Fallback to RSS
        logger.info("API returned no matches, falling back to RSS")
        results, live, upcoming = build_from_rss()
        
        if results or live or upcoming:
            if results:
                lines.append("🏁 **RESULTS**")
                for r in results[:5]:
                    lines.append(r)
                lines.append("")
            if live:
                lines.append("🔴 **LIVE MATCHES**")
                for l in live[:3]:
                    lines.append(l)
                lines.append("")
            if upcoming:
                lines.append("⏳ **UPCOMING FIXTURES**")
                for u in upcoming[:5]:
                    lines.append(u)
                lines.append("")
            lines.append("⚽ *Data sourced from BBC, Sky, and Guardian RSS feeds.*")
        else:
            lines.append("No matches scheduled for today.")
            lines.append("")
            lines.append("📅 **UPCOMING WORLD CUP FIXTURES:**")
            lines.append("• June 19: Group A & B matches")
            lines.append("• June 20: Group C & D matches")
            lines.append("• June 21: Group E & F matches")
            lines.append("• June 22: Group G & H matches")

    lines.append("\n📲 @wcupdates2026")
    return "\n".join(lines)

# ---------- SEND ----------
def send_briefing():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            if f.read().strip() == datetime.datetime.utcnow().strftime("%Y-%m-%d"):
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
        resp = requests.post(url, json=payload)
        if resp.status_code == 200:
            logger.info("✅ Briefing sent successfully!")
            with open(STATE_FILE, "w") as f:
                f.write(datetime.datetime.utcnow().strftime("%Y-%m-%d"))
        else:
            logger.error(f"Telegram failed: {resp.text}")
    except Exception as e:
        logger.error(f"Send error: {e}")

if __name__ == "__main__":
    send_briefing()
