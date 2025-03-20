import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SESSION_ID = os.getenv("SESSION_ID")

# Configuración del cliente de Pyrogram
app = Client(
    "osint_bot",
    bot_token=BOT_TOKEN
)

# Función para extraer información pública (simula funcionalidad OSINT)
def fetch_public_data(phone_number):
    url = f"https://api.example.com/fetch?sessionid={SESSION_ID}&phone={phone_number}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

# Comando /start
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(
        "¡Bienvenido al bot de OSINT para Telegram! 😊\n\nElige una opción del menú:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Extraer datos de un número", callback_data="extract_data")],
            [InlineKeyboardButton("Ayuda", callback_data="help")]
        ])
    )

# Manejo de botones del menú
@app.on_callback_query()
async def menu_handler(client, callback_query):
    data = callback_query.data

    if data == "extract_data":
        await callback_query.message.edit_text(
            "Por favor, envíame el número de teléfono (con prefijo internacional, por ejemplo +34)."
        )
    elif data == "help":
        await callback_query.message.edit_text(
            "Este bot te permite extraer información pública de cuentas de Telegram. Solo necesitas un número de teléfono válido.\n\n⚠️ Úsalo de forma ética y responsable."
        )

# Respuesta al envío de un número de teléfono
@app.on_message(filters.text & ~filters.command)
async def handle_phone_number(client, message):
    phone_number = message.text.strip()
    if not phone_number.startswith("+"):
        await message.reply_text("Por favor, introduce un número válido con el prefijo internacional, por ejemplo: +34...")
        return

    await message.reply_text("⏳ Procesando la solicitud...")
    data = fetch_public_data(phone_number)

    if "error" in data:
        await message.reply_text(f"❌ Error al obtener los datos: {data['error']}")
    else:
        info = (
            f"📞 **Número:** {phone_number}\n"
            f"👤 **Nombre:** {data.get('name', 'No disponible')}\n"
            f"📝 **Bio:** {data.get('bio', 'No disponible')}\n"
            f"📸 **Foto de perfil:** {data.get('profile_picture', 'No disponible')}\n"
        )
        await message.reply_text(info)

# Manejo de errores globales
@app.on_callback_query(filters.command("error"))
async def error_handler(client, message):
    await message.reply_text("⚠️ Ocurrió un error. Por favor, inténtalo de nuevo más tarde.")

# Ejecutar el bot
if __name__ == "__main__":
    app.run()
