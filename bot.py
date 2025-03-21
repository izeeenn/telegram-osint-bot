from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import requests
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Configuración de Mailgun
MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY", "")
MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN", "")

# Verificación de credenciales
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Depuración: Imprimir valores cargados
print("API_ID:", API_ID)
print("API_HASH:", API_HASH)
print("BOT_TOKEN:", BOT_TOKEN)

if not API_ID or not API_HASH or not BOT_TOKEN:
    raise ValueError("Error: Faltan credenciales en las variables de entorno.")

API_ID = int(API_ID)  # Convertir API_ID a entero

# Inicialización del bot
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Función para construir el nuevo menú principal
def main_menu():
    botones = [
        [InlineKeyboardButton("📌 Instagram", callback_data="menu_instagram")],
        [InlineKeyboardButton("📌 Tools", callback_data="menu_tools")]
    ]
    return InlineKeyboardMarkup(botones)

# Submenús
def instagram_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔎 Buscar usuario", callback_data="search_user")],
        [InlineKeyboardButton("🔑 Cambiar SESSION_ID", callback_data="change_session")],
        [InlineKeyboardButton("🔙 Volver", callback_data="back_to_main")]
    ])

def tools_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✉️ Email Spoofing", callback_data="email_spoofing")],
        [InlineKeyboardButton("🔙 Volver", callback_data="back_to_main")]
    ])

# Comando /start
@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    await message.reply_text("🌟 **Menú Principal**\nSelecciona una categoría:", reply_markup=main_menu())

# Callbacks de menú
@app.on_callback_query(filters.regex("menu_instagram"))
async def show_instagram_menu(client, callback_query):
    await callback_query.message.edit_text("📌 **Menú de Instagram**\nSelecciona una opción:", reply_markup=instagram_menu())

@app.on_callback_query(filters.regex("menu_tools"))
async def show_tools_menu(client, callback_query):
    await callback_query.message.edit_text("📌 **Menú de Tools**\nSelecciona una opción:", reply_markup=tools_menu())

# Email Spoofing
email_data_store = {}

@app.on_callback_query(filters.regex("email_spoofing"))
async def email_spoofing_start(client, callback_query):
    chat_id = callback_query.message.chat.id
    email_data_store[chat_id] = {}
    await callback_query.message.edit_text("✉️ **Email Spoofing**\nEnvíame el **nombre del remitente falso**.")

@app.on_message(filters.text & filters.private)
async def email_spoofing_flow(client, message):
    chat_id = message.chat.id
    step = len(email_data_store.get(chat_id, {}))
    
    steps = ["fake_name", "fake_sender", "recipient", "subject", "email_message"]
    prompts = [
        "📩 Ahora, ingresa el **correo del remitente falso**.",
        "📩 Ahora, ingresa el **correo del destinatario**.",
        "✏️ Ahora, ingresa el **asunto del correo**.",
        "📝 Finalmente, ingresa el **mensaje del correo** (puede ser en HTML)."
    ]
    
    if step < len(steps):
        email_data_store[chat_id][steps[step]] = message.text.strip()
        if step < len(prompts):
            await message.reply_text(prompts[step])
    else:
        email_data = email_data_store.get(chat_id, {})
        await message.reply_text(
            f"🧐 **Vista previa:**\n\n"
            f"📨 De: {email_data['fake_name']} <{email_data['fake_sender']}>\n"
            f"📩 Para: {email_data['recipient']}\n"
            f"📌 Asunto: {email_data['subject']}\n\n"
            f"💬 Mensaje:\n{email_data['email_message']}\n\n"
            f"¿Quieres enviarlo?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Enviar", callback_data="confirm_send_email")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="back_to_main")]
            ])
        )

@app.on_callback_query(filters.regex("confirm_send_email"))
async def confirm_send_email(client, callback_query):
    chat_id = callback_query.message.chat.id
    email_data = email_data_store.get(chat_id, {})
    
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

@app.on_callback_query(filters.regex("back_to_main"))
async def back_to_main(client, callback_query):
    await callback_query.message.edit_text("🌟 **Menú Principal**\nSelecciona una categoría:", reply_markup=main_menu())

# Iniciar el bot
if __name__ == "__main__":
    app.run()
