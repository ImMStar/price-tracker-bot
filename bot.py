import logging
import os
import threading
from bs4 import BeautifulSoup
from flask import Flask
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# আপনার টেলিগ্রাম বটের টোকেন এখানে বসান (অথবা আগের কোডের টোকেনটি এখানে দিন)
BOT_TOKEN = "8748621966:AAFvKWgoQGO4PeJWVKTF4A62IDaFVOH7jOs"

# ১. ফ্লাস্ক ওয়েব সার্ভার (রেন্ডারের পورت/টাইম-আউট সমস্যা সমাধানের জন্য)
app = Flask(__name__)


@app.route("/")
def home():
  return "Telegram Price Tracker Bot is running!"


def run_flask():
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)


# ২. টেলিগ্রাম বট কমান্ড ও মেসেজ হ্যান্ডলার
async def start(command_update: Update, context: ContextTypes.DEFAULT_TYPE):
  await command_update.message.reply_text(
      "হ্যালো! প্রোডাক্ট ট্র্যাক করতে এভাবে মেসেজ দিন:\n\n[প্রোডাক্ট"
      " লিংক] [টার্গেট দাম]\n\nউদাহরণ:\nhttps://www.amazon.in/dp/example"
      " 12000"
  )


async def handle_message(
    message_update: Update, context: ContextTypes.DEFAULT_TYPE
):
  text = message_update.message.text
  parts = text.split()
  if len(parts) >= 2:
    url = parts[0]
    try:
      target_price = float(parts[-1])
      await message_update.message.reply_text(
          f"প্রোডাক্টটি সফলভাবে লিস্টে যুক্ত করা হয়েছে!\nলিংক: {url}\nটার্গেট"
          f" দাম: {target_price}"
      )
      # এখানে প্রাইস স্ক্র্যাপিং ও চেকিংয়ের লজিক যোগ করতে পারেন
    except ValueError:
      await message_update.message.reply_text(
          "দয়া করে সঠিক ফরম্যাটে লিংক এবং টার্গেট দাম দিন।"
      )
  else:
    await message_update.message.reply_text(
        "সঠিক ফরম্যাটে দিন: [প্রোডাক্ট লিংক] [টার্গেট দাম]"
    )


def main():
  # ফ্লাস্ক সার্ভার ব্যাকগ্রাউন্ড থ্রেডে চালু করা হচ্ছে
  flask_thread = threading.Thread(target=run_flask)
  flask_thread.daemon = True
  flask_thread.start()

  # টেলিগ্রাম বট বিল্ড ও রান করা
  application = Application.builder().token(BOT_TOKEN).build()

  application.add_handler(CommandHandler("start", start))
  application.add_handler(
      MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
  )

  # বট চালু রাখা
  application.run_polling()


if __name__ == "__main__":
  main()
