import os
import smtplib
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from phonenumbers import parse, is_valid_number
import requests
import json
import pycountry
import random
import string

# Configuración del bot
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SESSION_ID = os.getenv("SESSION_ID")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("start"))
async def start(client, message: Message):
    await message.reply("¡Hola! Soy tu bot de OSINT. ¿En qué puedo ayudarte hoy?", reply_markup=main_menu())

@app.on_callback_query(filters.regex("search_user"))
async def search_user(client, callback_query: CallbackQuery):
    await callback_query.message.edit_text("🔍 Envíame el **nombre de usuario** de Instagram que quieres buscar.")
    
    @app.on_message(filters.text & filters.private)
    async def handle_instagram_username(client, message: Message):
        if message.chat.id == callback_query.message.chat.id:
            username = message.text.strip()
            # Aquí iría la lógica para buscar el usuario en Instagram
            await message.reply(f"Buscando el usuario de Instagram: {username}")
            app.remove_handler(handle_instagram_username)  # Eliminar el manejador una vez procesada la solicitud

@app.on_callback_query(filters.regex("change_session"))
async def change_session(client, callback_query: CallbackQuery):
    await callback_query.message.edit_text("🔐 Envíame el **nuevo SESSION_ID**.")
    
    @app.on_message(filters.text & filters.private)
    async def receive_new_session(client, message: Message):
        if message.chat.id == callback_query.message.chat.id:
            new_session_id = message.text.strip()
            if new_session_id:
                global SESSION_ID
                SESSION_ID = new_session_id
                os.environ["SESSION_ID"] = new_session_id  # Guardar en el entorno también
                await message.reply_text(f"✅ Nuevo SESSION_ID guardado: `{SESSION_ID}`")
                app.remove_handler(receive_new_session)
                await message.reply_text("¡SESSION_ID actualizado! ¿Qué más puedo hacer por ti?", reply_markup=main_menu())
            else:
                await message.reply_text("❌ El SESSION_ID no puede estar vacío. Por favor, ingresa uno válido.")
                app.remove_handler(receive_new_session)

@app.on_callback_query(filters.regex("check_plate"))
async def check_plate(client, callback_query: CallbackQuery):
    await callback_query.message.edit_text("🔍 Envíame la **matrícula** del coche que quieres consultar.")
    
    @app.on_message(filters.text & filters.private)
    async def handle_plate(client, message: Message):
        if message.chat.id == callback_query.message.chat.id:
            plate = message.text.strip()
            # Aquí iría la lógica para consultar la matrícula
            await message.reply(f"Consultando la matrícula: {plate}")
            app.remove_handler(handle_plate)

@app.on_callback_query(filters.regex("validate_phone"))
async def validate_phone(client, callback_query: CallbackQuery):
    await callback_query.message.edit_text("📱 Envíame el **número de teléfono** que quieres validar.")
    
    @app.on_message(filters.text & filters.private)
    async def handle_phone(client, message: Message):
        if message.chat.id == callback_query.message.chat.id:
            phone = message.text.strip()
            try:
                parsed_phone = parse(phone, None)
                if is_valid_number(parsed_phone):
                    await message.reply(f"✅ El número de teléfono **{phone}** es válido.")
                else:
                    await message.reply(f"❌ El número de teléfono **{phone}** no es válido.")
            except Exception as e:
                await message.reply(f"❌ Error al validar el número: {str(e)}")
            app.remove_handler(handle_phone)

@app.on_callback_query(filters.regex("get_country_info"))
async def get_country_info(client, callback_query: CallbackQuery):
    await callback_query.message.edit_text("🌍 Envíame el **nombre del país** del que quieres obtener información.")
    
    @app.on_message(filters.text & filters.private)
    async def handle_country(client, message: Message):
        if message.chat.id == callback_query.message.chat.id:
            country_name = message.text.strip()
            country = pycountry.countries.get(name=country_name)
            if country:
                await message.reply(f"🌍 Información del país: {country.name}\nCódigo de país: {country.alpha_2}")
            else:
                await message.reply(f"❌ No se encontró información para el país: {country_name}")
            app.remove_handler(handle_country)

# Función para enviar correo (spoofing)
def send_email(mail_to, subject, message, mail_from, count):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    msg = MIMEMultipart()
    msg['From'] = mail_from
    msg['To'] = mail_to
    msg['Subject'] = subject
    msg.attach(MIMEText(message, 'plain'))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            for _ in range(count):
                server.sendmail(mail_from, mail_to, msg.as_string())
            return "Correo enviado correctamente"
    except Exception as e:
        return f"Error al enviar correo: {str(e)}"

# Función para generar contraseñas aleatorias
def generate_random_password(length=12):
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choice(characters) for i in range(length))
    return password

# Menú principal
def main_menu():
    return {
        "keyboard": [
            [{"text": "Buscar usuario de Instagram", "callback_data": "search_user"}],
            [{"text": "Cambiar SESSION_ID", "callback_data": "change_session"}],
            [{"text": "Consultar matrícula", "callback_data": "check_plate"}],
            [{"text": "Validar teléfono", "callback_data": "validate_phone"}],
            [{"text": "Obtener información de país", "callback_data": "get_country_info"}]
        ],
        "resize_keyboard": True
    }

app.run()
