# CommunityLinkGuardBot 🛡️

Bot de Telegram que controla y limita el número de enlaces en grupos.

## Comandos

- `/start` - Inicia el bot
- `/setlimite <número>` - Establece el límite de enlaces por usuario (ej: `/setlimite 4`)
- `/verlimite` - Muestra el límite actual del grupo

## Características

✅ Controla el número de enlaces por usuario  
✅ Elimina mensajes que exceden el límite  
✅ Configurable por grupo  
✅ Límite por defecto: 4 enlaces  

## Despliegue en Railway

1. Ve a [railway.app](https://railway.app)
2. Conecta tu repositorio de GitHub
3. Añade la variable de entorno:
   - `TELEGRAM_TOKEN` = Tu token de bot

## Variables de Entorno

```
TELEGRAM_TOKEN=tu_token_aqui
```

## Instalación Local

```bash
pip install -r requirements.txt
python main.py
```
