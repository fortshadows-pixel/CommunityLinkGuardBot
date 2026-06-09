from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    JobQueue,
    ConversationHandler,
)
from telegram import Update, ChatPermissions
from telegram.error import BadRequest
import re
import os
from datetime import time
import pytz
import json

TOKEN = os.getenv("TELEGRAM_TOKEN", "8916338468:AAFF7ZT_tKwgYpBpF8HBMoiv9IhEv3Xev4g")

# Limites por grupo
limites = {}

# Conteo de enlaces por usuario (se reinicia diariamente)
# clave = (grupo_id, usuario_id), valor = cantidad de enlaces hoy
conteo = {}

# Configuración de horarios por grupo
# clave = grupo_id, valor = {'cierre': 'HH:MM', 'apertura': 'HH:MM', 'eliminar': 'HH:MM'}
horarios_config = {}

# Zona horaria Argentina
argentina_tz = pytz.timezone('America/Argentina/Buenos_Aires')

URL_REGEX = r"(https?://\S+|www\.\S+)"

# Estados para conversación
CONFIGURAR_CIERRE, CONFIGURAR_APERTURA, CONFIGURAR_ELIMINAR, CONFIGURAR_LIMITE = range(4)

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
        await update.message.reply_text(f"✅ Límite configurado en {limite} enlaces")
    except:
        await update.message.reply_text("❌ Debes indicar un número.")

async def verlimite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    grupo = update.effective_chat.id
    limite = limites.get(grupo, 4)
    await update.message.reply_text(f"📊 Límite actual: {limite} enlaces")

async def es_moderador(user_id, chat_id, context: ContextTypes.DEFAULT_TYPE):
    """Verifica si el usuario es moderador o admin del grupo"""
    try:
        miembro = await context.bot.get_chat_member(chat_id, user_id)
        # Comprobar si es admin o creador
        return miembro.status in ['administrator', 'creator']
    except:
        return False

async def revisar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    texto = update.message.text or ""

    if not re.search(URL_REGEX, texto):
        return

    grupo = update.effective_chat.id
    usuario = update.effective_user.id
    clave = (grupo, usuario)

    # Contar enlaces para todos (incluyendo moderadores)
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
            print(f"Error: {e}")

async def reiniciar_conteo_diario(context: ContextTypes.DEFAULT_TYPE):
    """Reinicia el conteo de enlaces cada día"""
    global conteo
    conteo = {}
    print("🔄 Conteo de enlaces reiniciado")

async def eliminar_todos_mensajes(context: ContextTypes.DEFAULT_TYPE):
    """Elimina todos los mensajes del grupo y envía mensaje de cierre"""
    job_context = context.job.data
    grupo_id = job_context.get('grupo_id')
    hora_eliminar = job_context.get('hora')
    
    print(f"🕐 Ejecutando tarea: Eliminar todos los mensajes a las {hora_eliminar}")
    
    if grupo_id:
        try:
            # Enviar mensaje de cierre prominente
            await context.bot.send_message(
                chat_id=grupo_id,
                text="🔒 GRUPO CERRADO, HASTA MAS TARDE 🔒",
                parse_mode="HTML"
            )
            
            print(f"✅ Mensaje de cierre enviado para grupo {grupo_id}")
        except Exception as e:
            print(f"❌ Error enviando mensaje de cierre: {e}")

async def cerrar_grupo(context: ContextTypes.DEFAULT_TYPE):
    """Cierra el grupo"""
    job_context = context.job.data
    grupo_id = job_context.get('grupo_id')
    hora_cierre = job_context.get('hora')
    
    print(f"🕐 Ejecutando tarea: Cerrar grupo a las {hora_cierre}")
    
    if grupo_id:
        try:
            # Cerrar el grupo (restringir permisos)
            restricted_permissions = ChatPermissions(
                can_send_messages=False,
                can_send_media_messages=False,
                can_send_polls=False,
                can_send_other_messages=False
            )
            await context.bot.set_chat_permissions(
                chat_id=grupo_id,
                permissions=restricted_permissions
            )
            print(f"✅ Grupo {grupo_id} cerrado a las {hora_cierre}")
        except Exception as e:
            print(f"❌ Error cerrando grupo: {e}")

async def abrir_grupo(context: ContextTypes.DEFAULT_TYPE):
    """Abre el grupo"""
    job_context = context.job.data
    grupo_id = job_context.get('grupo_id')
    hora_apertura = job_context.get('hora')
    
    print(f"🕐 Ejecutando tarea: Abrir grupo a las {hora_apertura}")
    
    if grupo_id:
        try:
            # Abrir el grupo
            allowed_permissions = ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
            await context.bot.set_chat_permissions(
                chat_id=grupo_id,
                permissions=allowed_permissions
            )
            await context.bot.send_message(
                chat_id=grupo_id,
                text=f"🔓 Grupo abierto a las {hora_apertura} (Argentina)"
            )
            print(f"✅ Grupo {grupo_id} abierto")
        except Exception as e:
            print(f"❌ Error abriendo grupo: {e}")

async def configurar_horarios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia configuración de horarios"""
    grupo_id = update.effective_chat.id
    
    # Mostrar horarios actuales
    config_actual = horarios_config.get(grupo_id, {})
    cierre_actual = config_actual.get('cierre', 'No configurado')
    apertura_actual = config_actual.get('apertura', 'No configurado')
    eliminar_actual = config_actual.get('eliminar', 'No configurado')
    limite_actual = limites.get(grupo_id, 4)
    
    texto = (
        "⏰ *Configurar horarios del grupo*\n\n"
        f"🔒 Horario de cierre actual: {cierre_actual}\n"
        f"🗑️ Horario de eliminación actual: {eliminar_actual}\n"
        f"🔓 Horario de apertura actual: {apertura_actual}\n"
        f"📊 Límite de enlaces actual: {limite_actual}\n\n"
        "¿A qué hora deseas que se *cierren los mensajes* del grupo?\n"
        "Formato: HH:MM (ejemplo: 05:00)"
    )
    
    await update.message.reply_text(texto, parse_mode="Markdown")
    return CONFIGURAR_CIERRE

async def recibir_cierre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe la hora de cierre"""
    texto = update.message.text.strip()
    
    # Validar formato HH:MM
    try:
        partes = texto.split(':')
        if len(partes) != 2:
            raise ValueError("Formato inválido")
        
        hora = int(partes[0])
        minuto = int(partes[1])
        
        if hora < 0 or hora > 23 or minuto < 0 or minuto > 59:
            raise ValueError("Hora o minuto fuera de rango")
        
        context.user_data['cierre'] = texto
        
        await update.message.reply_text(
            f"✅ Hora de cierre configurada: {texto}\n\n"
            "Ahora, ¿a qué hora desitas que se *eliminen todos los mensajes*?\n"
            "Formato: HH:MM (ejemplo: 05:05)"
        )
        return CONFIGURAR_ELIMINAR
    
    except:
        await update.message.reply_text(
            "❌ Formato inválido. Por favor usa HH:MM\n"
            "Ejemplo: 05:00"
        )
        return CONFIGURAR_CIERRE

async def recibir_eliminar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe la hora de eliminación"""
    texto = update.message.text.strip()
    
    try:
        partes = texto.split(':')
        if len(partes) != 2:
            raise ValueError("Formato inválido")
        
        hora = int(partes[0])
        minuto = int(partes[1])
        
        if hora < 0 or hora > 23 or minuto < 0 or minuto > 59:
            raise ValueError("Hora o minuto fuera de rango")
        
        context.user_data['eliminar'] = texto
        
        await update.message.reply_text(
            f"✅ Hora de eliminación configurada: {texto}\n\n"
            "Ahora, ¿a qué hora desitas que se *abra* el grupo nuevamente?\n"
            "Formato: HH:MM (ejemplo: 10:30)"
        )
        return CONFIGURAR_APERTURA
    
    except:
        await update.message.reply_text(
            "❌ Formato inválido. Por favor usa HH:MM\n"
            "Ejemplo: 05:05"
        )
        return CONFIGURAR_ELIMINAR

async def recibir_apertura(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe la hora de apertura"""
    texto = update.message.text.strip()
    
    try:
        partes = texto.split(':')
        if len(partes) != 2:
            raise ValueError("Formato inválido")
        
        hora = int(partes[0])
        minuto = int(partes[1])
        
        if hora < 0 or hora > 23 or minuto < 0 or minuto > 59:
            raise ValueError("Hora o minuto fuera de rango")
        
        context.user_data['apertura'] = texto
        
        await update.message.reply_text(
            f"✅ Hora de apertura configurada: {texto}\n\n"
            "Finalmente, ¿cuál será el *límite de enlaces* por usuario?\n"
            "(Número de enlaces permitidos, ejemplo: 4)"
        )
        return CONFIGURAR_LIMITE
    
    except:
        await update.message.reply_text(
            "❌ Formato inválido. Por favor usa HH:MM\n"
            "Ejemplo: 10:30"
        )
        return CONFIGURAR_APERTURA

async def recibir_limite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el límite de enlaces y guarda toda la configuración"""
    texto = update.message.text.strip()
    
    try:
        limite = int(texto)
        
        if limite < 1:
            raise ValueError("El límite debe ser mayor a 0")
        
        grupo_id = update.effective_chat.id
        cierre = context.user_data.get('cierre', '05:00')
        eliminar = context.user_data.get('eliminar', '05:05')
        apertura = context.user_data.get('apertura', '10:30')
        
        # Guardar configuración de horarios
        horarios_config[grupo_id] = {
            'cierre': cierre,
            'eliminar': eliminar,
            'apertura': apertura
        }
        
        # Guardar configuración de límite
        limites[grupo_id] = limite
        
        # Eliminar tareas existentes
        current_jobs = context.job_queue.get_jobs_by_name(f"close_{grupo_id}")
        for job in current_jobs:
            job.schedule_removal()
        
        current_jobs = context.job_queue.get_jobs_by_name(f"delete_{grupo_id}")
        for job in current_jobs:
            job.schedule_removal()
        
        current_jobs = context.job_queue.get_jobs_by_name(f"open_{grupo_id}")
        for job in current_jobs:
            job.schedule_removal()
        
        current_jobs = context.job_queue.get_jobs_by_name(f"reset_{grupo_id}")
        for job in current_jobs:
            job.schedule_removal()
        
        # Programar nuevas tareas
        partes_cierre = cierre.split(':')
        hora_cierre = time(int(partes_cierre[0]), int(partes_cierre[1]), 0)
        
        partes_eliminar = eliminar.split(':')
        hora_eliminar = time(int(partes_eliminar[0]), int(partes_eliminar[1]), 0)
        
        partes_apertura = apertura.split(':')
        hora_apertura = time(int(partes_apertura[0]), int(partes_apertura[1]), 0)
        
        context.job_queue.run_daily(
            cerrar_grupo,
            time=hora_cierre,
            tzinfo=argentina_tz,
            name=f"close_{grupo_id}",
            data={'grupo_id': grupo_id, 'hora': cierre}
        )
        
        context.job_queue.run_daily(
            eliminar_todos_mensajes,
            time=hora_eliminar,
            tzinfo=argentina_tz,
            name=f"delete_{grupo_id}",
            data={'grupo_id': grupo_id, 'hora': eliminar}
        )
        
        context.job_queue.run_daily(
            abrir_grupo,
            time=hora_apertura,
            tzinfo=argentina_tz,
            name=f"open_{grupo_id}",
            data={'grupo_id': grupo_id, 'hora': apertura}
        )
        
        # Programar reinicio de conteo a las 00:00 (medianoche)
        context.job_queue.run_daily(
            reiniciar_conteo_diario,
            time=time(0, 0, 0),
            tzinfo=argentina_tz,
            name=f"reset_{grupo_id}"
        )
        
        await update.message.reply_text(
            f"✅ *Configuración completa guardada*\n\n"
            f"🔒 Cierre: {cierre} (Argentina)\n"
            f"🗑️ Eliminación: {eliminar} (Argentina)\n"
            f"🔓 Apertura: {apertura} (Argentina)\n"
            f"📊 Límite de enlaces: {limite} (para TODOS)\n\n"
            "✨ El conteo se reinicia diariamente a las 00:00\n"
            "Las tareas están activas y se ejecutarán diariamente.",
            parse_mode="Markdown"
        )
        
        return ConversationHandler.END
    
    except:
        await update.message.reply_text(
            "❌ Debes indicar un número válido.\n"
            "Ejemplo: 4"
        )
        return CONFIGURAR_LIMITE

async def ver_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra la configuración actual del grupo"""
    grupo_id = update.effective_chat.id
    config = horarios_config.get(grupo_id, {})
    
    if not config:
        await update.message.reply_text("❌ No hay configuración establecida.\nUsa /config para configurar.")
        return
    
    cierre = config.get('cierre', 'No configurado')
    apertura = config.get('apertura', 'No configurado')
    eliminar = config.get('eliminar', 'No configurado')
    limite = limites.get(grupo_id, 4)
    
    texto = (
        "⏰ *Configuración actual del grupo*\n\n"
        f"🔒 Horario de cierre: {cierre}\n"
        f"🗑️ Horario de eliminación: {eliminar}\n"
        f"🔓 Horario de apertura: {apertura}\n"
        f"📊 Límite de enlaces: {limite} (para TODOS)"
    )
    
    await update.message.reply_text(texto, parse_mode="Markdown")

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela la configuración"""
    await update.message.reply_text("❌ Configuración cancelada.")
    return ConversationHandler.END

async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra la ayuda de comandos"""
    texto = (
        "🤖 *Comandos disponibles*\n\n"
        "/start - Inicia el bot\n"
        "/setlimite <número> - Configura límite de enlaces (ej: /setlimite 4)\n"
        "/verlimite - Muestra el límite actual\n"
        "/config - Configura todo (horarios + límite de enlaces)\n"
        "/verconfig - Muestra la configuración actual\n"
        "/ayuda - Muestra esta ayuda\n\n"
        "📌 *Notas importantes:*\n"
        "• El límite de enlaces se aplica a TODOS (incluyendo moderadores)\n"
        "• El conteo se reinicia diariamente a las 00:00\n"
        "• Los moderadores pueden enviar mensajes cuando el grupo está cerrado\n"
        "• El mensaje 'GRUPO CERRADO, HASTA MAS TARDE' se envía automáticamente"
    )
    await update.message.reply_text(texto, parse_mode="Markdown")

app = Application.builder().token(TOKEN).build()

# Manejador de conversación para configurar horarios
config_handler = ConversationHandler(
    entry_points=[CommandHandler('config', configurar_horarios)],
    states={
        CONFIGURAR_CIERRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_cierre)],
        CONFIGURAR_ELIMINAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_eliminar)],
        CONFIGURAR_APERTURA: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_apertura)],
        CONFIGURAR_LIMITE: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_limite)],
    },
    fallbacks=[CommandHandler('cancelar', cancelar)],
)

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("setlimite", setlimite))
app.add_handler(CommandHandler("verlimite", verlimite))
app.add_handler(CommandHandler("verconfig", ver_config))
app.add_handler(CommandHandler("ayuda", ayuda))
app.add_handler(config_handler)

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        revisar_mensaje
    )
)

print("🤖 Bot iniciado...")
app.run_polling()
