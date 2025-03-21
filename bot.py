import os
import requests
import json
from urllib.parse import quote_plus
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText

# Cargar variables de entorno
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SESSION_ID = os.getenv("SESSION_ID")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")

app = Client("osint_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

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

def main_menu():
    botones = [
        [InlineKeyboardButton("🔎 Buscar usuario de Instagram", callback_data="search_user")],
        [InlineKeyboardButton("🔐 Cambiar SESSION_ID", callback_data="change_session")],
        [InlineKeyboardButton("✉️ Enviar Email Spoofeado", callback_data="email_spoofer")]
    ]
    return InlineKeyboardMarkup(botones)

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(
        f"🌟 **SESSION_ID actual:** `{SESSION_ID}`\n\n"
        "¡Bienvenido! 🔍\nSelecciona una opción del menú:",
        reply_markup=main_menu()
    )

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
                    f"📧 **Email público:** {data['public_email']}\n"
                    f"📞 **Teléfono público:** {data['public_phone']}\n"
                    f"📧 **Correo oculto:** {data['obfuscated_email']}\n"
                    f"📞 **Teléfono oculto:** {data['obfuscated_phone']}\n"
                )
                await message.reply_photo(photo=data['profile_picture'], caption=info_msg)
                app.remove_handler(receive_username)

@app.on_callback_query(filters.regex("change_session"))
async def change_session(client, callback_query):
    chat_id = callback_query.message.chat.id
    await callback_query.message.edit_text("🔐 Envíame el **nuevo SESSION_ID**.")

    @app.on_message(filters.text & filters.private)
    async def receive_new_session(client, message):
        if message.chat.id == chat_id:
            new_session_id = message.text.strip()
            if new_session_id:
                global SESSION_ID
                SESSION_ID = new_session_id
                os.environ["SESSION_ID"] = new_session_id
                await message.reply_text(f"✅ Nuevo SESSION_ID guardado: `{SESSION_ID}`")
                app.remove_handler(receive_new_session)
                await message.reply_text(
                    f"🌟 **SESSION_ID actual:** `{SESSION_ID}`\n\n"
                    "¡Bienvenido! 🔍\nSelecciona una opción del menú:",
                    reply_markup=main_menu()
                )
            else:
                await message.reply_text("❌ El SESSION_ID no puede estar vacío.")
                app.remove_handler(receive_new_session)

@app.on_callback_query(filters.regex("email_spoofer"))
async def email_spoofer(client, callback_query):
    chat_id = callback_query.message.chat.id
    await callback_query.message.edit_text("✉️ Envíame el **correo del remitente falso**.")
    spoof_data = {}

    @app.on_message(filters.text & filters.private)
    async def step1(client, message):
        if message.chat.id == chat_id:
            spoof_data['from_email'] = message.text.strip()
            await message.reply_text("📨 Ahora dime el **correo del destinatario real**.")
            app.remove_handler(step1)

            @app.on_message(filters.text & filters.private)
            async def step2(client, message):
                if message.chat.id == chat_id:
                    spoof_data['to_email'] = message.text.strip()
                    await message.reply_text("📝 Escribe el **asunto del correo**.")
                    app.remove_handler(step2)

                    @app.on_message(filters.text & filters.private)
                    async def step3(client, message):
                        if message.chat.id == chat_id:
                            spoof_data['subject'] = message.text.strip()
                            await message.reply_text("💬 Ahora dime el **contenido del mensaje**.")
                            app.remove_handler(step3)

                            @app.on_message(filters.text & filters.private)
                            async def step4(client, message):
                                if message.chat.id == chat_id:
                                    spoof_data['message'] = message.text.strip()
                                    await message.reply_text("⏳ Enviando correo...")

                                    result = send_spoof_email(
                                        spoof_data['from_email'],
                                        spoof_data['to_email'],
                                        spoof_data['subject'],
                                        spoof_data['message']
                                    )

                                    if result:
                                        await message.reply_text("✅ ¡Correo enviado correctamente!")
                                    else:
                                        await message.reply_text("❌ Error al enviar el correo.")
                                    
                                    app.remove_handler(step4)

def send_spoof_email(from_email, to_email, subject, message):
    try:
        smtp_host = "smtp.mailjet.com"
        smtp_port = 587
        msg = MIMEText(message, "plain")
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = to_email

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(from_email, to_email, msg.as_string())

        return True
    except Exception as e:
        print(f"[Error spoofing email] {e}")
        return False

if __name__ == "__main__":
    app.run()
