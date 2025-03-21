from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
import os
import requests

# Cargar variables de entorno
load_dotenv()

# Configuración del bot
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY")
MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN")

# Definir el bot
app = Client(
    "osint_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Función para construir el nuevo menú principal
def main_menu():
    botones = [
        [InlineKeyboardButton("📌 Instagram", callback_data="menu_instagram")],
        [InlineKeyboardButton("📌 Tools", callback_data="menu_tools")]
    ]
    return InlineKeyboardMarkup(botones)

# Submenú de Instagram
def instagram_menu():
    botones = [
        [InlineKeyboardButton("🔎 Buscar usuario", callback_data="search_user")],
        [InlineKeyboardButton("🔑 Cambiar SESSION_ID", callback_data="change_session")],
        [InlineKeyboardButton("🔙 Volver", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(botones)

# Submenú de Tools
def tools_menu():
    botones = [
        [InlineKeyboardButton("✉️ Email Spoofing", callback_data="email_spoofing")],
        [InlineKeyboardButton("🔙 Volver", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(botones)

# Callback para mostrar el menú de Instagram
@app.on_callback_query(filters.regex("menu_instagram"))
async def show_instagram_menu(client, callback_query):
    await callback_query.message.edit_text(
        "📌 **Menú de Instagram**\nSelecciona una opción:",
        reply_markup=instagram_menu()
    )

# Callback para mostrar el menú de Tools
@app.on_callback_query(filters.regex("menu_tools"))
async def show_tools_menu(client, callback_query):
    await callback_query.message.edit_text(
        "📌 **Menú de Tools**\nSelecciona una opción:",
        reply_markup=tools_menu()
    )

# Callback para iniciar Email Spoofing
@app.on_callback_query(filters.regex("email_spoofing"))
async def email_spoofing_start(client, callback_query):
    chat_id = callback_query.message.chat.id
    await callback_query.message.edit_text("✉️ **Email Spoofing**\nEnvíame el **nombre del remitente falso**.")

    @app.on_message(filters.text & filters.private)
    async def get_fake_name(client, message):
        if message.chat.id == chat_id:
            fake_name = message.text.strip()
            await message.reply_text("📩 Ahora, ingresa el **correo del remitente falso**.")

            @app.on_message(filters.text & filters.private)
            async def get_fake_sender(client, message):
                if message.chat.id == chat_id:
                    fake_sender = message.text.strip()
                    await message.reply_text("📩 Ahora, ingresa el **correo del destinatario**.")

                    @app.on_message(filters.text & filters.private)
                    async def get_recipient(client, message):
                        if message.chat.id == chat_id:
                            recipient = message.text.strip()
                            await message.reply_text("✏️ Ahora, ingresa el **asunto del correo**.")

                            @app.on_message(filters.text & filters.private)
                            async def get_subject(client, message):
                                if message.chat.id == chat_id:
                                    subject = message.text.strip()
                                    await message.reply_text("📝 Finalmente, ingresa el **mensaje del correo** (puede ser en HTML).")

                                    @app.on_message(filters.text & filters.private)
                                    async def get_message(client, message):
                                        if message.chat.id == chat_id:
                                            email_message = message.text.strip()

                                            # Confirmación antes de enviar
                                            await message.reply_text(
                                                f"🧐 **Vista previa:**\n\n"
                                                f"📨 De: {fake_name} <{fake_sender}>\n"
                                                f"📩 Para: {recipient}\n"
                                                f"📌 Asunto: {subject}\n\n"
                                                f"💬 Mensaje:\n{email_message}\n\n"
                                                f"¿Quieres enviarlo?",
                                                reply_markup=InlineKeyboardMarkup([
                                                    [InlineKeyboardButton("✅ Enviar", callback_data="confirm_send_email")],
                                                    [InlineKeyboardButton("❌ Cancelar", callback_data="back_to_main")]
                                                ])
                                            )

                                            # Guardamos los datos en el contexto del chat
                                            client.chat_data[chat_id] = {
                                                "fake_name": fake_name,
                                                "fake_sender": fake_sender,
                                                "recipient": recipient,
                                                "subject": subject,
                                                "email_message": email_message
                                            }

# Callback para confirmar el envío
@app.on_callback_query(filters.regex("confirm_send_email"))
async def confirm_send_email(client, callback_query):
    chat_id = callback_query.message.chat.id
    email_data = client.chat_data.get(chat_id, {})

    response = send_email(
        email_data.get("fake_name"),
        email_data.get("fake_sender"),
        email_data.get("recipient"),
        email_data.get("subject"),
        email_data.get("email_message")
    )

    if response:
        await callback_query.message.edit_text("✅ **Correo enviado con éxito.**")
    else:
        await callback_query.message.edit_text("❌ **Error al enviar el correo.**")

# Función para enviar email con Mailgun
def send_email(fake_name, fake_sender, recipient, subject, email_message):
    try:
        response = requests.post(
            f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
            auth=("api", MAILGUN_API_KEY),
            data={
                "from": f"{fake_name} <{fake_sender}>",
                "to": recipient,
                "subject": subject,
                "html": email_message
            }
        )
        return response.status_code == 200
    except Exception as e:
        print("Error al enviar correo:", e)
        return False

# Callback para volver al menú principal
@app.on_callback_query(filters.regex("back_to_main"))
async def back_to_main(client, callback_query):
    await callback_query.message.edit_text(
        "🌟 **Menú Principal**\nSelecciona una categoría:",
        reply_markup=main_menu()
    )

# Iniciar el bot
if __name__ == "__main__":
    app.run()
