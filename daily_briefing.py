import os
import requests
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

# Fotmob base URL (unofficial public API)
FOTMOB_BASE = "https://www.fotmob.com/api"

# Known FIFA World Cup league ID on Fotmob (men's)
# We can also fetch dynamically if needed
WC_LEAGUE_ID = 42   # FIFA World Cup

def get_league_id_by_name(name_fragment):
    """Fetch all leagues and find one matching 'World Cup'."""
    try:
        resp = requests.get(f"{FOTMOB_BASE}/leagues", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            for league in data:
                if name_fragment.lower() in league.get("name", "").lower():
                    return league["id"]
    except:
        pass
    return None

# Optionally, you can dynamically find the ID to be safe
# But 42 works for World Cup
# You can uncomment the next line to override
# WC_LEAGUE_ID = get_league_id_by_name("World Cup") or 42

def fetch_matches_by_date(date_str):
    """Fetch all matches for a given date (YYYY-MM-DD)."""
    url = f"{FOTMOB_BASE}/matches"
    params = {"date": date_str}
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            # The response is a list of matches grouped by league
            # We need to filter for our league
            all_matches = []
            for league in data.get("matches", []):
                if league.get("id") == WC_LEAGUE_ID:
                    all_matches.extend(league.get("matches", []))
            return all_matches
        else:
            logger.error(f"Fotmob error: {resp.status_code}")
            return []
    except Exception as e:
        logger.error(f"Fotmob request failed: {e}")
        return []

def format_match(m):
    home = m["home"]["name"]
    away = m["away"]["name"]
    status = m.get("status", {})
    # Check if finished or live
    if status.get("finished", False):
        # Get scores
        hg = m["home"]["score"]
        ag = m["away"]["score"]
        return f"{home} {hg}-{ag} {away}"
    elif status.get("live", False):
        hg = m["home"]["score"]
        ag = m["away"]["score"]
        minute = status.get("minute", "LIVE")
        return f"{home} {hg}-{ag} {away} ({minute}')"
    else:
        # Not started – show only teams and time
        time_str = m.get("time", {}).get("utcTime", "").split("T")[1][:5]
        return f"{home} vs {away} – {time_str} UTC"

def build_briefing():
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    matches = fetch_matches_by_date(today)
    if not matches:
        # If no matches today, look for tomorrow
        tomorrow = (datetime.datetime.utcnow() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        matches = fetch_matches_by_date(tomorrow)
        if not matches:
            return "No World Cup matches today or tomorrow."

    # Categorise
    results = []
    live = []
    upcoming = []
    for m in matches:
        status = m.get("status", {})
        if status.get("finished", False):
            results.append(m)
        elif status.get("live", False):
            live.append(m)
        else:
            upcoming.append(m)

    lines = []
    if results:
        lines.append("🏁 RESULTS")
        for m in results[:5]:
            lines.append(format_match(m))
        lines.append("")
    if live:
        lines.append("🔴 LIVE")
        for m in live[:3]:
            lines.append(format_match(m))
        lines.append("")
    if upcoming:
        lines.append("🔥 NEXT MATCH")
        # Show the first upcoming match
        lines.append(format_match(upcoming[0]))
    else:
        lines.append("🔥 No upcoming matches today.")

    lines.append("\n🏆 FIFA WORLD CUP 2026")
    lines.append("📲 @wcupdates2026")
    return "\n".join(lines)

def send_briefing():
    try:
        text = build_briefing()
        if not text:
            logger.warning("No content.")
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
