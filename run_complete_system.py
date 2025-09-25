#!/usr/bin/env python3
"""
Sistema Completo de Agente de Ventas con Evolution API
Coordina todos los componentes del sistema
"""
import asyncio
import logging
import signal
import sys
import os
import json
import threading
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/sistema_completo.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Estado del sistema
system_status = {
    "webhook_server": False,
    "evolution_sync": False,
    "ai_service": False,
    "message_processor": False,
    "product_scraper": False,
    "overall_status": "stopped"
}

def update_system_status(component, status):
    """Actualizar estado del sistema"""
    system_status[component] = status
    logger.info(f"📊 {component}: {'✅' if status else '❌'}")

def signal_handler(signum, frame):
    """Manejador de señales"""
    logger.info(f"Señal {signum} recibida, deteniendo sistema...")
    system_status["overall_status"] = "stopping"
    sys.exit(0)

async def start_webhook_server():
    """Iniciar servidor de webhook"""
    try:
        from main import app
        import uvicorn

        config = uvicorn.Config(
            app=app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )

        server = uvicorn.Server(config)

        update_system_status("webhook_server", True)
        logger.info("🌐 Servidor webhook iniciado en http://0.0.0.0:8000")

        await server.serve()

    except Exception as e:
        update_system_status("webhook_server", False)
        logger.error(f"❌ Error en servidor webhook: {str(e)}")
        raise

async def start_evolution_sync():
    """Iniciar sincronizador con Evolution"""
    try:
        from sync_with_evolution import sync_loop

        update_system_status("evolution_sync", True)
        logger.info("🔄 Sincronizador Evolution iniciado")

        await sync_loop()

    except Exception as e:
        update_system_status("evolution_sync", False)
        logger.error(f"❌ Error en sincronizador Evolution: {str(e)}")
        raise

async def start_ai_service():
    """Iniciar servicio de IA"""
    try:
        from services.ai_service import AIService

        ai_service = AIService()
        await ai_service.initialize()

        if ai_service.is_configured():
            update_system_status("ai_service", True)
            logger.info("🤖 Servicio de IA inicializado")
            return ai_service
        else:
            update_system_status("ai_service", False)
            logger.error("❌ Servicio de IA no configurado")
            return None

    except Exception as e:
        update_system_status("ai_service", False)
        logger.error(f"❌ Error en servicio de IA: {str(e)}")
        return None

async def start_message_processor():
    """Iniciar procesador de mensajes"""
    try:
        from services.message_processor import MessageProcessor

        processor = MessageProcessor()
        update_system_status("message_processor", True)
        logger.info("📝 Procesador de mensajes iniciado")
        return processor

    except Exception as e:
        update_system_status("message_processor", False)
        logger.error(f"❌ Error en procesador de mensajes: {str(e)}")
        return None

async def start_product_scraper():
    """Iniciar scraper de productos"""
    try:
        from services.scraping_service import ScrapingService

        async with ScrapingService() as scraper:
            products = await scraper.scrape_all_stores()
            total_products = sum(len(p) for p in products.values())

            update_system_status("product_scraper", True)
            logger.info(f"📦 Scraper de productos iniciado - {total_products} productos cargados")
            return scraper

    except Exception as e:
        update_system_status("product_scraper", False)
        logger.error(f"❌ Error en scraper de productos: {str(e)}")
        return None

def log_system_status():
    """Log del estado del sistema"""
    status_emoji = {
        True: "✅",
        False: "❌"
    }

    status_msg = f"""
🚀 SISTEMA COMPLETO DE AGENTE DE VENTAS
{'='*50}
🌐 Servidor Webhook: {status_emoji[system_status['webhook_server']]}
🔄 Sincronizador Evolution: {status_emoji[system_status['evolution_sync']]}
🤖 Servicio de IA: {status_emoji[system_status['ai_service']]}
📝 Procesador de Mensajes: {status_emoji[system_status['message_processor']]}
📦 Scraper de Productos: {status_emoji[system_status['product_scraper']]}
📊 Estado General: {system_status['overall_status'].upper()}
{'='*50}
"""
    logger.info(status_msg.strip())

async def main():
    """Función principal del sistema completo"""
    logger.info("🎯 INICIANDO SISTEMA COMPLETO DE AGENTE DE VENTAS")
    logger.info("=" * 60)

    system_status["overall_status"] = "starting"

    try:
        # Inicializar servicios
        logger.info("🔧 Inicializando servicios...")

        ai_service = await start_ai_service()
        message_processor = await start_message_processor()
        product_scraper = await start_product_scraper()

        if not all([ai_service, message_processor, product_scraper]):
            logger.error("❌ Error inicializando servicios básicos")
            system_status["overall_status"] = "error"
            return

        # Iniciar tareas en paralelo
        logger.info("🚀 Iniciando componentes en paralelo...")

        # Crear tareas
        webhook_task = asyncio.create_task(start_webhook_server())
        evolution_task = asyncio.create_task(start_evolution_sync())

        # Log inicial del estado
        log_system_status()

        # Mantener el sistema ejecutándose
        system_status["overall_status"] = "running"
        logger.info("✅ Sistema completo iniciado correctamente!")

        try:
            # Esperar a que alguna tarea termine (o mantener vivo)
            await asyncio.gather(webhook_task, evolution_task)

        except KeyboardInterrupt:
            logger.info("🛑 Sistema detenido por usuario")
        except Exception as e:
            logger.error(f"❌ Error en sistema: {str(e)}")
        finally:
            system_status["overall_status"] = "stopping"
            log_system_status()

    except Exception as e:
        system_status["overall_status"] = "error"
        logger.error(f"❌ Error fatal en sistema: {str(e)}")
        log_system_status()
    finally:
        system_status["overall_status"] = "stopped"
        logger.info("👋 Sistema detenido")

if __name__ == "__main__":
    # Registrar manejadores de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Ejecutar sistema completo
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Sistema detenido por usuario")
    except Exception as e:
        logger.error(f"Error fatal: {str(e)}")
        sys.exit(1)