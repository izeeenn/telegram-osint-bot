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

# Validar que las variables necesarias están presentes
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SESSION_ID = os.getenv("SESSION_ID")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

if not all([API_ID, API_HASH, BOT_TOKEN, SESSION_ID, SMTP_USER, SMTP_PASSWORD]):
    raise ValueError("Faltan variables de entorno críticas. Asegúrate de tener todas las variables necesarias en .env")

SMTP_SERVER = "smtp-relay.brevo.com"
SMTP_PORT = 587

# Validación de correo electrónico
def validate_email(email):
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(pattern, email) is not None

# Configuración del bot
app = Client(
    "osint_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Función para enviar correos
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
        return "✅ Correo enviado exitosamente."
    except smtplib.SMTPAuthenticationError:
        return "❌ Error de autenticación. Verifica tus credenciales SMTP."
    except smtplib.SMTPConnectError:
        return "❌ Error al conectar al servidor SMTP."
    except Exception as e:
        return f"❌ Error desconocido al enviar el correo: {str(e)}"

# Función para obtener información de Instagram
def get_instagram_info(username, session_id):
    headers = {"User-Agent": "Instagram 101.0.0.15.120", "x-ig-app-id": "936619743392459"}
    cookies = {"sessionid": session_id}
    profile_url = f'https://i.instagram.com/api/v1/users/web_profile_info/?username={username}'

    try:
        response = requests.get(profile_url, headers=headers, cookies=cookies)
        response.raise_for_status()  # Lanza un error si el código de estado no es 2xx
    except requests.exceptions.RequestException as e:
        return {"error": f"Error al acceder al perfil: {str(e)}"}

    if response.status_code == 404:
        return {"error": "Usuario no encontrado"}
    
    if response.status_code != 200:
        return {"error": f"Error al acceder al perfil. Código de estado: {response.status_code}"}
    
    if 'application/json' not in response.headers['Content-Type']:
        return {"error": "Respuesta no válida de la API"}
    
    user_data = response.json().get("data", {}).get("user", {})
    if not user_data:
        return {"error": "No se pudo obtener información del usuario"}
    
    phone_number = user_data.get("public_phone_number", "No disponible")
    if phone_number != "No disponible":
        phone_number = f"***{phone_number[-4:]}"  # Ofuscar el teléfono
    
    profile_picture = user_data.get("profile_pic_url_hd", "No disponible")
    if profile_picture == "No disponible":
        profile_picture = "https://example.com/default-profile-pic.jpg"  # Imagen predeterminada si no está disponible
    
    return {
        "username": user_data.get("username", "No disponible"),
        "full_name": user_data.get("full_name", "No disponible"),
        "user_id": user_data.get("id", "Desconocido"),
        "followers": user_data.get("edge_followed_by", {}).get("count", "No disponible"),
        "is_private": user_data.get("is_private", False),
        "bio": user_data.get("biography", "No disponible"),
        "profile_picture": profile_picture,
        "email": user_data.get("public_email", "No disponible"),
        "phone": phone_number,
    }

# Función para crear menús interactivos
def main_menu():
    buttons = [
        [InlineKeyboardButton("🔍 Buscar usuario de Instagram", callback_data="search_user")],
        [InlineKeyboardButton("📧 Email Spoofing", callback_data="email_spoofing")],
        [InlineKeyboardButton("🔑 Cambiar SESSION_ID", callback_data="change_session")]
    ]
    return InlineKeyboardMarkup(buttons)

# Manejadores de mensajes y botones
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(
        f"🌟 **SESSION_ID actual:** `{SESSION_ID}`\n\n"
        "¡Bienvenido! 🔍\nSelecciona una opción del menú:",
        reply_markup=main_menu()
    )

# Opción de buscar usuario de Instagram
@app.on_callback_query(filters.regex("search_user"))
async def search_user(client, callback_query):
    await callback_query.message.edit_text("🔍 Envíame el **nombre de usuario** de Instagram que quieres buscar.")

# Recibe el nombre de usuario de Instagram
@app.on_message(filters.text & filters.private)
async def receive_username(client, message):
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
            f"📧 **Correo:** {data['email']}\n"
            f"📞 **Teléfono (ofuscado):** {data['phone']}\n"
        )
        await message.reply_photo(photo=data['profile_picture'], caption=info_msg)

# Flujo de email spoofing
@app.on_callback_query(filters.regex("email_spoofing"))
async def email_spoofing_menu(client, callback_query):
    await callback_query.message.edit_text("📧 Envíame el **correo del remitente falso**.")

# Manejadores para el flujo de email spoofing (agregar validación y cambios de estado)
# Aquí podrías usar un diccionario para almacenar el estado de los usuarios

if __name__ == "__main__":
    app.run()
