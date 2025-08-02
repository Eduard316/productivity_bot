
import logging
import asyncio
import nest_asyncio
from flask import Flask
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)
import threading

# Token de tu bot
TOKEN = "7958544063:AAGyM4Mj2QisNpAkwbcyv5TgDKWGqvZr_xU"

# Habilitar logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Soy tu bot de productividad 🚀 (v20.3 con Flask)")

# Iniciar la aplicación de Telegram
async def run_bot():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    await app.run_polling()

# Flask app
flask_app = Flask(__name__)

@flask_app.route('/')
def index():
    return 'Bot funcionando correctamente ✅'

def start_flask():
    flask_app.run(host='0.0.0.0', port=10000)

if __name__ == "__main__":
    # Aplicar patch para evitar conflicto de asyncio con Flask
    nest_asyncio.apply()

    threading.Thread(target=start_flask).start()
    asyncio.run(run_bot())
