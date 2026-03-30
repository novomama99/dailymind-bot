import os
from zoneinfo import ZoneInfo

BOT_TOKEN: str = os.environ["BOT_TOKEN"]
CHANNEL_ID: str = os.environ.get("CHANNEL_ID", "")
ADMIN_IDS: set[int] = {
    int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()
}

SGT = ZoneInfo("Asia/Singapore")

QUESTIONS_PER_DAY = 8
QUESTION_TIMEOUT = 30  # seconds

BASE_POINTS = 100
SPEED_BONUS_FAST = 30   # < 5 s
SPEED_BONUS_MED = 15    # 5–15 s
SPEED_BONUS_SLOW = 5    # 15–30 s
MAX_DAILY_SCORE = 1040

DB_PATH = "dailymind.db"
OPENTDB_URL = "https://opentdb.com/api.php"
