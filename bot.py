# -*- coding: utf-8 -*-
import nest_asyncio
import pandas as pd
from datetime import datetime
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

nest_asyncio.apply()

# === CONFIGURACIÓN ===
TOKEN = "7958544063:AAGyM4Mj2QisNpAkwbcyv5TgDKWGqvZr_xU"

# === BASE DE DATOS EN MEMORIA ===
user_data = {}
historial = []

# === /start con presentación ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_data[chat_id] = {"step": "nombre"}

    bienvenida = (
        "👋 *Bienvenido al Bot de Productividad*\n\n"
        "Este bot te ayudará a calcular la **productividad por turno** en segundos.\n\n"
        "Solo responde unas preguntas sencillas y te mostraré:\n"
        "📦 Ocupación aproximada por unidad\n"
        "🧾 Facturación estimada\n"
        "🧮 Unidades necesarias para cumplir con mínimo 2100 cajas por unidad\n\n"
        "*Por favor, dime tu nombre o turno responsable para comenzar:*"
    )
    await update.message.reply_text(bienvenida, parse_mode="Markdown")

# === Flujo de preguntas ===
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text
    data = user_data.get(chat_id)

    if not data:
        await update.message.reply_text("Usa el comando /start para comenzar.")
        return

    step = data.get("step")

    if step == "nombre":
        data["nombre"] = text.strip()
        data["step"] = "tarimas"
        await update.message.reply_text(f"✅ Nombre registrado: *{data['nombre']}*\n\n¿Cuántas TARIMAS tienes en el turno?", parse_mode="Markdown")

    elif step == "tarimas":
        if not text.isdigit():
            await update.message.reply_text("❗ Ingresa solo números para las tarimas.")
            return
        data["tarimas"] = int(text)
        data["step"] = "cajas"
        await update.message.reply_text("¿Cuántas CAJAS tienes en shipping?")

    elif step == "cajas":
        if not text.isdigit():
            await update.message.reply_text("❗ Ingresa solo números para las cajas.")
            return
        data["cajas"] = int(text)
        data["step"] = "unidades"
        await update.message.reply_text("¿Cuántas UNIDADES se formaron?")

    elif step == "unidades":
        if not text.isdigit():
            await update.message.reply_text("❗ Ingresa solo números para las unidades.")
            return
        data["unidades"] = int(text)

        tarimas = data["tarimas"]
        cajas = data["cajas"]
        unidades = data["unidades"]
        nombre = data["nombre"]
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        unidades_utiles = unidades - 10
        if unidades_utiles <= 0:
            await update.message.reply_text("❌ Las unidades deben ser mayores a 10 para un cálculo válido.")
            return

        cajas_por_tarima = cajas / tarimas
        tarimas_por_unidad = tarimas / unidades_utiles
        ocupacion_real = round(cajas_por_tarima * tarimas_por_unidad)
        unidades_requeridas = cajas // 2100

        await update.message.reply_text(
            f"📊 *Resultados estimados del turno para {nombre}*:\n\n"
            f"1️⃣ Ocupación actual: *{ocupacion_real} cajas por unidad*\n"
            f"2️⃣ Unidades útiles recomendadas (mín. 2100): *{unidades_requeridas}*\n"
            f"📦 Facturación estimada: *{cajas} cajas*\n"
            f"🕒 Fecha y hora: {fecha}",
            parse_mode="Markdown"
        )

        historial.append({
            "nombre": nombre,
            "tarimas": tarimas,
            "cajas": cajas,
            "unidades_formadas": unidades,
            "unidades_utiles": unidades_utiles,
            "ocupacion_real": ocupacion_real,
            "unidades_recomendadas_2100": unidades_requeridas,
            "fecha_hora": fecha
        })

        keyboard = [
            [InlineKeyboardButton("🔁 Hacer otro cálculo", callback_data="repetir")],
            [InlineKeyboardButton("❌ Terminar", callback_data="terminar")]
        ]
        await update.message.reply_text("¿Qué deseas hacer ahora?", reply_markup=InlineKeyboardMarkup(keyboard))

        data["step"] = "finalizado"

# === Botones ===
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id

    if query.data == "repetir":
        user_data[chat_id] = {"step": "nombre"}
        await query.edit_message_text("🔄 Nuevo cálculo.\n\n👤 Por favor, dime tu *nombre*:", parse_mode="Markdown")

    elif query.data == "terminar":
        nombre = user_data[chat_id].get("nombre", "usuario")
        user_data.pop(chat_id, None)
        await query.edit_message_text(f"✅ Gracias, *{nombre}*, por usar el bot. ¡Hasta pronto!", parse_mode="Markdown")

# === Comando /id ===
async def show_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    username = update.effective_user.username
    await update.message.reply_text(
        f"🆔 Tu ID: `{uid}`\n👤 Tu username: @{username or 'no definido'}",
        parse_mode="Markdown"
    )

# === Comando /reporte ===
async def enviar_reporte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not historial:
        await update.message.reply_text("No hay datos aún para generar el reporte.")
        return

    df = pd.DataFrame(historial)
    buffer = BytesIO()
    df.to_csv(buffer, index=False, encoding='utf-8-sig')
    buffer.seek(0)

    await update.message.reply_document(
        document=InputFile(buffer, filename="reporte_productividad.csv"),
        filename="reporte_productividad.csv",
        caption="📊 Aquí está el reporte de productividad."
    )

# === Handlers ===
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("id", show_id))
app.add_handler(CommandHandler("reporte", enviar_reporte))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
app.add_handler(CallbackQueryHandler(button_handler))

# === Ejecutar ===
import asyncio
asyncio.run(app.run_polling())
