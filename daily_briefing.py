import os
import requests
import datetime
import logging
import sys
import feedparser
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
API_KEY = os.environ.get("FOOTBALL_DATA_KEY") or os.environ.get("FOOTBALLDATAKEY")

if not BOT_TOKEN or not CHAT_ID:
    logger.error("BOT_TOKEN or CHAT_ID missing.")
    sys.exit(1)

STATE_FILE = "daily_briefing_state.txt"

# ---------- API configuration ----------
BASE_URL_FD = "https://api.football-data.org/v4"
HEADERS_FD = {"X-Auth-Token": API_KEY} if API_KEY else {}

WC_API_BASE = "https://worldcup26.ir"  # Free dedicated WC 2026 API

def get_wc_matches():
    """Fetch from dedicated World Cup 2026 API (preferred)."""
    try:
        # Today's and tomorrow's matches
        today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        resp = requests.get(f"{WC_API_BASE}/get/games", timeout=15)
        if resp.status_code == 200:
            all_matches = resp.json()
            # Filter for today/tomorrow (adjust based on actual response structure)
            relevant = [m for m in all_matches if today in m.get("date", "")]
            return relevant
    except Exception as e:
        logger.warning(f"WC dedicated API failed: {e}")
    return []

def fetch_matches_fd(date_from, date_to):
    """Fallback to Football-Data.org."""
    if not API_KEY:
        return []
    try:
        url = f"{BASE_URL_FD}/matches"
        params = {"competitions": "WC", "dateFrom": date_from, "dateTo": date_to}  # Use code 'WC'
        resp = requests.get(url, headers=HEADERS_FD, params=params, timeout=15)
        if resp.status_code == 200:
            return resp.json().get("matches", [])
    except Exception as e:
        logger.error(f"FD API failed: {e}")
    return []

def fetch_standings():
    """Try dedicated API then FD."""
    try:
        resp = requests.get(f"{WC_API_BASE}/get/groups", timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    # FD fallback
    if API_KEY:
        try:
            resp = requests.get(f"{BASE_URL_FD}/competitions/WC/standings", headers=HEADERS_FD, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("standings", [])
        except:
            pass
    return []

# ---------- Formatting ----------
def format_match_detailed(m):
    """Rich match formatting with time/venue."""
    home = m.get("homeTeam", {}).get("name") or m.get("home", "TBD")
    away = m.get("awayTeam", {}).get("name") or m.get("away", "TBD")
    date_str = m.get("utcDate") or m.get("date", "")
    venue = m.get("venue", {}).get("name") or m.get("stadium", "TBD")
    
    score = ""
    if m.get("score"):
        ft = m["score"].get("fullTime", {})
        if ft.get("home") is not None:
            score = f" {ft.get('home')}-{ft.get('away')} "
    
    time_info = f"({date_str} • {venue})" if venue != "TBD" else ""
    return f"• **{home}**{score}**{away}** {time_info}"

def build_briefing():
    today_str = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    lines = []
    lines.append("🌍 **WORLD CUP DAILY BRIEFING**")
    lines.append(f"📅 {today_str} (ET times)\n")

    # Fetch data
    matches = get_wc_matches() or fetch_matches_fd(today_str, today_str)
    
    if matches:
        completed = [m for m in matches if m.get("status") in ["FINISHED", "FT"]]
        live = [m for m in matches if m.get("status") in ["LIVE", "IN_PLAY"]]
        upcoming = [m for m in matches if m.get("status") in ["SCHEDULED", "TIMED"]]

        standings = fetch_standings()

        if completed:
            lines.append("🏁 **RESULTS**")
            for m in completed[:6]:
                lines.append(format_match_detailed(m))
            lines.append("")

        if live:
            lines.append("🔴 **LIVE**")
            for m in live:
                lines.append(format_match_detailed(m))
            lines.append("")

        if upcoming:
            lines.append("⏳ **TODAY'S KEY FIXTURES**")
            for m in upcoming[:8]:
                lines.append(format_match_detailed(m))
            lines.append("")

        if standings:
            lines.append("🏆 **GROUP STANDINGS** (Top teams)")
            # Adapt based on actual structure
            for group in standings[:4]:  # Example
                lines.append(f"**Group {group.get('group', '')}**")
                for team in group.get("table", [])[:4]:
                    name = team.get("team", {}).get("name", team.get("name", "TBD"))
                    pts = team.get("points", 0)
                    lines.append(f"  • {name} — {pts} pts")
            lines.append("")

        lines.append("\n🏆 **FIFA World Cup 2026**")
        lines.append("Stay tuned for live updates! ⚽")
        lines.append("📲 Follow for more")
    else:
        # RSS fallback (kept but simplified)
        lines.append("No matches found via primary APIs. Checking news...")
        # (Your original RSS logic can be called here if needed)

    return "\n".join(lines)

# ---------- Send ----------
def send_briefing():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            if f.read().strip() == datetime.datetime.utcnow().strftime("%Y-%m-%d"):
                logger.info("Already sent today – skipping.")
                return

    text = build_briefing()
    if not text or len(text) < 50:
        logger.warning("Empty briefing – skipping.")
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
            logger.error(f"Telegram error: {resp.text}")
    except Exception as e:
        logger.error(f"Send failed: {e}")

if __name__ == "__main__":
    send_briefing()
