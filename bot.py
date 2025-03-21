import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# Configuración de logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Token de tu bot
BOT_TOKEN = '7063978224:AAF0YIR07nep1ygCgLPY9GdXrndV-3efVgU'

# Detalles para el Email Spoofing
SENDER_EMAIL = "tucorreo@gmail.com"  # Tu correo real
SENDER_PASSWORD = "tu_contraseña"  # La contraseña de tu cuenta de correo
SMTP_SERVER = "smtp.gmail.com"  # Usamos Gmail como servidor SMTP
SMTP_PORT = 587

# Comando /start
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('¡Hola! Soy tu bot, ¿en qué puedo ayudarte?')

# Función para realizar email spoofing
def spoof_email(to_email, subject, body):
    try:
        # Crear el mensaje del correo
        message = MIMEMultipart()
        message['From'] = SENDER_EMAIL
        message['To'] = to_email
        message['Subject'] = subject

        # Agregar cuerpo al correo
        message.attach(MIMEText(body, 'plain'))

        # Establecer conexión con el servidor SMTP y enviar el correo
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()  # Cifra la conexión
        server.login(SENDER_EMAIL, SENDER_PASSWORD)  # Inicia sesión en el correo
        text = message.as_string()  # Convierte el mensaje en formato string
        server.sendmail(SENDER_EMAIL, to_email, text)  # Envía el correo
        server.quit()  # Cierra la conexión
        return "Correo enviado exitosamente."
    except Exception as e:
        return f"Ocurrió un error al enviar el correo: {e}"

# Comando /spoof para ejecutar el email spoofing
def spoof(update: Update, context: CallbackContext) -> None:
    try:
        # Leer los parámetros del comando: /spoof <to_email> <subject> <body>
        if len(context.args) < 3:
            update.message.reply_text("Por favor, usa el formato: /spoof <correo_destino> <asunto> <cuerpo>")
            return
        
        to_email = context.args[0]
        subject = context.args[1]
        body = ' '.join(context.args[2:])
        
        result = spoof_email(to_email, subject, body)
        update.message.reply_text(result)
    except Exception as e:
        update.message.reply_text(f"Error: {str(e)}")

# Función principal que arranca el bot
def main() -> None:
    # Crea un Updater con el token de tu bot
    updater = Updater(BOT_TOKEN)

    # Obtiene el dispatcher para registrar los handlers
    dispatcher = updater.dispatcher

    # Registro del comando /start y /spoof
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("spoof", spoof))

    # Empieza el bot
    updater.start_polling()

    # Mantiene el bot funcionando hasta que se interrumpa con Ctrl+C
    updater.idle()

if __name__ == '__main__':
    main()
