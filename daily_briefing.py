import os
import requests
import datetime
import logging
import sys
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    logger.error("BOT_TOKEN or CHAT_ID missing.")
    sys.exit(1)

# ---------- State file for duplicate protection ----------
STATE_FILE = "daily_briefing_state.txt"

# ---------- Fotmob API (unofficial – used as primary) ----------
FOTMOB_BASE = "https://www.fotmob.com/api"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# ---------- Timezone helper (UTC to WAT) ----------
def utc_to_wat(utc_time_str):
    """
    Convert UTC time string (HH:MM) to WAT (UTC+1).
    If time_str is invalid, return original.
    """
    try:
        hour, minute = map(int, utc_time_str.split(":"))
        hour += 1
        if hour >= 24:
            hour -= 24
        return f"{hour:02d}:{minute:02d} WAT"
    except:
        return utc_time_str

# ---------- Dynamic league discovery ----------
def discover_league_id():
    """Find the FIFA World Cup league ID dynamically."""
    try:
        resp = requests.get(f"{FOTMOB_BASE}/leagues", headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            for league in data:
                name = league.get("name", "")
                if "World Cup" in name or "FIFA" in name:
                    logger.info(f"Found league: {name} (ID: {league['id']})")
                    return league["id"]
    except Exception as e:
        logger.error(f"League discovery failed: {e}")
    # Fallback – known World Cup ID (men's)
    return 42

WC_LEAGUE_ID = discover_league_id()
logger.info(f"Using league ID: {WC_LEAGUE_ID}")

# ---------- Fetch matches ----------
def fetch_matches_by_date(date_str):
    """Fetch matches for a given date using /matchlist endpoint."""
    url = f"{FOTMOB_BASE}/matchlist"
    params = {"date": date_str}
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            all_matches = []
            for league_entry in data.get("matches", []):
                if league_entry.get("id") == WC_LEAGUE_ID:
                    all_matches.extend(league_entry.get("matches", []))
            return all_matches
        else:
            logger.error(f"Fotmob error: {resp.status_code}")
            return []
    except Exception as e:
        logger.error(f"Request failed: {e}")
        return []

# ---------- Formatting (plain text, no Markdown) ----------
def format_match(m):
    """Format a match as plain text (no Markdown)."""
    home = m["home"]["name"]
    away = m["away"]["name"]
    status = m.get("status", {})
    time_info = m.get("time", {})

    if status.get("finished", False):
        hg = m["home"]["score"]
        ag = m["away"]["score"]
        return f"{home} {hg}-{ag} {away}"

    elif status.get("live", False):
        hg = m["home"]["score"]
        ag = m["away"]["score"]
        minute = status.get("minute", "LIVE")
        return f"{home} {hg}-{ag} {away} ({minute}')"

    else:
        # Upcoming – show time in WAT
        utc_time = time_info.get("utcTime", "").split("T")[1][:5]
        wat_time = utc_to_wat(utc_time)
        return f"{home} vs {away} – {wat_time}"

# ---------- Sort upcoming by kickoff time ----------
def get_match_timestamp(m):
    """Return UTC timestamp for sorting."""
    time_info = m.get("time", {})
    utc_time = time_info.get("utcTime", "")
    if utc_time:
        try:
            # Convert ISO to datetime
            dt = datetime.datetime.fromisoformat(utc_time.replace("Z", "+00:00"))
            return dt.timestamp()
        except:
            pass
    return 0

# ---------- Build the briefing ----------
def build_briefing():
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")

    # Check state file – if we already sent today, skip
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            last_run = f.read().strip()
        if last_run == today:
            logger.info("Briefing already sent today – skipping.")
            return None

    matches = fetch_matches_by_date(today)
    if not matches:
        # Try tomorrow
        tomorrow = (datetime.datetime.utcnow() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        matches = fetch_matches_by_date(tomorrow)
        if not matches:
            return "No World Cup matches today or tomorrow."

    # Categorise
    results = [m for m in matches if m.get("status", {}).get("finished", False)]
    live = [m for m in matches if m.get("status", {}).get("live", False)]
    upcoming = [m for m in matches if not m.get("status", {}).get("finished", False) and not m.get("status", {}).get("live", False)]

    # Sort upcoming by kickoff time
    upcoming.sort(key=get_match_timestamp)

    lines = []

    # ---------- Results ----------
    if results:
        lines.append("🏁 RESULTS")
        for m in results[:5]:
            lines.append(format_match(m))
        lines.append("")

    # ---------- Live ----------
    if live:
        lines.append("🔴 LIVE")
        for m in live[:3]:
            lines.append(format_match(m))
        lines.append("")

    # ---------- Next Match ----------
    if upcoming:
        lines.append("🔥 NEXT MATCH")
        lines.append(format_match(upcoming[0]))
    else:
        lines.append("🔥 No upcoming matches today.")

    # ---------- Tournament storyline (optional) ----------
    # If we have results, add a simple story
    if results:
        first_result = results[0]
        home = first_result["home"]["name"]
        away = first_result["away"]["name"]
        hg = first_result["home"]["score"]
        ag = first_result["away"]["score"]
        if hg > ag:
            lines.append(f"\n📝 {home} opened their campaign with a {hg}-{ag} win over {away}.")
        elif hg < ag:
            lines.append(f"\n📝 {away} defeated {home} {ag}-{hg} in today's match.")
        else:
            lines.append(f"\n📝 {home} and {away} shared the points in a {hg}-{ag} draw.")

    lines.append("\n🏆 FIFA WORLD CUP 2026")
    lines.append("📲 @wcupdates2026")

    return "\n".join(lines)

# ---------- Send the briefing ----------
def send_briefing():
    try:
        text = build_briefing()
        if text is None:
            logger.info("Skipped – already sent today.")
            return
        if not text:
            logger.warning("No text to send.")
            return

        # Send as plain text (no Markdown)
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": None,   # plain text
            "disable_web_page_preview": True
        }
        resp = requests.post(url, json=payload)
        if resp.status_code == 200:
            logger.info("Briefing sent.")
            # Save state
            today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
            with open(STATE_FILE, "w") as f:
                f.write(today)
        else:
            logger.error(f"Failed to send: {resp.text}")
    except Exception as e:
        logger.error(f"Error sending: {e}")

if __name__ == "__main__":
    send_briefing()
