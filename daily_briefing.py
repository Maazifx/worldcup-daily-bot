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

# ---------- WORLD CUP 2026 TEAMS (48) ----------
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
        hour, minute = map(int, utc_time_str.split(":"))
        hour = (hour + 1) % 24
        return f"{hour:02d}:{minute:02d} WAT"
    except Exception:
        return utc_time_str

def parse_time_from_text(text):
    match = re.search(r'(\d{1,2}):(\d{2})', text)
    if match:
        return f"{int(match.group(1)):02d}:{match.group(2)}"
    return None

# ---------- API ----------
WC_API_BASE = "https://worldcup26.ir"

def get_today_matches():
    try:
        resp = requests.get(f"{WC_API_BASE}/get/games", timeout=15, verify=False)
        if resp.status_code != 200:
            return []
        data = resp.json()
        
        # Get UTC dates in both YYYY-MM-DD and components to bypass dynamic string variants
        now = datetime.datetime.utcnow()
        today_iso = now.strftime("%Y-%m-%d")
        today_alt = now.strftime("%d/%m/%Y") 
        
        all_games = data.get("games", [])
        today_matches = []
        for g in all_games:
            local_date = str(g.get("local_date", ""))
            # Handle both common format paradigms (YYYY-MM-DD and DD/MM/YYYY)
            if today_iso in local_date or today_alt in local_date or local_date.replace('/', '-')[:10] == today_iso:
                today_matches.append(g)
        return today_matches
    except Exception as e:
        logger.warning(f"API failed: {e}")
        return []

# ---------- RSS FALLBACK ----------
RSS_FEEDS = {
    "BBC Sport": "https://feeds.bbci.co.uk/sport/football/rss.xml",
    "Sky Sports": "https://www.skysports.com/rss/12040",
    "Guardian": "https://www.theguardian.com/football/rss",
}

def fetch_articles_from_feed(url):
    try:
        feed = feedparser.parse(url, request_headers={"User-Agent": "Mozilla/5.0"})
        return feed.entries[:30] if hasattr(feed, 'entries') else []
    except Exception as e:
        logger.error(f"RSS failed for {url}: {e}")
        return []

def is_valid_team(name):
    return name in WORLD_CUP_TEAMS

def extract_match_info(text):
    # Match pattern: Team 1 2-1 Team 2
    pattern = r'([A-Za-z\s\.]+)\s+(\d+)\s*[-:;]\s*(\d+)\s+([A-Za-z\s\.]+)'
    matches = re.findall(pattern, text, re.IGNORECASE)
    for home, hg, ag, away in matches:
        home = home.strip()
        away = away.strip()
        if is_valid_team(home) and is_valid_team(away):
            score = f"{hg}-{ag}"
            time_str = parse_time_from_text(text)
            return (home, away, score, time_str)
    
    # Match pattern: Team 1 vs Team 2
    pattern2 = r'([A-Za-z\s\.]+)\s+v(?:s)?\.?\s+([A-Za-z\s\.]+)'
    matches2 = re.findall(pattern2, text, re.IGNORECASE)
    for home, away in matches2:
        home = home.strip()
        away = away.strip()
        if is_valid_team(home) and is_valid_team(away):
            time_str = parse_time_from_text(text)
            return (home, away, None, time_str)
    
    return (None, None, None, None)

def is_live(text):
    return any(kw in text.lower() for kw in ["live", "minute", "half-time", "updates"])

def is_finished(text):
    return any(kw in text.lower() for kw in ["full-time", "result", "final", "wins", "beat", "defeat", "draw"])

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
        return {"results": [], "live": [], "upcoming": []}
    
    seen = set()
    results, live, upcoming = [], [], []
    for art in all_articles:
        text = art["title"] + " " + art["summary"]
        home, away, score, time_str = extract_match_info(text)
        if not home or not away:
            continue
        key = f"{home}_{away}_{score}"
        if key in seen:
            continue
        seen.add(key)
        
        entry = {"home": home, "away": away, "score": score, "time": time_str, "source": art["source"]}
        if score and is_finished(text):
            results.append(entry)
        elif is_live(text):
            live.append(entry)
        else:
            upcoming.append(entry)
    
    def dedup(lst):
        seen2 = set()
        out = []
        for item in lst:
            k = f"{item['home']}_{item['away']}"
            if k not in seen2:
                seen2.add(k)
                out.append(item)
        return out
    
    return {"results": dedup(results), "live": dedup(live), "upcoming": dedup(upcoming)}

def format_match_line(home, away, score=None, time=None, extra=""):
    flag_home = get_flag(home)
    flag_away = get_flag(away)
    score_part = f" *{score}*" if score else ""
    time_part = f" 🕒 {time}" if time else ""
    # Clean up names for safe markdown presentation (removes illegal formatting markers)
    clean_home = home.replace('_', '\\_').replace('*', '')
    clean_away = away.replace('_', '\\_').replace('*', '')
    return f"{flag_home} {clean_home}{score_part} {flag_away} {clean_away}{time_part}{extra}"

def build_briefing():
    today = datetime.datetime.utcnow()
    today_str = today.strftime("%d %B %Y")
    time_wat = utc_to_wat(today.strftime("%H:%M"))

    lines = [
        "🌎 *FIFA WORLD CUP 2026 DAILY BRIEFING*",
        "",
        f"📅 {today_str}",
        f"🕒 {time_wat}",
        "━━━━━━━━━━━━━━"
    ]

    matches = get_today_matches()
    if matches:
        completed = [m for m in matches if str(m.get("finished")).upper() == "TRUE"]
        live_now = [m for m in matches if str(m.get("finished")).upper() != "TRUE" and m.get("status") == "live"]
        upcoming = [m for m in matches if str(m.get("finished")).upper() != "TRUE" and m.get("status") != "live"]

        if completed:
            lines.append("🏁 *RESULTS*")
            for m in completed[:5]:
                home = m.get("home_team_name_en", "TBD")
                away = m.get("away_team_name_en", "TBD")
                hg = m.get("home_score", 0)
                ag = m.get("away_score", 0)
                lines.append(format_match_line(home, away, score=f"{hg}-{ag}"))
            lines.append("━━━━━━━━━━━━━━")
        
        if live_now:
            lines.append("🔴 *LIVE NOW*")
            for m in live_now[:3]:
                home = m.get("home_team_name_en", "TBD")
                away = m.get("away_team_name_en", "TBD")
                hg = m.get("home_score", 0)
                ag = m.get("away_score", 0)
                minute = m.get("minute", "")
                lines.append(format_match_line(home, away, score=f"{hg}-{ag}", extra=f" ({minute}')"))
            lines.append("━━━━━━━━━━━━━━")
        
        if upcoming:
            lines.append("📅 *TODAY'S FIXTURES*")
            for m in upcoming[:5]:
                home = m.get("home_team_name_en", "TBD")
                away = m.get("away_team_name_en", "TBD")
                time_str = m.get("local_date", "")
                if " " in time_str:
                    time_part = time_str.split(" ")[-1]
                    # Ensure only a valid time pattern is converted
                    if ":" in time_part:
                        time_part = utc_to_wat(time_part[:5])
                else:
                    time_part = ""
                lines.append(format_match_line(home, away, time=time_part))
            lines.append("━━━━━━━━━━━━━━")
        
        if upcoming:
            m = upcoming[0]
            home = m.get("home_team_name_en", "TBD")
            away = m.get("away_team_name_en", "TBD")
            lines.append("⭐ *MATCH TO WATCH*")
            lines.append(format_match_line(home, away))
            lines.append("")
            lines.append(f"A victory would move {home} closer to the Round of 16 while {away} look to pull off an upset.")
            lines.append("━━━━━━━━━━━━━━")
        
        lines.append("🏆 *FIFA WORLD CUP 2026*")
        lines.append("📲 @wcupdates2026")
        return "\n".join(lines)

    logger.info("API returned no matches, falling back to RSS")
    data = build_from_rss()
    results = data.get("results", [])
    live = data.get("live", [])
    upcoming = data.get("upcoming", [])

    if results or live or upcoming:
        if results:
            lines.append("🏁 *RESULTS*")
            for r in results[:5]:
                lines.append(format_match_line(r["home"], r["away"], score=r["score"]))
            lines.append("━━━━━━━━━━━━━━")
        if live:
            lines.append("🔴 *LIVE NOW*")
            for l in live[:3]:
                lines.append(format_match_line(l["home"], l["away"], extra=" (LIVE)"))
            lines.append("━━━━━━━━━━━━━━")
        if upcoming:
            lines.append("📅 *TODAY'S FIXTURES*")
            for u in upcoming[:5]:
                time_part = u["time"] if u["time"] else ""
                if time_part:
                    time_part = utc_to_wat(time_part)
                lines.append(format_match_line(u["home"], u["away"], time=time_part))
            lines.append("━━━━━━━━━━━━━━")
        if upcoming:
            u = upcoming[0]
            lines.append("⭐ *MATCH TO WATCH*")
            lines.append(format_match_line(u["home"], u["away"]))
            lines.append("")
            lines.append(f"A victory would move {u['home']} closer to the Round of 16 while {u['away']} look to pull off an upset.")
            lines.append("━━━━━━━━━━━━━━")
        
        lines.append("⚽ _Data sourced from BBC, Sky, and Guardian RSS feeds._")
    else:
        lines.append("No matches scheduled for today.")
        lines.append("")
        lines.append("📅 *UPCOMING WORLD CUP FIXTURES:*")
        lines.append("• June 19: Group A & B matches")
        lines.append("• June 20: Group C & D matches")
        lines.append("• June 21: Group E & F matches")
        lines.append("• June 22: Group G & H matches")
        lines.append("━━━━━━━━━━━━━━")

    lines.append("🏆 *FIFA WORLD CUP 2026*")
    lines.append("📲 @wcupdates2026")
    return "\n".join(lines)

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
