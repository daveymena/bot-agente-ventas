#!/usr/bin/env python3
"""
Script para ejecutar el bot con ngrok para exponer el webhook públicamente
"""
import asyncio
import threading
import time
import sys
import os
from pyngrok import ngrok

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import app
import uvicorn

def start_ngrok():
    """Iniciar ngrok tunnel"""
    try:
        # Crear tunnel HTTP en puerto 8000
        public_url = ngrok.connect(8000, "http")
        print("\n🔗 NGROK TUNNEL ACTIVO:")
        print(f"   URL Pública: {public_url}")
        print(f"   Webhook URL: {public_url}/webhook")
        print("\n📋 CONFIGURA ESTA URL EN EVOLUTION API:")
        print(f"   {public_url}/webhook")
        print("\n⚠️  IMPORTANTE: Mantén esta terminal abierta")
        print("   El tunnel se cerrará al cerrar esta ventana\n")

        return public_url
    except Exception as e:
        print(f"❌ Error iniciando ngrok: {e}")
        print("💡 Asegúrate de tener ngrok instalado y configurado")
        return None

async def start_server():
    """Iniciar servidor FastAPI"""
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True
    )

    server = uvicorn.Server(config)

    try:
        await server.serve()
    except KeyboardInterrupt:
        print("\n🛑 Servidor detenido por usuario")
    except Exception as e:
        print(f"❌ Error en servidor: {e}")

async def main():
    """Función principal"""
    print("🚀 Iniciando Agente de Ventas con Ngrok...")
    print("=" * 50)

    # Iniciar ngrok en un hilo separado
    ngrok_thread = threading.Thread(target=start_ngrok, daemon=True)
    ngrok_thread.start()

    # Esperar un poco para que ngrok se inicie
    time.sleep(3)

    # Iniciar servidor
    await start_server()

if __name__ == "__main__":
    asyncio.run(main())
