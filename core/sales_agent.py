"""
Agente de Ventas Principal
Coordina todos los servicios para procesar mensajes de WhatsApp
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from models.message import WhatsAppMessage
from models.product import Product
from services.whatsapp_service import WhatsAppService
from services.scraping_service import ScrapingService
from services.ai_service import AIService
from services.audio_service import AudioService
from services.message_processor import MessageProcessor

logger = logging.getLogger(__name__)

class SalesAgent:
    """Agente principal de ventas para WhatsApp"""

    def __init__(self):
        self.whatsapp_service = WhatsAppService()
        self.scraping_service = ScrapingService()
        self.ai_service = AIService()
        self.audio_service = AudioService()
        self.message_processor = MessageProcessor()

        self.is_running = False
        self.products_cache: Dict[str, Any] = {}
        self.last_cache_update: Optional[datetime] = None

    async def initialize(self):
        """Inicializar el agente y todos sus servicios"""
        try:
            logger.info("Inicializando Agente de Ventas...")

            # Inicializar servicios
            await self.ai_service.initialize()

            # Validar configuración
            config_valid = settings.validate_config()
            if not config_valid["valid"]:
                logger.error(f"Configuración inválida: {config_valid['errors']}")
                return False

            # Validar conexión con WhatsApp
            if not await self.whatsapp_service.validate_connection():
                logger.warning("No se pudo validar conexión con WhatsApp")

            # Cargar productos iniciales
            await self._update_products_cache()

            logger.info("Agente de Ventas inicializado correctamente")
            return True

        except Exception as e:
            logger.error(f"Error inicializando agente: {str(e)}")
            return False

    async def _update_products_cache(self):
        """Actualizar caché de productos"""
        try:
            logger.info("Actualizando caché de productos...")
            self.products_cache = await self.scraping_service.scrape_all_stores()
            self.last_cache_update = datetime.now()
            logger.info(f"Caché actualizado: {sum(len(p) for p in self.products_cache.values())} productos")
        except Exception as e:
            logger.error(f"Error actualizando caché: {str(e)}")

    async def process_message(self, webhook_data: Dict[str, Any]) -> bool:
        """
        Procesar un mensaje de WhatsApp

        Args:
            webhook_data: Datos del webhook

        Returns:
            bool: True si se procesó correctamente
        """
        try:
            # Normalizar mensaje
            message = self.message_processor.normalize_message_data(webhook_data)

            # Limpiar datos nulos
            cleaned_data = self.message_processor.clean_null_data(message.to_dict())
            message = WhatsAppMessage(**cleaned_data)

            # Validar mensaje
            is_valid, reason = self.message_processor.validate_message(message)
            if not is_valid:
                logger.info(f"Mensaje inválido: {reason}")
                return False

            # Verificar si debe responder
            should_respond, reason = self.message_processor.should_respond(message)
            if not should_respond:
                logger.info(f"No responder: {reason}")
                return False

            # Procesar según tipo de mensaje
            if self.message_processor.is_duplicate_message(message):
                logger.info("Mensaje duplicado ignorado")
                return False

            # Procesar mensaje de texto
            if message.message_type == "text":
                return await self._process_text_message(message)

            # Procesar mensaje de audio
            elif message.message_type == "audio":
                return await self._process_audio_message(message)

            else:
                logger.warning(f"Tipo de mensaje no soportado: {message.message_type}")
                return False

        except Exception as e:
            logger.error(f"Error procesando mensaje: {str(e)}")
            return False

    async def _process_text_message(self, message: WhatsAppMessage) -> bool:
        """
        Procesar mensaje de texto

        Args:
            message: Mensaje de texto

        Returns:
            bool: True si se procesó correctamente
        """
        try:
            # Procesar productos
            products_result = self.message_processor.process_products(
                self.products_cache,
                message.content
            )

            # Preparar contexto para IA
            context = self.message_processor.prepare_ai_context(message, products_result)

            # Generar respuesta con IA
            response = await self.ai_service.generate_response(
                message.content,
                products_result.get("alternativas", []),
                message.chat_id
            )

            if not response:
                logger.error("No se pudo generar respuesta")
                return False

            # Enviar respuesta
            success = await self.whatsapp_service.send_text_message(
                message.chat_id,
                response,
                settings.DELAY_BETWEEN_MESSAGES
            )

            if success:
                # Agregar a memoria de IA
                self.ai_service.add_to_memory(message.chat_id, message.content, response)
                logger.info(f"Respuesta enviada a {message.chat_id}")

                # Si hay producto encontrado, intentar enviar imagen
                if products_result.get("productoEncontrado"):
                    await self._send_product_image(message, products_result["productoEncontrado"])

            return success

        except Exception as e:
            logger.error(f"Error procesando mensaje de texto: {str(e)}")
            return False

    async def _process_audio_message(self, message: WhatsAppMessage) -> bool:
        """
        Procesar mensaje de audio

        Args:
            message: Mensaje de audio

        Returns:
            bool: True si se procesó correctamente
        """
        try:
            # Descargar audio
            audio_data = await self.whatsapp_service.download_media(message.message_id)

            if not audio_data:
                logger.error("No se pudo descargar audio")
                return False

            # Transcribir audio
            transcription = await self.audio_service.transcribe_audio(audio_data)

            if not transcription:
                logger.error("No se pudo transcribir audio")
                return False

            logger.info(f"Audio transcrito: {transcription[:100]}...")

            # Procesar como mensaje de texto
            text_message = WhatsAppMessage(
                message_id=message.message_id,
                chat_id=message.chat_id,
                content=transcription,
                user_name=message.user_name,
                message_type="text",
                server_url=message.server_url,
                instance_name=message.instance_name,
                api_key=message.api_key
            )

            return await self._process_text_message(text_message)

        except Exception as e:
            logger.error(f"Error procesando mensaje de audio: {str(e)}")
            return False

    async def _send_product_image(self, message: WhatsAppMessage, product: Product) -> bool:
        """
        Enviar imagen del producto si está disponible

        Args:
            message: Mensaje original
            product: Producto con imagen

        Returns:
            bool: True si se envió correctamente
        """
        try:
            if not product.imagen:
                return False

            # Enviar imagen con caption
            success = await self.whatsapp_service.send_image_message(
                message.chat_id,
                product.imagen,
                product.get_display_info()
            )

            if success:
                logger.info(f"Imagen de producto enviada: {product.nombre}")

            return success

        except Exception as e:
            logger.error(f"Error enviando imagen de producto: {str(e)}")
            return False

    async def start(self):
        """Iniciar el agente"""
        if self.is_running:
            logger.warning("El agente ya está ejecutándose")
            return

        success = await self.initialize()
        if not success:
            logger.error("No se pudo inicializar el agente")
            return

        self.is_running = True
        logger.info("Agente de Ventas iniciado")

    async def stop(self):
        """Detener el agente"""
        self.is_running = False
        logger.info("Agente de Ventas detenido")

    def get_status(self) -> Dict[str, Any]:
        """
        Obtener estado del agente

        Returns:
            Dict[str, Any]: Estado actual
        """
        return {
            "is_running": self.is_running,
            "products_cache_size": sum(len(p) for p in self.products_cache.values()),
            "last_cache_update": self.last_cache_update.isoformat() if self.last_cache_update else None,
            "whatsapp_configured": self.whatsapp_service.is_configured(),
            "ai_configured": self.ai_service.is_configured(),
            "audio_configured": bool(self.audio_service.openai_api_key)
        }