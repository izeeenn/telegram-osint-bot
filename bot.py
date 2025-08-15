# ==============================================================================
#                      💻 Exyl Bot de Búsqueda
# ==============================================================================
# Este bot de Telegram permite a los usuarios buscar en bases de datos públicas
# de España utilizando una clave de API. Incluye funciones de administración
# para gestionar usuarios y claves.
# ------------------------------------------------------------------------------

import logging
import sqlite3
import requests
import json
import time
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)

# 🚀 Cargar las variables de entorno desde el archivo .env
load_dotenv()

# ==============================================================================
#                           ⚙️ Configuración
# ==============================================================================

# 📝 Configuración del logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# 🔑 Cargar variables de entorno
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
EXYL_API_KEY = os.getenv("EXYL_API_KEY")

# 👥 Manejo robusto de ADMIN_IDS
# Convierte la cadena de IDs de entorno en una lista de enteros.
admin_ids_str = os.getenv("ADMIN_IDS")
ADMIN_IDS = [int(admin_id) for admin_id in admin_ids_str.split(",")] if admin_ids_str else []

# 🤖 Estados para ConversationHandler
(
    REDEEM_KEY_INPUT,
    ADMIN_MENU_HANDLER,
    CREATE_KEY_DURATION,
    REVOKE_KEY_INPUT,
) = range(4)

# ==============================================================================
#                           📊 Base de Datos SQLite
# ==============================================================================


def init_db():
    """
    🛠️ Inicializa las tablas de la base de datos 'bot_data.db' si no existen.

    Crea tres tablas:
    - `users`: Para almacenar la información de los usuarios del bot.
    - `api_keys`: Para gestionar las claves de API, su estado y asignación.
    - `search_history`: Para registrar las búsquedas realizadas.
    """
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            api_key TEXT,
            last_search INTEGER DEFAULT 0,
            is_admin BOOLEAN DEFAULT 0
        )
    """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS api_keys (
            key TEXT PRIMARY KEY,
            user_id INTEGER,
            is_lifetime BOOLEAN,
            expiry_date INTEGER
        )
    """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            query TEXT,
            timestamp INTEGER
        )
    """
    )
    conn.commit()
    conn.close()


# ------------------------------------------------------------------------------
#                          Helper Functions de DB
# ------------------------------------------------------------------------------


def get_user_data(user_id):
    """Obtiene los datos de un usuario de la base de datos."""
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT api_key, last_search FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result


def create_user_if_not_exists(user_id):
    """Crea un nuevo usuario en la base de datos si no existe previamente."""
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()


def get_cooldown(user_id):
    """
    ⏳ Calcula el tiempo restante de enfriamiento para un usuario.

    Args:
        user_id (int): El ID del usuario.

    Returns:
        int: El tiempo de enfriamiento restante en segundos.
    """
    user_data = get_user_data(user_id)
    if user_data:
        last_search = user_data[1] if user_data[1] is not None else 0
        cooldown_time = 7
        remaining = cooldown_time - (int(time.time()) - last_search)
        return remaining if remaining > 0 else 0
    return 0


def update_last_search(user_id):
    """Actualiza el timestamp de la última búsqueda de un usuario."""
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET last_search = ? WHERE user_id = ?",
        (int(time.time()), user_id),
    )
    conn.commit()
    conn.close()


def log_search(user_id, query):
    """Registra una búsqueda en el historial con timestamp."""
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO search_history (user_id, query, timestamp) VALUES (?, ?, ?)",
        (user_id, query, int(time.time())),
    )
    conn.commit()
    conn.close()


def is_admin(user_id):
    """Verifica si un usuario es administrador."""
    return user_id in ADMIN_IDS


def get_api_key_for_user(user_id):
    """Obtiene la clave API asignada a un usuario."""
    user_data = get_user_data(user_id)
    return user_data[0] if user_data else None


def get_api_key_details(key):
    """Obtiene los detalles de una clave API específica."""
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT expiry_date, is_lifetime FROM api_keys WHERE key = ?", (key,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {"expiry_date": result[0], "is_lifetime": result[1]}
    return None


def is_api_key_valid(key):
    """Verifica si una clave API es válida y no ha caducado."""
    details = get_api_key_details(key)
    if not details:
        return False

    if details["is_lifetime"]:
        return True

    return int(time.time()) < details["expiry_date"]


def get_session():
    """Retorna una sesión HTTP persistente para mejorar el rendimiento de las peticiones."""
    return requests.Session()


# ==============================================================================
#                          ⌨️ Menús y Teclados Inline
# ==============================================================================


def get_admin_inline_keyboard():
    """Genera el teclado inline para el menú de administración."""
    keyboard = [
        [InlineKeyboardButton("➕ Crear Clave", callback_data="admin_create_key")],
        [InlineKeyboardButton("➖ Revocar Clave", callback_data="admin_revoke_key")],
        [InlineKeyboardButton("📋 Listar Claves", callback_data="admin_list_keys")],
        [InlineKeyboardButton("📊 Exportar Historial", callback_data="admin_export_db")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_create_key_duration_keyboard():
    """Genera el teclado inline para elegir la duración de la clave a crear."""
    keyboard = [
        [
            InlineKeyboardButton("1 Día", callback_data="create_key_1d"),
            InlineKeyboardButton("7 Días", callback_data="create_key_7d"),
        ],
        [
            InlineKeyboardButton("30 Días", callback_data="create_key_30d"),
            InlineKeyboardButton("1 Año", callback_data="create_key_1y"),
        ],
        [InlineKeyboardButton("✅ Lifetime", callback_data="create_key_lifetime")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_admin_action")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ==============================================================================
#                           🤖 Comandos del Bot
# ==============================================================================


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el comando /start. Saluda al usuario y muestra los comandos principales."""
    create_user_if_not_exists(update.effective_user.id)

    start_message = (
        "🚀 **¡Hola! Bienvenido a Spain O$int Bot!**\n\n"
        "Este bot te permite buscar información multiples bases de datos de España.\n"
        "Para empezar, activa tu clave con `/redeem`.\n\n"
        "📌 **Comandos disponibles:**\n"
        "• `/spain <consulta>`\n"
        "• `/redeem`\n"
        "• `/profile`\n"
    )
    await update.message.reply_text(start_message, parse_mode="Markdown")


async def spain_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el comando /spain para realizar una búsqueda directa."""
    user_id = update.effective_user.id
    query = " ".join(context.args)

    if not query:
        await update.message.reply_text(
            "🚫 **Error:** Por favor, escribe lo que deseas buscar después del comando.\n"
            "Ejemplo: `/spain Juan Pérez`"
        )
        return

    api_key = get_api_key_for_user(user_id)
    if not api_key or not is_api_key_valid(api_key):
        await update.message.reply_text(
            "🚫 **Acceso Denegado:** Necesitas una clave API válida para realizar búsquedas.\n"
            "Usa el comando `/redeem` para activarla."
        )
        return

    cooldown_remaining = get_cooldown(user_id)
    if cooldown_remaining > 0:
        await update.message.reply_text(
            f"⏱️ **Espera por favor:** Debes esperar {cooldown_remaining} segundos para realizar otra búsqueda."
        )
        return

    headers = {"X-Api-Key": EXYL_API_KEY}
    session = get_session()
    api_url = f"http://exyl.org/search?q={query}"

    try:
        await update.message.reply_text("⌛️ **Buscando...**")
        response = session.get(api_url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        log_search(user_id, query)
        update_last_search(user_id)

        if not data or not data.get("results"):
            await update.message.reply_text("🤷 **Búsqueda sin resultados:** No se encontraron datos que coincidan con tu consulta.")
            return

        # ------------------- 🆕 INICIO DE LA MEJORA VISUAL 🆕 -------------------
        
        # Simplemente adjuntar el archivo JSON directamente
        json_filename = f"results_{user_id}_{int(time.time())}.json"
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            
        await update.message.reply_document(
            open(json_filename, "rb"),
            caption=f"✅ Se encontraron {len(data['results'])} resultados."
        )
        os.remove(json_filename)
        
        # -------------------- 🔚 FIN DE LA MEJORA VISUAL 🔚 --------------------

    except requests.exceptions.RequestException as e:
        logger.error(f"Error de red/HTTP al buscar: {e}")
        await update.message.reply_text("🔌 **Error de Conexión:** Ha ocurrido un problema al contactar con la API. Inténtalo de nuevo más tarde.")
    except Exception as e:
        logger.error(f"Error inesperado al buscar: {e}")
        await update.message.reply_text("😵 **Error Inesperado:** Algo ha salido mal. Por favor, avisa a un administrador.")


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra el perfil del usuario, incluyendo el estado de su clave API."""
    user_id = update.effective_user.id
    create_user_if_not_exists(user_id)
    api_key = get_api_key_for_user(user_id)

    profile_message = f"👤 **Tu Perfil de Usuario**\n\n"

    if api_key:
        key_details = get_api_key_details(api_key)
        if key_details:
            is_lifetime = key_details["is_lifetime"]
            expiry_date = key_details["expiry_date"]

            status = "✅ *Activa*"
            if not is_api_key_valid(api_key):
                status = "❌ *Caducada*"

            expiry_info = "Lifetime ✨" if is_lifetime else f"{datetime.fromtimestamp(expiry_date).strftime('%Y-%m-%d %H:%M:%S')}"

            profile_message += f"🔑 **Clave API:** `{api_key}`\n"
            profile_message += f"🚦 **Estado:** {status}\n"
            profile_message += f"📅 **Expira:** {expiry_info}\n"
        else:
            profile_message += f"⚠️ **Clave API:** `{api_key}`\n"
            profile_message += "🚦 **Estado:** *Inválida o eliminada*. Contacta a un administrador.\n"
    else:
        profile_message += "⚠️ **Clave API:** *No tienes una clave API activa.*\n"
        profile_message += "Usa el comando `/redeem` para activar una clave y empezar a buscar."

    await update.message.reply_text(profile_message, parse_mode="Markdown")


# ==============================================================================
#                           🔐 Redención de Clave
# ==============================================================================


async def redeem_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el proceso para redimir una clave API."""
    create_user_if_not_exists(update.effective_user.id)
    await update.message.reply_text(
        "🔑 **Activación de Clave:**\n"
        "Por favor, introduce la clave API que deseas activar."
    )
    return REDEEM_KEY_INPUT


async def redeem_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la clave API introducida por el usuario y la asigna si es válida."""
    user_id = update.effective_user.id
    key = update.message.text.strip()
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()

    cursor.execute("SELECT user_id, is_lifetime, expiry_date FROM api_keys WHERE key = ?", (key,))
    result = cursor.fetchone()

    if not result:
        await update.message.reply_text("❌ **Clave Inválida:** La clave que has introducido no es válida o no existe.")
        conn.close()
        return ConversationHandler.END

    assigned_user_id, is_lifetime, expiry_date = result

    if assigned_user_id is not None:
        await update.message.reply_text("⚠️ **Clave Usada:** Esta clave ya ha sido utilizada por otro usuario. No se puede usar de nuevo.")
        conn.close()
        return ConversationHandler.END

    if not is_lifetime and int(time.time()) >= expiry_date:
        await update.message.reply_text("⏳ **Clave Caducada:** Esta clave ha expirado. Por favor, solicita una nueva.")
        conn.close()
        return ConversationHandler.END

    cursor.execute("REPLACE INTO users (user_id, api_key) VALUES (?, ?)", (user_id, key))
    cursor.execute("UPDATE api_keys SET user_id = ? WHERE key = ?", (user_id, key))
    conn.commit()
    conn.close()

    await update.message.reply_text(
        "✅ **¡Éxito!** 🎉 Tu clave ha sido activada correctamente.\n"
        "Ahora puedes comenzar a buscar con el comando `/spain <consulta>`."
    )
    return ConversationHandler.END


# ==============================================================================
#                           👨‍💻 Menú de Administración
# ==============================================================================


async def admin_menu_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra el menú de administración con botones inline."""
    message_text = "🛠️ **Menú de Administración** 🛠️\n\nSelecciona una opción para gestionar el bot:"

    if update.message:
        await update.message.reply_text(
            message_text,
            reply_markup=get_admin_inline_keyboard(),
            parse_mode="Markdown",
        )
    elif update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            message_text,
            reply_markup=get_admin_inline_keyboard(),
            parse_mode="Markdown",
        )
    return ADMIN_MENU_HANDLER


async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja los callbacks de los botones del menú de administración."""
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == "admin_create_key":
        await query.edit_message_text(
            "⏳ **Crear Clave:**\n"
            "Selecciona la duración de la nueva clave.",
            reply_markup=get_create_key_duration_keyboard(),
        )
        return CREATE_KEY_DURATION

    elif action == "admin_revoke_key":
        await query.edit_message_text(
            "🗑️ **Revocar Clave:**\n"
            "Por favor, introduce la clave que quieres anular."
        )
        return REVOKE_KEY_INPUT

    elif action == "admin_list_keys":
        await list_keys(update, context)
        # Volver al menú de administración después de la acción
        await query.message.reply_text(
            "🛠️ **Menú de Administración** 🛠️\n\nSelecciona una opción:",
            reply_markup=get_admin_inline_keyboard(),
            parse_mode="Markdown",
        )
        return ADMIN_MENU_HANDLER

    elif action == "admin_export_db":
        await export_db(update, context)
        # Volver al menú de administración después de la acción
        await query.message.reply_text(
            "🛠️ **Menú de Administración** 🛠️\n\nSelecciona una opción:",
            reply_markup=get_admin_inline_keyboard(),
            parse_mode="Markdown",
        )
        return ADMIN_MENU_HANDLER

    return ADMIN_MENU_HANDLER


async def handle_create_key_duration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la duración seleccionada para la creación de una clave y la inserta en la DB."""
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == "cancel_admin_action":
        await query.edit_message_text("❌ **Acción Cancelada:** Has cancelado la operación.", reply_markup=get_admin_inline_keyboard())
        return ADMIN_MENU_HANDLER

    duration_type = action.replace("create_key_", "")
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    new_key = os.urandom(16).hex()
    is_lifetime = False
    expiry_date = 0

    if duration_type == "lifetime":
        is_lifetime = True
        duration_str = "Lifetime"
    else:
        now = datetime.now()
        if duration_type == "1d":
            expiry_date = int((now + timedelta(days=1)).timestamp())
            duration_str = "1 Día"
        elif duration_type == "7d":
            expiry_date = int((now + timedelta(days=7)).timestamp())
            duration_str = "7 Días"
        elif duration_type == "30d":
            expiry_date = int((now + timedelta(days=30)).timestamp())
            duration_str = "30 Días"
        elif duration_type == "1y":
            expiry_date = int((now + timedelta(days=365)).timestamp())
            duration_str = "1 Año"
        else:
            await query.edit_message_text(
                "❌ **Error:** Duración no válida. Por favor, selecciona una opción del menú.",
                reply_markup=get_create_key_duration_keyboard(),
            )
            conn.close()
            return CREATE_KEY_DURATION

    try:
        cursor.execute(
            "INSERT INTO api_keys (key, is_lifetime, expiry_date) VALUES (?, ?, ?)",
            (new_key, is_lifetime, expiry_date),
        )
        conn.commit()
        await query.edit_message_text(
            f"✅ **¡Clave Creada con Éxito!** 🎉\n\n"
            f"**Tipo:** `{duration_str}`\n"
            f"**Clave:** `{new_key}`\n\n"
            "Puedes copiarla y asignarla a un usuario.",
            parse_mode="Markdown",
            reply_markup=get_admin_inline_keyboard(),
        )
    except sqlite3.Error as e:
        logger.error(f"Error al crear clave: {e}")
        await query.edit_message_text("❌ **Error:** No se pudo crear la clave. Revisa los logs.")
    finally:
        conn.close()

    return ADMIN_MENU_HANDLER


async def revoke_key_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la clave a revocar introducida por el administrador y la elimina de la DB."""
    key = update.message.text.strip()
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()

    cursor.execute("SELECT key FROM api_keys WHERE key = ?", (key,))
    exists = cursor.fetchone()

    if not exists:
        await update.message.reply_text("❌ **Error:** Esa clave no existe en la base de datos. Intenta de nuevo o `/cancel`.")
        conn.close()
        return REVOKE_KEY_INPUT

    cursor.execute("DELETE FROM api_keys WHERE key = ?", (key,))
    cursor.execute("UPDATE users SET api_key = NULL WHERE api_key = ?", (key,))
    conn.commit()
    conn.close()
    await update.message.reply_text(
        f"✅ **Clave Revocada:** La clave `{key}` ha sido anulada con éxito. 🗑️",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def list_keys(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lista todas las claves API registradas y su estado."""
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT key, user_id, is_lifetime, expiry_date FROM api_keys")
    keys = cursor.fetchall()
    conn.close()

    if not keys:
        message_text = "📋 **Listado de Claves:** No hay claves API registradas."
        await update.callback_query.message.reply_text(message_text, parse_mode="Markdown")
        return

    message_text = "📋 **Listado de Claves API** 📋\n\n"
    for key_data in keys:
        key_str, user_id, is_lifetime, expiry_date = key_data
        status = "Lifetime ✨" if is_lifetime else f"Expira el: {datetime.fromtimestamp(expiry_date).strftime('%Y-%m-%d %H:%M:%S')}"
        user_info = f"Asignada a: `{user_id}`" if user_id else "Sin asignar 🆓"
        message_text += f"• `{key_str}`\n  Estado: {status}\n  {user_info}\n\n"

    await update.callback_query.message.reply_text(message_text, parse_mode="Markdown")


async def export_db(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Exporta el historial de búsquedas a un archivo CSV."""
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, query, timestamp FROM search_history")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.callback_query.message.reply_text("🤷‍♀️ **Historial:** No hay historial de búsquedas para exportar.")
        return

    import csv

    csv_filename = f"search_history_{int(time.time())}.csv"
    with open(csv_filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["user_id", "query", "timestamp"])
        writer.writerows(rows)

    await update.callback_query.message.reply_document(open(csv_filename, "rb"), caption="📊 **Exportado:** Historial de búsquedas.")
    os.remove(csv_filename)


# ==============================================================================
#                             ✨ Funciones Generales
# ==============================================================================


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela cualquier conversación activa."""
    if update.message:
        await update.message.reply_text("❌ **Cancelado:** Acción cancelada. Puedes usar un nuevo comando para empezar.")
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text("❌ **Cancelado:** Acción cancelada. Puedes usar un nuevo comando para empezar.")
    return ConversationHandler.END


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja errores de forma elegante y notifica al usuario."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    try:
        if update.effective_chat:
            await update.effective_chat.send_message(
                "⚠️ **¡Ups!** Algo salió mal. Por favor, intenta de nuevo más tarde."
            )
    except Exception as e:
        logger.error(f"Failed to send error message to user: {e}")


async def post_init(application: Application):
    """
    Configura los comandos del bot al iniciar.
    Esto permite que los comandos aparezcan en el menú de Telegram.
    """
    commands_for_all = [
        BotCommand("start", "Inicia el bot y ve los comandos"),
        BotCommand("spain", "Busca datos públicos de España"),
        BotCommand("redeem", "Activa tu clave API"),
        BotCommand("profile", "Ver el estado de tu clave API"),
        BotCommand("admin", "Ver el estado de tu clave API"),
    ]
    await application.bot.set_my_commands(commands_for_all)
    logger.info("Comandos globales configurados.")


def main() -> None:
    """
    🌟 Función principal para ejecutar el bot.
    Configura la aplicación, añade los handlers y la inicia.
    """
    init_db()

    if not TELEGRAM_BOT_TOKEN:
        logger.error("Error: TELEGRAM_BOT_TOKEN no está configurado.")
        exit(1)

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    # Manejador de comandos directos (sin ConversationHandler)
    application.add_handler(CommandHandler("spain", spain_search_command))

    # ConversationHandler para redimir clave
    application.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("redeem", redeem_start)],
            states={REDEEM_KEY_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, redeem_key)]},
            fallbacks=[CommandHandler("cancel", cancel_conversation)],
        )
    )

    # ConversationHandler para el menú de administración (Solo para ADMINS)
    application.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("admin", admin_menu_start, filters.User(user_id=ADMIN_IDS))],
            states={
                ADMIN_MENU_HANDLER: [CallbackQueryHandler(admin_callback_handler)],
                CREATE_KEY_DURATION: [CallbackQueryHandler(handle_create_key_duration, pattern="^create_key_|^cancel_admin_action")],
                REVOKE_KEY_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, revoke_key_input)],
            },
            fallbacks=[
                CommandHandler("cancel", cancel_conversation),
                CallbackQueryHandler(cancel_conversation, pattern="^cancel_admin_action"),
            ],
        )
    )

    # Comandos que no inician conversación
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("profile", profile))

    # Manejador de errores
    application.add_error_handler(error_handler)

    logger.info("Bot iniciado y esperando actualizaciones...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
