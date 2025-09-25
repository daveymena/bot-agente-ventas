#!/usr/bin/env python3
"""
Script para desplegar en Vercel
"""
import os
import json
import subprocess
import sys

def create_vercel_config():
    """Crear configuración de Vercel"""
    vercel_config = {
        "version": 2,
        "builds": [
            {
                "src": "main.py",
                "use": "@vercel/python"
            }
        ],
        "routes": [
            {
                "src": "/api/(.*)",
                "dest": "/main.py"
            },
            {
                "src": "/(.*)",
                "dest": "/main.py"
            }
        ],
        "env": {
            "PYTHON_VERSION": "3.9",
            "GOOGLE_GEMINI_API_KEY": "@google-gemini-api-key",
            "WHATSAPP_SERVER_URL": "@whatsapp-server-url",
            "WHATSAPP_INSTANCE_NAME": "@whatsapp-instance-name",
            "WHATSAPP_API_KEY": "@whatsapp-api-key"
        }
    }

    with open('vercel.json', 'w') as f:
        json.dump(vercel_config, f, indent=2)

    print("✅ Configuración de Vercel creada")

def create_requirements_for_vercel():
    """Crear requirements.txt optimizado para Vercel"""
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

    print("✅ Requirements.txt actualizado para Vercel")

def create_api_wrapper():
    """Crear wrapper para Vercel"""
    api_wrapper = '''import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import asyncio
from dotenv import load_dotenv

load_dotenv()

# Importar el agente
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from core.sales_agent import SalesAgent

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Agente de Ventas activo", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "evolution-api-bot"}

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        print(f"Webhook recibido: {data}")

        # Procesar con el agente
        agent = SalesAgent()
        success = await agent.process_message(data)

        if success:
            return {"status": "success", "message": "Procesado correctamente"}
        else:
            return {"status": "ignored", "message": "Mensaje no procesado"}

    except Exception as e:
        print(f"Error en webhook: {str(e)}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
'''

    with open('api.py', 'w') as f:
        f.write(api_wrapper)

    print("✅ Wrapper API creado para Vercel")

def deploy_to_vercel():
    """Desplegar en Vercel"""
    print("🚀 Desplegando en Vercel...")
    print("=" * 50)

    try:
        # Instalar Vercel CLI si no está instalado
        result = subprocess.run(['npm', 'list', '-g', 'vercel'],
                              capture_output=True, text=True)

        if 'vercel' not in result.stdout:
            print("📦 Instalando Vercel CLI...")
            subprocess.run(['npm', 'install', '-g', 'vercel'], check=True)

        print("✅ Vercel CLI instalado")

        # Hacer login en Vercel
        print("🔐 Iniciando sesión en Vercel...")
        print("💡 Abre el navegador y sigue las instrucciones...")
        subprocess.run(['vercel', 'login'], check=True)

        # Desplegar
        print("🚀 Desplegando aplicación...")
        result = subprocess.run(['vercel', '--prod'], capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Despliegue exitoso!")
            print("📍 Tu aplicación está disponible en la URL que Vercel te proporcione")
        else:
            print(f"❌ Error en despliegue: {result.stderr}")

    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {str(e)}")
    except Exception as e:
        print(f"❌ Error inesperado: {str(e)}")

def main():
    """Función principal"""
    print("🚀 CONFIGURANDO DESPLIEGUE EN VERCEL")
    print("=" * 50)
    print("🌐 Vercel es un hosting gratuito perfecto para tu bot")
    print("📊 Te da una URL pública permanente")
    print("🔄 Se reinicia automáticamente si hay errores")
    print()

    # Crear archivos necesarios
    create_vercel_config()
    create_requirements_for_vercel()
    create_api_wrapper()

    print()
    print("📋 ARCHIVOS CREADOS:")
    print("   ✅ vercel.json - Configuración de Vercel")
    print("   ✅ requirements.txt - Dependencias optimizadas")
    print("   ✅ api.py - Wrapper para Vercel")
    print()

    print("🔑 CONFIGURACIÓN DE VARIABLES DE ENTORNO EN VERCEL:")
    print("   • GOOGLE_GEMINI_API_KEY")
    print("   • WHATSAPP_SERVER_URL")
    print("   • WHATSAPP_INSTANCE_NAME")
    print("   • WHATSAPP_API_KEY")
    print()

    # Preguntar si desplegar
    deploy = input("¿Deseas desplegar ahora en Vercel? (y/n): ").lower().strip()

    if deploy == 'y':
        deploy_to_vercel()
    else:
        print("✅ Archivos configurados para Vercel")
        print("💡 Ejecuta 'python deploy_to_vercel.py' cuando quieras desplegar")

if __name__ == "__main__":
    main()