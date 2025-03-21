#!/bin/bash

# Variables de entorno
GITHUB_REPO="izeeenn/telegram-osint-bot"
SMTP_USER="izen"
BOT_TOKEN="7063978224:AAF0YIR07nep1ygCgLPY9GdXrndV-3efVgU"
API_ID="21697830"
API_HASH="8d1daf27b44c5ecbca8707b73a4007f1"

# Crear y configurar el entorno virtual
echo "📦 Instalando dependencias..."
sudo apt update && sudo apt install -y git python3 python3-pip postfix mailutils

# Clonar el repositorio de GitHub
echo "📥 Clonando repositorio..."
git clone https://github.com/$GITHUB_REPO.git
cd smtp || exit 1

# Crear archivo .env
echo "🔧 Configurando archivo .env..."
cat <<EOT > .env
BOT_TOKEN=$BOT_TOKEN
API_ID=$API_ID
API_HASH=$API_HASH
SMTP_USER=$SMTP_USER
SMTP_PASSWORD=izen
SMTP_SERVER=localhost
SMTP_PORT=587
EOT

# Configurar Postfix para SMTP local
echo "📧 Configurando Postfix..."
sudo debconf-set-selections <<< "postfix postfix/mailname string localhost"
sudo debconf-set-selections <<< "postfix postfix/main_mailer_type string 'Internet Site'"
sudo systemctl restart postfix

# Subir cambios a GitHub
echo "🚀 Subiendo cambios a GitHub..."
git add .
git commit -m "Automated deployment"
git push origin main

# Desplegar en Railway
echo "🚂 Desplegando en Railway..."
railway login
railway link $GITHUB_REPO
railway up

echo "✅ ¡Despliegue completado!"
