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
SESSION_ID = os.getenv("SESSION_ID")  # Cargar SESSION_ID desde .env
MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY")
MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN")

# Configuración del bot
app = Client(
    "osint_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Función para enviar correos electrónicos falsificados con Mailgun
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

# Comando para enviar correos falsificados
@app.on_message(filters.command("spoofemail") & filters.private)
async def spoof_email(client, message):
    args = message.text.split(" ", 4)  # Separa en máximo 5 partes
    
    if len(args) < 5:
        await message.reply_text("❌ Uso incorrecto.\nFormato correcto:\n`/spoofemail remitente destinatario asunto mensaje`")
        return
    
    from_email, to_email, subject, message_text = args[1], args[2], args[3], args[4]

    response = send_spoofed_email(from_email, to_email, subject, message_text)

    if response.get("message") == "Queued. Thank you.":
        await message.reply_text(f"✅ Correo enviado con éxito de `{from_email}` a `{to_email}`.")
    else:
        await message.reply_text(f"❌ Error al enviar el correo: {response}")

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

# Función para obtener datos de correo y teléfono ocultos
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

# Comando para buscar un usuario de Instagram
@app.on_message(filters.command("insta") & filters.private)
async def search_instagram(client, message):
    args = message.text.split(" ", 1)
    
    if len(args) < 2:
        await message.reply_text("❌ Uso incorrecto.\nFormato correcto:\n`/insta usuario`")
        return
    
    username = args[1]
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

# Ejecutar el bot
if __name__ == "__main__":
    app.run()
