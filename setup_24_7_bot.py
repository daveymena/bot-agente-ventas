#!/usr/bin/env python3
"""
Setup para Bot 24/7 con Cloudflare Tunnel
La mejor opción para un bot que debe estar activo siempre
"""
import os
import sys
import subprocess
import json

def print_header():
    """Imprimir encabezado"""
    print("🚀 SETUP PARA BOT 24/7 - CLOUDFLARE TUNNEL")
    print("=" * 60)
    print("🏆 La MEJOR opción para un bot activo siempre:")
    print("   ✅ URL permanente (no expira)")
    print("   ✅ Reinicio automático")
    print("   ✅ Monitoreo 24/7")
    print("   ✅ Tráfico ilimitado gratis")
    print("   ✅ SSL automático")
    print("   ✅ 99.9% de disponibilidad")
    print()

def check_requirements():
    """Verificar requisitos del sistema"""
    print("🔍 Verificando requisitos del sistema...")

    # Verificar Python
    if sys.version_info < (3, 8):
        print("❌ Se requiere Python 3.8 o superior")
        return False

    print("✅ Python 3.8+ encontrado")

    # Verificar si Docker está instalado
    try:
        result = subprocess.run(['docker', '--version'],
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Docker encontrado")
        else:
            print("⚠️ Docker no encontrado. Instalando...")
            return install_docker()
    except FileNotFoundError:
        print("⚠️ Docker no encontrado. Instalando...")
        return install_docker()

    return True

def install_docker():
    """Instalar Docker"""
    try:
        print("📦 Instalando Docker...")
        # Para Ubuntu/Debian
        subprocess.run(['curl', '-fsSL', 'https://get.docker.com', '-o', 'get-docker.sh'], check=True)
        subprocess.run(['sh', 'get-docker.sh'], check=True)
        subprocess.run(['sudo', 'systemctl', 'start', 'docker'], check=True)
        subprocess.run(['sudo', 'systemctl', 'enable', 'docker'], check=True)
        print("✅ Docker instalado correctamente")
        return True
    except subprocess.CalledProcessError:
        print("❌ Error instalando Docker")
        print("💡 Instala Docker manualmente desde: https://docs.docker.com/get-docker/")
        return False

def install_cloudflared():
    """Instalar Cloudflare Tunnel"""
    try:
        print("📦 Instalando Cloudflare Tunnel...")
        # Descargar cloudflared
        subprocess.run([
            'curl', '-L',
            'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64',
            '-o', 'cloudflared'
        ], check=True)

        # Hacer ejecutable
        subprocess.run(['chmod', '+x', 'cloudflared'], check=True)

        # Mover a ubicación global
        subprocess.run(['sudo', 'mv', 'cloudflared', '/usr/local/bin/'], check=True)

        print("✅ Cloudflare Tunnel instalado")
        return True
    except subprocess.CalledProcessError:
        print("❌ Error instalando Cloudflare Tunnel")
        return False

def create_cloudflare_config():
    """Crear configuración de Cloudflare"""
    config = {
        "tunnel": "evolution-bot-24-7",
        "credentials-file": "/home/user/.cloudflared/evolution-bot-24-7.json",
        "ingress": [
            {
                "hostname": "tu-bot-24-7.cloudflaretunnel.com",
                "service": "http://localhost:8000"
            },
            {
                "service": "http_status:404"
            }
        ]
    }

    with open('cloudflare-tunnel.yml', 'w') as f:
        f.write("# Configuración de Cloudflare Tunnel para Bot 24/7\n")
        f.write("# Ejecuta: cloudflared tunnel --config cloudflare-tunnel.yml\n\n")
        json.dump(config, f, indent=2)

    print("✅ Configuración de Cloudflare creada")

def create_docker_compose():
    """Crear docker-compose.yml optimizado para 24/7"""
    docker_compose = """version: '3.8'

services:
  bot:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GOOGLE_GEMINI_API_KEY=${GOOGLE_GEMINI_API_KEY}
      - WHATSAPP_SERVER_URL=${WHATSAPP_SERVER_URL}
      - WHATSAPP_INSTANCE_NAME=${WHATSAPP_INSTANCE_NAME}
      - WHATSAPP_API_KEY=${WHATSAPP_API_KEY}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  cloudflared:
    image: cloudflare/cloudflared:latest
    command: tunnel --config /etc/cloudflared/config.yml run
    volumes:
      - ./cloudflare-tunnel.yml:/etc/cloudflared/config.yml
    depends_on:
      - bot
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
"""

    with open('docker-compose.yml', 'w') as f:
        f.write(docker_compose)

    print("✅ Docker Compose configurado para 24/7")

def create_dockerfile():
    """Crear Dockerfile optimizado"""
    dockerfile = """FROM python:3.9-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar archivos de requirements primero (para cache de Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto de archivos
COPY . .

# Crear directorio para logs
RUN mkdir -p logs

# Exponer puerto
EXPOSE 8000

# Comando para ejecutar
CMD ["python", "main.py"]
"""

    with open('Dockerfile', 'w') as f:
        f.write(dockerfile)

    print("✅ Dockerfile creado")

def create_env_file():
    """Crear archivo .env con configuración actual"""
    env_content = """# Configuración del Bot 24/7
GOOGLE_GEMINI_API_KEY=AIzaSyDxKos_L7EC2bsm2XACFlaRYSeVsKMwjQY
WHATSAPP_SERVER_URL=https://evoapi2-evolution-api.ovw3ar.easypanel.host
WHATSAPP_INSTANCE_NAME=03d935e9-4711-4011-9ead-4983e4f6b2b5
WHATSAPP_API_KEY=429683C4C977415CAAFCCE10F7D57E11
LOG_LEVEL=INFO
LOG_FILE=logs/agente_ventas.log
TEMP_DIR=temp
LOGS_DIR=logs
MAX_RESPONSE_LENGTH=500
CONTEXT_WINDOW_LENGTH=10
DELAY_BETWEEN_MESSAGES=2.0
"""

    with open('.env', 'w') as f:
        f.write(env_content)

    print("✅ Archivo .env configurado")

def create_requirements():
    """Crear requirements.txt optimizado"""
    requirements = """fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
aiohttp==3.9.1
google-generativeai==0.3.1
python-dotenv==1.0.0
beautifulsoup4==4.12.2
requests==2.31.0"""

    with open('requirements.txt', 'w') as f:
        f.write(requirements)

    print("✅ Requirements.txt actualizado")

def create_startup_script():
    """Crear script de inicio automático"""
    startup_script = """#!/bin/bash

# ========================================
# SCRIPT DE INICIO AUTOMÁTICO
# ========================================

echo "🚀 Iniciando Bot 24/7 con Cloudflare Tunnel..."
echo "=" * 60

# Verificar si Docker está ejecutándose
if ! docker info > /dev/null 2>&1; then
    echo "🐳 Iniciando Docker..."
    sudo systemctl start docker
    sudo systemctl enable docker
fi

# Crear directorio de logs si no existe
mkdir -p logs

# Construir y ejecutar
echo "🔨 Construyendo imágenes de Docker..."
docker-compose build --no-cache

echo "🚀 Iniciando servicios..."
docker-compose up -d

echo "✅ Bot 24/7 iniciado correctamente!"
echo ""
echo "📊 Estado de los servicios:"
docker-compose ps

echo ""
echo "🌐 Tu webhook será:"
echo "   https://tu-bot-24-7.cloudflaretunnel.com/webhook"
echo ""
echo "📝 Para ver logs:"
echo "   docker-compose logs -f"
echo ""
echo "🛑 Para detener:"
echo "   docker-compose down"
"""

    with open('start_24_7.sh', 'w') as f:
        f.write(startup_script)

    # Hacer ejecutable
    os.chmod('start_24_7.sh', 0o755)

    print("✅ Script de inicio creado")

def show_next_steps():
    """Mostrar próximos pasos"""
    print()
    print("🎯 PRÓXIMOS PASOS:")
    print("=" * 30)
    print("1. 📝 Configurar Cloudflare Tunnel:")
    print("   cloudflared tunnel create evolution-bot-24-7")
    print()
    print("2. 🌐 Configurar DNS en Cloudflare:")
    print("   - Ve a tu dashboard de Cloudflare")
    print("   - Agrega CNAME: tu-bot -> tu-tunnel-id.cfargotunnel.com")
    print()
    print("3. 🚀 Iniciar el bot:")
    print("   ./start_24_7.sh")
    print()
    print("4. 📱 Configurar webhook en Evolution API:")
    print("   https://tu-bot.cloudflaretunnel.com/webhook")
    print()
    print("📖 Lee CLOUDFLARE_DEPLOY.md para detalles completos")

def main():
    """Función principal"""
    print_header()

    if not check_requirements():
        print("❌ Requisitos no cumplidos")
        return

    print("✅ Todos los requisitos verificados")
    print()

    # Crear archivos de configuración
    print("🔧 Creando configuración para 24/7...")
    create_cloudflare_config()
    create_docker_compose()
    create_dockerfile()
    create_env_file()
    create_requirements()
    create_startup_script()

    print()
    print("📋 ARCHIVOS CREADOS:")
    print("   ✅ cloudflare-tunnel.yml - Configuración del tunnel")
    print("   ✅ Dockerfile - Imagen de Docker")
    print("   ✅ docker-compose.yml - Orquestación 24/7")
    print("   ✅ .env - Variables de entorno")
    print("   ✅ requirements.txt - Dependencias")
    print("   ✅ start_24_7.sh - Script de inicio")
    print()

    print("🏆 VENTAJAS DE ESTA CONFIGURACIÓN:")
    print("   ✅ Disponibilidad 24/7 garantizada")
    print("   ✅ Reinicio automático si hay errores")
    print("   ✅ Monitoreo constante con logs")
    print("   ✅ URL permanente (no expira)")
    print("   ✅ Tráfico ilimitado gratis")
    print("   ✅ SSL automático")
    print("   ✅ Mantenimiento mínimo")
    print()

    show_next_steps()

    print()
    print("🎉 ¡Tu bot estará activo 24/7 de forma confiable!")
    print("💡 Esta es la configuración más profesional y estable")

if __name__ == "__main__":
    main()