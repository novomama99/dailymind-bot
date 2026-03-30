import datetime
import logging
from datetime import date

from telegram.ext import Application, ContextTypes

from config import CHANNEL_ID, SGT
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


def setup_scheduler(app: Application) -> None:
    jq = app.job_queue

    # 6:00 AM SGT — generate today's questions
    jq.run_daily(
        _generate_questions_job,
        time=datetime.time(6, 0, 0, tzinfo=SGT),
        name="generate_questions",
    )

    # 10:00 PM SGT — post results to channel
    jq.run_daily(
        _post_leaderboard_job,
        time=datetime.time(22, 0, 0, tzinfo=SGT),
        name="post_leaderboard",
    )
