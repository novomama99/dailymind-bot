from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

import db
from config import sgt_today


def _display_name(row) -> str:
    if row["username"]:
        return f"@{row['username']}"
    return row["first_name"] or "Player"


def _fmt_time(seconds: float) -> str:
    mins, secs = divmod(int(seconds), 60)
    return f"{mins}m {secs:02d}s" if mins else f"{secs}s"


def format_leaderboard(game_date: str) -> str:
    try:
        d = datetime.strptime(game_date, "%Y-%m-%d")
        display_date = d.strftime("%-d %b")
    except Exception:
        display_date = game_date

    medals = ["🥇", "🥈", "🥉"]
    rows = db.get_leaderboard(game_date, limit=10)
    if rows:
        lines = [f"📅 *Today — {display_date}*\n"]
        for i, r in enumerate(rows):
            medal = medals[i] if i < 3 else f"{i + 1}."
            name = _display_name(r)
            time_str = _fmt_time(r["total_time_seconds"])
            lines.append(f"{medal} {name} — {r['total_score']} pts ({time_str})")
        total = db.count_players(game_date)
        if total > 10:
            lines.append(f"_...and {total - 10} more_")
    else:
        lines = [f"📅 *Today — {display_date}*\n", "_No one has played yet. Be the first — /play!_"]

    return "\n".join(lines)


def format_hall_of_fame() -> str:
    medals = ["🥇", "🥈", "🥉"]
    rows = db.get_alltime_leaderboard(limit=10)
    lines = ["🏆 *Hall of Fame — All-Time*\n"]
    if rows:
        for i, r in enumerate(rows):
            medal = medals[i] if i < 3 else f"{i + 1}."
            name = _display_name(r)
            lines.append(f"{medal} {name} — {r['total_score']} pts ({r['games_played']} games)")
    else:
        lines.append("_No finished games yet._")
    return "\n".join(lines)


def format_evening_post(game_date: str) -> str:
    rows = db.get_leaderboard(game_date, limit=10)
    if not rows:
        return f"🏆 DailyMind — {game_date}\n\nNo players today. Come back tomorrow!"

    try:
        d = datetime.strptime(game_date, "%Y-%m-%d")
        display_date = d.strftime("%-d %b")
    except Exception:
        display_date = game_date

    medals = ["🥇", "🥈", "🥉"]
    lines = [f"🏆 *DailyMind — {display_date} Results*\n"]
    for i, r in enumerate(rows):
        medal = medals[i] if i < 3 else f"    {i + 1}."
        name = _display_name(r)
        time_str = _fmt_time(r["total_time_seconds"])
        lines.append(f"{medal} {name} — {r['total_score']} pts ({time_str})")

    total = db.count_players(game_date)
    if total > 10:
        lines.append(f"\n_...+{total - 10} more players_")

    streak_row = db.get_longest_streak_player(game_date)
    if streak_row and streak_row["current_streak"] > 1:
        name = _display_name(streak_row)
        lines.append(f"\n🔥 Longest streak: {name} ({streak_row['current_streak']} days)")

    lines.append("\nPlay now → t.me/DailyMindBot")
    return "\n".join(lines)


async def handle_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    today = sgt_today()
    text = format_leaderboard(today)
    await update.message.reply_text(text, parse_mode="Markdown")
