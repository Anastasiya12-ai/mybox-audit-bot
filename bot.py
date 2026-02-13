import os
import requests
import asyncio
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# Переменные окружения
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
HDE_API_KEY = os.environ.get("HDE_API_KEY")
HDE_DOMAIN = "https://service.mybox.ru"

user_text = {}
media_groups = {}

app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot is running"

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text[update.effective_user.id] = update.message.text
    await update.message.reply_text("Описание сохранено. Теперь отправьте фото одним сообщением.")

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_text:
        await update.message.reply_text("Сначала отправьте описание.")
        return

    media_group_id = update.message.media_group_id

    if media_group_id not in media_groups:
        media_groups[media_group_id] = []

    file = await context.bot.get_file(update.message.photo[-1].file_id)
    media_groups[media_group_id].append(file.file_path)

    await asyncio.sleep(2)

    photos = media_groups.pop(media_group_id, [])
    description = user_text.pop(user_id)

    if photos:
        # создаем заявку
        ticket_data = {
            "subject": "Аудит вкуса",
            "content": description,
            "public": True
        }

        headers = {
            "Authorization": f"Bearer {HDE_API_KEY}",
            "Content-Type": "application/json"
        }

        ticket_response = requests.post(
            f"{HDE_DOMAIN}/api/v2/tickets",
            json=ticket_data,
            headers=headers
        )

        ticket_id = ticket_response.json().get("id")

        # добавляем фото в комментарий
        html_content = "<p>Фото проверки:</p>"
        for url in photos:
            html_content += f'<img src="{url}"><br>'

        requests.post(
            f"{HDE_DOMAIN}/api/v2/tickets/{ticket_id}/comments",
            json={"content": html_content, "public": True},
            headers=headers
        )

        await update.message.reply_text(f"Заявка создана №{ticket_id}")

telegram_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
telegram_app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

if __name__ == "__main__":
    import threading
    threading.Thread(target=lambda: telegram_app.run_polling()).start()
    app_flask.run(host="0.0.0.0", port=10000)
