import os
import re
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# Cargar .env
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SESSION_ID = os.getenv("SESSION_ID")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

SMTP_SERVER = "smtp-relay.brevo.com"
SMTP_PORT = 587

user_states = {}
user_sessions = {}

# Validador de email
def validate_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email) is not None

# Formateo de número con ofuscado
def obfuscate_number(phone):
    return f"***{phone[-4:]}" if phone and phone[-4:].isdigit() else "No disponible"

# Enviar email spoofing
def send_spoof_email(sender, recipient, subject, message):
    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(message, "plain"))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(sender, recipient, msg.as_string())
        server.quit()
        return "✅ Correo enviado correctamente."
    except Exception as e:
        return f"❌ Error al enviar el correo: {str(e)}"

# Extraer info de Instagram
def get_instagram_info(username, sessionid, user_id=None):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "x-ig-app-id": "936619743392459"
    }
    cookies = {
        "sessionid": user_sessions.get(user_id, sessionid)
    }

    url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}"
    try:
        r = requests.get(url, headers=headers, cookies=cookies)
        r.raise_for_status()
    except Exception as e:
        return {"error": f"❌ Error al obtener datos: {e}"}

    data = r.json().get("data", {}).get("user", {})
    if not data:
        return {"error": "❌ Usuario no encontrado o perfil privado."}

    # Extracción segura
    return {
        "username": data.get("username", "N/A"),
        "full_name": data.get("full_name", "N/A"),
        "user_id": data.get("id", "N/A"),
        "followers": data.get("edge_followed_by", {}).get("count", "N/A"),
        "is_private": data.get("is_private", False),
        "bio": data.get("biography", "N/A"),
        "email": data.get("public_email", "No disponible"),
        "phone": obfuscate_number(data.get("public_phone_number", "")),
        "pfp": data.get("profile_pic_url_hd", None),
    }

# Iniciar bot
app = Client("osintbot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# /start con botones
@app.on_message(filters.command("start"))
async def start(client, message):
    user_states.pop(message.from_user.id, None)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Instagram", callback_data="instagram")],
        [InlineKeyboardButton("📧 Email Spoofing", callback_data="spoof")],
        [InlineKeyboardButton("🧪 Cambiar SessionID", callback_data="set_session")]
    ])
    await message.reply("Bienvenido, elige una opción:", reply_markup=keyboard)

# Manejo de botones
@app.on_callback_query()
async def callback_handler(client, callback_query):
    user_id = callback_query.from_user.id
    data = callback_query.data

    await callback_query.answer()  # IMPORTANTE

    if data == "instagram":
        user_states[user_id] = "instagram"
        await callback_query.message.reply("📸 Escribe el nombre de usuario de Instagram.")

    elif data == "spoof":
        user_states[user_id] = "spoof"
        await callback_query.message.reply(
            "✉️ Envíame el correo en este formato:\n`remitente|destinatario|asunto|mensaje`", parse_mode="markdown"
        )

    elif data == "set_session":
        user_states[user_id] = "set_session"
        await callback_query.message.reply("🔐 Escribe tu nuevo sessionid para Instagram.")

# Procesar entrada de texto
@app.on_message(filters.text & filters.private)
async def text_handler(client, message):
    user_id = message.from_user.id
    state = user_states.get(user_id)

    if not state:
        return await message.reply("Usa /start para comenzar.")

    text = message.text.strip()

    if state == "instagram":
        await message.reply("🔍 Buscando información...")
        data = get_instagram_info(text, SESSION_ID, user_id)

        if "error" in data:
            await message.reply(data["error"])
        else:
            info = (
                f"👤 Usuario: `{data['username']}`\n"
                f"📛 Nombre: {data['full_name']}\n"
                f"🆔 ID: {data['user_id']}\n"
                f"👥 Seguidores: {data['followers']}\n"
                f"🔐 Privado: {'Sí' if data['is_private'] else 'No'}\n"
                f"📝 Bio: {data['bio']}\n"
                f"📧 Email: {data['email']}\n"
                f"📞 Teléfono: {data['phone']}\n"
            )
            if data["pfp"]:
                await message.reply_photo(data["pfp"], caption=info, parse_mode="markdown")
            else:
                await message.reply(info, parse_mode="markdown")

        user_states.pop(user_id)

    elif state == "spoof":
        parts = text.split("|")
        if len(parts) != 4:
            return await message.reply("❌ Formato incorrecto. Usa:\n`remitente|destinatario|asunto|mensaje`", parse_mode="markdown")
        remitente, destino, asunto, cuerpo = map(str.strip, parts)
        result = send_spoof_email(remitente, destino, asunto, cuerpo)
        await message.reply(result)
        user_states.pop(user_id)

    elif state == "set_session":
        user_sessions[user_id] = text
        await message.reply("✅ Nuevo sessionid establecido temporalmente.")
        user_states.pop(user_id)

# Lanzar bot
if __name__ == "__main__":
    app.run()
