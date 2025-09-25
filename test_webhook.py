#!/usr/bin/env python3
"""
Script para probar el webhook manualmente
"""
import json
import requests
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def test_webhook():
    """Probar el webhook con datos de ejemplo"""

    # Datos de ejemplo simulando un mensaje de WhatsApp
    test_data = {
        "body": {
            "URL del servidor": "https://evoapi2-evolution-api.ovw3ar.easypanel.host",
            "nombreInstancia": "03d935e9-4711-4011-9ead-4983e4f6b2b5",
            "clave API": "429683C4C977415CAAFCCE10F7D57E11",
            "data": {
                "id": "test_message_123",
                "remoteJid": "1234567890@c.us",
                "message": {
                    "conversation": "Hola, ¿qué productos tienes?"
                },
                "pushName": "Cliente de Prueba",
                "tipo de mensaje": "conversación"
            }
        }
    }

    print("🧪 Probando webhook manualmente...")
    print("=" * 50)
    print(f"📡 Enviando a: http://localhost:8000/webhook")
    print(f"📊 Datos: {json.dumps(test_data, indent=2)}")
    print()

    try:
        response = requests.post(
            "http://localhost:8000/webhook",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        print(f"📡 Respuesta del servidor: {response.status_code}")
        print(f"📄 Contenido: {response.text}")

        if response.status_code == 200:
            print("✅ Webhook funcionando correctamente")
        else:
            print("❌ Error en el webhook")

    except requests.exceptions.ConnectionError:
        print("❌ No se pudo conectar al servidor")
        print("💡 Asegúrate de que el agente esté ejecutándose: python main.py")
    except requests.exceptions.Timeout:
        print("❌ Timeout - el servidor tardó demasiado en responder")
    except Exception as e:
        print(f"❌ Error inesperado: {str(e)}")

def test_health():
    """Probar el endpoint de salud"""
    print("🏥 Probando endpoint de salud...")

    try:
        response = requests.get("http://localhost:8000/health", timeout=10)
        print(f"📡 Respuesta: {response.status_code}")
        print(f"📄 Contenido: {response.text}")

        if response.status_code == 200:
            print("✅ Servidor funcionando correctamente")
        else:
            print("❌ Error en el servidor")

    except Exception as e:
        print(f"❌ No se pudo conectar: {str(e)}")
        print("💡 Inicia el servidor con: python main.py")

if __name__ == "__main__":
    print("🚀 PRUEBA DEL WEBHOOK DEL AGENTE DE VENTAS")
    print("=" * 60)
    print()

    # Probar salud primero
    test_health()
    print()

    # Probar webhook
    test_webhook()
    print()

    print("💡 INSTRUCCIONES:")
    print("   1. Asegúrate de que el agente esté ejecutándose")
    print("   2. Configura el webhook en Evolution API")
    print("   3. Envía un mensaje real de WhatsApp para probar")
    print()
    print("📖 Consulta GUIA_EVOLUTION_API.md para más detalles")