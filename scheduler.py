import asyncio
import datetime
import logging
from datetime import date

from telegram.ext import Application, ContextTypes

from config import CHANNEL_ID, SGT
import db
import questions
import leaderboard

logger = logging.getLogger(__name__)


async def generate_questions_for_date(game_date: str) -> None:
    """Generate questions for the given date. No-op if already stored."""
    logger.info("Generating daily questions for %s", game_date)
    await questions.generate_daily_questions(game_date)
    logger.info("Questions generated for %s", game_date)


async def _generate_questions_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    today = date.today().isoformat()
    try:
        await generate_questions_for_date(today)
    except Exception:
        logger.exception("Failed to generate questions for %s", today)


async def _post_leaderboard_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    if not CHANNEL_ID:
        logger.warning("CHANNEL_ID not set — skipping evening post")
        return
    today = date.today().isoformat()
    text = leaderboard.format_evening_post(today)
    try:
        await context.bot.send_message(
            chat_id=CHANNEL_ID, text=text, parse_mode="Markdown"
        )
        logger.info("Evening leaderboard posted for %s", today)
    except Exception:
        logger.exception("Failed to post evening leaderboard for %s", today)


async def _broadcast(context: ContextTypes.DEFAULT_TYPE, user_ids: list[int], text: str) -> None:
    sent = 0
    for user_id in user_ids:
        try:
            await context.bot.send_message(chat_id=user_id, text=text)
            sent += 1
        except Exception:
            logger.warning("Failed to notify user %d", user_id, exc_info=True)
        # Stay safely under Telegram's 30 msg/sec global limit
        await asyncio.sleep(1 / 25)
    logger.info("Broadcast sent to %d/%d users", sent, len(user_ids))


async def _send_daily_notification_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    user_ids = db.get_notifiable_users()
    if not user_ids:
        return
    logger.info("Sending morning notification to %d users", len(user_ids))
    await _broadcast(context, user_ids, "Today's challenge is ready! /play to start. 🧠")


async def _send_evening_notification_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    today = date.today().isoformat()
    user_ids = db.get_unplayed_users_today(today)
    if not user_ids:
        return
    logger.info("Sending evening notification to %d unplayed users", len(user_ids))
    await _broadcast(context, user_ids, "Haven't played today? You still have time! /play before midnight. 🌙")


def setup_scheduler(app: Application) -> None:
    jq = app.job_queue

    # 5:00 AM SGT — generate today's questions
    jq.run_daily(
        _generate_questions_job,
        time=datetime.time(5, 0, 0, tzinfo=SGT),
        name="generate_questions",
    )

    # 5:05 AM SGT — morning notification to all returning users
    jq.run_daily(
        _send_daily_notification_job,
        time=datetime.time(5, 5, 0, tzinfo=SGT),
        name="send_notifications_morning",
    )

    # 8:00 PM SGT — evening nudge to users who haven't played yet
    jq.run_daily(
        _send_evening_notification_job,
        time=datetime.time(20, 0, 0, tzinfo=SGT),
        name="send_notifications_evening",
    )

    # 10:00 PM SGT — post results to channel
    jq.run_daily(
        _post_leaderboard_job,
        time=datetime.time(22, 0, 0, tzinfo=SGT),
        name="post_leaderboard",
    )
