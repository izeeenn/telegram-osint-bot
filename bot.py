from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import requests

# Configuración de Mailgun
MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY")
MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN")

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
    await callback_query.message.edit_text("✉️ **Email Spoofing**\nEnvíame el **correo del remitente falso**.")
    
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
                            await message.reply_text("📝 Finalmente, ingresa el **mensaje del correo**.")
                            
                            @app.on_message(filters.text & filters.private)
                            async def get_message(client, message):
                                if message.chat.id == chat_id:
                                    email_message = message.text.strip()
                                    
                                    # Enviar email con Mailgun
                                    response = send_email(fake_sender, recipient, subject, email_message)
                                    
                                    if response:
                                        await message.reply_text("✅ **Correo enviado con éxito.**")
                                    else:
                                        await message.reply_text("❌ **Error al enviar el correo.**")
                                    
                                    # Remover handlers para evitar interferencias
                                    app.remove_handler(get_fake_sender)
                                    app.remove_handler(get_recipient)
                                    app.remove_handler(get_subject)
                                    app.remove_handler(get_message)
                                    
                                    # Volver al menú principal
                                    await message.reply_text(
                                        "🌟 **Menú Principal**\nSelecciona una categoría:",
                                        reply_markup=main_menu()
                                    )

# Función para enviar email con Mailgun
def send_email(fake_sender, recipient, subject, email_message):
    try:
        response = requests.post(
            f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
            auth=("api", MAILGUN_API_KEY),
            data={
                "from": fake_sender,
                "to": recipient,
                "subject": subject,
                "text": email_message
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
