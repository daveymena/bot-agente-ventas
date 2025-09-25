#!/usr/bin/env python3
"""
Script de prueba para verificar la configuración del Agente de Ventas
"""
import asyncio
import logging
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from services.whatsapp_service import WhatsAppService
from services.ai_service import AIService

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_configuration():
    """Probar la configuración del agente"""
    print("Probando configuracion del Agente de Ventas...")
    print("=" * 50)

    # Verificar configuración básica
    print("CONFIGURACION BASICA:")
    print(f"   WhatsApp Server: {settings.WHATSAPP_SERVER_URL}")
    print(f"   Instance Name: {settings.WHATSAPP_INSTANCE_NAME}")
    print(f"   API Key: {'Configurada' if settings.WHATSAPP_API_KEY else 'No configurada'}")
    print(f"   Gemini API: {'Configurada' if settings.GOOGLE_GEMINI_API_KEY else 'No configurada'}")
    print()

    # Probar conexión con WhatsApp
    print("PROBANDO CONEXION WHATSAPP...")
    try:
        async with WhatsAppService() as whatsapp:
            is_connected = await whatsapp.validate_connection()
            if is_connected:
                print("   Conexion con Evolution API exitosa")
                print(f"   URL: {settings.WHATSAPP_SERVER_URL}")
                print(f"   Instance: {settings.WHATSAPP_INSTANCE_NAME}")
            else:
                print("   Error de conexion con WhatsApp")
                print("   Verifica que la instancia este activa en Evolution API")
    except Exception as e:
        print(f"   Error conectando a WhatsApp: {str(e)}")
    print()

    # Probar configuración de IA
    print("PROBANDO CONFIGURACION DE IA...")
    ai_service = AIService()
    await ai_service.initialize()

    if ai_service.is_configured():
        print("   Servicio de IA configurado correctamente")
        print("   Usara Google Gemini como motor principal")
    else:
        print("   Ningun servicio de IA configurado")
    print()

    # Verificar configuración completa
    print("VERIFICACION GENERAL:")
    config_valid = settings.validate_config()
    if config_valid["valid"]:
        print("   Configuracion valida - Todo listo!")
        print("   Puedes ejecutar: python main.py")
    else:
        print("   Configuracion incompleta:")
        for error in config_valid["errors"]:
            print(f"      • {error}")
    print()

    # Mostrar próximos pasos
    print("PROXIMOS PASOS:")
    print("   1. Ejecutar: python main.py")
    print("   2. Configurar webhook en Evolution API apuntando a:")
    print("      http://tu-servidor:8000/webhook")
    print("   3. Probar con un mensaje de WhatsApp")
    print()

    print("Para mas informacion, consulta el README.md")

if __name__ == "__main__":
    asyncio.run(test_configuration())