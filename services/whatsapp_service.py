"""
Servicio para manejar la comunicación con WhatsApp
"""
import asyncio
import aiohttp
import logging
from typing import Dict, Any, Optional
from urllib.parse import quote

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from models.message import WhatsAppMessage

logger = logging.getLogger(__name__)

class WhatsAppService:
    """Servicio para interactuar con la API de WhatsApp"""

    def __init__(self):
        self.server_url = settings.WHATSAPP_SERVER_URL
        self.instance_name = settings.WHATSAPP_INSTANCE_NAME
        self.api_key = settings.WHATSAPP_API_KEY
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Inicializar sesión HTTP"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cerrar sesión HTTP"""
        if self.session:
            await self.session.close()

    async def send_text_message(self, chat_id: str, text: str, delay: float = 2.0) -> bool:
        """
        Enviar mensaje de texto

        Args:
            chat_id: ID del chat
            text: Texto del mensaje
            delay: Retraso en segundos

        Returns:
            bool: True si se envió correctamente
        """
        if not self.session:
            await self.__aenter__()

        try:
            # Limitar longitud del mensaje
            text = text[:settings.MAX_RESPONSE_LENGTH]

            url = f"{self.server_url}/message/sendText/{quote(self.instance_name)}"

            payload = {
                "number": chat_id,
                "text": text,
                "delay": delay * 1000  # Convertir a milisegundos
            }

            headers = {
                "apikey": self.api_key,
                "Content-Type": "application/json"
            }

            async with self.session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    logger.info(f"Mensaje de texto enviado a {chat_id}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Error enviando mensaje: {response.status} - {error_text}")
                    return False

        except Exception as e:
            logger.error(f"Error en envío de mensaje: {str(e)}")
            return False

    async def send_image_message(self, chat_id: str, image_url: str, caption: str = "") -> bool:
        """
        Enviar mensaje con imagen

        Args:
            chat_id: ID del chat
            image_url: URL de la imagen
            caption: Texto del caption

        Returns:
            bool: True si se envió correctamente
        """
        if not self.session:
            await self.__aenter__()

        try:
            url = f"{self.server_url}/message/sendImage/{quote(self.instance_name)}"

            payload = {
                "number": chat_id,
                "image": image_url,
                "caption": caption[:settings.MAX_RESPONSE_LENGTH]
            }

            headers = {
                "apikey": self.api_key,
                "Content-Type": "application/json"
            }

            async with self.session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    logger.info(f"Mensaje con imagen enviado a {chat_id}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Error enviando imagen: {response.status} - {error_text}")
                    return False

        except Exception as e:
            logger.error(f"Error en envío de imagen: {str(e)}")
            return False

    async def download_media(self, message_id: str) -> Optional[bytes]:
        """
        Descargar archivo multimedia

        Args:
            message_id: ID del mensaje con multimedia

        Returns:
            bytes: Contenido del archivo o None si hay error
        """
        if not self.session:
            await self.__aenter__()

        try:
            url = f"{self.server_url}/chat/getBase64FromMediaMessage/{quote(self.instance_name)}"

            payload = {
                "message.key.id": message_id,
                "convertToMp4": False
            }

            headers = {
                "apikey": self.api_key,
                "Content-Type": "application/json"
            }

            async with self.session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('success') and 'data' in data:
                        # Decodificar base64
                        import base64
                        return base64.b64decode(data['data'])
                    else:
                        logger.error(f"Error en respuesta de descarga: {data}")
                        return None
                else:
                    error_text = await response.text()
                    logger.error(f"Error descargando media: {response.status} - {error_text}")
                    return None

        except Exception as e:
            logger.error(f"Error descargando multimedia: {str(e)}")
            return None

    def is_configured(self) -> bool:
        """Verificar si el servicio está configurado correctamente"""
        return bool(
            self.server_url and
            self.instance_name and
            self.api_key
        )

    async def validate_connection(self) -> bool:
        """
        Validar conexión con el servidor de WhatsApp

        Returns:
            bool: True si la conexión es válida
        """
        if not self.is_configured():
            return False

        if not self.session:
            await self.__aenter__()

        try:
            # Intentar obtener información de la instancia
            url = f"{self.server_url}/instance/info/{quote(self.instance_name)}"

            headers = {
                "apikey": self.api_key
            }

            async with self.session.get(url, headers=headers) as response:
                return response.status == 200

        except Exception as e:
            logger.error(f"Error validando conexión: {str(e)}")
            return False