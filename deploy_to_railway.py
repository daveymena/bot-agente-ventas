#!/usr/bin/env python3
"""
Script para desplegar en Railway
"""
import os
import json
import subprocess
import sys

def create_railway_config():
    """Crear archivos de configuración para Railway"""
    # railway.toml
    railway_config = """[build]
builder = "python3.9"

[deploy]
startCommand = "python main.py"
healthcheckPath = "/health"
healthcheckTimeout = 100
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10

[environments]
production = { variables = { } }
"""

    with open('railway.toml', 'w') as f:
        f.write(railway_config)

    # requirements.txt optimizado
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

    # nixpacks.toml para configuración específica
    nixpacks_config = """[phases.setup]
nixPkgs = ["python39", "gcc"]

[phases.install]
cmds = ["pip install -r requirements.txt"]

[start]
cmd = "python main.py"
"""

    with open('nixpacks.toml', 'w') as f:
        f.write(nixpacks_config)

    print("✅ Configuración de Railway creada")

def create_railway_readme():
    """Crear README específico para Railway"""
    readme = """# 🚀 Despliegue en Railway

## 📋 Pasos para Desplegar

### 1. Instalar Railway CLI
```bash
npm install -g @railway/cli
```

### 2. Hacer Login
```bash
railway login
```

### 3. Inicializar Proyecto
```bash
railway init
```

### 4. Configurar Variables de Entorno
```bash
railway variables set GOOGLE_GEMINI_API_KEY=tu_clave_aqui
railway variables set WHATSAPP_SERVER_URL=https://evoapi2-evolution-api.ovw3ar.easypanel.host
railway variables set WHATSAPP_INSTANCE_NAME=03d935e9-4711-4011-9ead-4983e4f6b2b5
railway variables set WHATSAPP_API_KEY=429683C4C977415CAAFCCE10F7D57E11
```

### 5. Desplegar
```bash
railway up
```

## 🌐 URL del Webhook

Una vez desplegado, Railway te dará una URL como:
```
https://tu-app.railway.app
```

Tu webhook será:
```
https://tu-app.railway.app/webhook
```

## 📊 Monitoreo

- **Logs**: `railway logs`
- **Estado**: `railway status`
- **Variables**: `railway variables`

## 🔄 Actualizaciones

```bash
git add .
git commit -m "Actualización"
git push
railway up
```
"""

    with open('RAILWAY_DEPLOY.md', 'w') as f:
        f.write(readme)

    print("✅ README de Railway creado")

def deploy_to_railway():
    """Desplegar en Railway"""
    print("🚀 Desplegando en Railway...")
    print("=" * 50)

    try:
        # Verificar si Railway CLI está instalado
        result = subprocess.run(['railway', '--version'],
                              capture_output=True, text=True)

        if result.returncode != 0:
            print("📦 Instalando Railway CLI...")
            subprocess.run(['npm', 'install', '-g', '@railway/cli'], check=True)

        print("✅ Railway CLI instalado")

        # Hacer login
        print("🔐 Iniciando sesión en Railway...")
        print("💡 Abre el navegador y sigue las instrucciones...")
        subprocess.run(['railway', 'login'], check=True)

        # Inicializar proyecto
        print("📁 Inicializando proyecto...")
        result = subprocess.run(['railway', 'init'], capture_output=True, text=True)

        if "already initialized" in result.stderr:
            print("✅ Proyecto ya inicializado")
        else:
            print("✅ Proyecto inicializado")

        # Desplegar
        print("🚀 Desplegando aplicación...")
        result = subprocess.run(['railway', 'up'], capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Despliegue exitoso!")
            print("📍 Tu aplicación está disponible en Railway")
            print("🔗 Configura este webhook en Evolution API:")
            print("   https://tu-app.railway.app/webhook")
        else:
            print(f"❌ Error en despliegue: {result.stderr}")

    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {str(e)}")
    except Exception as e:
        print(f"❌ Error inesperado: {str(e)}")

def main():
    """Función principal"""
    print("🚀 CONFIGURANDO DESPLIEGUE EN RAILWAY")
    print("=" * 50)
    print("🌐 Railway es un hosting gratuito excelente para Python")
    print("📊 500MB RAM, 1GB almacenamiento gratis")
    print("🔄 Despliegue automático desde GitHub")
    print("🌍 URL permanente y confiable")
    print()

    # Crear archivos de configuración
    create_railway_config()
    create_railway_readme()

    print()
    print("📋 ARCHIVOS CREADOS:")
    print("   ✅ railway.toml - Configuración de Railway")
    print("   ✅ nixpacks.toml - Configuración de build")
    print("   ✅ requirements.txt - Dependencias")
    print("   ✅ RAILWAY_DEPLOY.md - Guía de despliegue")
    print()

    print("🔑 VARIABLES DE ENTORNO A CONFIGURAR EN RAILWAY:")
    print("   • GOOGLE_GEMINI_API_KEY=AIzaSyDxKos_L7EC2bsm2XACFlaRYSeVsKMwjQY")
    print("   • WHATSAPP_SERVER_URL=https://evoapi2-evolution-api.ovw3ar.easypanel.host")
    print("   • WHATSAPP_INSTANCE_NAME=03d935e9-4711-4011-9ead-4983e4f6b2b5")
    print("   • WHATSAPP_API_KEY=429683C4C977415CAAFCCE10F7D57E11")
    print()

    # Preguntar si desplegar
    deploy = input("¿Deseas desplegar ahora en Railway? (y/n): ").lower().strip()

    if deploy == 'y':
        deploy_to_railway()
    else:
        print("✅ Archivos configurados para Railway")
        print("💡 Ejecuta 'python deploy_to_railway.py' cuando quieras desplegar")
        print("📖 Lee RAILWAY_DEPLOY.md para instrucciones detalladas")

if __name__ == "__main__":
    main()