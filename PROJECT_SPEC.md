# DailyMind — Telegram Quiz Bot

## Overview
A solo-play Telegram bot that serves 8 daily questions (mental math + trivia). Players compete on a global leaderboard by accuracy and speed. One attempt per day.

## Tech Stack
- Python 3.11+
- `python-telegram-bot` (v20+, async)
- SQLite (single file DB)
- APScheduler for scheduled tasks (daily question generation, evening leaderboard post)

## Core User Flow

1. User discovers bot, taps **Start** → welcome message + `/play` instructions
2. User sends `/play` anytime after 6am SGT
3. Bot sends "Ready?" confirmation with **[Start]** button
4. Bot sends 8 questions one at a time:
   - Shows question + 4 multiple choice buttons
   - 30-second timeout per question
   - On answer: show result (✓/✗), time taken, points earned, auto-advance to next
   - On timeout: show correct answer, 0 points, auto-advance
5. After Q8: session summary (score, correct count, total time, current global rank)
6. If user tries `/play` again same day: "Already played" message with score + rank

## Question Format

**8 questions per day, same set for all players:**
- 5 mental math (randomly generated, escalating difficulty)
- 3 true/false trivia (sourced from Open Trivia DB API or stored pool)

**Math difficulty tiers (1 question each for tiers 1-4, plus 1 random from tier 3-4):**
- Tier 1: Simple addition/subtraction (two 2-digit numbers)
- Tier 2: Multiplication (2-digit × 1-digit)
- Tier 3: Percentages, fractions-to-decimals, simple division
- Tier 4: Two-digit × two-digit multiplication, multi-step

**All questions presented as 4-option multiple choice** (including math). One correct, three plausible distractors.

## Scoring

- Correct answer: 100 base points
- Wrong answer: 0 points
- Timeout: 0 points (auto-skipped)

**Speed bonus (per question, only if correct):**
- < 5 seconds: +30 pts
- 5–15 seconds: +15 pts
- 15–30 seconds: +5 pts

**Max daily score: 1,040** (8 × 130)

**Leaderboard ranking:** Score descending, then total time ascending (tiebreaker)

## Commands

- `/start` — Welcome message + instructions
- `/play` — Start today's challenge (or show "already played" status)
- `/leaderboard` — Today's global top 10
- `/stats` — Personal stats: current streak, best streak, consistency %, best score, total games played
- `/review` — Show your answers vs correct answers for today (only available after playing)

## Scheduled Tasks

1. **6:00am SGT daily** — Generate that day's 8 questions and store in DB
2. **10:00pm SGT daily** — Post leaderboard summary to the public Telegram channel

## Evening Channel Post Format
```
🏆 DailyMind — 28 Mar Results

🥇 @alice — 920 pts (1m 12s)
🥈 @bob — 870 pts (1m 34s)
🥉 @charlie — 685 pts (1m 47s)
... +9 more players

🔥 Longest streak: @alice (12 days)

Play now → t.me/DailyMindBot
```

## Database Schema

### users
- user_id (INTEGER PK) — Telegram user ID
- username (TEXT)
- first_name (TEXT)
- joined_at (TIMESTAMP)
- current_streak (INTEGER, default 0)
- best_streak (INTEGER, default 0)
- last_played (DATE)

### daily_questions
- id (INTEGER PK AUTOINCREMENT)
- game_date (DATE)
- question_index (INTEGER, 0-7)
- question_type (TEXT — 'math' or 'trivia')
- question_text (TEXT)
- options (TEXT — JSON array of 4 strings)
- correct_index (INTEGER, 0-3)
- UNIQUE(game_date, question_index)

### game_sessions
- id (INTEGER PK AUTOINCREMENT)
- user_id (INTEGER FK → users)
- game_date (DATE)
- started_at (TIMESTAMP)
- finished_at (TIMESTAMP)
- total_score (INTEGER)
- correct_count (INTEGER)
- total_time_seconds (REAL)
- UNIQUE(user_id, game_date) — enforces one attempt per day

### answers
- id (INTEGER PK AUTOINCREMENT)
- session_id (INTEGER FK → game_sessions)
- question_index (INTEGER, 0-7)
- selected_index (INTEGER, nullable — null if timed out)
- is_correct (BOOLEAN)
- time_seconds (REAL)
- points_earned (INTEGER)

## Config (environment variables)
- `BOT_TOKEN` — Telegram bot token from @BotFather
- `CHANNEL_ID` — Channel ID or @handle for evening leaderboard posts

## Project Structure
```
dailymind-bot/
├── bot.py              # Main entry point, handler registration
├── config.py           # Constants and env var loading
├── db.py               # SQLite schema init + query helpers
├── questions.py         # Math generator + trivia fetcher
├── game.py             # Game session logic (play flow, scoring, timeouts)
├── leaderboard.py      # Leaderboard queries + formatting
├── scheduler.py        # APScheduler setup (question gen, evening post)
├── requirements.txt
└── README.md
```

## Setup Steps
1. Create bot with @BotFather on Telegram, get token
2. Create a public channel for results, get channel ID
3. `pip install -r requirements.txt`
4. Set BOT_TOKEN and CHANNEL_ID as env vars
5. `python bot.py`

## Future (not for v1)
- Group-scoped leaderboards (add bot to group → friend circle)
- Free text input for math (instead of multiple choice)
- Themed rounds / special categories
- Referral / share-your-score mechanic
- Mini App UI for richer leaderboard / stats view
