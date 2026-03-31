import json
import logging

from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

import db
from config import ADMIN_IDS, BOT_TOKEN, sgt_today
from game import handle_callback, handle_play
from leaderboard import handle_leaderboard, format_hall_of_fame
from questions import seed_all_pools
from scheduler import generate_questions_for_date, setup_scheduler, _send_daily_notification_job

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db.upsert_user(
        update.effective_user.id,
        update.effective_user.username,
        update.effective_user.first_name,
    )
    await update.message.reply_text(
        "👋 Welcome to *DailyMind*!\n\n"
        "Every day: 8 fresh questions — mental math + trivia.\n"
        "One shot per day. Fastest, most accurate player wins.\n\n"
        "Use /help to see all commands.",
        parse_mode="Markdown",
    )


async def handle_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    stats = db.get_user_stats(user_id)
    if not stats or stats["total_games"] == 0:
        await update.message.reply_text(
            "You haven't finished a game yet. Use /play to start!"
        )
        return

    days = max(1, stats["days_since_joined"])
    consistency = round(stats["total_games"] / days * 100)
    alltime_rank = db.get_alltime_rank(user_id)
    avg_time = db.get_avg_answer_time(user_id)
    avg_time_str = f"{avg_time:.1f}s" if avg_time is not None else "N/A"

    await update.message.reply_text(
        f"📊 *Your Stats*\n\n"
        f"🔥 Current streak: *{stats['current_streak']} days*\n"
        f"🏅 Best streak: *{stats['best_streak']} days*\n"
        f"💰 All-time score: *{stats['all_time_score']} pts*\n"
        f"🌍 All-time rank: *#{alltime_rank}*\n"
        f"🎮 Games played: *{stats['total_games']}*\n"
        f"📅 Consistency: *{consistency}%*\n"
        f"⚡ Avg answer time: *{avg_time_str}*",
        parse_mode="Markdown",
    )


async def handle_halloffame(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(format_hall_of_fame(), parse_mode="Markdown")


async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🧠 *DailyMind Commands*\n\n"
        "/play — Start today's challenge\n"
        "/leaderboard — Today's top 10\n"
        "/halloffame — All-time top 10 by total score\n"
        "/stats — Your streaks, score, and answer stats\n"
        "/review — See your answers vs correct answers for today\n"
        "/help — Show this message",
        parse_mode="Markdown",
    )


_ADMIN_ID = 45878459


async def handle_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != _ADMIN_ID:
        await update.message.reply_text("Not authorised.")
        return
    today = sgt_today()
    deleted = db.reset_user_session(_ADMIN_ID, today)
    if deleted:
        await update.message.reply_text(f"Session for {today} cleared. You can /play again.")
    else:
        await update.message.reply_text(f"No session found for {today}.")


async def handle_testnotify(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != _ADMIN_ID:
        await update.message.reply_text("Not authorised.")
        return
    await update.message.reply_text("Triggering daily notification job…")
    await _send_daily_notification_job(context)
    await update.message.reply_text("Done.")


async def handle_preview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != _ADMIN_ID:
        await update.message.reply_text("Not authorised.")
        return
    today = sgt_today()
    questions = db.get_daily_questions(today)
    if not questions:
        await update.message.reply_text(f"No questions generated for {today} yet.")
        return

    lines = [f"📋 *Preview — {today}*\n"]
    for q in questions:
        opts = json.loads(q["options"])
        correct_text = opts[q["correct_index"]]
        lines.append(f"*Q{q['question_index'] + 1}* `[{q['question_type']}]`")
        lines.append(q["question_text"])
        for i, opt in enumerate(opts):
            marker = "✅" if i == q["correct_index"] else "◦"
            lines.append(f"  {marker} {opt}")
        lines.append("")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def handle_testgenerate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != _ADMIN_ID:
        await update.message.reply_text("Not authorised.")
        return
    today = sgt_today()
    await update.message.reply_text(f"Generating questions for {today}…")
    try:
        await generate_questions_for_date(today)
        qs = db.get_daily_questions(today)
        await update.message.reply_text(f"Done. {len(qs)} questions ready for {today}.")
    except Exception as exc:
        logger.exception("Test question generation failed")
        await update.message.reply_text(f"Failed: {exc}")


async def handle_generate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if ADMIN_IDS and update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("Not authorised.")
        return
    today = sgt_today()
    await update.message.reply_text(f"Generating questions for {today}…")
    try:
        await generate_questions_for_date(today)
        qs = db.get_daily_questions(today)
        await update.message.reply_text(f"Done. {len(qs)} questions ready for {today}.")
    except Exception as exc:
        logger.exception("Manual question generation failed")
        await update.message.reply_text(f"Failed: {exc}")


async def handle_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    today = sgt_today()

    session = db.get_session(user_id, today)
    if not session or not session["finished_at"]:
        await update.message.reply_text(
            "You haven't completed today's challenge yet. Use /play!"
        )
        return

    answers = db.get_user_answers(session["id"])
    questions = db.get_daily_questions(today)

    answers_by_idx = {a["question_index"]: a for a in answers}

    lines = ["📋 *Today's Review*\n"]
    for q in questions:
        opts = json.loads(q["options"])
        correct_text = opts[q["correct_index"]]
        a = answers_by_idx.get(q["question_index"])

        if a and a["is_correct"]:
            status = "✅"
        elif a and a["selected_index"] is None:
            status = "⏰"
        else:
            status = "❌"

        q_short = q["question_text"][:60] + ("…" if len(q["question_text"]) > 60 else "")
        lines.append(f"{status} *Q{q['question_index'] + 1}:* {q_short}")

        if not (a and a["is_correct"]):
            lines.append(f"   ✔ Correct: _{correct_text}_")
            if a and a["selected_index"] is not None:
                lines.append(f"   ✘ Your answer: _{opts[a['selected_index']]}_")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def _on_startup(app: Application) -> None:
    seed_all_pools()
    today = sgt_today()
    if not db.get_daily_questions(today):
        logger.info("No questions found for %s — generating now…", today)
        try:
            await generate_questions_for_date(today)
        except Exception:
            logger.exception("Startup question generation failed for %s", today)
    else:
        logger.info("Questions already exist for %s — skipping generation", today)


def main() -> None:
    db.init_db()

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(_on_startup)
        .build()
    )

    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("help", handle_help))
    app.add_handler(CommandHandler("play", handle_play))
    app.add_handler(CommandHandler("leaderboard", handle_leaderboard))
    app.add_handler(CommandHandler("halloffame", handle_halloffame))
    app.add_handler(CommandHandler("stats", handle_stats))
    app.add_handler(CommandHandler("review", handle_review))
    app.add_handler(CommandHandler("generate", handle_generate))
    app.add_handler(CommandHandler("reset", handle_reset))
    app.add_handler(CommandHandler("preview", handle_preview))
    app.add_handler(CommandHandler("testnotify", handle_testnotify))
    app.add_handler(CommandHandler("testgenerate", handle_testgenerate))
    app.add_handler(CallbackQueryHandler(handle_callback))

    setup_scheduler(app)

    logger.info("DailyMind bot starting…")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
