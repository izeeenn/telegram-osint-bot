import os
import requests
import json
import asyncio
from urllib.parse import quote_plus
from pyrogram import Client, filters
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
    
    obfuscated_info = advanced_lookup(username, session_id)

    return {
        "username": user_data.get("username", "No disponible"),
        "full_name": user_data.get("full_name", "No disponible"),
        "user_id": user_data.get("id", "Desconocido"),
        "followers": user_data.get("edge_followed_by", {}).get("count", "No disponible"),
        "is_private": user_data.get("is_private", False),
        "bio": user_data.get("biography", "No disponible"),
        "profile_picture": user_data.get("profile_pic_url_hd", "No disponible"),
        "public_email": user_data.get("public_email", "No disponible"),
        "public_phone": user_data.get("public_phone_number", "No disponible"),
        "obfuscated_email": obfuscated_info.get("obfuscated_email", "No disponible"),
        "obfuscated_phone": obfuscated_info.get("obfuscated_phone", "No disponible"),
    }

# Función para obtener datos ocultos de Instagram
def advanced_lookup(username, session_id):
    data = "signed_body=SIGNATURE." + quote_plus(json.dumps({"q": username, "skip_recovery": "1"}))
    headers = {
        "User-Agent": "Instagram 101.0.0.15.120",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }
    response = requests.post("https://i.instagram.com/api/v1/users/lookup/", headers=headers, data=data, cookies={"sessionid": session_id})
    
    try:
        return response.json()
    except json.JSONDecodeError:
        return {"error": "Rate limit"}

# Función para enviar correos falsificados
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
        [InlineKeyboardButton("🔑 Cambiar SESSION_ID", callback_data="change_session")],
        [InlineKeyboardButton("📧 Email Spoofing", callback_data="email_spoof")]
    ]
    return InlineKeyboardMarkup(botones)

# Comando /start
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(
        f"🌟 **SESSION_ID actual:** `{SESSION_ID}`\n\n"
        "¡Bienvenido! 🔍\nSelecciona una opción:",
        reply_markup=main_menu()
    )

# Callback para buscar usuario
@app.on_callback_query(filters.regex("search_user"))
async def search_user(client, callback_query):
    chat_id = callback_query.message.chat.id
    await callback_query.message.edit_text("🔍 Envíame el **nombre de usuario** de Instagram:")

    username_msg = await app.listen(chat_id, filters.text)
    username = username_msg.text.strip()
    
    await username_msg.reply_text("🔍 Buscando información, espera un momento...")
    data = get_instagram_info(username, SESSION_ID)

    if "error" in data:
        await username_msg.reply_text(f"❌ Error: {data['error']}")
    else:
        info_msg = (
            f"📌 **Usuario:** {data['username']}\n"
            f"📛 **Nombre:** {data['full_name']}\n"
            f"🆔 **ID:** {data['user_id']}\n"
            f"👥 **Seguidores:** {data['followers']}\n"
            f"🔒 **Cuenta privada:** {'Sí' if data['is_private'] else 'No'}\n"
            f"📝 **Bio:** {data['bio']}\n"
            f"📧 **Email oculto:** {data['obfuscated_email']}\n"
            f"📞 **Teléfono oculto:** {data['obfuscated_phone']}\n"
        )
        await username_msg.reply_photo(
            photo=data['profile_picture'],
            caption=info_msg
        )

# Callback para cambiar SESSION_ID
@app.on_callback_query(filters.regex("change_session"))
async def change_session(client, callback_query):
    chat_id = callback_query.message.chat.id
    await callback_query.message.edit_text("🔐 Envíame el **nuevo SESSION_ID**.")

    new_session_msg = await app.listen(chat_id, filters.text)
    global SESSION_ID
    SESSION_ID = new_session_msg.text.strip()
    
    await new_session_msg.reply_text(f"✅ Nuevo SESSION_ID guardado: `{SESSION_ID}`")
    await new_session_msg.reply_text("🌟 **Menú principal:**", reply_markup=main_menu())

# Callback para email spoofing
@app.on_callback_query(filters.regex("email_spoof"))
async def email_spoof(client, callback_query):
    chat_id = callback_query.message.chat.id
    await callback_query.message.edit_text("✉️ Envíame el email en formato: `destino,origen,asunto,mensaje`")

    email_msg = await app.listen(chat_id, filters.text)
    to_email, from_email, subject, message = email_msg.text.split(",")

    result = send_spoof_email(to_email.strip(), from_email.strip(), subject.strip(), message.strip())

    await email_msg.reply_text(f"📨 **Email enviado**\n🔹 Estado: {result['message']}")

# Ejecutar el bot
if __name__ == "__main__":
    app.run()
