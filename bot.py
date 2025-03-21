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
MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY")
MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN")

SESSION_ID = os.getenv("SESSION_ID")  # Se carga desde .env

# Configuración del bot
app = Client(
    "osint_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Obtener información de Instagram
def get_instagram_info(username, session_id):
    headers = {"User-Agent": "Instagram 101.0.0.15.120", "x-ig-app-id": "936619743392459"}
    cookies = {"sessionid": session_id}

    # Datos básicos del usuario
    profile_url = f'https://i.instagram.com/api/v1/users/web_profile_info/?username={username}'
    response = requests.get(profile_url, headers=headers, cookies=cookies)

    if response.status_code == 404:
        return {"error": "Usuario no encontrado"}

    user_data = response.json().get("data", {}).get("user", {})
    if not user_data:
        return {"error": "No se pudo obtener información del usuario"}

    # Obtener teléfono y email obfuscado
    obfuscated_info = get_obfuscated_info(username, session_id)

    return {
        "username": user_data.get("username", "No disponible"),
        "full_name": user_data.get("full_name", "No disponible"),
        "user_id": user_data.get("id", "No disponible"),
        "followers": user_data.get("edge_followed_by", {}).get("count", "No disponible"),
        "is_private": user_data.get("is_private", False),
        "bio": user_data.get("biography", "No disponible"),
        "profile_picture": user_data.get("profile_pic_url_hd", "No disponible"),
        "obfuscated_email": obfuscated_info.get("obfuscated_email", "No disponible"),
        "obfuscated_phone": obfuscated_info.get("obfuscated_phone", "No disponible"),
    }

# Obtener datos obfuscados (teléfono y email)
def get_obfuscated_info(username, session_id):
    data = "signed_body=SIGNATURE." + quote_plus(json.dumps({"q": username, "skip_recovery": "1"}))
    headers = {
        "User-Agent": "Instagram 101.0.0.15.120",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }

    response = requests.post("https://i.instagram.com/api/v1/users/lookup/", headers=headers, data=data, cookies={"sessionid": session_id})

    try:
        result = response.json()
        return {
            "obfuscated_email": result.get("obfuscated_email", "No disponible"),
            "obfuscated_phone": result.get("obfuscated_phone", "No disponible")
        }
    except json.JSONDecodeError:
        return {"error": "Rate limit alcanzado"}

# Enviar Email Spoofing con Mailgun
def send_spoof_email(to_email, from_email, subject, body):
    url = f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages"
    auth = ("api", MAILGUN_API_KEY)

    data = {
        "from": from_email,
        "to": to_email,
        "subject": subject,
        "text": body
    }

    response = requests.post(url, auth=auth, data=data)

    return response.json()

# Construir menú principal
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔎 Buscar usuario de Instagram", callback_data="search_user")],
        [InlineKeyboardButton("🔑 Cambiar SESSION_ID", callback_data="change_session")],
        [InlineKeyboardButton("✉️ Enviar Email Spoofing", callback_data="spoof_email")]
    ])

# Comando /start
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(
        f"🌟 **SESSION_ID actual:** `{SESSION_ID}`\n\n"
        "¡Bienvenido! 🔍\nSelecciona una opción del menú:",
        reply_markup=main_menu()
    )

# Callback para buscar usuario
@app.on_callback_query(filters.regex("search_user"))
async def search_user(client, callback_query):
    chat_id = callback_query.message.chat.id
    await callback_query.message.edit_text("🔍 Envíame el **nombre de usuario** de Instagram que quieres buscar.")

    @app.on_message(filters.text & filters.private)
    async def receive_username(client, message):
        if message.chat.id == chat_id:
            username = message.text.strip()
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
                    f"📧 **Correo oculto:** {data['obfuscated_email']}\n"
                    f"📞 **Teléfono oculto:** {data['obfuscated_phone']}\n"
                )

                await message.reply_photo(
                    photo=data['profile_picture'],
                    caption=info_msg
                )

                app.remove_handler(receive_username)

# Callback para cambiar SESSION_ID
@app.on_callback_query(filters.regex("change_session"))
async def change_session(client, callback_query):
    chat_id = callback_query.message.chat.id
    await callback_query.message.edit_text("🔐 Envíame el **nuevo SESSION_ID**.")

    @app.on_message(filters.private & filters.text)
    async def receive_new_session(client, message):
        global SESSION_ID
        new_session = message.text.strip()

        if new_session:
            SESSION_ID = new_session
            os.environ["SESSION_ID"] = new_session
            await message.reply_text(f"✅ Nuevo SESSION_ID guardado: `{SESSION_ID}`")
        else:
            await message.reply_text("❌ El SESSION_ID no puede estar vacío.")

# Callback para enviar Email Spoofing
@app.on_callback_query(filters.regex("spoof_email"))
async def spoof_email(client, callback_query):
    chat_id = callback_query.message.chat.id
    await callback_query.message.edit_text("✉️ Envíame el email en este formato:\n\n`destinatario,remitente,título,mensaje`")

    @app.on_message(filters.private & filters.text)
    async def receive_email_data(client, message):
        if message.chat.id == chat_id:
            try:
                to_email, from_email, subject, body = message.text.split(",", 3)
                response = send_spoof_email(to_email.strip(), from_email.strip(), subject.strip(), body.strip())

                if "id" in response:
                    await message.reply_text(f"✅ **Email enviado con éxito a {to_email}**")
                else:
                    await message.reply_text(f"❌ Error al enviar el email: {response}")
            except ValueError:
                await message.reply_text("❌ Formato incorrecto. Usa:\n\n`destinatario,remitente,título,mensaje`")

            app.remove_handler(receive_email_data)

# Ejecutar el bot
if __name__ == "__main__":
    app.run()
