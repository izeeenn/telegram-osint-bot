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

# Configuración del bot
app = Client(
    "osint_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Variable global para almacenar el SESSION_ID temporalmente
session_id = None

# Función para construir el menú dinámico
def main_menu():
    global session_id
    botones = [[InlineKeyboardButton("🛠 Añadir SESSION_ID", callback_data="add_session")]]

    if session_id:
        botones.append([InlineKeyboardButton("🔎 Buscar usuario de Instagram", callback_data="search_user")])

    return InlineKeyboardMarkup(botones)

# Comando /start
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(
        f"🌟 **SESSION_ID actual:** `{session_id if session_id else 'No disponible'}`\n\n"
        "¡Bienvenido! 🔍\nSelecciona una opción del menú:",
        reply_markup=main_menu()
    )

# Callback para añadir SESSION_ID
@app.on_callback_query(filters.regex("add_session"))
async def add_session(client, callback_query):
    global session_id

    # Preguntar al usuario por su SESSION_ID
    await callback_query.message.edit_text("✍️ Envíame tu `SESSION_ID` para continuar.")

    # Esperar el mensaje del usuario
    session_message = await client.listen(callback_query.message.chat.id, filters=filters.text)
    session_id = session_message.text.strip()

    if not session_id:
        await callback_query.message.reply_text("⚠️ El **SESSION_ID** es necesario. Por favor, envíalo de nuevo.")
        return

    # Confirmación y actualizar menú
    await callback_query.message.reply_text(
        "✅ **SESSION_ID guardado correctamente.**\n\n"
        "Ahora puedes buscar un usuario de Instagram desde el menú.",
        reply_markup=main_menu()
    )

# Callback para buscar usuario
@app.on_callback_query(filters.regex("search_user"))
async def search_user(client, callback_query):
    global session_id

    if not session_id:
        await callback_query.message.edit_text(
            "⚠️ No has proporcionado un **SESSION_ID**. Añádelo antes de continuar.",
            reply_markup=main_menu()
        )
        return

    await callback_query.message.edit_text("🔍 Envíame el **nombre de usuario** de Instagram que quieres buscar.")

    # Esperar el mensaje del usuario con el nombre
    username_message = await client.listen(callback_query.message.chat.id, filters=filters.text)
    username = username_message.text.strip()

    await callback_query.message.reply_text("🔍 Buscando información, espera un momento...")

    # Obtener datos del usuario
    data = get_instagram_info(username, session_id)

    if "error" in data:
        await callback_query.message.reply_text(f"❌ Error: {data['error']}")
    else:
        info_msg = (
            f"📌 **Usuario:** {data['username']}\n"
            f"📛 **Nombre:** {data['full_name']}\n"
            f"🆔 **ID:** {data['user_id']}\n"
            f"👥 **Seguidores:** {data['followers']}\n"
            f"🔒 **Cuenta privada:** {'Sí' if data['is_private'] else 'No'}\n"
            f"📝 **Bio:** {data['bio']}\n"
            f"📧 **Email:** {data['public_email']}\n"
            f"📞 **Teléfono:** {data['public_phone']}\n"
            f"🖼️ [Foto de perfil]({data['profile_picture']})"
        )

        await callback_query.message.reply_text(info_msg, disable_web_page_preview=False)

# Función para obtener datos de Instagram
def get_instagram_info(username, session_id):
    headers = {
        "User-Agent": "Instagram 101.0.0.15.120",
        "x-ig-app-id": "936619743392459"
    }
    cookies = {"sessionid": session_id}

    profile_url = f'https://i.instagram.com/api/v1/users/web_profile_info/?username={username}'
    response = requests.get(profile_url, headers=headers, cookies=cookies)

    if response.status_code == 404:
        return {"error": "Usuario no encontrado"}

    user_data = response.json().get("data", {}).get("user", {})
    if not user_data:
        return {"error": "No se pudo obtener información del usuario"}

    user_id = user_data.get("id", "Desconocido")

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
    }

# Ejecutar el bot
if __name__ == "__main__":
    app.run()
