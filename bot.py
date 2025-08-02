
import logging
import asyncio
from flask import Flask
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)
import threading

# Configura tu token aquí
TOKEN = "7958544063:AAGyM4Mj2QisNpAkwbcyv5TgDKWGqvZr_xU"

# Activar logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Soy tu bot de productividad 🚀 (versión async)")

# Crear la app de Telegram
async def run_bot():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    await app.run_polling()

# Servidor Flask para mantener vivo el bot
flask_app = Flask(__name__)

@flask_app.route('/')
def index():
    return 'Bot funcionando (async)'

def start_flask():
    flask_app.run(host='0.0.0.0', port=10000)

if __name__ == "__main__":
    threading.Thread(target=start_flask).start()
    asyncio.run(run_bot())
