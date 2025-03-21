import os
import requests
import json
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

# ✅ Función para generar el menú principal
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📷 Instagram OSINT", callback_data="menu_instagram")],
        [InlineKeyboardButton("🛠️ Tools", callback_data="menu_tools")]
    ])

# ✅ Menú de Instagram
def instagram_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Buscar usuario", callback_data="search_instagram")],
        [InlineKeyboardButton("⬅️ Volver", callback_data="back_main")]
    ])

# ✅ Menú de herramientas
def tools_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📧 Email Spoofing", callback_data="email_spoofing")],
        [InlineKeyboardButton("⬅️ Volver", callback_data="back_main")]
    ])

# ✅ Comando /start con menú principal
@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text("👋 ¡Bienvenido!\nSelecciona una opción:", reply_markup=main_menu())

# ✅ Manejo de callbacks para el menú
@app.on_callback_query()
async def menu_navigation(client, callback_query):
    data = callback_query.data

    if data == "menu_instagram":
        await callback_query.message.edit_text("📷 **Instagram OSINT**\nSelecciona una opción:", reply_markup=instagram_menu())

    elif data == "menu_tools":
        await callback_query.message.edit_text("🛠️ **Tools**\nSelecciona una herramienta:", reply_markup=tools_menu())

    elif data == "back_main":
        await callback_query.message.edit_text("👋 ¡Bienvenido!\nSelecciona una opción:", reply_markup=main_menu())

    elif data == "search_instagram":
        await callback_query.message.edit_text("🔎 Envíame el **nombre de usuario** de Instagram.")

        # ✅ Esperar respuesta sin crear un nuevo handler
        response = await client.listen(callback_query.message.chat.id, filters=filters.text, timeout=60)
        if response:
            username = response.text.strip()
            await search_instagram(client, callback_query.message, username)

# ✅ Función para buscar usuarios en Instagram
async def search_instagram(client, message, username):
    await message.reply_text("🔍 Buscando información, espera un momento...")

    data = get_instagram_info(username, SESSION_ID)

    if "error" in data:
        await message.reply_text(f"❌ Error: {data['error']}")
    else:
        info_msg = (
            f"📌 **Usuario:** {data['username']}\n"
            f"📛 **Nombre:** {data['full_name']}\n"
            f"🆔 **ID:** {data['user_id']}\n"
            f"👥 **Seguidores:** {data['followers']}\n"
            f"🔒 **Cuenta privada:** {'Sí' if data['is_private'] else 'No'}\n"
            f"📝 **Bio:** {data['bio']}\n"
            f"📧 **Email público:** {data['public_email']}\n"
            f"📞 **Teléfono público:** {data['public_phone']}\n"
            f"📧 **Correo oculto:** {data['obfuscated_email']}\n"
            f"📞 **Teléfono oculto:** {data['obfuscated_phone']}\n"
        )
        
        await message.reply_text(info_msg)

# ✅ Función para obtener datos de Instagram
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
    
    user_id = user_data.get("id", "Desconocido")
    obfuscated_info = advanced_lookup(username, session_id)
    
    return {
        "username": user_data.get("username", "No disponible"),
        "full_name": user_data.get("full_name", "No disponible"),
        "user_id": user_id,
        "followers": user_data.get("edge_followed_by", {}).get("count", "No disponible"),
        "is_private": user_data.get("is_private", False),
        "bio": user_data.get("biography", "No disponible"),
        "profile_picture": user_data.get("profile_pic_url_hd", "No disponible"),
        "public_email": user_data.get("public_email", "No disponible"),
        "public_phone": user_data.get("public_phone_number", "No disponible"),
        "obfuscated_email": obfuscated_info.get("obfuscated_email", "No disponible"),
        "obfuscated_phone": obfuscated_info.get("obfuscated_phone", "No disponible"),
    }

# ✅ Email Spoofing con Mailgun
@app.on_message(filters.command("spoofemail") & filters.private)
async def spoof_email(client, message):
    args = message.text.split(" ", 4)
    
    if len(args) < 5:
        await message.reply_text("❌ Uso incorrecto.\nFormato correcto:\n`/spoofemail remitente destinatario asunto mensaje`")
        return
    
    from_email, to_email, subject, message_text = args[1], args[2], args[3], args[4]

    response = send_spoofed_email(from_email, to_email, subject, message_text)

    if response.get("message") == "Queued. Thank you.":
        await message.reply_text(f"✅ Correo enviado con éxito de `{from_email}` a `{to_email}`.")
    else:
        await message.reply_text(f"❌ Error al enviar el correo: {response}")

def send_spoofed_email(from_email, to_email, subject, message):
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

# ✅ Ejecutar el bot
if __name__ == "__main__":
    app.run()
