import logging
from bs4 import BeautifulSoup
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# =====================================================================
# 👇 [TELEGRAM BOT API AREA] নিচের লাইনে আপনার বটের টোকেন বসান 👇
# =====================================================================

TOKEN = "8748621966:AAFvKWgoQGO4PeJWVKTF4A62IDaFVOH7jOs"

# =====================================================================
# 👆 কোটেশন (" ") চিহ্নের ভেতরে আপনার BotFather-এর টোকেনটি পেস্ট করবেন 👆
# =====================================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# প্রোডাক্টের ডেটা সেভ রাখার লিস্ট
tracked_products = {}


# দাম চেক করার ফাংশন (Amazon ও Flipkart)
def get_product_price(url):
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
          " like Gecko) Chrome/122.0.0.0 Safari/537.36"
      ),
      "Accept-Language": "en-US,en;q=0.9",
  }
  try:
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code != 200:
      return None

    soup = BeautifulSoup(response.text, "html.parser")

    # Amazon প্রাইস খোঁজা
    amazon_price = soup.find("span", {"class": "a-price-whole"})
    if amazon_price:
      price_str = (
          amazon_price.get_text().replace(",", "").replace(".", "").strip()
      )
      return float(price_str)

    # Flipkart প্রাইস খোঁজা
    flipkart_price = soup.find("div", {"class": "Nx9bqj"}) or soup.find(
        "div", {"class": "_30jeq3"}
    )
    if flipkart_price:
      price_str = (
          flipkart_price.get_text().replace("₹", "").replace(",", "").strip()
      )
      return float(price_str)

  except Exception as e:
    print(f"Error: {e}")

  return None


# /start কমান্ড
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(
      "হ্যালো! প্রোডাক্ট ট্র্যাক করতে এইভাবে মেসেজ দিন:\n\n`[প্রোডাক্ট লিংক]"
      " [টার্গেট দাম]`\n\nউদাহরণ:\n`https://www.amazon.in/dp/example 12000`",
      parse_mode="Markdown",
  )


# মেসেজ রিসিভ করা
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
  text = update.message.text
  chat_id = update.message.chat_id

  parts = text.split()
  if len(parts) == 2:
    url = parts[0]
    try:
      target_price = float(parts[1])
      tracked_products[chat_id] = {"url": url, "target_price": target_price}
      await update.message.reply_text(
          f"✅ ট্র্যাকিং চালু হয়েছে!\nটার্গেট দাম: ₹{target_price}"
      )
    except ValueError:
      await update.message.reply_text("দয়া করে শেষে সঠিক সংখ্যায় দাম লিখুন।")
  else:
    await update.message.reply_text(
        "ভুল ফরম্যাট! প্রথমে লিংক দিন, তারপর একটি স্পেস দিয়ে দাম লিখুন।"
    )


# প্রতি ১ ঘণ্টা পর পর দাম চেক করা
async def check_prices(context: ContextTypes.DEFAULT_TYPE):
  for chat_id, data in list(tracked_products.items()):
    url = data["url"]
    target_price = data["target_price"]

    current_price = get_product_price(url)
    if current_price and current_price <= target_price:
      await context.bot.send_message(
          chat_id=chat_id,
          text=(
              f"🚨 **দাম কমে গেছে!** 🚨\nবর্তমান দাম: ₹{current_price}\nআপনার"
              f" টার্গেট ছিল: ₹{target_price}\n\nলিংক: {url}"
          ),
          parse_mode="Markdown",
      )
      # একবার অ্যালার্ট দেওয়ার পর লিস্ট থেকে মুছে ফেলা হবে
      del tracked_products[chat_id]


def main():
  # এখানে TOKEN ভেরিয়েবলটি টেলিগ্রাম API-এর সাথে কানেক্ট হচ্ছে
  application = ApplicationBuilder().token(TOKEN).build()

  application.add_handler(CommandHandler("start", start))
  application.add_handler(
      MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
  )

  # প্রতি ৩৬০০ সেকেন্ড (১ ঘণ্টা) অন্তর চেক করবে
  application.job_queue.run_repeating(check_prices, interval=3600, first=10)

  print("Bot is running...")
  application.run_polling()


if __name__ == "__main__":
  main()