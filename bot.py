import os
import asyncio
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import subprocess

# Cargar variables del entorno
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Crear cliente de Pyrogram
app = Client("instagram_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Almacenar SESSION_ID temporalmente en memoria
session_data = {}

# Función para generar el menú dinámico
def get_main_menu(chat_id):
    session_id = session_data.get(chat_id, "No configurado")
    
    keyboard = [
        [InlineKeyboardButton("🛠️ Añadir Session ID", callback_data="add_session")],
    ]

    if session_id != "No configurado":
        keyboard.append([InlineKeyboardButton("🔎 Buscar Usuario de Instagram", callback_data="search_user")])
    
    return InlineKeyboardMarkup(keyboard), f"📌 *Session ID actual:* `{session_id}`"

# Manejador para el comando /start
@app.on_message(filters.command("start"))
async def start(client, message):
    menu, text = get_main_menu(message.chat.id)
    await message.reply(text, reply_markup=menu, parse_mode="Markdown")

# Manejador para añadir SESSION_ID
@app.on_callback_query(filters.regex("add_session"))
async def add_session(client, callback_query):
    await callback_query.message.reply("✏️ Envíame tu SESSION_ID para continuar.")
    
    session_response = await client.listen(callback_query.message.chat.id, filters=filters.text)
    
    session_data[callback_query.message.chat.id] = session_response.text
    menu, text = get_main_menu(callback_query.message.chat.id)
    
    await callback_query.message.reply(f"✅ SESSION_ID guardado correctamente.\n{text}", reply_markup=menu, parse_mode="Markdown")

# Manejador para buscar un usuario en Instagram
@app.on_callback_query(filters.regex("search_user"))
async def search_user(client, callback_query):
    chat_id = callback_query.message.chat.id
    session_id = session_data.get(chat_id)

    if not session_id:
        await callback_query.message.reply("⚠️ No tienes un SESSION_ID configurado. Usa el botón 'Añadir Session ID' primero.")
        return

    await callback_query.message.reply("🔎 Envíame el nombre de usuario de Instagram que quieres buscar.")

    user_response = await client.listen(chat_id, filters=filters.text)
    username = user_response.text

    await callback_query.message.reply(f"⏳ Buscando información de {username}...")

    # Ejecutar Toutatis con el SESSION_ID
    command = f"toutatis -u {username} -s {session_id} --json"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    if result.returncode == 0:
        response_text = f"📄 *Resultado para @{username}:*\n```{result.stdout}```"
    else:
        response_text = "❌ No se pudo obtener información o error en la ejecución."

    await callback_query.message.reply(response_text, parse_mode="Markdown")

# Iniciar el bot
app.run()
