import os
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
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

# Función para obtener información de Instagram (incluyendo datos obfuscados)
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

# Comando /start
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(
        "¡Bienvenido al bot OSINT de Instagram! 🔍\n\nPor favor, introduce tu session_id de Instagram para comenzar:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("Enviar session_id")]], 
            one_time_keyboard=True
        )
    )

# Recibir session_id
@app.on_message(filters.text & ~filters.command(["start", "help"]))
async def receive_session_id(client, message):
    session_id = message.text.strip()
    
    # Verificar si el session_id parece válido (esto es solo una validación básica)
    if len(session_id) > 10:  # Comprobamos si tiene longitud suficiente
        # Almacenar el session_id (se puede almacenar temporalmente en memoria o en base de datos si fuera necesario)
        user_id = message.from_user.id
        client_data = app.get_chat(user_id).get("session_id", None)
        
        # Guardar session_id en el diccionario o base de datos (aquí solo lo estamos almacenando en la memoria)
        app.storage[user_id] = {"session_id": session_id}
        
        await message.reply_text(f"Session ID guardada correctamente. Ahora, envíame un nombre de usuario de Instagram para buscar.")
    else:
        await message.reply_text("❌ El session_id no es válido. Por favor, revisa e intenta nuevamente.")

# Buscar usuario de Instagram
@app.on_message(filters.text & ~filters.command("start"))
async def handle_instagram_username(client, message):
    username = message.text.strip()

    # Obtener session_id almacenado
    user_id = message.from_user.id
    user_data = app.storage.get(user_id, None)
    if not user_data or "session_id" not in user_data:
        await message.reply_text("❌ No se ha guardado tu session_id. Por favor, envíalo primero.")
        return

    session_id = user_data["session_id"]
    await message.reply_text("🔍 Buscando información, espera un momento...")

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
    app.storage = {}  # Asegúrate de usar un diccionario para almacenar los session_id de cada usuario
    app.run()
