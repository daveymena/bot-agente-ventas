#!/bin/bash

# ========================================
# DESPLIEGUE EN GITHUB + VERCEL
# ========================================

echo "Desplegando en GitHub + Vercel..."
echo "=" * 60

# Verificar si Git esta inicializado
if [ ! -d .git ]; then
    echo "Git no inicializado. Ejecuta setup_git_and_vercel.py primero"
    exit 1
fi

# Verificar si hay cambios
if git diff --quiet && git diff --staged --quiet; then
    echo "No hay cambios para commitear"
else
    echo "Agregando cambios..."
    git add .
    git commit -m "Actualizacion del Agente de Ventas"
fi

# Crear rama main si no existe
if ! git show-ref --verify --quiet refs/heads/main; then
    git branch -M main
fi

# Conectar con GitHub (si no esta conectado)
if ! git remote get-url origin > /dev/null 2>&1; then
    echo "Conectando con GitHub..."
    echo "Necesitas crear un repositorio en GitHub primero"
    echo "Ve a: https://github.com/new"
    echo "Crea un repositorio llamado: evolution-bot-python"
    echo ""
    read -p "URL del repositorio GitHub: " repo_url

    git remote add origin $repo_url
    git push -u origin main
else
    echo "Subiendo cambios a GitHub..."
    git push
fi

echo "Codigo subido a GitHub"
echo ""
echo "PROXIMOS PASOS EN VERCEL:"
echo "   1. Ve a: https://vercel.com"
echo "   2. Conecta tu cuenta de GitHub"
echo "   3. Importa el repositorio: evolution-bot-python"
echo "   4. Configura las variables de entorno:"
echo "      • GOOGLE_GEMINI_API_KEY"
echo "      • WHATSAPP_SERVER_URL"
echo "      • WHATSAPP_INSTANCE_NAME"
echo "      • WHATSAPP_API_KEY"
echo "   5. Despliega!"
echo ""
echo "Tu webhook sera:"
echo "   https://tu-app.vercel.app/webhook"
