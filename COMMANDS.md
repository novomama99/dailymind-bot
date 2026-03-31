# DailyMind Bot — Command Reference

## Player Commands

| Command | Description |
|---|---|
| `/start` | Welcome message and intro to the bot |
| `/help` | List all player commands with short descriptions |
| `/play` | Start today's challenge (one attempt per day) |
| `/leaderboard` | Today's top 10 players (score desc, time asc tiebreak) |
| `/halloffame` | All-time top 10 by cumulative total score across all days |
| `/stats` | Personal stats: streaks, games played, consistency %, avg answer time, all-time score and rank |
| `/review` | Show your answers vs correct answers for today — only available after completing today's game |

### Notes
- `/play` is blocked if you've already completed today's game. It will show your score and rank instead.
- `/review` is blocked until all 8 questions are answered or timed out.

---

## Admin Commands

Restricted to Telegram user ID `45878459`. All others receive "Not authorised."

| Command | Description |
|---|---|
| `/admin` | List all admin commands |
| `/reset` | Delete your game session and answers for today so you can `/play` again |
| `/preview` | Show today's 8 questions with correct answers marked — no game session created |
| `/testgenerate` | Force question generation for today (no-op if questions already exist) |
| `/testnotify` | Trigger the morning notification job immediately — sends to all returning users |

### Example Usage

```
/reset
→ "Session for 2026-03-31 cleared. You can /play again."
→ "No session found for 2026-03-31." (if no session exists)

/preview
→ Lists all 8 questions with options, correct answer marked ✅

/testgenerate
→ "Generating questions for 2026-03-31…"
→ "Done. 8 questions ready for 2026-03-31."

/testnotify
→ "Triggering daily notification job…"
→ Sends "Today's challenge is ready! /play to start. 🧠" to all users who have played before
→ "Done."
```

---

## Scheduled Jobs (not commands)

| Time (SGT) | Job |
|---|---|
| 5:00 AM | Generate today's 8 questions |
| 5:05 AM | Morning notification to all returning users |
| 8:00 PM | Evening nudge to users who haven't played today yet |
| 10:00 PM | Post leaderboard summary to the configured channel |

---

## Legacy Admin Command

| Command | Description |
|---|---|
| `/generate` | Force question generation for today — restricted to user IDs in the `ADMIN_IDS` environment variable (separate from the hardcoded admin) |
