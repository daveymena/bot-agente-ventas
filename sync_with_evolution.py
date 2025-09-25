#!/usr/bin/env python3
"""
Sincronizador del Agente de Ventas con Evolution API
Mantiene el bot funcionando y sincronizado
"""
import asyncio
import logging
import signal
import sys
import os
import time
import json
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/sync_evolution.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Estado del sincronizador
sync_status = {
    "is_running": False,
    "last_sync": None,
    "messages_processed": 0,
    "errors_count": 0,
    "evolution_connected": False,
    "ai_ready": False
}

def update_status(key, value):
    """Actualizar estado del sincronizador"""
    sync_status[key] = value
    sync_status["last_update"] = datetime.now().isoformat()

    # Log del cambio de estado
    logger.info(f"📊 Estado actualizado: {key} = {value}")

def signal_handler(signum, frame):
    """Manejador de señales"""
    logger.info(f"Señal {signum} recibida, deteniendo sincronizador...")
    update_status("is_running", False)
    sys.exit(0)

async def check_evolution_health():
    """Verificar salud de Evolution API"""
    try:
        from services.whatsapp_service import WhatsAppService
        async with WhatsAppService() as whatsapp:
            is_connected = await whatsapp.validate_connection()

            if is_connected:
                update_status("evolution_connected", True)
                logger.info("✅ Evolution API conectada")
                return True
            else:
                update_status("evolution_connected", False)
                logger.warning("⚠️ Evolution API desconectada")
                return False

    except Exception as e:
        update_status("evolution_connected", False)
        logger.error(f"❌ Error verificando Evolution API: {str(e)}")
        return False

async def check_ai_health():
    """Verificar salud del servicio de IA"""
    try:
        from services.ai_service import AIService
        ai_service = AIService()
        await ai_service.initialize()

        if ai_service.is_configured():
            update_status("ai_ready", True)
            logger.info("✅ Servicio de IA listo")
            return True
        else:
            update_status("ai_ready", False)
            logger.warning("⚠️ Servicio de IA no configurado")
            return False

    except Exception as e:
        update_status("ai_ready", False)
        logger.error(f"❌ Error en servicio de IA: {str(e)}")
        return False

async def update_products_cache():
    """Actualizar caché de productos"""
    try:
        from services.scraping_service import ScrapingService
        async with ScrapingService() as scraper:
            products = await scraper.scrape_all_stores()
            total_products = sum(len(p) for p in products.values())

            logger.info(f"📦 Caché de productos actualizado: {total_products} productos")
            return total_products

    except Exception as e:
        logger.error(f"❌ Error actualizando productos: {str(e)}")
        return 0

async def log_status():
    """Log del estado actual"""
    status_msg = f"""
🔄 SINCRONIZADOR EVOLUTION API
{'='*40}
📱 Evolution API: {'✅ Conectado' if sync_status['evolution_connected'] else '❌ Desconectado'}
🤖 IA: {'✅ Lista' if sync_status['ai_ready'] else '❌ No lista'}
📊 Mensajes procesados: {sync_status['messages_processed']}
❌ Errores: {sync_status['errors_count']}
⏰ Última sincronización: {sync_status['last_sync'] or 'Nunca'}
🔄 Estado: {'🟢 Ejecutándose' if sync_status['is_running'] else '🔴 Detenido'}
{'='*40}
"""
    logger.info(status_msg.strip())

async def sync_loop():
    """Bucle principal de sincronización"""
    logger.info("🚀 Iniciando sincronizador con Evolution API...")

    update_status("is_running", True)

    # Verificaciones iniciales
    evolution_ok = await check_evolution_health()
    ai_ok = await check_ai_health()

    if not (evolution_ok and ai_ok):
        logger.error("❌ Verificaciones iniciales fallidas")
        update_status("is_running", False)
        return

    # Actualizar caché de productos
    await update_products_cache()

    # Bucle de sincronización
    sync_counter = 0
    while sync_status["is_running"]:
        sync_counter += 1
        update_status("last_sync", datetime.now().isoformat())

        try:
            # Verificaciones de salud cada 30 segundos
            if sync_counter % 6 == 0:  # Cada 3 minutos (30s * 6)
                await log_status()

                # Verificar conexiones
                await check_evolution_health()
                await check_ai_health()

                # Actualizar productos cada 10 minutos
                if sync_counter % 20 == 0:  # Cada 10 minutos (30s * 20)
                    await update_products_cache()

            # Simular procesamiento de mensajes (en producción esto vendría del webhook)
            # Aquí podrías agregar lógica para procesar mensajes pendientes

            await asyncio.sleep(30)  # Esperar 30 segundos

        except Exception as e:
            sync_status["errors_count"] += 1
            logger.error(f"❌ Error en bucle de sincronización: {str(e)}")

            # Si hay muchos errores, intentar reiniciar
            if sync_status["errors_count"] > 10:
                logger.error("🔄 Demasiados errores, reiniciando sincronizador...")
                sync_status["errors_count"] = 0
                await asyncio.sleep(60)  # Esperar 1 minuto antes de continuar

    logger.info("🛑 Sincronizador detenido")

async def main():
    """Función principal"""
    logger.info("🎯 INICIANDO SINCRONIZACIÓN COMPLETA CON EVOLUTION API")
    logger.info("=" * 60)

    try:
        await sync_loop()

    except KeyboardInterrupt:
        logger.info("🛑 Sincronizador detenido por usuario")
    except Exception as e:
        logger.error(f"❌ Error fatal en sincronizador: {str(e)}")
    finally:
        update_status("is_running", False)
        await log_status()
        logger.info("👋 Sincronizador finalizado")

if __name__ == "__main__":
    # Registrar manejadores de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Ejecutar sincronizador
    asyncio.run(main())