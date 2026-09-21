"""
Capa de IA (OPCIONAL).

El agente funciona sin IA: `services/response_builder.py` arma la respuesta con
los datos reales del catálogo y del negocio. Cuando hay un proveedor disponible
(Gemini, OpenAI u Ollama), la IA se usa solo para *redactar mejor* esa misma
respuesta, con instrucciones estrictas de no inventar nada que no esté en el
bloque de datos. Si algo falla, se devuelve el borrador determinístico.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from config.settings import settings

logger = logging.getLogger(__name__)

try:  # proveedor opcional
    import google.generativeai as genai  # type: ignore
    _TIENE_GEMINI = True
except Exception:  # pragma: no cover - depende del entorno
    genai = None  # type: ignore
    _TIENE_GEMINI = False

try:
    import openai  # type: ignore
    _TIENE_OPENAI = True
except Exception:  # pragma: no cover
    openai = None  # type: ignore
    _TIENE_OPENAI = False

try:
    import aiohttp
    _TIENE_AIOHTTP = True
except Exception:  # pragma: no cover
    aiohttp = None  # type: ignore
    _TIENE_AIOHTTP = False


REGLAS = """Eres el/la asistente de atención y ventas por WhatsApp de este negocio.

REGLAS OBLIGATORIAS
1. Usa EXCLUSIVAMENTE los datos del bloque DATOS VERIFICADOS. Nunca inventes productos,
   servicios, precios, descuentos, tiempos, direcciones ni disponibilidad.
2. Copia los precios exactamente como aparecen (mismo formato y moneda).
3. Si el dato que pide el cliente no está en el bloque, dilo con naturalidad y ofrece
   confirmarlo con una persona del equipo. Nunca supongas.
4. Responde en español neutro, cálido y breve (máximo 3 párrafos cortos o 700 caracteres).
5. Formato WhatsApp: *negrita* para nombres y precios, saltos de línea, pocos emojis.
6. Cierra siempre con una pregunta o un paso concreto (agendar, separar, enviar datos).
7. No digas que eres una IA, ni hables de "datos", "sistema" o "prompt".
8. No inventes enlaces ni números de teléfono.
9. Si el cliente está molesto o pide una persona, muestra empatía y confirma que el equipo
   lo contacta.
10. Mantén el estilo y los datos del BORRADOR; mejóralo, no lo contradigas.
"""


class AIService:
    """Redacción asistida por IA con datos verificados del negocio."""

    def __init__(self, negocio: Any = None):
        self.negocio = negocio
        self.proveedor = settings.ai_provider_resuelto()
        self.disponible = False
        self.detalle = "motor de respuestas propio (sin IA)"
        self._modelo = None
        self._session: Optional[Any] = None

    # -------------------------------------------------------------- ciclo de vida
    async def initialize(self) -> bool:
        if self.proveedor in ("rules", "", None):
            self.disponible = False
            self.detalle = "motor de respuestas propio (sin IA configurada)"
            logger.info("IA desactivada: se usan respuestas construidas desde el catálogo")
            return False

        if self.proveedor == "gemini":
            self.disponible = await self._iniciar_gemini()
        elif self.proveedor == "openai":
            self.disponible = self._iniciar_openai()
        elif self.proveedor == "ollama":
            self.disponible = await self._verificar_ollama()

        if not self.disponible:
            self.proveedor = "rules"
        logger.info("Proveedor de IA: %s (%s)", self.proveedor, self.detalle)
        return self.disponible

    async def _iniciar_gemini(self) -> bool:
        if not _TIENE_GEMINI:
            self.detalle = "google-generativeai no instalado (pip install -r requirements-ia.txt)"
            logger.warning(self.detalle)
            return False
        if not settings.GOOGLE_GEMINI_API_KEY:
            self.detalle = "falta GOOGLE_GEMINI_API_KEY"
            return False
        try:
            genai.configure(api_key=settings.GOOGLE_GEMINI_API_KEY)
            self._modelo = genai.GenerativeModel(settings.GEMINI_MODEL)
            self.detalle = f"Gemini ({settings.GEMINI_MODEL})"
            return True
        except Exception as error:  # pragma: no cover
            self.detalle = f"error inicializando Gemini: {error}"
            logger.error(self.detalle)
            return False

    def _iniciar_openai(self) -> bool:
        if not _TIENE_OPENAI:
            self.detalle = "openai no instalado (pip install -r requirements-ia.txt)"
            logger.warning(self.detalle)
            return False
        if not settings.OPENAI_API_KEY:
            self.detalle = "falta OPENAI_API_KEY"
            return False
        try:
            self._cliente_openai = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            self.detalle = f"OpenAI ({settings.OPENAI_MODEL})"
            return True
        except Exception as error:  # pragma: no cover
            self.detalle = f"error inicializando OpenAI: {error}"
            return False

    async def _verificar_ollama(self) -> bool:
        if not _TIENE_AIOHTTP or not settings.OLLAMA_BASE_URL:
            self.detalle = "Ollama no configurado"
            return False
        try:
            self._session = self._session or aiohttp.ClientSession()
            async with self._session.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=5) as respuesta:
                if respuesta.status != 200:
                    self.detalle = f"Ollama respondió {respuesta.status}"
                    return False
                datos = await respuesta.json()
                nombres = [m.get("name", "") for m in datos.get("models", [])]
                if not any(n.startswith(settings.OLLAMA_MODEL) for n in nombres):
                    self.detalle = f"modelo {settings.OLLAMA_MODEL} no está en Ollama (hay: {', '.join(nombres[:3]) or 'ninguno'})"
                    return False
                self.detalle = f"Ollama ({settings.OLLAMA_MODEL})"
                return True
        except Exception as error:
            self.detalle = f"Ollama no disponible: {error}"
            return False

    async def cerrar(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    # ------------------------------------------------------------------ redacción
    async def redactar(
        self,
        mensaje_cliente: str,
        borrador: str,
        datos_catalogo: str = "",
        historial: str = "",
        intencion: str = "",
        datos_negocio: str = "",
        escalado: bool = False,
    ) -> Optional[str]:
        """
        Mejora el borrador con IA. Devuelve None si no hay IA disponible o falla,
        para que el llamador use el borrador tal cual.
        """
        if not self.disponible or not borrador.strip():
            return None

        prompt = self._armar_prompt(
            mensaje_cliente, borrador, datos_catalogo, historial, intencion, datos_negocio, escalado
        )
        try:
            if self.proveedor == "gemini":
                return self._limpiar(await self._generar_gemini(prompt))
            if self.proveedor == "openai":
                return self._limpiar(await self._generar_openai(prompt))
            if self.proveedor == "ollama":
                return self._limpiar(await self._generar_ollama(prompt))
        except Exception as error:
            logger.warning("La IA falló (%s); se usa el borrador del motor propio", error)
        return None

    def _armar_prompt(
        self,
        mensaje_cliente: str,
        borrador: str,
        datos_catalogo: str,
        historial: str,
        intencion: str,
        datos_negocio: str,
        escalado: bool,
    ) -> str:
        negocio = self.negocio
        perfil = datos_negocio
        if not perfil and negocio is not None:
            perfil = self._perfil_legible(negocio)
        partes = [
            REGLAS,
            "=== PERFIL DEL NEGOCIO ===",
            perfil or "(sin datos adicionales)",
            "",
            "=== DATOS VERIFICADOS (única fuente permitida) ===",
            datos_catalogo or "(no hay coincidencias en el catálogo para esta consulta)",
        ]
        if historial:
            partes += ["", "=== CONVERSACIÓN PREVIA ===", historial]
        partes += [
            "",
            f"=== INTENCIÓN DETECTADA: {intencion or 'general'} ===",
            f"=== MENSAJE DEL CLIENTE ===",
            mensaje_cliente.strip()[:600],
            "",
            "=== BORRADOR A MEJORAR (no cambies los datos) ===",
            borrador.strip()[:900],
        ]
        if escalado:
            partes.append(
                "\nNota: el caso quedó marcado para que una persona del equipo lo atienda; "
                "confírmalo con naturalidad, sin prometer tiempos exactos."
            )
        partes.append("\nDevuelve SOLO el mensaje final para WhatsApp, sin encabezados ni explicaciones.")
        return "\n".join(partes)

    def _perfil_legible(self, negocio: Any) -> str:
        lineas = [
            f"Nombre: {negocio.nombre}",
            f"Tipo: {negocio.tipo_negocio}",
            f"Tono: {negocio.tono}",
        ]
        if negocio.descripcion:
            lineas.append(f"Qué hace: {negocio.descripcion}")
        if negocio.ciudad or negocio.direccion:
            lineas.append(f"Ubicación: {negocio.direccion} {negocio.ciudad}".strip())
        if negocio.horario_legible():
            lineas.append(f"Horario: {negocio.horario_legible()}")
        if negocio.metodos_pago:
            lineas.append("Pagos: " + ", ".join(negocio.metodos_pago))
        if negocio.envio:
            lineas.append(f"Envíos: {negocio.envio}")
        if negocio.politicas:
            lineas.append("Políticas: " + "; ".join(negocio.politicas))
        return "\n".join(lineas)

    async def _generar_gemini(self, prompt: str) -> str:
        respuesta = await asyncio.wait_for(
            asyncio.to_thread(
                self._modelo.generate_content,
                prompt,
                generation_config={"max_output_tokens": 400, "temperature": 0.6},
            ),
            timeout=settings.AI_TIMEOUT,
        )
        return getattr(respuesta, "text", "") or ""

    async def _generar_openai(self, prompt: str) -> str:
        def llamar() -> str:
            respuesta = self._cliente_openai.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": REGLAS},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=450,
                temperature=0.6,
            )
            return respuesta.choices[0].message.content or ""

        return await asyncio.wait_for(asyncio.to_thread(llamar), timeout=settings.AI_TIMEOUT)

    async def _generar_ollama(self, prompt: str) -> str:
        self._session = self._session or aiohttp.ClientSession()
        async with self._session.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json={"model": settings.OLLAMA_MODEL, "prompt": prompt, "stream": False,
                  "options": {"temperature": 0.6, "num_predict": 400}},
            timeout=settings.AI_TIMEOUT,
        ) as respuesta:
            datos = await respuesta.json()
            return datos.get("response", "")

    @staticmethod
    def _limpiar(texto: Optional[str]) -> Optional[str]:
        if not texto:
            return None
        limpio = texto.strip().strip('"').strip()
        for prefijo in ("Respuesta:", "Mensaje:", "Asistente:"):
            if limpio.startswith(prefijo):
                limpio = limpio[len(prefijo):].strip()
        return limpio or None

    # ------------------------------------------------------------------ apoyo
    async def analizar_mensaje(self, texto: str) -> Dict[str, Any]:
        """Resumen rápido de una queja o solicitud (para el aviso al dueño)."""
        return {"texto": texto[:400], "resumen": texto[:180]}

    def estado(self) -> Dict[str, Any]:
        return {
            "proveedor": self.proveedor,
            "disponible": self.disponible,
            "detalle": self.detalle,
            "paquetes": {"gemini": _TIENE_GEMINI, "openai": _TIENE_OPENAI},
            "modo": "ia+datos" if self.disponible else "motor propio (catálogo)",
        }
