import os
import requests
import datetime
import logging
import sys
import json

# Logging setup – we want everything in the Actions log
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ---------- Environment variables ----------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
API_KEY = os.environ.get("FOOTBALL_DATA_KEY") or os.environ.get("FOOTBALLDATAKEY")

if not BOT_TOKEN or not CHAT_ID:
    logger.error("BOT_TOKEN or CHAT_ID missing.")
    sys.exit(1)

if not API_KEY:
    logger.error("No API key found. Check secret name (FOOTBALL_DATA_KEY or FOOTBALLDATAKEY).")
    sys.exit(1)

logger.info(f"API key found (length: {len(API_KEY)})")

# ---------- API configuration ----------
BASE_URL = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": API_KEY}

def get_world_cup_competition_id():
    """Find the FIFA World Cup competition ID dynamically."""
    url = f"{BASE_URL}/competitions"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            competitions = resp.json().get("competitions", [])
            logger.info(f"Fetched {len(competitions)} competitions.")
            for comp in competitions:
                name = comp.get("name", "")
                code = comp.get("code", "")
                logger.info(f"Competition: {name} ({code}) - ID: {comp['id']}")
                # Look for World Cup 2026
                if "world cup" in name.lower() and "2026" in code.upper():
                    return comp["id"]
                if "fifa world cup" in name.lower():
                    return comp["id"]
            # Fallback: any "World Cup"
            for comp in competitions:
                if "world cup" in comp.get("name", "").lower():
                    return comp["id"]
        else:
            logger.error(f"Failed to fetch competitions: {resp.status_code} - {resp.text[:200]}")
    except Exception as e:
        logger.error(f"Failed to fetch competitions: {e}")
    # Hardcoded fallback – often 2000 for men's World Cup
    logger.warning("Using fallback competition ID 2000")
    return 2000

WC_COMPETITION_ID = get_world_cup_competition_id()
logger.info(f"Using competition ID: {WC_COMPETITION_ID}")

def fetch_matches(competition_id=None, date_from=None, date_to=None):
    url = f"{BASE_URL}/matches"
    params = {}
    if competition_id:
        params["competitions"] = competition_id
    if date_from:
        params["dateFrom"] = date_from
    if date_to:
        params["dateTo"] = date_to
    logger.info(f"Fetching matches with params: {params}")
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        logger.info(f"API response status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            matches = data.get("matches", [])
            logger.info(f"Fetched {len(matches)} matches for date range {date_from} to {date_to}")
            # Log a sample if any
            if matches:
                logger.info(f"Sample match: {matches[0].get('homeTeam',{}).get('name')} vs {matches[0].get('awayTeam',{}).get('name')}")
            else:
                logger.warning("No matches returned.")
            return matches
        else:
            logger.error(f"API error {resp.status_code}: {resp.text[:500]}")
            return []
    except Exception as e:
        logger.error(f"Request failed: {e}")
        return []

def fetch_standings(competition_id):
    url = f"{BASE_URL}/competitions/{competition_id}/standings"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            standings = data.get("standings", [])
            if standings:
                return standings[0].get("table", [])
        return []
    except Exception as e:
        logger.error(f"Standings error: {e}")
        return []

def fetch_top_scorers(competition_id):
    url = f"{BASE_URL}/competitions/{competition_id}/scorers"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            return resp.json().get("scorers", [])
        return []
    except Exception as e:
        logger.error(f"Scorers error: {e}")
        return []

def format_match(match):
    home = match["homeTeam"]["name"]
    away = match["awayTeam"]["name"]
    score = match.get("score", {})
    full_time = score.get("fullTime", {})
    home_goals = full_time.get("home") if full_time else None
    away_goals = full_time.get("away") if full_time else None
    if home_goals is not None and away_goals is not None:
        return f"{home} {home_goals} – {away_goals} {away}"
    else:
        return f"{home} vs {away}"

def get_status_emoji(status):
    mapping = {
        "FINISHED": "✅",
        "LIVE": "🟢",
        "SCHEDULED": "⏳",
        "POSTPONED": "⏸️",
        "CANCELLED": "🚫"
    }
    return mapping.get(status, "⚪")

def build_briefing():
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    logger.info(f"Building briefing for {today}")

    # First try: fetch directly by competition ID
    wc_matches = fetch_matches(competition_id=WC_COMPETITION_ID, date_from=today, date_to=today)

    if not wc_matches:
        # Second try: fetch all matches and filter by competition name
        logger.info("No matches found for competition ID, trying all matches filter")
        all_matches = fetch_matches(date_from=today, date_to=today)
        if not all_matches:
            logger.error("No matches at all today (any competition).")
            return "No matches found today."

        # Filter by competition name
        for m in all_matches:
            comp = m.get("competition", {})
            comp_name = comp.get("name", "")
            if "World Cup" in comp_name or "FIFA" in comp_name or comp.get("id") == WC_COMPETITION_ID:
                wc_matches.append(m)

        if not wc_matches:
            logger.error(f"Found matches but none are World Cup. Competitions seen: {set(m.get('competition',{}).get('name') for m in all_matches)}")
            return "No World Cup matches today."

    # Categorise
    completed = [m for m in wc_matches if m["status"] == "FINISHED"]
    live      = [m for m in wc_matches if m["status"] == "LIVE"]
    upcoming  = [m for m in wc_matches if m["status"] == "SCHEDULED"]

    standings = fetch_standings(WC_COMPETITION_ID)
    scorers = fetch_top_scorers(WC_COMPETITION_ID)

    lines = []
    lines.append("🌍 *WORLD CUP DAILY BRIEFING*")
    lines.append(f"📅 {today}\n")

    lines.append("🏁 *COMPLETED MATCHES*")
    if completed:
        for m in completed[:5]:
            lines.append(f"{get_status_emoji('FINISHED')} {format_match(m)}")
    else:
        lines.append("_No completed matches today._")
    lines.append("")

    if live:
        lines.append("🟢 *LIVE MATCHES*")
        for m in live:
            elapsed = m.get("minute", "LIVE")
            lines.append(f"{get_status_emoji('LIVE')} {format_match(m)} ({elapsed}')")
        lines.append("")
    else:
        lines.append("🟢 *No live matches.*\n")

    lines.append("⏳ *UPCOMING MATCHES*")
    if upcoming:
        for m in upcoming[:5]:
            utc_time = m["utcDate"].split("T")[1][:5]
            lines.append(f"{get_status_emoji('SCHEDULED')} {format_match(m)} – {utc_time} UTC")
    else:
        lines.append("_No upcoming matches._")
    lines.append("")

    lines.append("🏆 *GROUP STANDINGS*")
    if standings:
        for i, team in enumerate(standings[:5], 1):
            name = team.get("team", {}).get("name", "Unknown")
            points = team.get("points", 0)
            lines.append(f"{i}. {name} – {points} pts")
    else:
        lines.append("_Standings not available._")
    lines.append("")

    lines.append("⚽ *TOP SCORERS*")
    if scorers:
        for i, scorer in enumerate(scorers[:5], 1):
            name = scorer.get("player", {}).get("name", "Unknown")
            goals = scorer.get("goals", 0)
            team = scorer.get("team", {}).get("name", "")
            lines.append(f"{i}. {name} – {goals} goals ({team})")
    else:
        lines.append("_Top scorers not available._")
    lines.append("")

    if upcoming:
        m = upcoming[0]
        home = m["homeTeam"]["name"]
        away = m["awayTeam"]["name"]
        time_str = m["utcDate"].split("T")[1][:5]
        lines.append(f"🔥 *MATCH TO WATCH* – {home} vs {away}")
        lines.append(f"🕒 {time_str} UTC")
    else:
        lines.append("🔥 *No upcoming match to highlight today*")

    lines.append("\n🏆 *FIFA WORLD CUP 2026*")
    lines.append("📲 @wcupdates2026")
    return "\n".join(lines)

def send_briefing():
    try:
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
        resp = requests.post(url, json=payload)
        if resp.status_code == 200:
            logger.info("Briefing sent.")
        else:
            logger.error(f"Failed to send: {resp.text}")
    except Exception as e:
        logger.error(f"Error sending: {e}")

if __name__ == "__main__":
    send_briefing()
