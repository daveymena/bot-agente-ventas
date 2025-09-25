#!/usr/bin/env python3
"""
Script para iniciar el bot de ventas con Evolution API
"""
import asyncio
import logging
import signal
import sys
import os
import time
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/agente_ventas.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Importar después de configurar el path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from core.sales_agent import SalesAgent

# Variable global para el agente
sales_agent = None

def signal_handler(signum, frame):
    """Manejador de señales para graceful shutdown"""
    logger.info(f"Señal {signum} recibida, deteniendo bot...")
    if sales_agent:
        asyncio.create_task(sales_agent.stop())
    sys.exit(0)

async def check_evolution_connection():
    """Verificar conexión con Evolution API"""
    try:
        from services.whatsapp_service import WhatsAppService
        async with WhatsAppService() as whatsapp:
            is_connected = await whatsapp.validate_connection()
            if is_connected:
                logger.info("✅ Conexión con Evolution API verificada")
                return True
            else:
                logger.error("❌ No se pudo conectar con Evolution API")
                return False
    except Exception as e:
        logger.error(f"❌ Error verificando Evolution API: {str(e)}")
        return False

async def check_ai_service():
    """Verificar servicio de IA"""
    try:
        from services.ai_service import AIService
        ai_service = AIService()
        await ai_service.initialize()

        if ai_service.is_configured():
            logger.info("✅ Servicio de IA configurado correctamente")
            return True
        else:
            logger.error("❌ Servicio de IA no configurado")
            return False
    except Exception as e:
        logger.error(f"❌ Error en servicio de IA: {str(e)}")
        return False

async def main():
    """Función principal del bot"""
    global sales_agent

    logger.info("🚀 Iniciando Agente de Ventas con Evolution API...")
    logger.info("=" * 60)

    # Verificar prerrequisitos
    logger.info("🔍 Verificando configuración...")

    evolution_ok = await check_evolution_connection()
    ai_ok = await check_ai_service()

    if not (evolution_ok and ai_ok):
        logger.error("❌ Configuración incompleta. Revisa los logs.")
        return

    # Inicializar agente
    logger.info("🤖 Inicializando agente de ventas...")
    sales_agent = SalesAgent()

    success = await sales_agent.initialize()
    if not success:
        logger.error("❌ Error inicializando el agente")
        return

    await sales_agent.start()

    logger.info("✅ Agente de Ventas iniciado correctamente!")
    logger.info("📱 Sincronizado con Evolution API")
    logger.info("🤖 IA lista para responder")
    logger.info("🔄 Bot ejecutándose en segundo plano...")
    logger.info("=" * 60)

    # Mantener el bot ejecutándose
    try:
        while True:
            await asyncio.sleep(10)

            # Verificación periódica de salud
            if sales_agent:
                status = sales_agent.get_status()
                if not status["is_running"]:
                    logger.error("⚠️ Agente detenido, reiniciando...")
                    await sales_agent.start()

    except KeyboardInterrupt:
        logger.info("🛑 Deteniendo bot por solicitud del usuario...")
    except Exception as e:
        logger.error(f"❌ Error en el bucle principal: {str(e)}")
    finally:
        if sales_agent:
            await sales_agent.stop()
        logger.info("👋 Bot detenido correctamente")

if __name__ == "__main__":
    # Registrar manejadores de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Ejecutar el bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot detenido por usuario")
    except Exception as e:
        logger.error(f"Error fatal: {str(e)}")
        sys.exit(1)