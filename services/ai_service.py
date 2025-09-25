"""
Servicio de IA para generar respuestas de ventas
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
import google.generativeai as genai
import openai
import aiohttp

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from models.product import Product

logger = logging.getLogger(__name__)

class AIService:
    """Servicio para interactuar con modelos de IA"""

    def __init__(self):
        self.gemini_api_key = settings.GOOGLE_GEMINI_API_KEY
        self.openai_api_key = settings.OPENAI_API_KEY
        self.ollama_base_url = settings.OLLAMA_BASE_URL
        self.ollama_model = settings.OLLAMA_MODEL
        self.model = None
        self.memory: Dict[str, List[Dict[str, str]]] = {}
        self.session: Optional[aiohttp.ClientSession] = None

    async def initialize(self):
        """Inicializar el servicio de IA"""
        # Inicializar sesión HTTP para Ollama
        self.session = aiohttp.ClientSession()

        # Prioridad: Gemini > OpenAI > Ollama
        if self.gemini_api_key:
            try:
                genai.configure(api_key=self.gemini_api_key)
                self.model = genai.GenerativeModel('gemini-pro')
                logger.info("Google Gemini inicializado")
                return
            except Exception as e:
                logger.error(f"Error inicializando Gemini: {str(e)}")

        if self.openai_api_key:
            try:
                openai.api_key = self.openai_api_key
                logger.info("OpenAI inicializado")
                return
            except Exception as e:
                logger.error(f"Error inicializando OpenAI: {str(e)}")

        # Verificar si Ollama está disponible
        if await self._check_ollama_availability():
            logger.info(f"Ollama inicializado con modelo {self.ollama_model}")
        else:
            logger.warning("Ningún servicio de IA disponible")

    def add_to_memory(self, chat_id: str, message: str, response: str):
        """
        Agregar intercambio a la memoria de la conversación

        Args:
            chat_id: ID del chat
            message: Mensaje del usuario
            response: Respuesta del agente
        """
        if chat_id not in self.memory:
            self.memory[chat_id] = []

        self.memory[chat_id].append({
            "user": message,
            "agent": response
        })

        # Mantener solo las últimas N interacciones
        if len(self.memory[chat_id]) > settings.CONTEXT_WINDOW_LENGTH:
            self.memory[chat_id] = self.memory[chat_id][-settings.CONTEXT_WINDOW_LENGTH:]

    def get_memory_context(self, chat_id: str) -> str:
        """
        Obtener contexto de memoria para el chat

        Args:
            chat_id: ID del chat

        Returns:
            str: Contexto formateado
        """
        if chat_id not in self.memory:
            return ""

        context = "Historial de conversación:\n"
        for i, exchange in enumerate(self.memory[chat_id], 1):
            context += f"{i}. Usuario: {exchange['user']}\n"
            context += f"   Agente: {exchange['agent']}\n"

        return context

    async def generate_response(self, message: str, products: List[Product], chat_id: str = "") -> str:
        """
        Generar respuesta usando IA

        Args:
            message: Mensaje del usuario
            products: Lista de productos disponibles
            chat_id: ID del chat para contexto

        Returns:
            str: Respuesta generada
        """
        try:
            # Preparar contexto
            memory_context = self.get_memory_context(chat_id) if chat_id else ""

            # Preparar información de productos
            products_info = ""
            if products:
                products_info = "Productos disponibles:\n"
                for product in products[:5]:  # Limitar a 5 productos
                    products_info += f"- {product.get_display_info()}\n"

            # Crear prompt del sistema
            system_prompt = """Eres un agente de ventas profesional especializado en productos tecnológicos.
            Responde en máximo 3 líneas, usa emojis como 💻📱🛒, no menciones webs de origen,
            y si hay imagen del producto inclúyela en la salida.

            Instrucciones específicas:
            - Sé amable y profesional
            - Destaca beneficios del producto
            - Ofrece información de precios y disponibilidad
            - Invita a la acción de compra
            - Mantén respuestas concisas pero informativas"""

            # Combinar contexto
            full_prompt = f"{system_prompt}\n\n{memory_context}\n\n{products_info}\n\nUsuario: {message}"

            # Generar respuesta con Gemini
            if self.model and hasattr(self.model, 'generate_content'):
                response = self.model.generate_content(
                    full_prompt,
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=150,
                        temperature=0.7
                    )
                )
                response_text = response.text.strip()

            # Generar respuesta con OpenAI
            elif self.openai_api_key:
                client = openai.OpenAI(api_key=self.openai_api_key)
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": full_prompt}
                    ],
                    max_tokens=150,
                    temperature=0.7
                )
                response_text = response.choices[0].message.content.strip()

            # Generar respuesta con Ollama
            elif await self._check_ollama_availability():
                response_text = await self._generate_ollama_response(system_prompt, full_prompt)

            else:
                # Fallback a respuesta básica
                response_text = self._generate_fallback_response(message, products)

            # Limitar longitud
            response_text = response_text[:settings.MAX_RESPONSE_LENGTH]

            # Agregar a memoria si hay chat_id
            if chat_id and response_text:
                self.add_to_memory(chat_id, message, response_text)

            return response_text

        except Exception as e:
            logger.error(f"Error generando respuesta: {str(e)}")
            return self._generate_fallback_response(message, products)

    def _generate_fallback_response(self, message: str, products: List[Product]) -> str:
        """
        Generar respuesta fallback cuando la IA no está disponible

        Args:
            message: Mensaje del usuario
            products: Lista de productos

        Returns:
            str: Respuesta fallback
        """
        message_lower = message.lower()

        # Buscar producto relacionado
        relevant_product = None
        for product in products:
            if any(keyword in message_lower for keyword in product.nombre.lower().split()):
                relevant_product = product
                break

        if relevant_product:
            return f"💻 ¡Excelente elección! {relevant_product.get_display_info()} 📱 ¿Te gustaría conocer más detalles sobre precios y disponibilidad? 🛒"

        # Respuestas genéricas
        if any(word in message_lower for word in ['precio', 'costo', 'cuánto']):
            return "💰 Nuestros precios son competitivos y varían según el modelo. ¿Qué producto te interesa? 📱"

        if any(word in message_lower for word in ['disponible', 'stock', 'existencia']):
            return "📦 Contamos con amplia disponibilidad. ¿Qué producto necesitas? 🛒"

        if any(word in message_lower for word in ['hola', 'buenos', 'saludos']):
            return "¡Hola! 👋 Soy tu asistente de ventas tecnológico. ¿En qué puedo ayudarte? 💻📱"

        return "💬 ¡Hola! ¿En qué producto tecnológico puedo ayudarte hoy? Disponemos de laptops, celulares y accesorios 🛒"

    def clear_memory(self, chat_id: str = None):
        """
        Limpiar memoria de conversación

        Args:
            chat_id: ID específico del chat, si es None limpia toda la memoria
        """
        if chat_id:
            self.memory.pop(chat_id, None)
        else:
            self.memory.clear()

    async def _check_ollama_availability(self) -> bool:
        """Verificar si Ollama está disponible"""
        if not self.session:
            self.session = aiohttp.ClientSession()

        try:
            async with self.session.get(f"{self.ollama_base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    models = data.get('models', [])
                    available_models = [model['name'] for model in models]

                    # Verificar si el modelo solicitado está disponible
                    if self.ollama_model in available_models:
                        return True
                    elif available_models:
                        logger.warning(f"Modelo {self.ollama_model} no encontrado. Modelos disponibles: {available_models}")
                        return False
                    else:
                        logger.warning("No hay modelos disponibles en Ollama")
                        return False
                return False
        except Exception as e:
            logger.error(f"Error verificando Ollama: {str(e)}")
            return False

    async def _generate_ollama_response(self, system_prompt: str, user_prompt: str) -> str:
        """
        Generar respuesta usando Ollama

        Args:
            system_prompt: Prompt del sistema
            user_prompt: Prompt del usuario

        Returns:
            str: Respuesta generada
        """
        if not self.session:
            self.session = aiohttp.ClientSession()

        try:
            # Combinar prompts para Ollama
            full_prompt = f"{system_prompt}\n\n{user_prompt}"

            payload = {
                "model": self.ollama_model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 150
                }
            }

            async with self.session.post(
                f"{self.ollama_base_url}/api/generate",
                json=payload,
                timeout=60
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('response', '').strip()
                else:
                    error_text = await response.text()
                    logger.error(f"Error en Ollama: {response.status} - {error_text}")
                    return ""

        except asyncio.TimeoutError:
            logger.error("Timeout en llamada a Ollama")
            return ""
        except Exception as e:
            logger.error(f"Error generando respuesta con Ollama: {str(e)}")
            return ""

    def is_configured(self) -> bool:
        """Verificar si el servicio está configurado"""
        return bool(self.gemini_api_key or self.openai_api_key or self.ollama_base_url)