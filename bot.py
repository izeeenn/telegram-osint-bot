import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
import requests
from pyrogram.types import CallbackQuery
from dotenv import load_dotenv
import phonenumbers

# Cargar variables de entorno desde .env
load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY")
MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN")

# Iniciar el bot con Pyrogram
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Función de búsqueda de usuarios en Instagram
def search_instagram_user(username):
    # Lógica de búsqueda para obtener información de Instagram (puedes agregar más lógica aquí)
    response = requests.get(f'https://www.instagram.com/{username}/')
    if response.status_code == 200:
        return f"Información del perfil de Instagram para @{username}: {response.url}"
    else:
        return "No se pudo encontrar el perfil de Instagram."

# Función para el spoofing de correos electrónicos
def send_spoofed_email(to_email, subject, body, from_email, smtp_server="smtp.mailgun.org"):
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(smtp_server, 587)
        server.starttls()
        server.login(f"postmaster@{MAILGUN_DOMAIN}", MAILGUN_API_KEY)
        server.sendmail(from_email, to_email, msg.as_string())
        server.close()
        return "Correo enviado correctamente."
    except Exception as e:
        return f"Error al enviar el correo: {str(e)}"

# Función de validación de teléfono
def validate_phone_number(phone_number):
    try:
        parsed_number = phonenumbers.parse(phone_number, "ES")
        if phonenumbers.is_valid_number(parsed_number):
            return "El número es válido."
        else:
            return "El número no es válido."
    except phonenumbers.phonenumberutil.NumberParseException:
        return "Error al analizar el número."

# Función para cambiar la sesión de Telegram
async def change_session(callback_query: CallbackQuery):
    await callback_query.message.edit_text("🔐 Envíame el **nuevo SESSION_ID**.")
    # Lógica para cambiar el session_id según el comando que recibe el usuario

# Función para iniciar la búsqueda de un usuario
async def search_user(client, message):
    await message.reply("🔍 Envíame el **nombre de usuario** de Instagram que quieres buscar.")

# Manejadores de comandos
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply("¡Hola! Soy tu bot. Usa /search para buscar un usuario en Instagram o /change para cambiar tu sesión.")

@app.on_message(filters.command("search"))
async def search(client, message):
    await search_user(client, message)

@app.on_message(filters.command("change"))
async def change(client, message):
    await message.reply("🔐 Envíame el **nuevo SESSION_ID** para cambiar la sesión.")

@app.on_message(filters.command("email"))
async def spoof_email(client, message):
    # Pide al usuario que ingrese el correo de destino
    await message.reply("Por favor, proporciona el correo electrónico de destino.")
    # Lógica para enviar un correo spoofed
    to_email = "destinatario@example.com"
    subject = "Asunto del correo"
    body = "Este es el cuerpo del correo."
    from_email = "remitente@tudominio.com"
    result = send_spoofed_email(to_email, subject, body, from_email)
    await message.reply(result)

@app.on_message(filters.command("phone"))
async def validate_phone(client, message):
    phone_number = message.text.split(' ', 1)[-1]  # El número de teléfono está después del comando
    result = validate_phone_number(phone_number)
    await message.reply(result)

# Configuración de la gestión de sesiones y otras configuraciones del bot
@app.on_callback_query(filters.regex("session"))
async def session_callback(client, callback_query):
    await change_session(callback_query)

# Arrancar el bot
app.run()
