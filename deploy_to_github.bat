@echo off
echo 🚀 Subiendo proyecto a GitHub...

cd /d %~dp0

REM Inicializar git si no está inicializado
if not exist .git (
    echo 📁 Inicializando repositorio git...
    git init
)

REM Configurar usuario (cambiar por tus datos)
git config user.name "Davey Mena"
git config user.email "daveymena@example.com"

REM Agregar remote si no existe
git remote -v | findstr "origin" >nul
if errorlevel 1 (
    echo 🔗 Agregando repositorio remoto...
    git remote add origin https://github.com/daveymena/bot-agente-ventas.git
)

REM Crear .gitignore si no existe
if not exist .gitignore (
    echo 📝 Creando .gitignore...
    echo venv/ > .gitignore
    echo __pycache__/ >> .gitignore
    echo *.pyc >> .gitignore
    echo .env >> .gitignore
    echo logs/ >> .gitignore
    echo temp/ >> .gitignore
    echo .vscode/ >> .gitignore
)

REM Agregar todos los archivos
echo 📦 Agregando archivos...
git add .

REM Hacer commit
echo 💾 Creando commit...
git commit -m "🚀 Agente de Ventas WhatsApp - Versión completa con despliegue

✅ Características implementadas:
- Procesamiento de mensajes WhatsApp
- IA con Google Gemini
- Scraping de productos
- Webhook API REST
- Validación de conexión Evolution API
- Sistema de logging completo

✅ Opciones de despliegue:
- Ngrok para desarrollo
- Vercel para producción
- Railway y Render alternativos
- VPS con guía completa

✅ Archivos de configuración:
- vercel.json para despliegue
- Scripts de automatización
- Guías de instalación y despliegue"

REM Subir a GitHub
echo 📤 Subiendo a GitHub...
git push -u origin main

if errorlevel 0 (
    echo ✅ ¡Proyecto subido exitosamente a GitHub!
    echo 🔗 https://github.com/daveymena/bot-agente-ventas
) else (
    echo ❌ Error al subir. Revisa las credenciales o el repositorio.
)

pause
