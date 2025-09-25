"""
Configuración del Agente de Ventas Python
"""
import os
from typing import Dict, Any
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class Settings:
    """Configuración centralizada del agente"""

    # Configuración de WhatsApp
    WHATSAPP_SERVER_URL: str = os.getenv("WHATSAPP_SERVER_URL", "")
    WHATSAPP_INSTANCE_NAME: str = os.getenv("WHATSAPP_INSTANCE_NAME", "")
    WHATSAPP_API_KEY: str = os.getenv("WHATSAPP_API_KEY", "")

    # Configuración de IA
    GOOGLE_GEMINI_API_KEY: str = os.getenv("GOOGLE_GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Configuración de Ollama
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama2")

    # Configuración de scraping
    MEGAPACK_URL: str = "https://megapack-nu.vercel.app/"
    MEGACOMPUTER_URL: str = "https://megacomputer.com.co/"

    # Configuración del agente
    MAX_RESPONSE_LENGTH: int = 500
    CONTEXT_WINDOW_LENGTH: int = 10
    DELAY_BETWEEN_MESSAGES: float = 2.0

    # Configuración de logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/agente_ventas.log")

    # Configuración del sistema de archivos
    TEMP_DIR: str = "temp"
    LOGS_DIR: str = "logs"

    @classmethod
    def validate_config(cls) -> Dict[str, Any]:
        """Validar configuración crítica"""
        errors = []

        if not cls.WHATSAPP_SERVER_URL:
            errors.append("WHATSAPP_SERVER_URL no configurado")

        if not cls.WHATSAPP_API_KEY:
            errors.append("WHATSAPP_API_KEY no configurado")

        if not cls.GOOGLE_GEMINI_API_KEY and not cls.OPENAI_API_KEY:
            errors.append("Se necesita al menos una API key de IA (Google Gemini o OpenAI)")

        return {
            "valid": len(errors) == 0,
            "errors": errors
        }

# Instancia global de configuración
settings = Settings()