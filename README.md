# Telegram Bot — Render Free (Webhook) + Aprendizaje

Listo para desplegar en **Render Free**. Incluye:
- Flask + `python-telegram-bot` 13.15 en **webhook** (sin polling).
- **/estadistica** para registrar resultado real y **ajustar** el factor (-6.8% → dinámico por chat).
- **SQLite** para pruebas (en Free puede perderse al reiniciar; en prod usar Render Postgres).

## Archivos
- `app.py` — código principal.
- `requirements.txt` — dependencias.
- `Procfile` — comando de arranque.
- `runtime.txt` — versión de Python.

## Variables de entorno (Render → Environment)
- `TELEGRAM_TOKEN` (obligatorio): token del bot.
- `BASE_URL` (opcional pero recomendado): URL pública (ej. `https://tuapp.onrender.com`).
- `SET_WEBHOOK_ON_START` = `1` (por defecto), para que configure el webhook solo.

## Despliegue (plan Free)
1. Crea un **Web Service** en Render y sube estos archivos.
2. En **Environment**, añade:
   - `TELEGRAM_TOKEN` = `xxxxxxxxxxxxxxxxxxxxxxxx`
   - `BASE_URL` = `https://tuapp.onrender.com` (al tener la URL definitiva)
   - `SET_WEBHOOK_ON_START` = `1`
3. Deploy. Comprueba `GET /health` → `{"status":"ok"}`.
4. Abre Telegram y escribe **/start** a tu bot.

> Configuración manual de webhook (opcional):
> ```bash
> curl -X POST "https://api.telegram.org/bot$TELEGRAM_TOKEN/setWebhook" \
>   -d "url=$BASE_URL/webhook/$TELEGRAM_TOKEN"
> ```

## Uso
- Flujo: `/start` → responde preguntas → el bot te envía cálculo.
- Registrar resultado real: `/estadistica 41000 26`
  - Ajusta el **factor** por chat vía EMA (80% viejo + 20% observado).
  - Muestra **MAE** de los últimos 10 registros.

## Notas del plan Free
- Contenedor puede **dormir** tras ~15 min sin tráfico → el bot puede tardar unos segundos en “despertar”.
- **SQLite** no es persistente garantizado. Para producción usa **Render PostgreSQL** y migra la tabla `registros`.

## Migración a Postgres (breve guía)
- Crea un servicio Postgres en Render.
- Reemplaza `sqlite3` por `psycopg` y usa `DATABASE_URL`.
- Ejecuta un script de migración (crear tabla y mover datos).

¡Listo para probar y luego escalar! 🚀
