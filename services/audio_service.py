"""
Servicio para procesar archivos de audio (transcripción)
"""
import asyncio
import logging
import tempfile
import os
from typing import Optional, Dict, Any
import openai

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings

logger = logging.getLogger(__name__)

class AudioService:
    """Servicio para procesar archivos de audio"""

    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.temp_dir = settings.TEMP_DIR

    async def transcribe_audio(self, audio_data: bytes, mime_type: str = "audio/mpeg") -> Optional[str]:
        """
        Transcribir audio usando OpenAI Whisper

        Args:
            audio_data: Datos del archivo de audio
            mime_type: Tipo MIME del audio

        Returns:
            Optional[str]: Texto transcrito o None si hay error
        """
        if not self.openai_api_key:
            logger.error("OpenAI API key no configurada para transcripción")
            return None

        try:
            # Crear archivo temporal
            with tempfile.NamedTemporaryFile(delete=False, suffix=self._get_extension(mime_type)) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name

            try:
                # Usar OpenAI Whisper para transcripción
                client = openai.OpenAI(api_key=self.openai_api_key)

                with open(temp_file_path, "rb") as audio_file:
                    transcription = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="text"
                    )

                return transcription.strip() if transcription else None

            finally:
                # Limpiar archivo temporal
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)

        except Exception as e:
            logger.error(f"Error transcribiendo audio: {str(e)}")
            return None

    def _get_extension(self, mime_type: str) -> str:
        """
        Obtener extensión de archivo basada en MIME type

        Args:
            mime_type: Tipo MIME

        Returns:
            str: Extensión del archivo
        """
        mime_to_ext = {
            "audio/mpeg": ".mp3",
            "audio/mp3": ".mp3",
            "audio/wav": ".wav",
            "audio/wave": ".wav",
            "audio/ogg": ".ogg",
            "audio/mp4": ".m4a",
            "audio/aac": ".aac",
            "audio/webm": ".webm"
        }

        return mime_to_ext.get(mime_type, ".mp3")

    async def convert_audio_format(self, audio_data: bytes, from_format: str, to_format: str) -> Optional[bytes]:
        """
        Convertir formato de audio (placeholder para futuras implementaciones)

        Args:
            audio_data: Datos del audio
            from_format: Formato original
            to_format: Formato destino

        Returns:
            Optional[bytes]: Audio convertido o None
        """
        # Por ahora, solo retornamos el audio original
        # En una implementación futura se podría usar ffmpeg o similar
        logger.info(f"Conversión de audio {from_format} -> {to_format} (no implementada)")
        return audio_data

    def is_audio_message(self, message_type: str) -> bool:
        """
        Verificar si el tipo de mensaje es audio

        Args:
            message_type: Tipo de mensaje

        Returns:
            bool: True si es mensaje de audio
        """
        return message_type.lower() in ['audio', 'voice', 'audioMessage']

    def get_supported_formats(self) -> list:
        """
        Obtener formatos de audio soportados

        Returns:
            list: Lista de formatos soportados
        """
        return [
            "audio/mpeg",
            "audio/mp3",
            "audio/wav",
            "audio/ogg",
            "audio/mp4",
            "audio/aac",
            "audio/webm"
        ]

    def is_format_supported(self, mime_type: str) -> bool:
        """
        Verificar si el formato está soportado

        Args:
            mime_type: Tipo MIME a verificar

        Returns:
            bool: True si está soportado
        """
        return mime_type in self.get_supported_formats()

    def validate_audio_data(self, audio_data: bytes) -> bool:
        """
        Validar datos de audio

        Args:
            audio_data: Datos del audio

        Returns:
            bool: True si los datos son válidos
        """
        if not audio_data or len(audio_data) == 0:
            return False

        # Verificar tamaño mínimo (1KB) y máximo (25MB)
        min_size = 1024
        max_size = 25 * 1024 * 1024

        return min_size <= len(audio_data) <= max_size