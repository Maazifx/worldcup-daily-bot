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
API_KEY = os.environ.get("FOOTBALL_DATA_KEY")  # Optional fallback

if not BOT_TOKEN or not CHAT_ID:
    logger.error("BOT_TOKEN or CHAT_ID missing.")
    sys.exit(1)

STATE_FILE = "daily_briefing_state.txt"

# ---------- APIs ----------
WC_API_BASE = "https://worldcup26.ir"

def get_today_matches():
    """Fetch today's World Cup matches from the excellent free API."""
    try:
        resp = requests.get(f"{WC_API_BASE}/get/games", timeout=15)
        if resp.status_code == 200:
            all_games = resp.json().get("games", [])
            today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
            # Filter for today's matches (local_date format: MM/DD/YYYY)
            today_matches = []
            for g in all_games:
                local_date = g.get("local_date", "")
                if today in local_date or (len(local_date) > 10 and local_date[:10].replace('/', '-') == today):
                    today_matches.append(g)
            logger.info(f"Found {len(today_matches)} matches for today")
            return today_matches
    except Exception as e:
        logger.warning(f"Primary WC API failed: {e}")
    return []

def get_standings():
    """Fetch group standings."""
    try:
        resp = requests.get(f"{WC_API_BASE}/get/groups", timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        logger.warning(f"Standings fetch failed: {e}")
    return []

def format_match(m):
    home = m.get("home_team_name_en", "TBD")
    away = m.get("away_team_name_en", "TBD")
    score = f"{m.get('home_score', 0)}-{m.get('away_score', 0)}" if m.get("finished") == "TRUE" else "vs"
    time_info = m.get("local_date", "TBD")
    stadium_id = m.get("stadium_id")
    venue = f" (Stadium {stadium_id})" if stadium_id else ""
    status = "✅" if m.get("finished") == "TRUE" else "⏳"
    return f"{status} **{home}** {score} **{away}** — {time_info}{venue}"

def build_briefing():
    today_str = datetime.datetime.utcnow().strftime("%B %d, %Y")
    lines = [
        "🌍 **WORLD CUP 2026 DAILY BRIEFING**",
        f"📅 {today_str}\n"
    ]

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

        # Standings
        standings = get_standings()
        if standings:
            lines.append("🏆 **CURRENT GROUP STANDINGS** (Highlights)")
            # Adapt to actual structure (usually list of groups)
            for group in standings[:4]:  # Show first few groups
                g_name = group.get("group", group.get("name", "Group"))
                lines.append(f"**{g_name}**")
                table = group.get("table", [])[:4]
                for team in table:
                    name = team.get("team_name_en", team.get("name", "TBD"))
                    pts = team.get("points", 0)
                    lines.append(f"  • {name} — {pts} pts")
            lines.append("")

        lines.append("\n⚽ **FIFA World Cup 2026** — Enjoy the games!")
    else:
        lines.append("No matches scheduled for today or data temporarily unavailable.")
        lines.append("Check back later or visit https://worldcup26.ir")

    lines.append("\n📲 Powered by your Telegram bot")
    return "\n".join(lines)

# ---------- Send ----------
def send_briefing():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            if f.read().strip() == datetime.datetime.utcnow().strftime("%Y-%m-%d"):
                logger.info("Already sent today – skipping.")
                return

    text = build_briefing()
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
