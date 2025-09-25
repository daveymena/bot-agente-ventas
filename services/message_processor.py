"""
Servicio para procesar y validar mensajes
"""
import logging
from typing import Dict, Any, Optional, Tuple

from models.message import WhatsAppMessage
from models.product import Product

logger = logging.getLogger(__name__)

class MessageProcessor:
    """Servicio para procesar mensajes de WhatsApp"""

    def __init__(self):
        self.processed_messages = set()

    def normalize_message_data(self, webhook_data: Dict[str, Any]) -> WhatsAppMessage:
        """
        Normalizar datos del webhook a objeto WhatsAppMessage

        Args:
            webhook_data: Datos del webhook

        Returns:
            WhatsAppMessage: Mensaje normalizado
        """
        try:
            message = WhatsAppMessage.from_webhook_data(webhook_data)
            logger.info(f"Mensaje normalizado: {message.chat_id} - {message.content[:50]}...")
            return message

        except Exception as e:
            logger.error(f"Error normalizando mensaje: {str(e)}")
            raise

    def clean_null_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Limpiar valores nulos del mensaje

        Args:
            data: Datos del mensaje

        Returns:
            Dict[str, Any]: Datos limpios
        """
        cleaned = {}
        for key, value in data.items():
            if value != "nulo" and value is not None and value != "":
                cleaned[key] = value
        return cleaned

    def validate_message(self, message: WhatsAppMessage) -> Tuple[bool, str]:
        """
        Validar que el mensaje tenga los datos necesarios

        Args:
            message: Mensaje a validar

        Returns:
            Tuple[bool, str]: (válido, razón si no es válido)
        """
        if not message.content:
            return False, "Mensaje sin contenido"

        if not message.chat_id:
            return False, "Mensaje sin chat_id"

        if len(message.content.strip()) < 2:
            return False, "Contenido del mensaje muy corto"

        return True, ""

    def process_products(self, products: Dict[str, Product], query: str) -> Dict[str, Any]:
        """
        Procesar productos y encontrar coincidencias

        Args:
            products: Diccionario con productos por tienda
            query: Consulta del usuario

        Returns:
            Dict[str, Any]: Resultado del procesamiento
        """
        try:
            all_products = []
            for store_products in products.values():
                all_products.extend(store_products)

            # Buscar producto que coincida
            matched_product = None
            for product in all_products:
                if product.matches_query(query):
                    matched_product = product
                    break

            # Si no hay coincidencia exacta, tomar el primero como alternativa
            alternatives = all_products[:3] if all_products else []

            return {
                "productoEncontrado": matched_product,
                "alternativas": alternatives,
                "totalProductos": len(all_products)
            }

        except Exception as e:
            logger.error(f"Error procesando productos: {str(e)}")
            return {
                "productoEncontrado": None,
                "alternativas": [],
                "totalProductos": 0
            }

    def extract_keywords(self, message: str) -> list:
        """
        Extraer palabras clave del mensaje

        Args:
            message: Mensaje del usuario

        Returns:
            list: Lista de palabras clave
        """
        if not message:
            return []

        # Palabras clave comunes de productos tecnológicos
        tech_keywords = [
            'laptop', 'computador', 'pc', 'notebook', 'portátil',
            'iphone', 'samsung', 'xiaomi', 'huawei', 'motorola',
            'tablet', 'ipad', 'galaxy', 'pro', 'max', 'plus',
            'ssd', 'hdd', 'ram', 'memoria', 'procesador', 'cpu',
            'monitor', 'pantalla', 'teclado', 'mouse', 'auricular',
            'cargador', 'batería', 'adaptador', 'cable', 'usb',
            'precio', 'costo', 'disponible', 'stock', 'compra'
        ]

        words = message.lower().split()
        keywords = []

        for word in words:
            # Limpiar palabra
            clean_word = word.strip('.,!?¿¡()[]{}"\'').lower()

            # Agregar si es palabra clave de tecnología
            if clean_word in tech_keywords:
                keywords.append(clean_word)

            # Agregar si tiene longitud significativa y parece nombre de producto
            elif len(clean_word) > 3 and not clean_word.isdigit():
                keywords.append(clean_word)

        return list(set(keywords))  # Remover duplicados

    def is_duplicate_message(self, message: WhatsAppMessage) -> bool:
        """
        Verificar si el mensaje es duplicado

        Args:
            message: Mensaje a verificar

        Returns:
            bool: True si es mensaje duplicado
        """
        message_key = f"{message.chat_id}:{message.message_id}:{hash(message.content)}"

        if message_key in self.processed_messages:
            return True

        self.processed_messages.add(message_key)

        # Limpiar mensajes antiguos (mantener solo 1000)
        if len(self.processed_messages) > 1000:
            # Remover 200 mensajes antiguos
            self.processed_messages = set(list(self.processed_messages)[200:])

        return False

    def prepare_ai_context(self, message: WhatsAppMessage, products: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preparar contexto para el agente de IA

        Args:
            message: Mensaje del usuario
            products: Productos procesados

        Returns:
            Dict[str, Any]: Contexto preparado
        """
        return {
            "message": message,
            "products": products,
            "keywords": self.extract_keywords(message.content),
            "is_product_query": len(self.extract_keywords(message.content)) > 0,
            "has_matched_product": products.get("productoEncontrado") is not None
        }

    def should_respond(self, message: WhatsAppMessage) -> Tuple[bool, str]:
        """
        Determinar si el agente debe responder al mensaje

        Args:
            message: Mensaje a evaluar

        Returns:
            Tuple[bool, str]: (debe_responder, razón)
        """
        # No responder a mensajes duplicados
        if self.is_duplicate_message(message):
            return False, "Mensaje duplicado"

        # No responder a mensajes vacíos o inválidos
        is_valid, reason = self.validate_message(message)
        if not is_valid:
            return False, reason

        # No responder a mensajes del propio bot
        if message.user_name.lower() in ['bot', 'asistente', 'agente']:
            return False, "Mensaje del bot"

        # Responder a consultas de productos
        keywords = self.extract_keywords(message.content)
        if keywords:
            return True, "Consulta de producto"

        # Responder a saludos
        greetings = ['hola', 'buenos', 'buenas', 'saludos', 'hello', 'hi']
        if any(greeting in message.content.lower() for greeting in greetings):
            return True, "Saludo"

        # Responder a consultas de precios o disponibilidad
        price_queries = ['precio', 'costo', 'cuánto', 'disponible', 'stock', 'existencia']
        if any(query in message.content.lower() for query in price_queries):
            return True, "Consulta de precio/disponibilidad"

        return False, "No requiere respuesta"