from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import subprocess
import asyncio

# Configuración del bot
API_ID = "TU_API_ID"
API_HASH = "TU_API_HASH"
BOT_TOKEN = "TU_BOT_TOKEN"

tg_bot = Client("instagram_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Almacenamiento del SESSION_ID
session_id = None

def get_main_menu():
    """Genera el menú principal con las opciones disponibles."""
    buttons = [[InlineKeyboardButton("Añadir SESSION_ID", callback_data="add_session")]]
    
    if session_id:
        buttons.append([InlineKeyboardButton("Buscar usuario de Instagram", callback_data="search_user")])
    
    return InlineKeyboardMarkup(buttons)

@tg_bot.on_message(filters.command("start"))
def start(client, message):
    """Maneja el comando /start y muestra el menú principal."""
    text = "Bienvenido al bot de Instagram\n\n"
    text += f"SESSION_ID actual: {session_id if session_id else 'No establecido'}\n\n"
    text += "Selecciona una opción:"
    
    message.reply_text(text, reply_markup=get_main_menu())

@tg_bot.on_callback_query()
async def handle_buttons(client, callback_query):
    """Maneja la interacción con los botones."""
    global session_id
    
    if callback_query.data == "add_session":
        await callback_query.message.edit_text("Por favor, envía tu SESSION_ID:")
        
        response = await client.listen(callback_query.message.chat.id, filters=filters.text)
        session_id = response.text
        
        await callback_query.message.reply_text("SESSION_ID guardado correctamente.", reply_markup=get_main_menu())
    
    elif callback_query.data == "search_user":
        if not session_id:
            await callback_query.message.reply_text("Debes introducir un SESSION_ID antes de buscar usuarios.")
            return
        
        await callback_query.message.edit_text("Envíame el nombre de usuario de Instagram que quieres buscar:")
        response = await client.listen(callback_query.message.chat.id, filters=filters.text)
        username = response.text
        
        await callback_query.message.reply_text("Buscando datos... Esto puede tardar unos segundos.")
        
        try:
            result = subprocess.run(["toutatis", "-u", username, "-s", session_id], capture_output=True, text=True)
            output = result.stdout if result.stdout else "No se encontraron datos."
        except Exception as e:
            output = f"Error al ejecutar Toutatis: {e}"
        
        await callback_query.message.reply_text(f"Resultados para @{username}:\n\n{output}", reply_markup=get_main_menu())

if __name__ == "__main__":
    tg_bot.run()
