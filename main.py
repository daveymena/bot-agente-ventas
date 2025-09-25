#!/usr/bin/env python3
"""
Agente de Ventas Profesional para WhatsApp
Punto de entrada principal de la aplicación
"""
import asyncio
import logging
import signal
import sys
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import uvicorn

# Add current directory to path for relative imports
sys.path.insert(0, os.path.dirname(__file__))

from config.settings import settings
from core.sales_agent import SalesAgent

# Configurar logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Instancia global del agente
sales_agent: SalesAgent = None

class WebhookPayload(BaseModel):
    """Modelo para el payload del webhook"""
    body: dict

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manejo del ciclo de vida de la aplicación"""
    global sales_agent

    # Inicializar agente
    sales_agent = SalesAgent()
    success = await sales_agent.initialize()

    if not success:
        logger.error("No se pudo inicializar el agente de ventas")
        sys.exit(1)

    await sales_agent.start()

    yield

    # Limpiar recursos
    if sales_agent:
        await sales_agent.stop()

# Crear aplicación FastAPI
app = FastAPI(
    title="Agente de Ventas WhatsApp",
    description="API para procesar mensajes de WhatsApp con IA",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/")
async def root():
    """Endpoint de salud"""
    if sales_agent:
        status = sales_agent.get_status()
        return {
            "message": "Agente de Ventas activo",
            "status": status
        }
    return {"message": "Agente de Ventas"}

@app.get("/health")
async def health_check():
    """Endpoint de verificación de salud"""
    if not sales_agent:
        raise HTTPException(status_code=503, detail="Agente no inicializado")

    status = sales_agent.get_status()
    return {
        "status": "healthy" if status["is_running"] else "unhealthy",
        "details": status
    }

@app.post("/webhook")
async def whatsapp_webhook(request: Request, payload: WebhookPayload):
    """
    Endpoint para recibir webhooks de WhatsApp

    Args:
        payload: Datos del webhook

    Returns:
        dict: Respuesta de confirmación
    """
    try:
        if not sales_agent:
            raise HTTPException(status_code=503, detail="Agente no disponible")

        # Procesar mensaje
        success = await sales_agent.process_message(payload.body)

        if success:
            return {"status": "success", "message": "Mensaje procesado correctamente"}
        else:
            return {"status": "ignored", "message": "Mensaje no procesado"}

    except Exception as e:
        logger.error(f"Error procesando webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.post("/refresh-products")
async def refresh_products():
    """Endpoint para refrescar caché de productos"""
    try:
        if not sales_agent:
            raise HTTPException(status_code=503, detail="Agente no disponible")

        await sales_agent._update_products_cache()
        return {"status": "success", "message": "Productos actualizados"}

    except Exception as e:
        logger.error(f"Error actualizando productos: {str(e)}")
        raise HTTPException(status_code=500, detail="Error actualizando productos")

@app.get("/products")
async def get_products():
    """Endpoint para obtener productos disponibles"""
    try:
        if not sales_agent:
            raise HTTPException(status_code=503, detail="Agente no disponible")

        all_products = []
        for store, products in sales_agent.products_cache.items():
            for product in products:
                all_products.append({
                    "nombre": product.nombre,
                    "tienda": product.tienda,
                    "precio": product.precio,
                    "disponibilidad": product.disponibilidad
                })

        return {
            "total": len(all_products),
            "products": all_products
        }

    except Exception as e:
        logger.error(f"Error obteniendo productos: {str(e)}")
        raise HTTPException(status_code=500, detail="Error obteniendo productos")

def signal_handler(signum, frame):
    """Manejador de señales para graceful shutdown"""
    logger.info(f"Señal {signum} recibida, deteniendo servidor...")
    sys.exit(0)

async def main():
    """Función principal"""
    # Registrar manejadores de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Configurar servidor
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=8000,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True
    )

    server = uvicorn.Server(config)

    try:
        logger.info("Iniciando servidor en http://0.0.0.0:8000")
        await server.serve()
    except KeyboardInterrupt:
        logger.info("Servidor detenido por usuario")
    except Exception as e:
        logger.error(f"Error en servidor: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # Ejecutar aplicación
    asyncio.run(main())