from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)
from telegram import Update
from telegram.ext import ContextTypes
import re
import os

TOKEN = os.getenv("TELEGRAM_TOKEN", "8916338468:AAFF7ZT_tKwgYpBpF8HBMoiv9IhEv3Xev4g")

# Limites por grupo
limites = {}

# Conteo de enlaces por usuario
# clave = (grupo_id, usuario_id)
conteo = {}

URL_REGEX = r"(https?://\S+|www\.\S+)"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot activo.")

async def setlimite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /setlimite 4")
        return

    try:
        limite = int(context.args[0])

        grupo = update.effective_chat.id

        limites[grupo] = limite

        await update.message.reply_text(
            f"Límite configurado en {limite}"
        )

    except:
        await update.message.reply_text("Debes indicar un número.")

async def verlimite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    grupo = update.effective_chat.id

    limite = limites.get(grupo, 4)

    await update.message.reply_text(
        f"Límite actual: {limite}"
    )

async def revisar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    texto = update.message.text or ""

    if not re.search(URL_REGEX, texto):
        return

    grupo = update.effective_chat.id
    usuario = update.effective_user.id

    clave = (grupo, usuario)

    conteo[clave] = conteo.get(clave, 0) + 1

    limite = limites.get(grupo, 4)

    if conteo[clave] > limite:

        try:
            await update.message.delete()

            await context.bot.send_message(
                chat_id=grupo,
                text=f"⚠️ Has superado el límite de {limite} enlaces."
            )

        except Exception as e:
            print(e)

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("setlimite", setlimite))
app.add_handler(CommandHandler("verlimite", verlimite))

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        revisar_mensaje
    )
)

print("Bot iniciado...")
app.run_polling()
