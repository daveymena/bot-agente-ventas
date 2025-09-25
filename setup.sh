#!/bin/bash

# ========================================
# SETUP AUTOMÁTICO DEL AGENTE DE VENTAS
# ========================================

echo "🚀 Configurando Agente de Ventas Python..."
echo "=" * 50

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 no encontrado. Instálalo primero."
    exit 1
fi

echo "✅ Python 3 encontrado"

# Crear directorios necesarios
echo "📁 Creando directorios..."
mkdir -p logs temp

# Instalar dependencias
echo "📦 Instalando dependencias..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Error instalando dependencias"
    exit 1
fi

echo "✅ Dependencias instaladas"

# Verificar configuración
echo "🔧 Verificando configuración..."
if [ -f .env ]; then
    echo "✅ Archivo .env encontrado"
else
    echo "⚠️  Archivo .env no encontrado. Usando configuración por defecto."
    cp .env.example .env
fi

# Ejecutar prueba de configuración
echo "🧪 Ejecutando prueba de configuración..."
python3 test_config.py

echo ""
echo "🎉 ¡Configuración completada!"
echo ""
echo "📋 PRÓXIMOS PASOS:"
echo "   1. Revisa la configuración en el archivo .env"
echo "   2. Ejecuta: python3 main.py"
echo "   3. Configura el webhook en Evolution API"
echo ""
echo "💡 Para más información, consulta el README.md"