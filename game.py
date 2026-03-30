import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

import db
from config import (
    BASE_POINTS,
    QUESTION_TIMEOUT,
    SPEED_BONUS_FAST,
    SPEED_BONUS_MED,
    SPEED_BONUS_SLOW,
)

_LABELS = ["A", "B", "C", "D"]


@dataclass
class _GameState:
    session_id: int
    user_id: int
    chat_id: int
    current_q_idx: int = 0
    q_start_time: float = 0.0
    awaiting_answer: bool = False
    timeout_task: Optional[asyncio.Task] = None
    current_message_id: Optional[int] = None


# user_id → _GameState
_sessions: dict[int, _GameState] = {}


def _calc_points(elapsed: float) -> int:
    if elapsed < 5:
        bonus = SPEED_BONUS_FAST
    elif elapsed < 15:
        bonus = SPEED_BONUS_MED
    else:
        bonus = SPEED_BONUS_SLOW
    return BASE_POINTS + bonus


async def _send_question(context: ContextTypes.DEFAULT_TYPE, state: _GameState) -> None:
    today = date.today().isoformat()
    questions = db.get_daily_questions(today)
    q = questions[state.current_q_idx]
    options = json.loads(q["options"])

    keyboard = [
        [InlineKeyboardButton(f"{_LABELS[i]}: {options[i]}", callback_data=f"game_answer_{i}")]
        for i in range(4)
    ]
    text = f"*Question {state.current_q_idx + 1}/8*\n\n{q['question_text']}"
    msg = await context.bot.send_message(
        chat_id=state.chat_id,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
    state.current_message_id = msg.message_id
    state.q_start_time = time.monotonic()
    state.awaiting_answer = True

    if state.timeout_task:
        state.timeout_task.cancel()
    state.timeout_task = asyncio.create_task(
        _handle_timeout(context, state.user_id, state.current_q_idx)
    )


async def _handle_timeout(
    context: ContextTypes.DEFAULT_TYPE, user_id: int, q_idx: int
) -> None:
    try:
        await asyncio.sleep(QUESTION_TIMEOUT)
    except asyncio.CancelledError:
        return

    state = _sessions.get(user_id)
    if state is None or state.current_q_idx != q_idx or not state.awaiting_answer:
        return

    state.awaiting_answer = False

    today = date.today().isoformat()
    questions = db.get_daily_questions(today)
    q = questions[q_idx]
    options = json.loads(q["options"])
    correct_text = options[q["correct_index"]]

    db.record_answer(
        session_id=state.session_id,
        question_index=q_idx,
        selected_index=None,
        is_correct=False,
        time_seconds=float(QUESTION_TIMEOUT),
        points_earned=0,
    )

    if state.current_message_id:
        try:
            await context.bot.edit_message_reply_markup(
                chat_id=state.chat_id,
                message_id=state.current_message_id,
                reply_markup=None,
            )
        except Exception:
            pass

    await context.bot.send_message(
        chat_id=state.chat_id,
        text=f"⏰ *Time's up!*\nCorrect answer: *{correct_text}* — 0 pts",
        parse_mode="Markdown",
    )
    await _advance(context, state)


async def _advance(context: ContextTypes.DEFAULT_TYPE, state: _GameState) -> None:
    state.current_q_idx += 1
    if state.current_q_idx >= 8:
        await _finish_session(context, state)
    else:
        await asyncio.sleep(1.5)
        await _send_question(context, state)


async def _finish_session(context: ContextTypes.DEFAULT_TYPE, state: _GameState) -> None:
    _sessions.pop(state.user_id, None)

    session = db.finish_session(state.session_id)
    rank = db.get_rank(state.session_id, session["game_date"])

    total_time = session["total_time_seconds"]
    mins, secs = divmod(int(total_time), 60)
    time_str = f"{mins}m {secs:02d}s" if mins else f"{secs}s"

    text = (
        f"🎉 *Daily Challenge Complete!*\n\n"
        f"Score: *{session['total_score']} pts*\n"
        f"Correct: *{session['correct_count']}/8*\n"
        f"Total time: *{time_str}*\n"
        f"Global rank: *#{rank}*\n\n"
        f"Use /review to see your answers."
    )
    await context.bot.send_message(
        chat_id=state.chat_id, text=text, parse_mode="Markdown"
    )
    db.update_streak(state.user_id)


# ── Public handlers ───────────────────────────────────────────────────────────

async def handle_play(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    today = date.today().isoformat()

    db.upsert_user(user.id, user.username, user.first_name)

    existing = db.get_session(user.id, today)
    if existing:
        rank = db.get_rank(existing["id"], today)
        await update.message.reply_text(
            f"You already played today! 🎯\n"
            f"Score: *{existing['total_score']} pts* | Rank: *#{rank}*\n\n"
            f"Come back tomorrow!",
            parse_mode="Markdown",
        )
        return

    if user.id in _sessions:
        await update.message.reply_text("You're already in the middle of a game!")
        return

    questions = db.get_daily_questions(today)
    if not questions:
        await update.message.reply_text(
            "Today's questions aren't ready yet. Check back after 6:00 AM SGT!"
        )
        return

    keyboard = [[InlineKeyboardButton("▶️  Start", callback_data="game_start")]]
    await update.message.reply_text(
        "Ready for today's *DailyMind* challenge?\n\n"
        "8 questions • 30 s per question • Speed bonuses!\n\n"
        "Tap Start when you're ready. ⬇️",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = query.from_user
    data = query.data

    if data == "game_start":
        today = date.today().isoformat()

        existing = db.get_session(user.id, today)
        if existing:
            await query.edit_message_text("You already played today!")
            return

        if user.id in _sessions:
            await query.edit_message_text("You're already playing!")
            return

        questions = db.get_daily_questions(today)
        if not questions:
            await query.edit_message_text("Today's questions aren't ready yet!")
            return

        session_id = db.create_session(user.id, today)
        state = _GameState(
            session_id=session_id,
            user_id=user.id,
            chat_id=query.message.chat_id,
        )
        _sessions[user.id] = state

        await query.edit_message_text("Let's go! 🚀")
        await _send_question(context, state)

    elif data.startswith("game_answer_"):
        state = _sessions.get(user.id)
        if state is None or not state.awaiting_answer:
            return

        state.awaiting_answer = False

        if state.timeout_task:
            state.timeout_task.cancel()
            state.timeout_task = None

        selected = int(data.split("_")[-1])
        elapsed = time.monotonic() - state.q_start_time

        today = date.today().isoformat()
        questions = db.get_daily_questions(today)
        q = questions[state.current_q_idx]
        options = json.loads(q["options"])

        is_correct = selected == q["correct_index"]
        points = _calc_points(elapsed) if is_correct else 0

        db.record_answer(
            session_id=state.session_id,
            question_index=state.current_q_idx,
            selected_index=selected,
            is_correct=is_correct,
            time_seconds=elapsed,
            points_earned=points,
        )

        try:
            await context.bot.edit_message_reply_markup(
                chat_id=state.chat_id,
                message_id=state.current_message_id,
                reply_markup=None,
            )
        except Exception:
            pass

        correct_text = options[q["correct_index"]]
        if is_correct:
            result = f"✅ *Correct!* +{points} pts ({elapsed:.1f}s)"
        else:
            result = f"❌ *Wrong!* The answer was: *{correct_text}* — 0 pts"

        await context.bot.send_message(
            chat_id=state.chat_id, text=result, parse_mode="Markdown"
        )
        await _advance(context, state)
