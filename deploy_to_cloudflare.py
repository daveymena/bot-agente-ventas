#!/usr/bin/env python3
"""
Script para desplegar con Cloudflare Tunnel
"""
import os
import json
import subprocess
import sys

def create_cloudflare_config():
    """Crear configuración de Cloudflare Tunnel"""
    # Configuración para cloudflared
    config = {
        "tunnel": "evolution-bot-tunnel",
        "credentials-file": "/home/user/.cloudflared/evolution-bot-tunnel.json",
        "ingress": [
            {
                "hostname": "tu-bot-tu-dominio.cloudflaretunnel.com",
                "service": "http://localhost:8000"
            },
            {
                "service": "http_status:404"
            }
        ]
    }

    with open('cloudflare-tunnel.yml', 'w') as f:
        f.write("# Configuración de Cloudflare Tunnel\n")
        f.write("# Ejecuta: cloudflared tunnel --config cloudflare-tunnel.yml\n\n")
        json.dump(config, f, indent=2)

    print("✅ Configuración de Cloudflare Tunnel creada")

def create_docker_config():
    """Crear configuración de Docker para producción"""
    dockerfile = """FROM python:3.9-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copiar archivos
COPY requirements.txt .
COPY .env .
COPY main.py .
COPY core/ ./core/
COPY models/ ./models/
COPY services/ ./services/
COPY config/ ./config/
COPY utils/ ./utils/

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Exponer puerto
EXPOSE 8000

# Comando para ejecutar
CMD ["python", "main.py"]
"""

    with open('Dockerfile', 'w') as f:
        f.write(dockerfile)

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

  cloudflared:
    image: cloudflare/cloudflared:latest
    command: tunnel --config /etc/cloudflared/config.yml run
    volumes:
      - ./cloudflare-tunnel.yml:/etc/cloudflared/config.yml
    depends_on:
      - bot
    restart: unless-stopped
"""

    with open('docker-compose.yml', 'w') as f:
        f.write(docker_compose)

    print("✅ Configuración de Docker creada")

def create_install_script():
    """Crear script de instalación"""
    install_script = """#!/bin/bash

# ========================================
# INSTALACIÓN AUTOMÁTICA DEL BOT
# ========================================

echo "🚀 Instalando Agente de Ventas con Cloudflare Tunnel..."
echo "=" * 60

# Verificar si Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "📦 Instalando Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    sudo systemctl start docker
    sudo systemctl enable docker
fi

# Verificar si cloudflared está instalado
if ! command -v cloudflared &> /dev/null; then
    echo "📦 Instalando Cloudflare Tunnel..."
    curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
    chmod +x cloudflared
    sudo mv cloudflared /usr/local/bin/
fi

echo "✅ Dependencias instaladas"

# Crear directorio de logs
mkdir -p logs

# Configurar variables de entorno
if [ ! -f .env ]; then
    echo "🔧 Configurando variables de entorno..."
    cat > .env << EOF
GOOGLE_GEMINI_API_KEY=AIzaSyDxKos_L7EC2bsm2XACFlaRYSeVsKMwjQY
WHATSAPP_SERVER_URL=https://evoapi2-evolution-api.ovw3ar.easypanel.host
WHATSAPP_INSTANCE_NAME=03d935e9-4711-4011-9ead-4983e4f6b2b5
WHATSAPP_API_KEY=429683C4C977415CAAFCCE10F7D57E11
LOG_LEVEL=INFO
LOG_FILE=logs/agente_ventas.log
EOF
fi

echo "✅ Configuración completada"
echo ""
echo "🎯 PRÓXIMOS PASOS:"
echo "   1. Ejecutar: docker-compose up -d"
echo "   2. Ver logs: docker-compose logs -f"
echo "   3. Configurar webhook en Evolution API"
echo ""
echo "📖 Consulta CLOUDFLARE_DEPLOY.md para más detalles"
"""

    with open('install.sh', 'w') as f:
        f.write(install_script)

    # Hacer ejecutable
    os.chmod('install.sh', 0o755)

    print("✅ Script de instalación creado")

def create_cloudflare_readme():
    """Crear documentación para Cloudflare"""
    readme = """# 🚀 Despliegue con Cloudflare Tunnel

## 🌟 Ventajas de Cloudflare Tunnel

- ✅ **URL permanente** (no cambia como ngrok)
- ✅ **Tráfico ilimitado** gratis
- ✅ **SSL automático**
- ✅ **Más estable** que ngrok
- ✅ **Sin límites de tiempo**

## 📋 Instalación

### 1. Instalar Docker y Cloudflare Tunnel
```bash
./install.sh
```

### 2. Configurar Cloudflare Tunnel
```bash
# Crear tunnel
cloudflared tunnel create evolution-bot-tunnel

# Obtener credenciales
cat ~/.cloudflared/evolution-bot-tunnel.json
```

### 3. Configurar DNS en Cloudflare
1. Ve a tu dashboard de Cloudflare
2. Agrega un CNAME record:
   - Name: tu-bot
   - Target: tu-tunnel-id.cfargotunnel.com
   - Proxy: naranja (activado)

### 4. Ejecutar el Sistema
```bash
docker-compose up -d
```

## 🌐 Tu Webhook Será:
```
https://tu-bot.tu-dominio.com/webhook
```

## 📊 Monitoreo

```bash
# Ver logs
docker-compose logs -f

# Ver estado
curl https://tu-bot.tu-dominio.com/health

# Ver productos
curl https://tu-bot.tu-dominio.com/products
```

## 🔄 Actualizaciones

```bash
# Detener
docker-compose down

# Actualizar código
git pull

# Reconstruir y ejecutar
docker-compose up -d --build
```

## 🆘 Solución de Problemas

### Tunnel no funciona
```bash
# Verificar estado del tunnel
cloudflared tunnel list

# Ver logs del tunnel
cloudflared tunnel logs evolution-bot-tunnel
```

### Docker no funciona
```bash
# Reiniciar Docker
sudo systemctl restart docker

# Ver logs de Docker
docker-compose logs bot
```

### Webhook no responde
```bash
# Probar localmente
curl http://localhost:8000/health

# Probar con Cloudflare
curl https://tu-bot.tu-dominio.com/health
```

## 🎉 ¡Listo!

Una vez configurado, tendrás:
- ✅ URL permanente para tu webhook
- ✅ SSL automático
- ✅ Monitoreo 24/7
- ✅ Reinicio automático
- ✅ Logs centralizados
"""

    with open('CLOUDFLARE_DEPLOY.md', 'w') as f:
        f.write(readme)

    print("✅ Documentación de Cloudflare creada")

def main():
    """Función principal"""
    print("🚀 CONFIGURANDO CLOUDFLARE TUNNEL")
    print("=" * 50)
    print("🌐 Cloudflare Tunnel es la mejor opción:")
    print("   ✅ URL permanente (no expira)")
    print("   ✅ SSL automático")
    print("   ✅ Tráfico ilimitado gratis")
    print("   ✅ Más estable que ngrok")
    print("   ✅ Sin límites de tiempo")
    print()

    # Crear archivos de configuración
    create_cloudflare_config()
    create_docker_config()
    create_install_script()
    create_cloudflare_readme()

    print()
    print("📋 ARCHIVOS CREADOS:")
    print("   ✅ cloudflare-tunnel.yml - Configuración del tunnel")
    print("   ✅ Dockerfile - Imagen de Docker")
    print("   ✅ docker-compose.yml - Orquestación")
    print("   ✅ install.sh - Script de instalación")
    print("   ✅ CLOUDFLARE_DEPLOY.md - Guía completa")
    print()

    print("🎯 VENTAJAS SOBRE NGROK:")
    print("   ✅ URL permanente (no cambia cada 8 horas)")
    print("   ✅ Sin límites de tiempo")
    print("   ✅ SSL automático")
    print("   ✅ Más confiable")
    print("   ✅ Monitoreo integrado")
    print()

    print("💡 RECOMENDACIÓN:")
    print("   Cloudflare Tunnel es la mejor opción para producción")
    print("   Es gratis, estable y profesional")

if __name__ == "__main__":
    main()