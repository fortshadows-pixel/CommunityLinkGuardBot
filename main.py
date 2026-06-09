async def recibir_limite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el límite de enlaces y guarda toda la configuración"""
    texto = update.message.text.strip()
    
    try:
        # Intentar convertir a número, removiendo espacios y caracteres especiales
        texto_limpio = texto.replace(" ", "").replace(",", "")
        limite = int(texto_limpio)
        
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
    
    except Exception as e:
        print(f"Error en recibir_limite: {e}")
        await update.message.reply_text(
            "❌ Debes indicar un número válido.\n"
            "Ejemplo: 4\n\n"
            f"(Recibí: '{texto}')"
        )
        return CONFIGURAR_LIMITE
