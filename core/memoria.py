"""
Memoria de conversación.

Guarda por chat: los últimos intercambios, el último ítem del catálogo del que
se habló, datos que el cliente fue soltando (nombre, ciudad, fecha deseada) y si
la conversación ya se pasó a un humano. Con esto las respuestas de seguimiento
tienen sentido ("sí" después de ofrecer algo, "¿y en otro color?").
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from config.settings import settings


@dataclass
class Conversacion:
    chat_id: str
    historial: List[Dict[str, str]] = field(default_factory=list)
    ultimo_item_id: Optional[str] = None
    ultima_intencion: str = ""
    datos: Dict[str, Any] = field(default_factory=dict)
    escalado: bool = False
    avisado_al_dueno: bool = False
    primer_contacto: float = field(default_factory=time.time)
    ultima_actividad: float = field(default_factory=time.time)
    mensajes_cliente: int = 0

    def agregar(self, mensaje: str, respuesta: str) -> None:
        self.historial.append({"cliente": mensaje, "agente": respuesta})
        limite = settings.CONTEXT_WINDOW_LENGTH
        if len(self.historial) > limite:
            self.historial = self.historial[-limite:]
        self.ultima_actividad = time.time()
        self.mensajes_cliente += 1

    def contexto_texto(self, maximo: int = 6) -> str:
        if not self.historial:
            return ""
        lineas = []
        for turno in self.historial[-maximo:]:
            lineas.append(f"Cliente: {turno.get('cliente','')[:160]}")
            lineas.append(f"Negocio: {turno.get('respuesta','')[:200]}")
        return "\n".join(lineas)

    def es_cliente_conocido(self) -> bool:
        return bool(self.datos.get("nombre")) or self.mensajes_cliente > 2


class Memoria:
    """Almacén en memoria (suficiente para una instancia; se puede cambiar por Redis)."""

    def __init__(self, max_conversaciones: int = 2000, ttl_horas: float = 24.0):
        self.conversaciones: Dict[str, Conversacion] = {}
        self.max_conversaciones = max_conversaciones
        self.ttl_segundos = ttl_horas * 3600

    def obtener(self, chat_id: str) -> Conversacion:
        self._limpiar()
        if chat_id not in self.conversaciones:
            self.conversaciones[chat_id] = Conversacion(chat_id=chat_id)
        return self.conversaciones[chat_id]

    def guardar_turno(self, chat_id: str, mensaje: str, respuesta: str) -> None:
        conv = self.obtener(chat_id)
        conv.agregar(mensaje, respuesta)

    def capturar_datos(self, chat_id: str, **datos: Any) -> None:
        conv = self.obtener(chat_id)
        for clave, valor in datos.items():
            if valor:
                conv.datos.setdefault(clave, valor)

    def marcar_escalado(self, chat_id: str, avisado: bool = False) -> None:
        conv = self.obtener(chat_id)
        conv.escalado = True
        if avisado:
            conv.avisado_al_dueno = True

    def limpiar(self, chat_id: Optional[str] = None) -> None:
        if chat_id:
            self.conversaciones.pop(chat_id, None)
        else:
            self.conversaciones.clear()

    def _limpiar(self) -> None:
        ahora = time.time()
        expiradas = [
            chat for chat, conv in self.conversaciones.items()
            if ahora - conv.ultima_actividad > self.ttl_segundos
        ]
        for chat in expiradas:
            self.conversaciones.pop(chat, None)
        if len(self.conversaciones) > self.max_conversaciones:
            ordenadas = sorted(self.conversaciones.items(), key=lambda kv: kv[1].ultima_actividad)
            for chat, _ in ordenadas[: len(self.conversaciones) - self.max_conversaciones]:
                self.conversaciones.pop(chat, None)

    def estadisticas(self) -> Dict[str, Any]:
        return {
            "conversaciones": len(self.conversaciones),
            "escaladas": sum(1 for c in self.conversaciones.values() if c.escalado),
            "clientes_con_datos": sum(1 for c in self.conversaciones.values() if c.datos),
        }
