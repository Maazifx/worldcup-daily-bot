import os
import requests
import json
import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
API_KEY = os.environ.get("FOOTBALL_DATA_KEY")

# Football-Data.org configuration
BASE_URL = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": API_KEY}

# World Cup competition ID – men's World Cup is 2000
# If that doesn't work, we'll try to search for it.
WC_COMPETITION_ID = 2000

# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------
def fetch_matches(competition_id=None, date_from=None, date_to=None):
    """Fetch matches for a given competition and date range."""
    url = f"{BASE_URL}/matches"
    params = {}
    if competition_id:
        params["competitions"] = competition_id
    if date_from:
        params["dateFrom"] = date_from
    if date_to:
        params["dateTo"] = date_to

    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("matches", [])
        else:
            logger.error(f"API error: {resp.status_code} - {resp.text}")
            return []
    except Exception as e:
        logger.error(f"Request failed: {e}")
        return []

def fetch_standings(competition_id):
    """Fetch standings for a competition."""
    url = f"{BASE_URL}/competitions/{competition_id}/standings"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            # standings is a list of tables; we take the first (overall)
            standings = data.get("standings", [])
            if standings:
                return standings[0].get("table", [])
        return []
    except Exception as e:
        logger.error(f"Standings error: {e}")
        return []

def fetch_top_scorers(competition_id):
    """Fetch top scorers for a competition."""
    url = f"{BASE_URL}/competitions/{competition_id}/scorers"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("scorers", [])
        return []
    except Exception as e:
        logger.error(f"Scorers error: {e}")
        return []

def format_match(match):
    home = match["homeTeam"]["name"]
    away = match["awayTeam"]["name"]
    # Score might be null if not played
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

# ----------------------------------------------------------------------
# Build the briefing
# ----------------------------------------------------------------------
def build_briefing():
    if not API_KEY:
        return "❌ FOOTBALL_DATA_KEY secret is not set."

    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    # Fetch matches for today (any competition, but we'll filter World Cup later)
    all_matches = fetch_matches(date_from=today, date_to=today)

    if not all_matches:
        return "No matches found today."

    # Filter only World Cup matches (competition ID 2000 or name contains "World Cup")
    wc_matches = []
    for m in all_matches:
        comp = m.get("competition", {})
        comp_name = comp.get("name", "")
        if "World Cup" in comp_name or "FIFA" in comp_name or comp.get("id") == WC_COMPETITION_ID:
            wc_matches.append(m)

    if not wc_matches:
        # Fallback: try with the competition ID directly
        wc_matches = fetch_matches(competition_id=WC_COMPETITION_ID, date_from=today, date_to=today)
        if not wc_matches:
            return "No World Cup matches today."

    # Categorise by status
    completed = [m for m in wc_matches if m["status"] == "FINISHED"]
    live      = [m for m in wc_matches if m["status"] == "LIVE"]
    upcoming  = [m for m in wc_matches if m["status"] == "SCHEDULED"]

    # Fetch standings and top scorers
    standings = fetch_standings(WC_COMPETITION_ID)
    scorers = fetch_top_scorers(WC_COMPETITION_ID)

    # Build message
    lines = []
    lines.append("🌍 *WORLD CUP DAILY BRIEFING*")
    lines.append(f"📅 {today}\n")

    # Completed matches
    lines.append("🏁 *COMPLETED MATCHES*")
    if completed:
        for m in completed[:5]:
            lines.append(f"{get_status_emoji('FINISHED')} {format_match(m)}")
    else:
        lines.append("_No completed matches today._")
    lines.append("")

    # Live matches
    if live:
        lines.append("🟢 *LIVE MATCHES*")
        for m in live:
            # Show elapsed minutes if available
            elapsed = m.get("minute") or ""
            lines.append(f"{get_status_emoji('LIVE')} {format_match(m)} ({elapsed}')")
        lines.append("")
    else:
        lines.append("🟢 *No live matches.*")
        lines.append("")

    # Upcoming matches
    lines.append("⏳ *UPCOMING MATCHES*")
    if upcoming:
        for m in upcoming[:5]:
            # UTC time
            utc_time = m["utcDate"].split("T")[1][:5]
            lines.append(f"{get_status_emoji('SCHEDULED')} {format_match(m)} – {utc_time} UTC")
    else:
        lines.append("_No upcoming matches._")
    lines.append("")

    # Group standings
    lines.append("🏆 *GROUP STANDINGS*")
    if standings:
        # Show top 2 of each group? Usually standings[0] is the table.
        # If there are multiple groups, we can show them.
        # For simplicity, show the top 5 overall.
        for i, team in enumerate(standings[:5], 1):
            name = team.get("team", {}).get("name", "Unknown")
            points = team.get("points", 0)
            lines.append(f"{i}. {name} – {points} pts")
    else:
        lines.append("_Standings not available._")
    lines.append("")

    # Top scorers
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

    # Match to watch (the first upcoming)
    if upcoming:
        m = upcoming[0]
        home = m["homeTeam"]["name"]
        away = m["awayTeam"]["name"]
        time_str = m["utcDate"].split("T")[1][:5]
        lines.append(f"🔥 *MATCH TO WATCH* – {home} vs {away}")
        lines.append(f"🕒 {time_str} UTC")
    else:
        lines.append("🔥 *No upcoming match to highlight today*")

    # Footer
    lines.append("\n🏆 *FIFA WORLD CUP 2026*")
    lines.append("📲 @wcupdates2026")

    return "\n".join(lines)

# ----------------------------------------------------------------------
# Send the briefing
# ----------------------------------------------------------------------
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
            logger.error(f"Failed: {resp.text}")

    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    send_briefing()
