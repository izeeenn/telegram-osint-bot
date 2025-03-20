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

# Variable global para almacenar el SESSION_ID
session_id = None

# Función para obtener información de Instagram
def get_instagram_info(username, session_id):
    headers = {
        "User-Agent": "Instagram 101.0.0.15.120",
        "x-ig-app-id": "936619743392459"
    }
    cookies = {"sessionid": session_id}

    # Obtener ID del usuario
    profile_url = f'https://i.instagram.com/api/v1/users/web_profile_info/?username={username}'
    response = requests.get(profile_url, headers=headers, cookies=cookies)

    if response.status_code == 404:
        return {"error": "Usuario no encontrado"}

    user_data = response.json().get("data", {}).get("user", {})
    if not user_data:
        return {"error": "No se pudo obtener información del usuario"}

    user_id = user_data.get("id", "Desconocido")

    # Obtener más detalles con el ID
    user_info_url = f'https://i.instagram.com/api/v1/users/{user_id}/info/'
    user_info_response = requests.get(user_info_url, headers=headers, cookies=cookies)
    user_info = user_info_response.json().get("user", {})

    # Obtener datos obfuscados
    lookup_data = f"signed_body=SIGNATURE.{{\"q\":\"{username}\",\"skip_recovery\":\"1\"}}"
    lookup_response = requests.post(
        "https://i.instagram.com/api/v1/users/lookup/",
        headers={
            "User-Agent": "Instagram 101.0.0.15.120",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-IG-App-ID": "124024574287414"
        },
        data=lookup_data
    )

    obfuscated_data = lookup_response.json()

    # Extraer emails y teléfonos públicos u obfuscados
    public_email = user_info.get("public_email", "No disponible")
    obfuscated_email = obfuscated_data.get("obfuscated_email", "No disponible")

    public_phone = user_info.get("public_phone_number", "No disponible")
    obfuscated_phone = obfuscated_data.get("obfuscated_phone", "No disponible")

    # Construir la respuesta
    info = {
        "username": user_data.get("username", "No disponible"),
        "full_name": user_data.get("full_name", "No disponible"),
        "user_id": user_id,
        "followers": user_data.get("edge_followed_by", {}).get("count", "No disponible"),
        "following": user_data.get("edge_follow", {}).get("count", "No disponible"),
        "is_private": user_data.get("is_private", False),
        "is_verified": user_data.get("is_verified", False),
        "bio": user_data.get("biography", "No disponible"),
        "profile_picture": user_data.get("profile_pic_url_hd", "No disponible"),
        "public_email": public_email,
        "obfuscated_email": obfuscated_email,
        "public_phone": public_phone,
        "obfuscated_phone": obfuscated_phone
    }

    return info

# Crear el menú principal
def main_menu():
    buttons = [
        [InlineKeyboardButton("Añadir SESSION_ID", callback_data="add_session")]
    ]
    
    if session_id:
        buttons.append([InlineKeyboardButton("Buscar usuario de Instagram", callback_data="search_user")])

    return InlineKeyboardMarkup(buttons)

# Crear el menú para buscar usuario
def search_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Buscar usuario de Instagram", callback_data="search_user")]
    ]) if session_id else None

# Comando /start
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(
        f"🌟 **SESSION_ID actual:** {session_id if session_id else 'No disponible'}\n\n"
        "¡Bienvenido al bot OSINT de Instagram! 🔍\n\n"
        "Por favor, selecciona una opción del menú.",
        reply_markup=main_menu()
    )

# Manejador para añadir SESSION_ID
@app.on_callback_query(filters.regex("add_session"))
async def add_session(client, callback_query):
    await callback_query.message.edit_text(
        "Por favor, envíame tu **SESSION_ID** para continuar.",
        reply_markup=None
    )
    app.add_handler(filters.text & ~filters.command(["start", "help"]), handle_session_id)

# Manejar el ingreso del SESSION_ID
async def handle_session_id(client, message):
    global session_id
    session_id = message.text.strip()
    
    if not session_id:
        await message.reply_text("❌ El **SESSION_ID** es necesario para continuar. Por favor, envíalo de nuevo.")
        return

    # Confirmar que se ha recibido el SESSION_ID correctamente
    await message.reply_text(
        "✅ **SESSION_ID** recibido correctamente.\n\n"
        "Ahora puedes buscar un usuario de Instagram. Usa el menú para hacerlo.",
        reply_markup=main_menu()
    )

    # Eliminar el manejador que espera el SESSION_ID para evitar bucles
    app.remove_handler(handle_session_id)

# Manejador para buscar usuario
@app.on_callback_query(filters.regex("search_user"))
async def search_user(client, callback_query):
    if not session_id:
        await callback_query.message.edit_text(
            "❌ **SESSION_ID** no ha sido proporcionado. Por favor, ingrésalo primero para poder buscar un usuario de Instagram."
        )
        return

    await callback_query.message.edit_text(
        "Envíame el nombre de usuario de Instagram que quieres buscar."
    )
    app.add_handler(filters.text & ~filters.command(["start", "help"]), handle_instagram_username)

# Buscar usuario de Instagram
async def handle_instagram_username(client, message):
    username = message.text.strip()

    await message.reply_text("🔍 Buscando información, espera un momento...")

    # Asegúrate de que el SESSION_ID esté presente
    if not session_id:
        await message.reply_text("❌ El **SESSION_ID** no está disponible. Proporciónalo primero.")
        return

    data = get_instagram_info(username, session_id)

    if "error" in data:
        await message.reply_text(f"❌ Error: {data['error']}")
    else:
        info_msg = (
            f"🔎 **Información de Instagram** 🔍\n\n"
            f"📧 **Email público:** {data['public_email']}\n"
            f"📧 **Email obfuscado:** {data['obfuscated_email']}\n"
            f"📞 **Teléfono público:** {data['public_phone']}\n"
            f"📞 **Teléfono obfuscado:** {data['obfuscated_phone']}\n"
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
