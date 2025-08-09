# app.py — Render Free ready (webhook) + aprendizaje con /estadistica (SQLite)
import os
import sqlite3
from datetime import datetime
from threading import Lock
from flask import Flask, request, jsonify, abort

from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext

# -------------------- Config --------------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")  # obligatorio
BASE_URL = os.environ.get("BASE_URL", "")          # ej. https://tu-servicio.onrender.com
SET_WEBHOOK_ON_START = os.environ.get("SET_WEBHOOK_ON_START", "1")  # en Free conviene dejar "1"

if not TELEGRAM_TOKEN:
    raise RuntimeError("Falta TELEGRAM_TOKEN en variables de entorno.")

WEBHOOK_PATH = f"/webhook/{TELEGRAM_TOKEN}"

# Telegram core
bot = Bot(token=TELEGRAM_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

# Flask app
app = Flask(__name__)

# -------------------- Estado en memoria --------------------
usuarios = {}                # estado conversacional por chat
ajuste_por_chat = {}         # factor dinámico por chat (default 0.932)
last_by_chat = {}            # último cálculo para validar con /estadistica

# -------------------- Persistencia (SQLite) --------------------
DB_PATH = "stats.db"
db_lock = Lock()

def init_db():
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS registros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT,
                chat_id INTEGER,
                nombre TEXT,
                cajas INTEGER,
                tarimas INTEGER,
                unidades INTEGER,
                unidades_utiles INTEGER,
                cajas_seguras INTEGER,
                cajas_por_unidad INTEGER,
                unidades_posibles INTEGER,
                real_cajas INTEGER,
                real_unidades INTEGER
            )
        """)
        conn.commit()
        conn.close()

init_db()

# -------------------- Lógica del bot --------------------
def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    usuarios[chat_id] = {"step": 1}
    context.bot.send_message(chat_id=chat_id, text="👋 ¡Hola! Antes de empezar, ¿cómo te llamas?")

def es_entero(texto: str) -> bool:
    try:
        int(texto)
        return True
    except Exception:
        return False

def message_handler(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    text = (update.message.text or "").strip()

    if chat_id not in usuarios:
        context.bot.send_message(chat_id=chat_id, text="Por favor escribe /start para comenzar.")
        return

    step = usuarios[chat_id]["step"]

    try:
        if step == 1:
            usuarios[chat_id]["nombre"] = text
            usuarios[chat_id]["step"] = 2
            context.bot.send_message(chat_id=chat_id, text=f"✨ Gracias, {text}.")
            context.bot.send_message(
                chat_id=chat_id,
                text=(
                    "Con base en las siguientes preguntas, generaremos una proyección aproximada "
                    "de la facturación por turno para ayudarte a decidir en tiempo real."
                ),
            )
            context.bot.send_message(chat_id=chat_id, text="¿Cuántas tarimas tienes en shipping?")

        elif step == 2:
            if not es_entero(text):
                context.bot.send_message(chat_id=chat_id, text="⚠️ Ingresa un número entero válido para tarimas.")
                return
            usuarios[chat_id]["tarimas"] = int(text)
            usuarios[chat_id]["step"] = 3
            context.bot.send_message(chat_id=chat_id, text="¿Cuántas cajas hay en shipping?")

        elif step == 3:
            if not es_entero(text):
                context.bot.send_message(chat_id=chat_id, text="⚠️ Ingresa un número entero válido para cajas.")
                return

            cajas_ingresadas = int(text)
            if cajas_ingresadas < 20000:
                context.bot.send_message(chat_id=chat_id, text="⚠️ Verifica el número de cajas. ¿Cuántas cajas hay en shipping?")
                return

            usuarios[chat_id]["cajas"] = cajas_ingresadas
            usuarios[chat_id]["step"] = 4
            context.bot.send_message(chat_id=chat_id, text="¿Cuántas unidades tienes en proceso?")

        elif step == 4:
            if not es_entero(text):
                context.bot.send_message(chat_id=chat_id, text="⚠️ Ingresa un número entero válido para unidades.")
                return

            unidades_ingresadas = int(text)
            if unidades_ingresadas == 20:
                context.bot.send_message(chat_id=chat_id, text="❌ No es posible calcular con 20 unidades. Verifica la información. Finalizando sesión.")
                usuarios.pop(chat_id, None)
                return

            usuarios[chat_id]["unidades"] = unidades_ingresadas

            nombre = usuarios[chat_id]["nombre"]
            cajas = usuarios[chat_id]["cajas"]
            tarimas = usuarios[chat_id]["tarimas"]
            unidades = usuarios[chat_id]["unidades"]

            # Ajuste aprendido (default -6.8% -> 0.932)
            ajuste = ajuste_por_chat.get(chat_id, 0.932)
            unidades_utiles = max(unidades - 10, 1)
            cajas_seguras = int(cajas * ajuste)
            cajas_por_unidad = int(cajas_seguras / unidades_utiles)
            unidades_posibles = int(cajas_seguras / 2100)

            evaluacion = (
                "✅ ¡Buen nivel de ocupación! Puedes cerrar las unidades sin riesgo, solo asegura los cierres con tu equipo.\n"
                "⚠️ ¡NO TE OLVIDES DEL LNI!"
                if cajas_por_unidad >= 2100 else
                "⚠️ Riesgo de baja ocupación. Considera pedir tarimas al proceso o buscar cierres seguros.\n"
                "⚠️ ¡NO TE OLVIDES DEL LNI!"
            )

            respuesta = (
                f"🧮 Análisis para {nombre}:\n"
                f"📦 Cajas seguras (ajuste actual {ajuste:.3f}): {cajas_seguras}\n"
                f"🚛 Unidades útiles para cálculo: {unidades_utiles}\n"
                f"📊 Ocupación aproximada: {cajas_por_unidad} cajas por unidad útil\n"
                f"🔢 Con esta ocupación podrías cerrar aproximadamente {unidades_posibles} unidades\n\n"
                f"{evaluacion}"
            )
            context.bot.send_message(chat_id=chat_id, text=respuesta)

            # Guardar último cálculo para /estadistica
            last_by_chat[chat_id] = {
                "ts": datetime.utcnow().isoformat(),
                "chat_id": chat_id,
                "nombre": nombre,
                "cajas": cajas,
                "tarimas": tarimas,
                "unidades": unidades,
                "unidades_utiles": unidades_utiles,
                "cajas_seguras": cajas_seguras,
                "cajas_por_unidad": cajas_por_unidad,
                "unidades_posibles": unidades_posibles,
            }

            usuarios.pop(chat_id, None)

    except Exception as e:
        context.bot.send_message(chat_id=chat_id, text=f"Ocurrió un error inesperado: {e}")
        usuarios.pop(chat_id, None)

def estadistica(update: Update, context: CallbackContext):
    """/estadistica <real_cajas> [real_unidades] — registra el resultado y ajusta el factor."""
    chat_id = update.effective_chat.id
    args = context.args or []

    if chat_id not in last_by_chat:
        context.bot.send_message(chat_id=chat_id,
            text="No tengo un cálculo previo en este chat. Ejecuta primero /start y completa el flujo.")
        return

    if len(args) < 1:
        context.bot.send_message(chat_id=chat_id,
            text="Uso: /estadistica <real_cajas> [real_unidades]\nEjemplo: /estadistica 41000 26")
        return

    # Parseo
    try:
        real_cajas = int(args[0])
        real_unidades = int(args[1]) if len(args) > 1 else None
    except Exception:
        context.bot.send_message(chat_id=chat_id,
            text="Argumentos inválidos. Usa enteros. Ejemplo: /estadistica 41000 26")
        return

    prev = last_by_chat[chat_id]

    # Insertar registro y calcular métricas
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            INSERT INTO registros (
                ts, chat_id, nombre, cajas, tarimas, unidades, unidades_utiles,
                cajas_seguras, cajas_por_unidad, unidades_posibles, real_cajas, real_unidades
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            prev["ts"], prev["chat_id"], prev["nombre"], prev["cajas"], prev["tarimas"],
            prev["unidades"], prev["unidades_utiles"], prev["cajas_seguras"],
            prev["cajas_por_unidad"], prev["unidades_posibles"],
            real_cajas, real_unidades
        ))
        conn.commit()

        # Ajuste por observación: factor observado = real_cajas / cajas_originales
        try:
            factor_obs = real_cajas / max(prev["cajas"], 1)
            # Acotar para evitar saltos bruscos
            factor_obs = max(0.85, min(0.99, factor_obs))
        except Exception:
            factor_obs = 0.932

        # Suavizado exponencial (EMA): nuevo = 0.8 * viejo + 0.2 * observado
        old = ajuste_por_chat.get(chat_id, 0.932)
        nuevo_ajuste = 0.8 * old + 0.2 * factor_obs
        ajuste_por_chat[chat_id] = nuevo_ajuste

        # MAE últimos 10
        c.execute("""
            SELECT cajas_seguras, real_cajas
            FROM registros
            WHERE chat_id = ? AND real_cajas IS NOT NULL
            ORDER BY id DESC
            LIMIT 10
        """, (chat_id,))
        rows = c.fetchall()
        conn.close()

    mae = None
    if rows:
        errores = [abs(cs - rc) for (cs, rc) in rows if rc is not None]
        if errores:
            mae = int(sum(errores) / len(errores))

    msg = [
        "📊 Registro guardado. ¡Gracias por reportar el resultado real!",
        f"• Ajuste actualizado para este chat: {ajuste_por_chat[chat_id]:.4f} (antes 0.932 base)",
    ]
    if mae is not None:
        msg.append(f"• MAE (últimos {len(rows)}): {mae} cajas")

    context.bot.send_message(chat_id=chat_id, text="\n".join(msg))

# Registrar handlers
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("estadistica", estadistica, pass_args=True))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, message_handler))

# -------------------- Rutas Flask --------------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    # Protección simple: path debe incluir el token
    if not request.path.endswith(TELEGRAM_TOKEN):
        abort(403)

    update_json = request.get_json(silent=True, force=True)
    if not update_json:
        return jsonify({"ok": False, "error": "no json"}), 400

    try:
        update = Update.de_json(update_json, bot)
        dispatcher.process_update(update)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 200

    return jsonify({"ok": True}), 200

def set_webhook_if_needed():
    if SET_WEBHOOK_ON_START == "1" and BASE_URL:
        url = f"{BASE_URL}{WEBHOOK_PATH}"
        try:
            bot.delete_webhook()
        except Exception:
            pass
        bot.set_webhook(url)
        print(f"[init] Webhook configurado: {url}")
    else:
        print("[init] Webhook no configurado automáticamente (define BASE_URL y SET_WEBHOOK_ON_START=1).")

# Ejecutar al importar (modo Gunicorn/Render)
set_webhook_if_needed()

# WSGI app
# Render ejecuta: gunicorn app:app
