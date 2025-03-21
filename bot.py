from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Configuración de SMTP2GO
SMTP_SERVER = "mail.smtp2go.com"
SMTP_PORT = 2525  # También puedes usar 587 o 465
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")

# Verificación de credenciales
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SESSION_ID = os.getenv("SESSION_ID")

if not API_ID or not API_HASH or not BOT_TOKEN or not SESSION_ID or not SMTP_USER or not SMTP_PASS:
    raise ValueError("Error: Faltan credenciales en las variables de entorno. Verifica tu archivo .env")

API_ID = int(API_ID)  # Convertir API_ID a entero

# Inicialización del bot
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📌 Instagram", callback_data="menu_instagram")],
        [InlineKeyboardButton("🛠 Tools", callback_data="menu_tools")],
        [InlineKeyboardButton("ℹ️ Acerca del Bot", callback_data="about_bot")]
    ])

def tools_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✉️ Email Spoofing", callback_data="email_spoofing")],
        [InlineKeyboardButton("🔙 Volver", callback_data="back_to_main")]
    ])

@app.on_callback_query(filters.regex("email_spoofing"))
async def email_spoofing_start(client, callback_query):
    await callback_query.message.edit_text(
        "✉️ **Email Spoofing**\nIngresa el remitente falso en este formato: `Nombre <correo@falso.com>`"
    )

@app.on_message(filters.text & filters.private)
async def email_spoofing_flow(client, message):
    chat_id = message.chat.id
    step = len(draft_emails.get(chat_id, {}))
    
    steps = ["fake_sender", "recipient", "subject", "email_message"]
    prompts = [
        "📩 Ahora, ingresa el **correo del destinatario**.",
        "✏️ Ahora, ingresa el **asunto del correo**.",
        "📝 Finalmente, ingresa el **mensaje del correo** (puede ser en HTML)."
    ]
    
    if step < len(steps):
        draft_emails[chat_id][steps[step]] = message.text.strip()
        if step < len(prompts):
            await message.reply_text(prompts[step])
    else:
        email_data = draft_emails.get(chat_id, {})
        await message.reply_text(
            f"🧐 **Vista previa:**\n\n"
            f"📨 De: {email_data['fake_sender']}\n"
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
    email_data = draft_emails.get(chat_id, {})
    
    success = send_email(
        email_data.get("fake_sender"),
        email_data.get("recipient"),
        email_data.get("subject"),
        email_data.get("email_message")
    )
    
    if success:
        await callback_query.message.edit_text("✅ **Correo enviado con éxito.**")
    else:
        await callback_query.message.edit_text("❌ **Error al enviar el correo.**")

def send_email(sender, recipient, subject, message):
    try:
        msg = MIMEText(message, "html")
        msg["From"] = sender
        msg["To"] = recipient
        msg["Subject"] = subject
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(sender, recipient, msg.as_string())
        return True
    except Exception as e:
        print("Error al enviar correo:", e)
        return False

@app.on_callback_query(filters.regex("back_to_main"))
async def back_to_main(client, callback_query):
    await callback_query.message.edit_text(
        "🌟 **Menú Principal**\nSelecciona una categoría:", reply_markup=main_menu()
    )

if __name__ == "__main__":
    app.run()
