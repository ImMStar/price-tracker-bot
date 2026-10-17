import logging
import os
import threading
from bs4 import BeautifulSoup
from flask import Flask
import requests
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

# আপনার টেলিগ্রাম বটের টোকেন এখানে বসান
BOT_TOKEN = "8748621966:AAFvKWgoQGO4PeJWVKTF4A62IDaFVOH7jOs"

# ১. ফ্লাস্ক ওয়েব সার্ভার (রেন্ডারের টাইম-আউট সমস্যা সমাধানের জন্য)
app = Flask(__name__)


@app.route("/")
def home():
  return "Telegram Price Tracker Bot is running!"


def run_flask():
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)


# ট্র্যাক করা প্রোডাক্টগুলো জমানোর ডিকশনারি
tracked_products = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(
      "হ্যালো! প্রোডাক্ট ট্র্যাক করতে এভাবে মেসেজ দিন:\n\n[প্রোডাক্ট"
      " লিংক] [টার্গেট দাম]\n\nউদাহরণ:\nhttps://www.amazon.in/dp/example"
      " 12000"
  )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
  text = update.message.text
  chat_id = update.message.chat_id
  parts = text.split()

  if len(parts) >= 2:
    url = parts[0]
    try:
      target_price = float(parts[-1])

      if chat_id not in tracked_products:
        tracked_products[chat_id] = []

      tracked_products[chat_id].append(
          {"url": url, "target_price": target_price}
      )

      await update.message.reply_text(
          f"✅ সফলভাবে ট্র্যাকিং লিস্টে যুক্ত হয়েছে!\n🔗 লিংক: {url}\n🎯 টার্গেট"
          f" দাম: {target_price} টাকা\n\nদাম কমলেই বট আপনাকে অ্যালার্ট পাঠাবে!"
      )
    except ValueError:
      await update.message.reply_text(
          "দয়া করে সঠিক ফরম্যাটে লিংক এবং শেষে সংখ্যায় টার্গেট দাম দিন।"
      )
  else:
    await update.message.reply_text(
        "সঠিক ফরম্যাটে দিন: [প্রোডাক্ট লিংক] [টার্গেট দাম]"
    )


# নির্দিষ্ট সময় পরপর দাম চেক করার ফাংশন
async def check_prices(context: ContextTypes.DEFAULT_TYPE):
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
          " like Gecko) Chrome/115.0.0.0 Safari/537.36"
      ),
      "Accept-Language": "en-US,en;q=0.9",
  }

  for chat_id, items in tracked_products.items():
    for item in items:
      url = item["url"]
      target_price = item["target_price"]

      try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
          soup = BeautifulSoup(response.text, "html.parser")

          # উদাহরণস্বরূপ অ্যামাজনের প্রাইস ট্যাগ (অন্য সাইটের ক্ষেত্রে ট্যাগ পরিবর্তন হতে পারে)
          price_element = soup.find("span", {"class": "a-price-whole"})
          if price_element:
            price_text = (
                price_element.get_text()
                .replace(",", "")
                .replace("₹", "")
                .strip()
            )
            current_price = float(price_text)

            # বর্তমান দাম টার্গেট দামের সমান বা কম হলে অ্যালার্ট পাঠাবে
            if current_price <= target_price:
              await context.bot.send_message(
                  chat_id=chat_id,
                  text=(
                      f"🚨 প্রোডাক্টের দাম কমে গেছে!\n\nআপনার টার্গেট দাম ছিল:"
                      f" {target_price} টাকা\nবর্তমান দাম: {current_price}"
                      f" টাকা\n\nলিংক: {url}"
                  ),
              )
      except Exception as e:
        logging.error(f"Error checking price for {url}: {e}")


def main():
  # ফ্লাস্ক সার্ভার ব্যাকগ্রাউন্ডে চালু করা
  flask_thread = threading.Thread(target=run_flask)
  flask_thread.daemon = True
  flask_thread.start()

  # টেলিগ্রাম বট বিল্ড ও রান করা
  application = Application.builder().token(BOT_TOKEN).build()

  application.add_handler(CommandHandler("start", start))
  application.add_handler(
      MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
  )

  # প্রতি ৩০ মিনিটে স্বয়ংক্রিয়ভাবে দাম চেক করার জন্য জব কিউ (Job Queue) সেটআপ
  job_queue = application.job_queue
  job_queue.run_repeating(check_prices, interval=1800, first=10)

  application.run_polling()


if __name__ == "__main__":
  main()
