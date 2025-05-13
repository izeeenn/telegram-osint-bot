import os
import json
import requests
from urllib.parse import quote_plus
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from dotenv import load_dotenv

load_dotenv()
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SESSION_ID = os.getenv("SESSION_ID")

app = Client("osint_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Función para obtener información de Instagram
def get_instagram_info(username, session_id):
    headers = {
        "User-Agent": "Instagram 101.0.0.15.120",
        "x-ig-app-id": "936619743392459"
    }
    cookies = {"sessionid": session_id}

    try:
        response = requests.get(
            f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}",
            headers=headers,
            cookies=cookies,
            timeout=10
        )

        if response.status_code == 404:
            return {"error": "Usuario no encontrado"}

        user_data = response.json().get("data", {}).get("user")
        if not user_data:
            return {"error": "No se pudo obtener información del usuario"}

        obfuscated = advanced_lookup(username, session_id)

        return {
            "username": user_data.get("username", "No disponible"),
            "full_name": user_data.get("full_name", "No disponible"),
            "user_id": user_data.get("id", "Desconocido"),
            "followers": user_data.get("edge_followed_by", {}).get("count", "No disponible"),
            "is_private": user_data.get("is_private", False),
            "bio": user_data.get("biography", "No disponible"),
            "profile_picture": user_data.get("profile_pic_url_hd", "No disponible"),
            "public_email": user_data.get("public_email", "No disponible"),
            "public_phone": user_data.get("public_phone_number", "No disponible"),
            "obfuscated_email": obfuscated.get("obfuscated_email", "No disponible"),
            "obfuscated_phone": obfuscated.get("obfuscated_phone", "No disponible"),
        }

    except Exception as e:
        return {"error": f"Error al obtener información: {str(e)}"}

def advanced_lookup(username, session_id):
    headers = {
        "User-Agent": "Instagram 101.0.0.15.120",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
    }

    data = "signed_body=SIGNATURE." + quote_plus(json.dumps({"q": username, "skip_recovery": "1"}))

    try:
        response = requests.post(
            "https://i.instagram.com/api/v1/users/lookup/",
            headers=headers,
            data=data,
            cookies={"sessionid": session_id},
            timeout=10
        )
        return response.json()
    except Exception:
        return {"obfuscated_email": "Error", "obfuscated_phone": "Error"}

# Menús
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔎 Buscar usuario de Instagram", callback_data="search_user")],
        [InlineKeyboardButton("🔑 Cambiar SESSION_ID", callback_data="change_session")]
    ])

def back_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Volver al menú principal", callback_data="back_to_main")]
    ])

# Estados por usuario (para saber si espera input)
user_states = {}

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(
        f"🌟 **SESSION_ID actual:** `{SESSION_ID}`\n\n"
        "¡Bienvenido! Selecciona una opción:",
        reply_markup=main_menu()
    )

@app.on_callback_query(filters.regex("search_user"))
async def handle_search_user(client, callback):
    user_id = callback.from_user.id
    user_states[user_id] = "waiting_for_username"
    await callback.message.edit_text("📥 Envíame el nombre de usuario de Instagram:")

@app.on_callback_query(filters.regex("change_session"))
async def change_session(client, callback):
    user_id = callback.from_user.id
    user_states[user_id] = "waiting_for_session"
    await callback.message.edit_text("🔐 Envíame el nuevo SESSION_ID:")

@app.on_callback_query(filters.regex("back_to_main"))
async def back_to_main(client, callback):
    await callback.message.edit_text(
        f"🌟 **SESSION_ID actual:** `{SESSION_ID}`",
        reply_markup=main_menu()
    )

@app.on_message(filters.private & filters.text)
async def handle_text(client, message):
    global SESSION_ID
    user_id = message.from_user.id
    state = user_states.get(user_id)

    if state == "waiting_for_username":
        username = message.text.strip()
        await message.reply_text("🔍 Buscando información...")

        data = get_instagram_info(username, SESSION_ID)

        if "error" in data:
            await message.reply_text(f"❌ Error: {data['error']}")
        else:
            caption = (
                f"📌 **Usuario:** {data['username']}\n"
                f"📛 **Nombre:** {data['full_name']}\n"
                f"🆔 **ID:** {data['user_id']}\n"
                f"👥 **Seguidores:** {data['followers']}\n"
                f"🔒 **Privada:** {'Sí' if data['is_private'] else 'No'}\n"
                f"📝 **Bio:** {data['bio']}\n"
                f"📧 **Email público:** {data['public_email']}\n"
                f"📞 **Teléfono público:** {data['public_phone']}\n"
                f"📧 **Correo oculto:** {data['obfuscated_email']}\n"
                f"📞 **Teléfono oculto:** {data['obfuscated_phone']}"
            )
            await message.reply_photo(data["profile_picture"], caption=caption)

        user_states[user_id] = None

    elif state == "waiting_for_session":
        new_sid = message.text.strip()
        if new_sid:
            SESSION_ID = new_sid
            await message.reply_text("✅ SESSION_ID actualizado correctamente.")
        else:
            await message.reply_text("❌ El SESSION_ID no puede estar vacío.")
        user_states[user_id] = None

        await message.reply_text(
            f"🌟 **SESSION_ID actual:** `{SESSION_ID}`",
            reply_markup=main_menu()
        )

if __name__ == "__main__":
    print("✅ Bot OSINT corriendo en Railway")
    app.run()
