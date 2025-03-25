import os
import requests
import json
from urllib.parse import quote_plus
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
import phonenumbers
from phonenumbers.phonenumberutil import region_code_for_country_code
import pycountry

# Cargar variables de entorno
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SESSION_ID = os.getenv("SESSION_ID")  # Cargar SESSION_ID desde .env
TEXTBELT_KEY = os.getenv("TEXTBELT_KEY")  # Clave de Textbelt

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

# Función para enviar SMS
def send_sms(phone, message):
    url = "https://textbelt.com/text"
    payload = {
        "phone": phone,
        "message": message,
        "key": TEXTBELT_KEY
    }
    response = requests.post(url, data=payload)
    return response.json()

# Comando para enviar SMS
@app.on_message(filters.command("send_sms"))
async def sms_command(client, message):
    await message.reply_text("📩 Envíame el número de teléfono y el mensaje separados por una coma.\n\nEjemplo: `+521234567890, Hola, ¿cómo estás?`")

    @app.on_message(filters.text & filters.private)
    async def receive_sms_info(client, msg):
        try:
            phone, sms_text = msg.text.split(",", 1)
            phone = phone.strip()
            sms_text = sms_text.strip()
            result = send_sms(phone, sms_text)
            
            if result.get("success"):
                await msg.reply_text(f"✅ SMS enviado correctamente a {phone}.")
            else:
                await msg.reply_text(f"❌ Error al enviar SMS: {result.get('error', 'Desconocido')}")
        except ValueError:
            await msg.reply_text("❌ Formato incorrecto. Usa: `+521234567890, Mensaje aquí`")
        finally:
            app.remove_handler(receive_sms_info)

# Ejecutar el bot
if __name__ == "__main__":
    app.run()
