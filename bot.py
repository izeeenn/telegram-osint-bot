import os
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_ID = os.getenv("SESSION_ID")  # Instagram sessionid

# Configuración del cliente de Pyrogram
app = Client(
    "osint_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Función para obtener información de Instagram
def get_instagram_info(username, session_id):
    headers = {"User-Agent": "iphone_ua", "x-ig-app-id": "936619743392459"}
    api = requests.get(
        f'https://i.instagram.com/api/v1/users/web_profile_info/?username={username}',
        headers=headers,
        cookies={'sessionid': session_id}
    )

    try:
        if api.status_code == 404:
            return {"error": "❌ Usuario no encontrado"}

        user = api.json()["data"]['user']
        return {
            "username": user.get("username", "N/A"),
            "id": user.get("id", "N/A"),
            "full_name": user.get("full_name", "N/A"),
            "is_verified": user.get("is_verified", False),
            "is_private": user.get("is_private", False),
            "followers": user.get("edge_followed_by", {}).get("count", "N/A"),
            "following": user.get("edge_follow", {}).get("count", "N/A"),
            "bio": user.get("biography", "N/A"),
            "profile_pic": user.get("profile_pic_url_hd", "N/A"),
            "external_url": user.get("external_url", "N/A"),
        }

    except requests.exceptions.RequestException:
        return {"error": "❌ No se pudo obtener la información"}

# Comando /start
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(
        "👋 ¡Bienvenido al bot de OSINT para Instagram!\n\n"
        "🔍 Puedes buscar información pública de un usuario de Instagram.\n"
        "⚠️ Úsalo de forma ética y responsable.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📖 Panel de Ayuda", callback_data="help")],
            [InlineKeyboardButton("🔍 Buscar Usuario", callback_data="search_user")]
        ])
    )

# Menú de ayuda
@app.on_callback_query(filters.regex("help"))
async def help_panel(client, callback_query):
    await callback_query.message.edit_text(
        "ℹ️ **Panel de Ayuda**\n\n"
        "🔹 _¿Qué hace este bot?_ \n"
        "Este bot utiliza la API privada de Instagram para extraer información pública de un usuario.\n\n"
        "🛠 **¿Cómo usarlo?**\n"
        "1️⃣ Pulsa en *Buscar Usuario*.\n"
        "2️⃣ Envía el nombre de usuario de Instagram.\n"
        "3️⃣ Recibirás la información disponible.\n\n"
        "✅ **Ejemplo de uso:**\n"
        "```\n"
        "instagram_username\n"
        "```",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Volver al menú", callback_data="back")]
        ])
    )

# Volver al menú principal
@app.on_callback_query(filters.regex("back"))
async def back_to_main(client, callback_query):
    await start(client, callback_query.message)

# Solicitar el nombre de usuario
@app.on_callback_query(filters.regex("search_user"))
async def request_username(client, callback_query):
    await callback_query.message.edit_text(
        "📝 Por favor, envíame el nombre de usuario de Instagram.\n\n"
        "Ejemplo: `instagram`",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Volver al menú", callback_data="back")]
        ])
    )

# Procesar el nombre de usuario y buscar información
@app.on_message(filters.text & ~filters.command(["start", "help"]))
async def handle_instagram_username(client, message):
    username = message.text.strip()

    await message.reply_text("⏳ Buscando información...")

    data = get_instagram_info(username, SESSION_ID)

    if "error" in data:
        await message.reply_text(data["error"])
        return

    info = (
        f"📊 **Resultados de Instagram**\n\n"
        f"👤 **Usuario:** @{data['username']}\n"
        f"🆔 **ID:** {data['id']}\n"
        f"📛 **Nombre Completo:** {data['full_name']}\n"
        f"✅ **Verificado:** {'Sí' if data['is_verified'] else 'No'}\n"
        f"🔒 **Cuenta Privada:** {'Sí' if data['is_private'] else 'No'}\n"
        f"👥 **Seguidores:** {data['followers']}\n"
        f"➡️ **Siguiendo:** {data['following']}\n"
        f"📄 **Biografía:** {data['bio']}\n"
        f"🌐 **URL Externa:** {data['external_url'] if data['external_url'] else 'Ninguna'}"
    )

    await message.reply_photo(photo=data["profile_pic"], caption=info)

# Ejecutar el bot
if __name__ == "__main__":
    app.run()
