"""
Configuración de INFRAESTRUCTURA del agente.

Aquí solo vive lo técnico (WhatsApp/Evolution API, proveedores de IA, rutas,
límites). El perfil del negocio (nombre, horarios, catálogo de productos y
servicios) NO va aquí: vive en config/negocio.json y lo carga config/business.py.

Esto es lo que permite usar el mismo agente para una tienda de tecnología, un
restaurante, una barbería, un taller, una clínica o una empresa de servicios.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# ---------------------------------------------------------------- rutas base
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def _bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "si", "sí", "on", "y"}


def _int(name: str, default: int) -> int:
    try:
        return int(str(os.getenv(name, "")).strip())
    except (TypeError, ValueError):
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(str(os.getenv(name, "")).strip())
    except (TypeError, ValueError):
        return default


def _list(name: str, default: str = "") -> List[str]:
    raw = os.getenv(name, default) or ""
    return [p.strip() for p in raw.split(",") if p.strip()]


def _path(name: str, default: str) -> Path:
    raw = os.getenv(name, "").strip() or default
    p = Path(raw)
    return p if p.is_absolute() else (BASE_DIR / p)


class Settings:
    """Configuración centralizada (leída de variables de entorno)."""

    BASE_DIR: Path = BASE_DIR

    # ------------------------------------------------------ WhatsApp / Evolution
    WHATSAPP_SERVER_URL: str = os.getenv("WHATSAPP_SERVER_URL", "").rstrip("/")
    WHATSAPP_INSTANCE_NAME: str = os.getenv("WHATSAPP_INSTANCE_NAME", "")
    WHATSAPP_API_KEY: str = os.getenv("WHATSAPP_API_KEY", "")
    WHATSAPP_TIMEOUT: float = _float("WHATSAPP_TIMEOUT", 20.0)
    WHATSAPP_RETRIES: int = _int("WHATSAPP_RETRIES", 2)
    # Token opcional: si se define, /webhook exige ?token=... o header apikey
    WEBHOOK_TOKEN: str = os.getenv("WEBHOOK_TOKEN", "")
    # Responder en grupos (por defecto NO, para no spamear)
    RESPOND_TO_GROUPS: bool = _bool("RESPOND_TO_GROUPS", False)
    # Solo responder mensajes directos de 1:1
    SEND_PRESENCE: bool = _bool("SEND_PRESENCE", True)

    # ------------------------------------------------------------------ IA
    # auto | gemini | openai | ollama | rules
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "auto").strip().lower()
    AI_ENABLED: bool = _bool("AI_ENABLED", True)
    GOOGLE_GEMINI_API_KEY: str = os.getenv("GOOGLE_GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3")
    AI_TIMEOUT: float = _float("AI_TIMEOUT", 25.0)

    # --------------------------------------------------------------- Negocio
    # Un solo archivo = perfil del negocio + catálogo de productos/servicios.
    BUSINESS_CONFIG: Path = _path("BUSINESS_CONFIG", "config/negocio.json")
    BUSINESS_EXAMPLES_DIR: Path = _path("BUSINESS_EXAMPLES_DIR", "negocios/ejemplos")
    # Fuentes web opcionales para refrescar el catálogo (scraping)
    SCRAPE_ENABLED: bool = _bool("SCRAPE_ENABLED", False)
    SCRAPE_TIMEOUT: float = _float("SCRAPE_TIMEOUT", 20.0)

    # --------------------------------------------------------- Comportamiento
    MAX_RESPONSE_LENGTH: int = _int("MAX_RESPONSE_LENGTH", 900)
    CONTEXT_WINDOW_LENGTH: int = _int("CONTEXT_WINDOW_LENGTH", 10)
    DELAY_BETWEEN_MESSAGES: float = _float("DELAY_BETWEEN_MESSAGES", 2.0)
    # Cuántos ítems listar como máximo en una respuesta
    MAX_ITEMS_IN_REPLY: int = _int("MAX_ITEMS_IN_REPLY", 5)
    # Umbral de coincidencia para considerar un producto/servicio "encontrado"
    MATCH_THRESHOLD: float = _float("MATCH_THRESHOLD", 0.42)
    # Si el cliente pide hablar con un humano, avisamos a este número (opcional)
    HUMAN_ESCALATION_NUMBER: str = os.getenv("HUMAN_ESCALATION_NUMBER", "")
    # Frase de escalado (se puede sobreescribir desde el negocio)
    HUMAN_ESCALATION_TEXT: str = os.getenv("HUMAN_ESCALATION_TEXT", "")

    # ---------------------------------------------------------------- Servidor
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = _int("PORT", 8000)

    # -------------------------------------------------------------- Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/agente_ventas.log")
    TEMP_DIR: str = os.getenv("TEMP_DIR", "temp")
    LOGS_DIR: str = os.getenv("LOGS_DIR", "logs")

    # Rutas resueltas (absolutas)
    @classmethod
    def log_file_path(cls) -> Path:
        p = Path(cls.LOG_FILE)
        return p if p.is_absolute() else cls.BASE_DIR / p

    @classmethod
    def temp_path(cls) -> Path:
        return cls.BASE_DIR / cls.TEMP_DIR

    # -------------------------------------------------------------- utilidades
    @classmethod
    def ai_provider_resuelto(cls) -> str:
        """
        Proveedor de IA a usar. 'auto' elige el primero disponible:
        gemini -> openai -> ollama -> rules (motor determinístico).
        """
        if not cls.AI_ENABLED:
            return "rules"
        if cls.AI_PROVIDER != "auto":
            return cls.AI_PROVIDER
        if cls.GOOGLE_GEMINI_API_KEY:
            return "gemini"
        if cls.OPENAI_API_KEY:
            return "openai"
        if os.getenv("OLLAMA_BASE_URL", "").strip():
            return "ollama"
        return "rules"

    @classmethod
    def whatsapp_configurado(cls) -> bool:
        return bool(cls.WHATSAPP_SERVER_URL and cls.WHATSAPP_INSTANCE_NAME and cls.WHATSAPP_API_KEY)

    @classmethod
    def validate_config(cls) -> Dict[str, Any]:
        """
        Validación no bloqueante: el agente puede arrancar en modo simulador
        aunque falte WhatsApp o la IA (así se puede probar cualquier negocio).
        """
        errores: List[str] = []
        avisos: List[str] = []

        if not cls.SCRAPE_ENABLED:
            avisos.append(
                "Importación del catálogo desde la web desactivada (SCRAPE_ENABLED=false). "
                "El catálogo se toma de config/negocio.json"
            )
        if cls.ai_provider_resuelto() == "rules":
            avisos.append(
                "Sin proveedor de IA activo: se usarán las respuestas determinísticas "
                "construidas desde el catálogo del negocio."
            )
        if not cls.BUSINESS_CONFIG.exists():
            avisos.append(
                f"No existe {cls.BUSINESS_CONFIG}. Copia un ejemplo de "
                f"{cls.BUSINESS_EXAMPLES_DIR}/ a config/negocio.json"
            )
        if cls.WEBHOOK_TOKEN == "" and cls.whatsapp_configurado():
            avisos.append(
                "WEBHOOK_TOKEN vacío: el webhook acepta cualquier petición. "
                "Define uno para producción."
            )

        return {"valid": len(errores) == 0, "errors": errores, "warnings": avisos}


settings = Settings()
