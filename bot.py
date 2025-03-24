import os
import re
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Cargar configuración
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SESSION_ID = os.getenv("SESSION_ID")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

if not all([API_ID, API_HASH, BOT_TOKEN, SESSION_ID, SMTP_USER, SMTP_PASSWORD]):
    raise ValueError("Faltan variables de entorno. Revisa tu archivo .env")

SMTP_SERVER = "smtp-relay.brevo.com"  # Puedes cambiarlo si usas otro proveedor
SMTP_PORT = 587

# Diccionarios para manejar estados y sesiones temporales por usuario
user_states = {}
user_sessions = {}

# Validar correos electrónicos
def validate_email(email):
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(pattern, email) is not None

# Validar nombre de usuario de Instagram
def is_valid_instagram_username(username):
    return re.match(r'^[a-zA-Z0-9_.]+$', username) is not None

# Función para enviar correos con spoofing
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
    except smtplib.SMTPAuthenticationError:
        return "❌ Error de autenticación SMTP."
    except smtplib.SMTPConnectError:
        return "❌ Error de conexión con el servidor SMTP."
    except Exception as e:
        return f"❌ Error al enviar el correo: {str(e)}"

# Función para obtener información pública de Instagram
def get_instagram_info(username, default_session_id, user_id=None):
    session_id = user_sessions.get(user_id, default_session_id)

    if not is_valid_instagram_username(username):
        return {"error": "Nombre de usuario no válido."}

    headers = {
        "User-Agent": "Instagram 101.0.0.15.120",
        "x-ig-app-id": "936619743392459"
    }
    cookies = {"sessionid": session_id}
    profile_url = f'https://i.instagram.com/api/v1/users/web_profile_info/?username={username}'

    try:
        response = requests.get(profile_url, headers=headers, cookies=cookies)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return {"error": f"Error al acceder al perfil: {str(e)}"}

    if response.status_code == 404:
        return {"error": "Usuario no encontrado"}

    if 'application/json' not in response.headers.get('Content-Type', ''):
        return {"error": "Respuesta inválida de la API"}

    user_data = response.json().get("data", {}).get("user", {})
    if not user_data:
        return {"error": "No se pudo obtener información del usuario"}

    # Datos públicos únicamente
    profile_picture = user_data.get("profile_pic_url_hd", "https://example.com/default.jpg")
    phone_number = user_data.get("public_phone_number", "No disponible")
    email = user_data.get("public_email", "No disponible")

    if phone_number != "No disponible":
        phone_number = f"***{phone_number[-4:]}"  # Ofuscar

    return {
        "username": user_data.get("username", "No disponible"),
        "full_name": user_data.get("full_name", "No disponible"),
        "user_id": user_data.get("id", "Desconocido"),
        "followers": user_data.get("edge_followed_by", {}).get("count", "No disponible"),
        "is_private": user_data.get("is_private", False),
        "bio": user_data.get("biography", "No disponible"),
        "profile_picture": profile_picture,
        "email": email,
        "phone": phone_number,
    }

# Iniciar el bot
app = Client("osint_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Comando /start con menú
@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Buscar en Instagram", callback_data="instagram")],
        [InlineKeyboardButton("📧 Enviar Email Spoofing", callback_data="spoof")],
        [InlineKeyboardButton("🧪 Cambiar sessionid", callback_data="set_session")]
    ])
    await message.reply("Selecciona una opción:", reply_markup=keyboard)

# Botón pulsado
@app.on_callback_query()
async def menu_handler(client, callback_query):
    user_id = callback_query.from_user.id
    data = callback_query.data

    if data == "instagram":
        await callback_query.message.reply("Envíame el nombre de usuario de Instagram.")
        user_states[user_id] = "instagram"

    elif data == "spoof":
        await callback_query.message.reply(
            "Introduce los datos del correo en el siguiente formato:\n\n`de|para|asunto|mensaje`",
            parse_mode="markdown"
        )
        user_states[user_id] = "spoof"

    elif data == "set_session":
        await callback_query.message.reply("Escribe tu nuevo sessionid de Instagram.")
        user_states[user_id] = "set_session"

# Mensajes de usuario según contexto
@app.on_message(filters.text & filters.private)
async def handle_message(client, message):
    user_id = message.from_user.id
    text = message.text.strip()
    state = user_states.get(user_id)

    if state == "instagram":
        await message.reply("🔍 Buscando datos...")
        data = get_instagram_info(text, SESSION_ID, user_id)

        if "error" in data:
            await message.reply(f"❌ {data['error']}")
        else:
            info = (
                f"📌 **Usuario:** {data['username']}\n"
                f"📛 **Nombre completo:** {data['full_name']}\n"
                f"🆔 **ID:** {data['user_id']}\n"
                f"👥 **Seguidores:** {data['followers']}\n"
                f"🔒 **Cuenta privada:** {'Sí' if data['is_private'] else 'No'}\n"
                f"📝 **Bio:** {data['bio']}\n"
                f"📧 **Correo:** {data['email']}\n"
                f"📞 **Teléfono:** {data['phone']}\n"
            )
            await message.reply_photo(photo=data['profile_picture'], caption=info)
        user_states.pop(user_id, None)

    elif state == "spoof":
        parts = text.split("|")
        if len(parts) != 4:
            await message.reply("❌ Formato incorrecto. Usa: `de|para|asunto|mensaje`", parse_mode="markdown")
        else:
            sender, recipient, subject, body = map(str.strip, parts)
            result = send_spoof_email(sender, recipient, subject, body)
            await message.reply(result)
        user_states.pop(user_id, None)

    elif state == "set_session":
        user_sessions[user_id] = text
        await message.reply("✅ Nuevo sessionid guardado temporalmente.")
        user_states.pop(user_id, None)

    else:
        await message.reply("❓ Usa /start para comenzar.")

# Ejecutar
if __name__ == "__main__":
    app.run()
