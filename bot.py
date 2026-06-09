from flask import Flask, request
import os
import telebot
import requests
import io
import time

from google import genai
from google.genai import types

# ---------------- CONFIG ----------------

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = genai.Client(api_key=GEMINI_KEY)

app = Flask(__name__)

SYSTEM_PROMPT = (
    "Ты — понимающий парень. "
    "Общайся будто живой человек, а не ИИ. "
    "Материться можно."
)

# ---------------- START ----------------

@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    bot.reply_to(
        message,
        "Йоу, бро! 🔥\n\n"
        "Я умею:\n"
        "1. Просто болтать\n"
        "2. Рисовать — /рисунок твой запрос\n\n"
        "Пример:\n"
        "/рисунок кот программист в очках"
    )

# ---------------- DRAW ----------------

@bot.message_handler(commands=["рисунок", "draw", "img"])
def handle_draw(message):

    prompt_parts = message.text.split(maxsplit=1)

    if len(prompt_parts) < 2:
        bot.reply_to(
            message,
            "Бро, напиши что рисовать:\n"
            "/рисунок киберпанк жигули"
        )
        return

    prompt = prompt_parts[1]

    try:

        msg = bot.send_message(
            message.chat.id,
            f"Рисую: {prompt} 🎨"
        )

        bot.send_chat_action(
            message.chat.id,
            "upload_photo"
        )

        safe_prompt = requests.utils.quote(
            f"{prompt}, high detail, masterpiece, 4k"
        )

        image_url = (
            f"https://image.pollinations.ai/prompt/"
            f"{safe_prompt}"
            f"?width=1024&height=1024"
            f"&nologo=true"
            f"&model=flux"
        )

        img_data = requests.get(
            image_url,
            timeout=90
        ).content

        if len(img_data) < 5000:
            bot.edit_message_text(
                "Не смог это нарисовать.",
                message.chat.id,
                msg.message_id
            )
            return

        bot.delete_message(
            message.chat.id,
            msg.message_id
        )

        bot.send_photo(
            message.chat.id,
            io.BytesIO(img_data),
            caption=f"Готово: {prompt}"
        )

    except requests.exceptions.Timeout:

        bot.reply_to(
            message,
            "Сервер художника долго думает 😅"
        )

    except Exception as e:

        bot.reply_to(
            message,
            f"Ошибка рисования:\n{e}"
        )

# ---------------- CHAT ----------------

@bot.message_handler(func=lambda message: True)
def handle_text(message):

    for attempt in range(3):

        try:

            bot.send_chat_action(
                message.chat.id,
                "typing"
            )

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=message.text,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    tools=[
                        types.Tool(
                            google_search=types.GoogleSearch()
                        )
                    ]
                )
            )

            answer = getattr(response, "text", None)

            if not answer:
                answer = "Gemini ничего не ответил."

            bot.reply_to(
                message,
                answer
            )

            return

        except Exception as e:

            if "503" in str(e) and attempt < 2:
                time.sleep(5)
            else:
                bot.reply_to(
                    message,
                    f"Gemini отвалился:\n{e}"
                )
                break

# ---------------- WEBHOOK ----------------

@app.route("/" + TELEGRAM_TOKEN, methods=["POST"])
def webhook():

    if request.headers.get("content-type") == "application/json":

        json_string = request.get_data().decode("utf-8")

        update = telebot.types.Update.de_json(
            json_string
        )

        bot.process_new_updates(
            [update]
        )

        return "ok", 200

    return "error", 403

@app.route("/")
def index():

    bot.remove_webhook()

    bot.set_webhook(
        url=f"https://tg-gemini-bot-6n8p.onrender.com/{TELEGRAM_TOKEN}"
    )

    return "Webhook set. Bot is alive.", 200

# ---------------- RUN ----------------

if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", 10000)
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
