import threading
from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
  port = int(os.environ.get('PORT', 5000))
  app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_flask).start()

import os
import telebot
import requests
import io
import time
from google import genai
from google.genai import types

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GEMINI_KEY = os.environ.get('GEMINI_KEY')
# ------------------

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = genai.Client(api_key=GEMINI_KEY)

SYSTEM_PROMPT = "Ты — понимающий парень общайся будто ты живой человек а не ии. Материться можно."

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Йоу, бро! Я ожил 🔥\n\nЯ умею:\n1. Просто болтать — пиши любой текст\n2. Рисовать — /рисунок твой запрос\n\nПример: /рисунок кот программист в очках")

@bot.message_handler(commands=['рисунок', 'draw', 'img'])
def handle_draw(message):
    prompt = message.text.split(maxsplit=1)
    if len(prompt) < 2:
        bot.reply_to(message, "Бро, напиши что рисовать: /рисунок киберпанк жигули")
        return

    prompt = prompt[1]

    try:
        msg = bot.send_message(message.chat.id, f"Рисую: {prompt} 🎨\nЩа будет... 10-20 сек")
        bot.send_chat_action(message.chat.id, 'upload_photo')

        # Кодируем промпт и делаем запрос к Pollinations
        safe_prompt = requests.utils.quote(f"{prompt}, high detail, masterpiece, 4k")
        image_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=1024&nologo=true&model=flux"

        img_data = requests.get(image_url, timeout=90).content

        # Если пришёл текст ошибки вместо картинки
        if len(img_data) < 5000:
            bot.edit_message_text("Не смог это нарисовать. Попробуй другой запрос", message.chat.id, msg.message_id)
            return

        bot.delete_message(message.chat.id, msg.message_id)
        bot.send_photo(message.chat.id, io.BytesIO(img_data), caption=f"Готово: {prompt}")

    except requests.exceptions.Timeout:
        bot.reply_to(message, "Чёт долго рисует, сервак тупит. Попробуй ещё раз")
    except Exception as e:
        bot.reply_to(message, f"Художник из меня так себе: {e}")

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    for attempt in range(3):
        try:
            bot.send_chat_action(message.chat.id, 'typing')
            response = client.models.generate_content(
                model='models/gemini-2.5-flash', 
                contents=message.text,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
tools=[types.Tool(google_search=types.GoogleSearch())]
                )
            )
            bot.reply_to(message, response.text)
            return
        except Exception as e:
            if "503" in str(e) and attempt < 2:
                time.sleep(5)
            else:
                bot.reply_to(message, f"Gemini отвалился: {e}")
                break

if __name__ == '__main__':
    print("Бот запущен с Pollinations... Ctrl+C чтобы выключить")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
