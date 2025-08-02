
from flask import Flask
import threading
import telegram
from telegram.ext import CommandHandler, MessageHandler, Filters, Updater

TOKEN = '7958544063:AAGyM4Mj2QisNpAkwbcyv5TgDKWGqvZr_xU'

bot = telegram.Bot(token=TOKEN)
updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher

def start(update, context):
    update.message.reply_text('¡Hola! Soy tu bot de productividad 🚀')

dispatcher.add_handler(CommandHandler('start', start))

app = Flask(__name__)

@app.route('/')
def index():
    return 'Bot funcionando'

def run_bot():
    updater.start_polling()

if __name__ == '__main__':
    threading.Thread(target=run_bot).start()
    app.run(host='0.0.0.0', port=10000)
