import os
import requests
import json
import asyncio
from urllib.parse import quote_plus
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SESSION_ID = os.getenv("SESSION_ID")
MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY")
MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN")

# Configuración del bot
app = Client(
    "osint_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

user_states = {}

# Función para obtener datos de Instagram
def get_instagram_info(username, session_id):
    headers = {"User-Agent": "Instagram 101.0.0.15.120", "x-ig-app-id": "936619743392459"}
    cookies = {"sessionid": session_id}
    
    profile_url = f'https://i.instagram.com/api/v1/users/web_profile_info/?username={username}'
    response = requests.get(profile_url, headers=headers, cookies=cookies)
    
    if response.status_code == 404:
        return {"error": "Usuario no encontrado"}
    
    user_data = response.json().get("data", {}).get("user", {})
    if not user_data:
        return {"error": "No se pudo obtener información del usuario"}
    
    return {
        "username": user_data.get("username", "No disponible"),
        "full_name": user_data.get("full_name", "No disponible"),
        "user_id": user_data.get("id", "Desconocido"),
        "followers": user_data.get("edge_followed_by", {}).get("count", "No disponible"),
        "is_private": user_data.get("is_private", False),
        "bio": user_data.get("biography", "No disponible"),
        "profile_picture": user_data.get("profile_pic_url_hd", "No disponible")
    }

# Enviar email spoof usando Mailgun
def send_spoof_email(to_email, from_email, subject, message):
    url = f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages"
    auth = ("api", MAILGUN_API_KEY)
    data = {
        "from": from_email,
        "to": to_email,
        "subject": subject,
        "text": message
    }
    response = requests.post(url, auth=auth, data=data)
    return response.json()

# Menú principal
def main_menu():
    botones = [
        [InlineKeyboardButton("🔎 Buscar usuario de Instagram", callback_data="search_user")],
        [InlineKeyboardButton("📧 Email Spoof", callback_data="email_spoof")],
        [InlineKeyboardButton("🔑 Cambiar SESSION_ID", callback_data="change_session")]
    ]
    return InlineKeyboardMarkup(botones)

@app.on_message(filters.command("start"))
async def start(client, message):
    user_states[message.chat.id] = None
    await message.reply_text(
        "🌟 Bienvenido al bot OSINT! 🔍\nSelecciona una opción:",
        reply_markup=main_menu()
    )

@app.on_callback_query(filters.regex("search_user"))
async def search_user(client, callback_query):
    user_states[callback_query.message.chat.id] = "search_user"
    await callback_query.message.edit_text("🔍 Envíame el **nombre de usuario** de Instagram.")

@app.on_callback_query(filters.regex("email_spoof"))
async def email_spoof(client, callback_query):
    user_states[callback_query.message.chat.id] = "email_spoof"
    await callback_query.message.edit_text("📧 Envíame el correo del destinatario.")

@app.on_callback_query(filters.regex("change_session"))
async def change_session(client, callback_query):
    user_states[callback_query.message.chat.id] = "change_session"
    await callback_query.message.edit_text("🔑 Envíame el nuevo SESSION_ID.")

@app.on_message(filters.text & filters.private)
async def handle_user_input(client, message):
    user_id = message.chat.id
    state = user_states.get(user_id)
    
    try:
        if state == "search_user":
            username = message.text.strip()
            await message.reply_text("🔍 Buscando información...")
            data = get_instagram_info(username, SESSION_ID)
            if "error" in data:
                await message.reply_text(f"❌ Error: {data['error']}")
            else:
                info_msg = f"📌 **Usuario:** {data['username']}\n📛 **Nombre:** {data['full_name']}\n🆔 **ID:** {data['user_id']}\n👥 **Seguidores:** {data['followers']}\n🔒 **Privado:** {'Sí' if data['is_private'] else 'No'}\n📝 **Bio:** {data['bio']}"
                await message.reply_photo(photo=data['profile_picture'], caption=info_msg)
            user_states[user_id] = None
        
        elif state == "change_session":
            global SESSION_ID
            SESSION_ID = message.text.strip()
            os.environ["SESSION_ID"] = SESSION_ID
            await message.reply_text(f"✅ Nuevo SESSION_ID guardado.")
            user_states[user_id] = None
        
        else:
            await message.reply_text("⚠️ Opción no válida. Usa /start para volver al menú.")
    
    except FloodWait as e:
        await asyncio.sleep(e.value)
        await message.reply_text("⚠️ Se ha detectado un exceso de solicitudes. Esperando...")

# Ejecutar el bot
if __name__ == "__main__":
    app.run()
