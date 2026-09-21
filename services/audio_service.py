"""
Transcripción de notas de voz.

Es opcional: si no hay proveedor de transcripción (OpenAI Whisper) el agente
responde pidiendo el mensaje por escrito, en lugar de fallar en silencio.
"""
from __future__ import annotations

import asyncio
import base64
import logging
import os
import tempfile
from typing import Any, Dict, Optional, Tuple

from config.settings import settings

logger = logging.getLogger(__name__)

try:
    import openai  # type: ignore
    _TIENE_OPENAI = True
except Exception:  # pragma: no cover
    openai = None  # type: ignore
    _TIENE_OPENAI = False

EXTENSIONES = {
    "audio/ogg": ".ogg", "audio/opus": ".opus", "audio/mpeg": ".mp3", "audio/mp3": ".mp3",
    "audio/mp4": ".m4a", "audio/x-m4a": ".m4a", "audio/aac": ".aac", "audio/wav": ".wav",
    "audio/webm": ".webm", "audio/amr": ".amr", "audio/3gpp": ".3gp",
}


class AudioService:
    """Convierte notas de voz en texto."""

    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY if _TIENE_OPENAI else ""
        self.temp_dir = settings.temp_path()
        self.modelo = os.getenv("WHISPER_MODEL", "whisper-1")
        self.idioma = os.getenv("WHISPER_LANGUAGE", "es")

    @property
    def disponible(self) -> bool:
        return bool(self.openai_api_key)

    def estado(self) -> Dict[str, Any]:
        return {
            "disponible": self.disponible,
            "modelo": self.modelo if self.disponible else None,
            "motivo": None if self.disponible else "falta OPENAI_API_KEY (opcional)",
        }

    def _extension(self, mimetype: str) -> str:
        base = (mimetype or "").split(";")[0].strip().lower()
        return EXTENSIONES.get(base, ".ogg")

    async def transcribir_media(self, media: Dict[str, Any]) -> Tuple[Optional[str], str]:
        """
        Devuelve (texto, motivo). Si no se puede transcribir, texto=None y un
        motivo legible para decidir qué contestarle al cliente.
        """
        if not media:
            return None, "no llegó el audio"
        base64_audio = media.get("base64")
        if not base64_audio:
            return None, "audio no descargado"
        if not self.disponible:
            return None, "transcripción no configurada"
        try:
            crudo = base64.b64decode(base64_audio)
        except Exception as error:
            return None, f"audio inválido: {error}"
        return await self.transcribir_bytes(crudo, media.get("mimetype", "audio/ogg"))

    async def transcribir_bytes(self, datos: bytes, mimetype: str = "audio/ogg") -> Tuple[Optional[str], str]:
        if not self.disponible:
            return None, "transcripción no configurada"
        if not datos:
            return None, "audio vacío"

        self.temp_dir.mkdir(parents=True, exist_ok=True)
        ruta = None
        try:
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=self._extension(mimetype), dir=str(self.temp_dir)
            ) as archivo:
                archivo.write(datos)
                ruta = archivo.name

            cliente = openai.OpenAI(api_key=self.openai_api_key)

            def llamar() -> str:
                with open(ruta, "rb") as audio:
                    respuesta = cliente.audio.transcriptions.create(
                        model=self.modelo,
                        file=audio,
                        language=self.idioma,
                        response_format="text",
                    )
                return respuesta if isinstance(respuesta, str) else getattr(respuesta, "text", "")

            texto = await asyncio.wait_for(asyncio.to_thread(llamar), timeout=settings.AI_TIMEOUT * 2)
            texto = (texto or "").strip()
            if not texto:
                return None, "la transcripción llegó vacía"
            logger.info("Audio transcrito (%s caracteres)", len(texto))
            return texto, ""
        except asyncio.TimeoutError:
            return None, "la transcripción tardó demasiado"
        except Exception as error:
            logger.error("Error transcribiendo audio: %s", error)
            return None, f"error transcribiendo: {error}"
        finally:
            if ruta and os.path.exists(ruta):
                try:
                    os.unlink(ruta)
                except OSError:
                    pass
