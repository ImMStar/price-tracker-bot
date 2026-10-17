import os
import re
import glob
import asyncio
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import yt_dlp
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.environ["BOT_TOKEN"]
MAX_SIZE = 50 * 1024 * 1024  # Telegram bot upload limit: 50 MB
IG_URL = re.compile(r"https?://(?:www\.)?instagram\.com/(?:reel|reels|p|tv)/[\w\-]+[^\s]*")


# ---- tiny web server so Render's free Web Service sees an open port ----
class Health(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *a):
        pass


def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Health).serve_forever()


# ---- downloader ----
def download_video(url: str, out_dir: str) -> str:
    opts = {
        "outtmpl": os.path.join(out_dir, "%(id)s.%(ext)s"),
        "format": "best[ext=mp4]/best",
        "quiet": True,
        "noplaylist": True,
        "max_filesize": MAX_SIZE,
    }
    # Optional: Instagram often needs login cookies. Put cookies.txt next to bot.py
    if os.path.exists("cookies.txt"):
        opts["cookiefile"] = "cookies.txt"
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    files = glob.glob(os.path.join(out_dir, "*"))
    if not files:
        raise RuntimeError("Nothing downloaded")
    return files[0]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send me a public Instagram Reel/Post link and I'll download the video.\n"
        "Only download content you own or have permission to use."
    )


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    match = IG_URL.search(update.message.text or "")
    if not match:
        await update.message.reply_text("Please send a valid Instagram video link.")
        return
    msg = await update.message.reply_text("Downloading... ⏳")
    try:
        with tempfile.TemporaryDirectory() as tmp:
            path = await asyncio.to_thread(download_video, match.group(0), tmp)
            if os.path.getsize(path) > MAX_SIZE:
                await msg.edit_text("Video is larger than Telegram's 50 MB bot limit.")
                return
            with open(path, "rb") as f:
                await update.message.reply_video(f, supports_streaming=True)
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"Failed to download (private post, login required, or link invalid).\n{str(e)[:150]}")


def main():
    threading.Thread(target=run_health_server, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.run_polling()


if __name__ == "__main__":
    main()
