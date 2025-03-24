import os
import re
import json
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
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

SMTP_SERVER = "smtp-relay.brevo.com"
SMTP_PORT = 587

DEFAULT_SESSION_ID = "71901593608%3Am1xRMM21dKOpV7%3A1%3AAYeufS7hJnkrlZ0gEfhb2jaauxW_NV8Av2jYoRCk3g"
STATE_FILE = "session_ids.json"
user_states = {}

# Cargar sesiones desde disco
def load_sessions():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

# Guardar sesiones
def save_sessions(sessions):
    with open(STATE_FILE, "w") as f:
        json.dump(sessions, f)

user_sessions = load_sessions()

# Validar email
def validate_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email) is not None

# Ofuscar número
def obfuscate_number(phone):
    return f"***{phone[-4:]}" if phone and phone[-4:].isdigit() else "No disponible"

# Enviar correo spoofing
def send_spoof_email(sender, recipient, subject, message):
    msg = MIMEMultipart()
    msg["From"] = "mi_correo@dominio.com"  # Dirección personalizada para el remitente
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

# Obtener datos de Instagram
def get_instagram_info(username, sessionid, user_id=None):
    cookies = {"sessionid": user_sessions.get(str(user_id), DEFAULT_SESSION_ID)}
    headers = {
        "User-Agent": "Mozilla/5.0",
        "x-ig-app-id": "936619743392459"
    }
    url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}"
    try:
        r = requests.get(url, headers=headers, cookies=cookies)
        r.raise_for_status()
        data = r.json().get("data", {}).get("user", {})
        if not data:
            return {"error": "❌ Usuario no encontrado o perfil privado."}

        return {
            "username": data.get("username", "N/A"),
            "full_name": data.get("full_name", "N/A"),
            "user_id": data.get("id", "N/A"),
            "followers": data.get("edge_followed_by", {}).get("count", "N/A"),
            "is_private": data.get("is_private", False),
            "bio": data.get("biography", "N/A"),
            "email": data.get("public_email", "No disponible"),
            "phone": obfuscate_number(data.get("public_phone_number", "")),
            "pfp": data.get("profile_pic_url_hd", None)
        }
    except Exception as e:
        return {"error": f"❌ Error al obtener datos: {e}"}

# Bot
app = Client("osintbot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("start"))
async def start(client, message):
    user_states.pop(message.from_user.id, None)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Instagram", callback_data="instagram")],
        [InlineKeyboardButton("📧 Email Spoofing", callback_data="spoof")],
        [
            InlineKeyboardButton("🧪 Cambiar SessionID", callback_data="set_session"),
            InlineKeyboardButton("🔎 Ver SessionID", callback_data="view_session")
        ],
        [InlineKeyboardButton("🗑️ Eliminar SessionID", callback_data="delete_session")]
    ])
    await message.reply("Bienvenido, elige una opción:", reply_markup=keyboard)

@app.on_callback_query()
async def callback_handler(client, callback_query):
    user_id = callback_query.from_user.id
    data = callback_query.data
    await callback_query.answer()

    if data == "instagram":
        user_states[user_id] = "instagram"
        await callback_query.message.reply("📸 Escribe el nombre de usuario de Instagram.")
    elif data == "spoof":
        user_states[user_id] = {"step": "from"}
        await callback_query.message.reply("✉️ ¿Quién será el remitente?")
    elif data == "set_session":
        user_states[user_id] = "set_session"
        await callback_query.message.reply("🔐 Escribe tu nuevo sessionid para Instagram.")
    elif data == "view_session":
        session = user_sessions.get(str(user_id), DEFAULT_SESSION_ID)
        await callback_query.message.reply(f"🔎 Tu sessionid actual:\n`{session}`", parse_mode="markdown")
    elif data == "delete_session":
        if str(user_id) in user_sessions:
            user_sessions.pop(str(user_id))
            save_sessions(user_sessions)
            await callback_query.message.reply("🗑️ Tu sessionid ha sido eliminado.")
        else:
            await callback_query.message.reply("⚠️ No tienes un sessionid personalizado guardado.")

@app.on_message(filters.text & filters.private)
async def text_handler(client, message):
    user_id = message.from_user.id
    state = user_states.get(user_id)
    text = message.text.strip()

    if not state:
        return await message.reply("Usa /start para comenzar.")

    if state == "instagram":
        await message.reply("🔍 Buscando información...")
        data = get_instagram_info(text, DEFAULT_SESSION_ID, user_id)
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

    elif isinstance(state, dict) and state.get("step") == "from":
        state["from"] = text
        state["step"] = "to"
        await message.reply("✉️ ¿Quién será el destinatario?")
    elif isinstance(state, dict) and state.get("step") == "to":
        state["to"] = text
        state["step"] = "subject"
        await message.reply("📝 ¿Cuál es el asunto?")
    elif isinstance(state, dict) and state.get("step") == "subject":
        state["subject"] = text
        state["step"] = "body"
        await message.reply("💬 Escribe el mensaje del correo:")
    elif isinstance(state, dict) and state.get("step") == "body":
        state["body"] = text
        result = send_spoof_email(state["from"], state["to"], state["subject"], state["body"])
        await message.reply(result)
        user_states.pop(user_id)

    elif state == "set_session":
        user_sessions[str(user_id)] = text
        save_sessions(user_sessions)
        await message.reply("✅ Nuevo sessionid establecido temporalmente.")
        user_states.pop(user_id)

if __name__ == "__main__":
    app.run()
