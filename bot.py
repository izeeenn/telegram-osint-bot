import os
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SESSION_ID = os.getenv("SESSION_ID")

# Configuración del bot
app = Client(
    "osint_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Función para ocultar parte del correo y del teléfono
def mask_info(info, visible=3):
    if not info or len(info) < visible * 2:
        return "No disponible"
    return f"{info[:visible]}***{info[-visible:]}"

# Función para obtener información de Instagram
def get_instagram_info(username, session_id):
    url = f'https://i.instagram.com/api/v1/users/web_profile_info/?username={username}'
    headers = {
        "User-Agent": "Instagram 101.0.0.15.120",
        "x-ig-app-id": "936619743392459"
    }
    cookies = {"sessionid": session_id}

    try:
        response = requests.get(url, headers=headers, cookies=cookies)
        response.raise_for_status()
        data = response.json().get("data", {}).get("user", {})

        if not data:
            return {"error": "Usuario no encontrado"}

        # Extraer información relevante
        email = mask_info(data.get("public_email", ""))
        phone_number = mask_info(data.get("public_phone_number", ""))

        info = {
            "username": data.get("username", "No disponible"),
            "full_name": data.get("full_name", "No disponible"),
            "user_id": data.get("id", "No disponible"),
            "followers": data.get("edge_followed_by", {}).get("count", "No disponible"),
            "following": data.get("edge_follow", {}).get("count", "No disponible"),
            "is_private": data.get("is_private", False),
            "is_verified": data.get("is_verified", False),
            "bio": data.get("biography", "No disponible"),
            "profile_picture": data.get("profile_pic_url_hd", "No disponible"),
            "email": email,
            "phone_number": phone_number
        }

        return info

    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

# Comando /start
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(
        "¡Bienvenido al bot OSINT de Instagram! 🔍\n\nSelecciona una opción:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Buscar usuario de Instagram", callback_data="search_instagram")],
            [InlineKeyboardButton("Ayuda", callback_data="help")]
        ])
    )

# Manejo de botones
@app.on_callback_query()
async def menu_handler(client, callback_query):
    data = callback_query.data

    if data == "search_instagram":
        await callback_query.message.edit_text("Envíame el nombre de usuario de Instagram que quieres buscar.")
    elif data == "help":
        await callback_query.message.edit_text("Este bot obtiene información pública de cuentas de Instagram. Introduce un nombre de usuario para comenzar.")

# Buscar usuario de Instagram
@app.on_message(filters.text & ~filters.command(["start", "help"]))
async def handle_instagram_username(client, message):
    username = message.text.strip()
    
    await message.reply_text("🔍 Buscando información, espera un momento...")
    
    data = get_instagram_info(username, SESSION_ID)

    if "error" in data:
        await message.reply_text(f"❌ Error: {data['error']}")
    else:
        info_msg = (
            f"🔎 **Información de Instagram** 🔍\n\n"
            f"📧 **Email:** {data['email']}\n"
            f"📞 **Teléfono:** {data['phone_number']}\n"
            f"👤 **Usuario:** {data['username']}\n"
            f"📛 **Nombre completo:** {data['full_name']}\n"
            f"🆔 **ID de usuario:** {data['user_id']}\n"
            f"👥 **Seguidores:** {data['followers']}\n"
            f"➡️ **Siguiendo:** {data['following']}\n"
            f"🔒 **Cuenta privada:** {'Sí' if data['is_private'] else 'No'}\n"
            f"✅ **Cuenta verificada:** {'Sí' if data['is_verified'] else 'No'}\n"
            f"📝 **Biografía:** {data['bio']}\n"
            f"🖼️ **Foto de perfil:** {data['profile_picture']}\n"
        )

        await message.reply_text(info_msg)

# Ejecutar el bot
if __name__ == "__main__":
    app.run()
