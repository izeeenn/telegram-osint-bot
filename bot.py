import os
import requests
import json
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from session_manager import load_session, save_session  # Importar la gestión de sesión

# Cargar variables de entorno
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Cargar SESSION_ID desde el archivo
SESSION_ID = load_session()

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
    elif response.status_code in [403, 429]:
        return {"error": "Instagram ha bloqueado las solicitudes. Intenta más tarde."}

    try:
        user_data = response.json().get("data", {}).get("user", {})
    except json.JSONDecodeError:
        return {"error": "Error en la respuesta de Instagram"}

    if not user_data:
        return {"error": "No se pudo obtener información del usuario"}
    
    return {
        "username": user_data.get("username", "No disponible"),
        "full_name": user_data.get("full_name", "No disponible"),
        "followers": user_data.get("edge_followed_by", {}).get("count", "No disponible"),
        "is_private": user_data.get("is_private", False),
        "bio": user_data.get("biography", "No disponible"),
        "profile_picture": user_data.get("profile_pic_url_hd", "No disponible"),
    }

# Menú principal
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔎 Buscar usuario de Instagram", callback_data="search_user")],
        [InlineKeyboardButton("🔑 Cambiar SESSION_ID", callback_data="change_session")]
    ])

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(
        f"🌟 **SESSION_ID actual:** `{SESSION_ID}`\n\n"
        "¡Bienvenido! 🔍\nSelecciona una opción del menú:",
        reply_markup=main_menu()
    )

@app.on_callback_query(filters.regex("search_user"))
async def search_user(client, callback_query):
    await callback_query.message.edit_text("🔍 Envíame el **nombre de usuario** de Instagram que quieres buscar.")

    @app.listen(filters.private & filters.text)
    async def receive_username(client, message):
        username = message.text.strip()
        await message.reply_text("🔍 Buscando información, espera un momento...")
        data = get_instagram_info(username, SESSION_ID)

        if "error" in data:
            await message.reply_text(f"❌ Error: {data['error']}")
        else:
            info_msg = (
                f"📌 **Usuario:** {data['username']}\n"
                f"📛 **Nombre:** {data['full_name']}\n"
                f"👥 **Seguidores:** {data['followers']}\n"
                f"🔒 **Cuenta privada:** {'Sí' if data['is_private'] else 'No'}\n"
                f"📝 **Bio:** {data['bio']}\n"
            )
            await message.reply_photo(photo=data['profile_picture'], caption=info_msg)

@app.on_callback_query(filters.regex("change_session"))
async def change_session(client, callback_query):
    await callback_query.message.edit_text("🔐 Envíame el **nuevo SESSION_ID**.")

    @app.listen(filters.private & filters.text)
    async def receive_new_session(client, message):
        global SESSION_ID
        new_session = message.text.strip()
        
        if new_session:
            SESSION_ID = new_session
            save_session(new_session)  # Guardar en archivo
            await message.reply_text(f"✅ Nuevo SESSION_ID guardado: `{SESSION_ID}`")
        else:
            await message.reply_text("❌ El SESSION_ID no puede estar vacío.")

# Ejecutar el bot
if __name__ == "__main__":
    app.run()
