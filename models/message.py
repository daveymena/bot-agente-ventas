"""
Modelo de mensaje entrante.

Se adapta a cualquier transporte: el puente Baileys envía un payload
normalizado, y aquí también se aceptan los formatos antiguos (Evolution API /
n8n en español) para no romper integraciones previas ni los scripts de prueba.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from utils.texto import normalizar, parsear_numero

TIPOS_TEXTO = {"texto", "text", "boton", "lista", "conversacion", "conversación"}
TIPOS_MEDIA = {"audio", "imagen", "image", "video", "documento", "document", "sticker", "ubicacion"}


@dataclass
class MensajeEntrante:
    """Mensaje ya normalizado, listo para el motor de respuestas."""

    id: str = ""
    chat_id: str = ""
    numero: str = ""
    texto: str = ""
    tipo: str = "texto"
    nombre: str = "Cliente"
    es_grupo: bool = False
    from_me: bool = False
    participante: str = ""
    timestamp: Optional[int] = None
    media: Dict[str, Any] = field(default_factory=dict)
    media_error: str = ""
    canal: str = "baileys"
    metadatos: Dict[str, Any] = field(default_factory=dict)
    recibido_en: datetime = field(default_factory=datetime.now)

    # ------------------------------------------------------------ propiedades
    @property
    def es_texto(self) -> bool:
        return self.tipo in TIPOS_TEXTO and bool(self.texto.strip())

    @property
    def es_audio(self) -> bool:
        return self.tipo == "audio"

    @property
    def texto_normalizado(self) -> str:
        return normalizar(self.texto)

    @property
    def id_unico(self) -> str:
        return self.id or f"{self.chat_id}:{hash(self.texto)}:{self.timestamp}"

    def presupuesto(self) -> Optional[float]:
        """
        Detecta un presupuesto/precio máximo mencionado por el cliente:
        "tengo 2 millones", "hasta 500 mil", "menos de 80.000".
        """
        t = normalizar(self.texto)
        marcadores = ["tengo", "presupuesto", "hasta", "maximo", "máximo", "menos de",
                      "no mas de", "no más de", "rango de", "cuento con", "dispongo de"]
        if not any(m in t for m in ["tengo", "presupuesto", "hasta", "maximo", "menos de",
                                    "no mas de", "rango", "cuento con", "dispongo",
                                    "mil", "millon", "millón"]) and "$" not in self.texto:
            return None
        if not any(m in t for m in marcadores + ["$"]) and not re.search(r"\d{3,}", t):
            return None
        return parsear_numero(self.texto)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "chat_id": self.chat_id,
            "numero": self.numero,
            "texto": self.texto,
            "tipo": self.tipo,
            "nombre": self.nombre,
            "es_grupo": self.es_grupo,
            "from_me": self.from_me,
            "participante": self.participante,
            "timestamp": self.timestamp,
            "canal": self.canal,
            "media_error": self.media_error,
            "tiene_media": bool(self.media),
            "recibido_en": self.recibido_en.isoformat(),
        }

    # --------------------------------------------------------------- fábricas
    @classmethod
    def desde_bridge(cls, datos: Dict[str, Any]) -> "MensajeEntrante":
        """Payload del puente Baileys (contrato v2)."""
        if not isinstance(datos, dict):
            raise TypeError("El mensaje debe ser un objeto JSON")
        numero = str(datos.get("numero") or "").strip()
        chat_id = str(datos.get("chat_id") or "").strip()
        if not chat_id and numero:
            chat_id = f"{re.sub(r'[^0-9]', '', numero)}@s.whatsapp.net"
        return cls(
            id=str(datos.get("id") or ""),
            chat_id=chat_id,
            numero=numero or re.sub(r"[^0-9]", "", chat_id.split("@")[0]),
            texto=str(datos.get("texto") or datos.get("text") or "").strip(),
            tipo=str(datos.get("tipo") or "texto").lower(),
            nombre=str(datos.get("nombre") or datos.get("pushName") or "Cliente").strip() or "Cliente",
            es_grupo=bool(datos.get("es_grupo") or str(chat_id).endswith("@g.us")),
            from_me=bool(datos.get("from_me")),
            participante=str(datos.get("participante") or ""),
            timestamp=datos.get("timestamp"),
            media=datos.get("media") if isinstance(datos.get("media"), dict) else {},
            media_error=str(datos.get("media_error") or ""),
            canal=str(datos.get("canal") or "baileys"),
            metadatos={k: v for k, v in datos.items() if k not in {
                "id", "chat_id", "numero", "texto", "text", "tipo", "nombre", "es_grupo",
                "from_me", "participante", "timestamp", "media", "media_error", "canal"}},
        )

    @classmethod
    def desde_webhook_legado(cls, datos: Dict[str, Any]) -> "MensajeEntrante":
        """
        Formatos antiguos: Evolution API (v1/v2) y el workflow de n8n en español.
        Se mantiene para no romper integraciones que ya existan.
        """
        def buscar(*rutas: str) -> Any:
            for ruta in rutas:
                actual: Any = datos
                for parte in ruta.split("."):
                    if isinstance(actual, dict) and parte in actual:
                        actual = actual[parte]
                    else:
                        actual = None
                        break
                if actual not in (None, "", "nulo"):
                    return actual
            return None

        # Evolution API v2: {event, instance, data:{key:{remoteJid,id,fromMe}, message:{...}, pushName}}
        data = datos.get("data") if isinstance(datos.get("data"), dict) else {}
        if "key" in data or "message" in data:
            key = data.get("key") or {}
            mensaje = data.get("message") or {}
            texto = (
                mensaje.get("conversation")
                or (mensaje.get("extendedTextMessage") or {}).get("text")
                or (mensaje.get("imageMessage") or {}).get("caption")
                or (mensaje.get("videoMessage") or {}).get("caption")
                or (mensaje.get("buttonsResponseMessage") or {}).get("selectedDisplayText")
                or (mensaje.get("listResponseMessage") or {}).get("title")
                or ""
            )
            if mensaje.get("audioMessage"):
                tipo = "audio"
            elif mensaje.get("imageMessage"):
                tipo = "imagen"
            else:
                tipo = "texto"
            jid = str(key.get("remoteJid") or "")
            return cls(
                id=str(key.get("id") or ""),
                chat_id=jid,
                numero=re.sub(r"[^0-9]", "", jid.split("@")[0]),
                texto=str(texto).strip(),
                tipo=tipo,
                nombre=str(data.get("pushName") or "Cliente"),
                es_grupo=jid.endswith("@g.us"),
                from_me=bool(key.get("fromMe")),
                participante=str(key.get("participant") or ""),
                timestamp=data.get("messageTimestamp"),
                canal="legado",
                metadatos={"crudo": datos},
            )

        # Formato n8n en español
        return cls(
            id=str(buscar("body.data.identificación", "body.data.id", "data.id") or ""),
            chat_id=str(buscar("body.data.Jid remoto", "body.data.remoteJid", "data.remoteJid") or ""),
            numero=re.sub(
                r"[^0-9]", "",
                str(buscar("body.data.Jid remoto", "body.data.remoteJid", "data.remoteJid") or "").split("@")[0],
            ),
            texto=str(
                buscar(
                    "body.data.mensaje.conversación", "body.data.message.conversation",
                    "body.data.contenido", "data.message.conversation", "data.contenido",
                ) or ""
            ).strip(),
            tipo=str(buscar("body.data.tipo de mensaje", "body.data.messageType", "data.messageType") or "texto").lower(),
            nombre=str(buscar("body.data.nombrePush", "body.data.pushName", "data.pushName") or "Cliente"),
            from_me=bool(buscar("body.data.es de mí", "body.data.fromMe", "data.fromMe") or False),
            canal="legado",
            metadatos={"crudo": datos},
        )

    @classmethod
    def desde_dict(cls, datos: Dict[str, Any], canal: str = "baileys") -> "MensajeEntrante":
        """Autodetecta el formato del payload entrante."""
        # 1) payload ya normalizado (lo que espera el puente Baileys)
        claves_propias = {"texto", "chat_id", "numero", "tipo"}
        if claves_propias & set(datos.keys()) and not any(
            k in datos for k in ("body", "data", "event")
        ):
            return cls.desde_bridge({**datos, "canal": canal})
        # 2) bridges con envoltorio {mensaje: {...}}
        if isinstance(datos.get("mensaje"), dict):
            return cls.desde_bridge({**datos["mensaje"], "canal": canal})
        # 3) formatos previos (Evolution / n8n)
        return cls.desde_webhook_legado(datos)

    # --------------------------------------------------------------- validación
    def es_valido(self) -> tuple[bool, str]:
        if not self.chat_id:
            return False, "sin chat de destino"
        if self.es_grupo:
            return False, "mensaje de grupo"
        if self.from_me:
            return False, "mensaje propio"

        es_media = self.tipo in TIPOS_MEDIA
        if not self.texto.strip() and not self.media and not es_media:
            return False, "mensaje vacío"
        if self.texto.strip() and len(self.texto.strip()) < 2 and not es_media:
            return False, "mensaje demasiado corto"
        # Un audio/imagen que no se pudo descargar sigue siendo un mensaje real:
        # se le responde pidiendo que lo reenvíe o lo escriba.
        return True, ""


# Compatibilidad con el nombre anterior
WhatsAppMessage = MensajeEntrante
