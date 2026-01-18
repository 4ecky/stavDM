from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)
import requests
import time
import os

# ================= НАСТРОЙКИ =================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 8080))

API_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_FOOTBALL_KEY}

BET_LINK = "https://melbet.ru/ru/sport"

# ================= СОСТОЯНИЯ =================

DM_CHATS = set()
NOTIFIED_EVENTS = set()  # защита от дублей

# ================= API =================

def fetch_live():
    try:
        r = requests.get(
            f"{API_URL}/fixtures",
            headers=HEADERS,
            params={"live": "all"},
            timeout=5,
        )
        return r.json().get("response", [])
    except Exception as e:
        print("LIVE API ERROR:", e)
        return []

# ================= ГОЛЫ =================

async def process_goals(context):
    matches = fetch_live()
    print(f"✅ LIVE FOUND: {len(matches)}")

    for m in matches:
        fixture = m["fixture"]
        league = m["league"]
        teams = m["teams"]
        goals = m["goals"]
        events = m.get("events", [])

        for e in events:
            if e["type"] != "Goal":
                continue

            event_id = f'{fixture["id"]}_{e["time"]["elapsed"]}_{e["player"]["id"]}'

            if event_id in NOTIFIED_EVENTS:
                continue

            NOTIFIED_EVENTS.add(event_id)

            minute = e["time"]["elapsed"]

            text = (
                "⚽ ГОООООЛ!\n\n"
                f"🏆 {league['name']}\n"
                f"{teams['home']['name']} — {teams['away']['name']}\n"
                f"📊 {goals['home']} : {goals['away']}\n"
                f"⏱ {minute} мин\n\n"
                f"👉 Смотреть: {BET_LINK}"
            )

            for chat_id in DM_CHATS:
                try:
                    await context.bot.send_message(chat_id, text)
                except Exception:
                    pass

# ================= JOB =================

async def main_job(context: ContextTypes.DEFAULT_TYPE):
    await process_goals(context)

# ================= КОМАНДЫ =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    DM_CHATS.add(chat_id)

    await context.bot.send_message(
        chat_id,
        "✅ Вы подписались на уведомления о голах.\n"
        "Я пришлю сообщение, как только будет забит гол.",
    )

# ================= ЗАПУСК (WEBHOOK) =================

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.job_queue.run_repeating(main_job, interval=120, first=10)

    print("✅ Бот запущен (WEBHOOK)")

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TELEGRAM_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}",
    )

if __name__ == "__main__":
    main()
