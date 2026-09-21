"""
Agente de ventas: decide qué responder a cada mensaje.

Flujo de un mensaje:
   payload -> MensajeEntrante -> (transcripción si es audio) -> intención
   -> búsqueda en el catálogo del negocio -> respuesta construida con datos reales
   -> (opcional) mejorada con IA -> plan de acciones para el puente WhatsApp

El agente NO habla con WhatsApp: devuelve acciones (texto, imagen, aviso al
dueño...) y el puente Baileys las ejecuta. Así el mismo motor sirve para el
simulador web, para Baileys o para cualquier otro canal.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

from config.business import Negocio
from config.settings import settings
from core.memoria import Conversacion, Memoria
from models.catalog import CatalogoItem
from models.message import MensajeEntrante
from services.ai_service import AIService
from services.audio_service import AudioService
from services.catalog_service import CatalogoService
from services.intent_service import Intencion, IntentService
from services.response_builder import ConstructorRespuestas, Respuesta
from services.scraping_service import ScrapingService
from utils.helpers import calcular_metricas_negocio, emoji_para, resumir_para_aviso

logger = logging.getLogger(__name__)

LIMITE_MENSAJES = 12          # mensajes por chat
VENTANA_SEGUNDOS = 60         # ventana del límite anti-spam
CACHE_IDS = 4000


class _Limitador:
    """Freno simple anti-spam por chat."""

    def __init__(self, limite: int = LIMITE_MENSAJES, ventana: int = VENTANA_SEGUNDOS):
        self.limite = limite
        self.ventana = ventana
        self._marcas: Dict[str, Deque[float]] = defaultdict(deque)
        self._avisados: Dict[str, float] = {}

    def excedido(self, chat_id: str) -> bool:
        ahora = time.time()
        marcas = self._marcas[chat_id]
        while marcas and ahora - marcas[0] > self.ventana:
            marcas.popleft()
        marcas.append(ahora)
        return len(marcas) > self.limite

    def debe_avisar(self, chat_id: str) -> bool:
        """Avisa una sola vez cada 5 minutos de que estamos saturados."""
        ahora = time.time()
        ultimo = self._avisados.get(chat_id, 0)
        if ahora - ultimo > 300:
            self._avisados[chat_id] = ahora
            return True
        return False


class SalesAgent:
    """Motor de respuestas multi-rubro."""

    def __init__(self, ruta_negocio: Optional[Path] = None):
        self.ruta_negocio = Path(ruta_negocio or settings.BUSINESS_CONFIG)
        self.negocio: Negocio = Negocio.cargar(self.ruta_negocio)
        self.catalogo = CatalogoService(self.negocio)
        self.intenciones = IntentService(self.negocio, self.catalogo)
        self.redactor = ConstructorRespuestas(self.negocio, self.catalogo)
        self.memoria = Memoria()
        self.ia = AIService(self.negocio)
        self.audio = AudioService()
        self.scraping = ScrapingService()
        self.limitador = _Limitador()
        self.ruta_importado = settings.BASE_DIR / "config" / "catalogo-importado.json"
        self._cargar_catalogo_importado()

        self.is_running = False
        self.iniciado_en = time.time()
        self.ultima_revision = 0.0
        self.ids_vistos: set[str] = set()
        self.orden_ids: Deque[str] = deque()
        self.metricas: Dict[str, Any] = {
            "mensajes_recibidos": 0,
            "respuestas_enviadas": 0,
            "ignorados": 0,
            "errores": 0,
            "por_intencion": {},
            "ultimo_mensaje": "",
            "ultimo_error": "",
            "escalados": 0,
            "eventos_whatsapp": [],
        }

    # ------------------------------------------------------------ ciclo de vida
    async def initialize(self) -> bool:
        logger.info("Iniciando agente para el negocio: %s", self.negocio.nombre)
        try:
            await self.ia.initialize()
        except Exception as error:  # nunca debe tumbar el arranque
            logger.error("La IA no pudo inicializarse: %s", error)

        if not self.negocio.catalogo:
            logger.warning(
                "El negocio no tiene catálogo cargado (%s). Revisa config/negocio.json "
                "o copia un ejemplo de negocios/ejemplos/", self.ruta_negocio,
            )
        logger.info(
            "Catálogo listo: %s productos, %s servicios",
            sum(1 for i in self.negocio.catalogo if not i.es_servicio),
            sum(1 for i in self.negocio.catalogo if i.es_servicio),
        )
        self.is_running = True
        return True

    async def start(self) -> None:
        if not self.is_running:
            await self.initialize()

    async def stop(self) -> None:
        self.is_running = False
        await self.ia.cerrar()
        await self.scraping.cerrar()
        logger.info("Agente detenido")

    # ------------------------------------------------------------- recarga en vivo
    def recargar_si_cambio(self, forzar: bool = False) -> bool:
        """Vuelve a leer negocio.json cuando cambia (editas el JSON y ya)."""
        try:
            if not self.ruta_negocio.exists():
                return False
            version = self.ruta_negocio.stat().st_mtime
            if not forzar and version <= (self.negocio.version_archivo or 0):
                return False
            if forzar or version != self.negocio.version_archivo:
                self.negocio = Negocio.cargar(self.ruta_negocio)
                self.catalogo.recargar(self.negocio)
                self.intenciones = IntentService(self.negocio, self.catalogo)
                self.redactor = ConstructorRespuestas(self.negocio, self.catalogo)
                self.ia.negocio = self.negocio
                logger.info(
                    "Negocio recargado desde %s (%s ítems en el catálogo)",
                    self.ruta_negocio.name, len(self.negocio.catalogo),
                )
                return True
        except Exception as error:
            logger.error("No se pudo recargar el negocio: %s", error)
        return False

    def _revisar_periodicamente(self) -> None:
        if time.time() - self.ultima_revision > 5:
            self.ultima_revision = time.time()
            self.recargar_si_cambio()

    # ------------------------------------------------- catálogo desde la web
    def _cargar_catalogo_importado(self) -> None:
        """Suma al catálogo los ítems que se importaron de la web (si hay)."""
        if not self.ruta_importado.exists():
            return
        try:
            import json

            datos = json.loads(self.ruta_importado.read_text(encoding="utf-8"))
            items = [CatalogoItem.from_dict(i) for i in datos.get("items", [])]
        except Exception as error:
            logger.warning("No pude leer %s: %s", self.ruta_importado.name, error)
            return
        agregados = self._fusionar_items(items)
        if agregados:
            self.catalogo.recargar(self.negocio)
            logger.info("Catálogo importado de la web: %s ítems", agregados)

    def _fusionar_items(self, items: List[CatalogoItem]) -> int:
        """Agrega ítems nuevos sin duplicar los que ya existen (por nombre)."""
        from utils.texto import normalizar

        existentes = {normalizar(i.nombre) for i in self.negocio.catalogo}
        agregados = 0
        for item in items:
            if normalizar(item.nombre) in existentes:
                continue
            self.negocio.catalogo.append(item)
            existentes.add(normalizar(item.nombre))
            agregados += 1
        return agregados

    async def importar_catalogo_web(self, guardar: bool = True) -> Dict[str, Any]:
        """
        Refresca el catálogo desde las fuentes web que declara el negocio
        (`fuentes_scraping` en config/negocio.json). Es opcional y explícito:
        nunca sobreescribe precios que ya tengas cargados a mano.
        """
        if not self.negocio.fuentes_scraping:
            return {"ok": False, "motivo": "el negocio no declara 'fuentes_scraping'"}
        resultado = await self.scraping.importar_fuentes(self.negocio.fuentes_scraping)
        if not resultado.get("ok"):
            return resultado

        agregados = self._fusionar_items(resultado.get("items", []))
        self.catalogo.recargar(self.negocio)

        if guardar and agregados:
            try:
                import json

                self.ruta_importado.parent.mkdir(parents=True, exist_ok=True)
                self.ruta_importado.write_text(
                    json.dumps(
                        {"importado_en": time.time(),
                         "items": [i.to_dict() for i in self.negocio.catalogo if i.fuente.startswith("scraping")]},
                        ensure_ascii=False, indent=2,
                    ),
                    encoding="utf-8",
                )
            except OSError as error:
                logger.warning("No pude guardar el catálogo importado: %s", error)

        return {
            "ok": True,
            "nuevos": agregados,
            "total_catalogo": len(self.negocio.catalogo),
            "detalle": resultado.get("detalle", []),
        }

    # ------------------------------------------------------------------ entrada
    async def procesar_mensaje(self, payload: Dict[str, Any], canal: str = "baileys") -> Dict[str, Any]:
        """
        Punto de entrada único. Devuelve:
          {ok, ignorado, motivo, intenciones, acciones[], debug{}}
        """
        self._revisar_periodicamente()

        try:
            mensaje = MensajeEntrante.desde_dict(payload, canal=canal)
        except Exception as error:
            self.metricas["errores"] += 1
            self.metricas["ultimo_error"] = str(error)
            logger.error("Payload inválido: %s", error)
            return self._salida(ignorado=True, motivo=f"payload inválido: {error}")

        self.metricas["mensajes_recibidos"] += 1

        # 1) duplicados: se marca UNA sola vez por mensaje
        if mensaje.id:
            if mensaje.id in self.ids_vistos:
                return self._salida(ignorado=True, motivo="mensaje duplicado")
            self.ids_vistos.add(mensaje.id)
            self.orden_ids.append(mensaje.id)
            if len(self.orden_ids) > CACHE_IDS:
                self.ids_vistos.discard(self.orden_ids.popleft())

        # 2) validación
        valido, motivo = mensaje.es_valido()
        if not valido:
            self.metricas["ignorados"] += 1
            return self._salida(ignorado=True, motivo=motivo)

        # 3) anti-spam
        if self.limitador.excedido(mensaje.chat_id):
            self.metricas["ignorados"] += 1
            if self.limitador.debe_avisar(mensaje.chat_id):
                return self._salida(
                    acciones=[{"tipo": "texto", "texto": "Recibí varios mensajes seguidos 🙌 Voy a responderlos en orden, dame un momento."}],
                    intenciones=["limite"],
                )
            return self._salida(ignorado=True, motivo="demasiados mensajes seguidos")

        # 4) audios
        texto = mensaje.texto
        if mensaje.es_audio:
            texto, motivo_audio = await self.audio.transcribir_media(mensaje.media)
            if not texto:
                logger.info("Audio sin transcribir (%s)", motivo_audio)
                conv = self.memoria.obtener(mensaje.chat_id)
                respuesta_audio = Respuesta(
                    texto=(
                        "Recibí tu nota de voz 🎧 pero no pude escucharla bien. "
                        "¿Me escribes tu pregunta en un mensaje de texto, por favor?"
                    ),
                    intencion="audio_no_leido",
                )
                acciones = self._planear_acciones(mensaje, respuesta_audio, conv)
                self.metricas["respuestas_enviadas"] += 1
                return self._salida(acciones=acciones, intenciones=["audio_no_leido"],
                                    debug={"motivo_audio": motivo_audio, "negocio": self.negocio.nombre})

        self.metricas["ultimo_mensaje"] = f"{mensaje.nombre}: {texto[:80]}"

        # 5) respuesta
        try:
            respuesta, intencion, extra = await self._decidir(mensaje, texto)
        except Exception as error:
            self.metricas["errores"] += 1
            self.metricas["ultimo_error"] = str(error)
            logger.exception("Error construyendo la respuesta")
            return self._salida(ignorado=True, motivo=f"error interno: {error}")

        if not respuesta.es_util():
            self.metricas["ignorados"] += 1
            return self._salida(ignorado=True, motivo="sin respuesta útil")

        conv = self.memoria.obtener(mensaje.chat_id)
        acciones = self._planear_acciones(mensaje, respuesta, conv)

        # 6) memoria
        conv.ultima_intencion = intencion.nombre
        self.memoria.capturar_datos(mensaje.chat_id, nombre=mensaje.nombre if mensaje.nombre != "Cliente" else None)
        if respuesta.escalar:
            self.memoria.marcar_escalado(mensaje.chat_id, avisado=respuesta.avisar_dueno)
            self.metricas["escalados"] += 1
        self.memoria.guardar_turno(mensaje.chat_id, texto, respuesta.texto)

        self.metricas["respuestas_enviadas"] += 1
        self.metricas["por_intencion"][intencion.nombre] = self.metricas["por_intencion"].get(intencion.nombre, 0) + 1

        logger.info(
            "↩️  %s | intención=%s | ítem=%s | %s",
            mensaje.numero or mensaje.chat_id, intencion.nombre,
            respuesta.item.nombre if respuesta.item else "-", resumir_para_aviso(respuesta.texto, 70),
        )

        return self._salida(
            acciones=acciones,
            intenciones=[intencion.nombre],
            debug={
                "negocio": self.negocio.nombre,
                "item": respuesta.item.to_dict() if respuesta.item else None,
                "puntajes": extra.get("puntajes", []),
                "ia": extra.get("ia", "motor-propio"),
                "escalar": respuesta.escalar,
                "sugerencias": respuesta.sugerencias,
                "texto_respuesta": respuesta.texto,
            },
        )

    # ---------------------------------------------------------------- decisiones
    async def _decidir(self, mensaje: MensajeEntrante, texto: str) -> tuple[Respuesta, Intencion, Dict[str, Any]]:
        conv = self.memoria.obtener(mensaje.chat_id)
        presupuesto = mensaje.presupuesto()
        if presupuesto:
            self.memoria.capturar_datos(mensaje.chat_id, presupuesto=presupuesto)

        intencion = self.intenciones.detectar(texto, presupuesto=presupuesto)

        # Matices: si piden precio de algo concreto, mostramos su ficha completa
        if intencion.nombre == "precio":
            mejor = self.catalogo.mejor(texto, presupuesto=presupuesto)
            if mejor:
                intencion = Intencion(
                    "consulta_item", 0.9,
                    {"item": mejor.item, "resultados": [mejor], "presupuesto": presupuesto},
                )

        # Si dio un presupuesto y hay varias opciones válidas de líneas distintas,
        # conviene listar alternativas en vez de empujar un solo ítem.
        if presupuesto and intencion.nombre in {"consulta_item", "sugerencia"}:
            candidatos = [r for r in IntentService.resultados_de(intencion) if r.coincide_fuerte]
            if len(candidatos) >= 3 and len({r.item.categoria for r in candidatos}) > 1:
                intencion = Intencion(
                    "sugerencia", 0.75,
                    {"resultados": candidatos[: settings.MAX_ITEMS_IN_REPLY], "presupuesto": presupuesto},
                )

        respuesta = self.redactor.construir(intencion, texto, conv)
        extra: Dict[str, Any] = {}

        resultados = IntentService.resultados_de(intencion)
        if resultados:
            extra["puntajes"] = [
                {"item": r.item.nombre, "puntaje": r.puntaje, "razones": r.razones[:4]}
                for r in resultados[:5]
            ]

        # La IA (si existe) solo reescribe el texto; los datos vienen del catálogo
        if self.ia.disponible and respuesta.texto:
            datos = self.catalogo.contexto_para_ia(resultados) if resultados else ""
            if not datos and respuesta.item:
                datos = self.catalogo.contexto_para_ia([type("R", (), {"item": respuesta.item})()])
            mejorado = await self.ia.redactar(
                mensaje_cliente=texto,
                borrador=respuesta.texto,
                datos_catalogo=datos,
                historial=conv.contexto_texto(),
                intencion=intencion.nombre,
                escalado=respuesta.escalar,
            )
            if mejorado:
                respuesta.texto = mejorado
                extra["ia"] = self.ia.proveedor
            else:
                extra["ia"] = f"{self.ia.proveedor}(sin usar)"
        else:
            extra["ia"] = "motor-propio"

        return respuesta, intencion, extra

    # ------------------------------------------------------------------ acciones
    def _planear_acciones(self, mensaje: MensajeEntrante, respuesta: Respuesta, conv: Conversacion) -> List[Dict[str, Any]]:
        """Convierte la respuesta en acciones ejecutables por el puente."""
        acciones: List[Dict[str, Any]] = []

        if settings.SEND_PRESENCE:
            acciones.append({"tipo": "leer"})
            acciones.append({"tipo": "presencia", "estado": "composing", "ms": 700})

        acciones.append({"tipo": "texto", "texto": respuesta.texto})

        # Imagen del ítem (si el negocio la definió)
        for accion in respuesta.acciones:
            if accion.get("tipo") == "imagen" and accion.get("url"):
                acciones.append(accion)

        # Avisos al dueño / equipo: se envían siempre y el puente decide a qué
        # número (o los registra en el log si no hay dueño configurado).
        for accion in respuesta.acciones:
            if accion.get("tipo") == "notificar" and accion.get("texto"):
                destino = self.negocio.numero_escalado or settings.HUMAN_ESCALATION_NUMBER
                aviso = {**accion}
                if destino:
                    aviso["numero"] = destino
                else:
                    logger.info(
                        "Aviso interno (configura HUMAN_ESCALATION_NUMBER para recibirlo en WhatsApp): %s",
                        resumir_para_aviso(accion["texto"], 140),
                    )
                acciones.append(aviso)

        # Presencia extra definida por la respuesta (p. ej. tras escalar)
        for accion in respuesta.acciones:
            if accion.get("tipo") == "presencia":
                acciones.append(accion)

        return acciones

    def _salida(
        self,
        acciones: Optional[List[Dict[str, Any]]] = None,
        intenciones: Optional[List[str]] = None,
        ignorado: bool = False,
        motivo: str = "",
        debug: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {
            "ok": True,
            "ignorado": ignorado,
            "motivo": motivo,
            "intenciones": intenciones or [],
            "acciones": acciones or [] if not ignorado else [],
            "debug": debug or {"negocio": self.negocio.nombre},
        }

    # ------------------------------------------------------------------ estado
    def registrar_evento_whatsapp(self, evento: str, datos: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        registro = {"evento": evento, "datos": datos or {}, "cuando": time.time()}
        eventos = self.metricas.setdefault("eventos_whatsapp", [])
        eventos.append(registro)
        if len(eventos) > 20:
            del eventos[:-20]
        logger.info("Evento del puente WhatsApp: %s %s", evento, datos or "")
        return registro

    def estado(self) -> Dict[str, Any]:
        metricas_negocio = calcular_metricas_negocio(self.negocio.catalogo)
        return {
            "is_running": self.is_running,
            "negocio": {
                "nombre": self.negocio.nombre,
                "tipo": self.negocio.tipo_negocio,
                "ciudad": self.negocio.ciudad,
                "archivo": str(self.ruta_negocio),
                "abierto_ahora": self.negocio.esta_abierto(),
                "horario": self.negocio.horario_legible(),
                "categorias": self.negocio.categorias_con_items(),
            },
            "catalogo": metricas_negocio,
            "ia": self.ia.estado(),
            "audio": self.audio.estado(),
            "scraping": {
                "disponible": self.scraping.disponible,
                "fuentes": len(self.negocio.fuentes_scraping),
                "importados": sum(1 for i in self.negocio.catalogo if i.fuente.startswith("scraping")),
            },
            "memoria": self.memoria.estadisticas(),
            "metricas": {
                k: v for k, v in self.metricas.items() if k != "eventos_whatsapp"
            },
            "ultimos_eventos_whatsapp": self.metricas.get("eventos_whatsapp", [])[-5:],
            "uptime_segundos": round(time.time() - self.iniciado_en),
        }

    # ----------------------------------------------------------- utilidades API
    def buscar_en_catalogo(self, consulta: str, limite: int = 5) -> List[Dict[str, Any]]:
        resultados = self.catalogo.buscar(consulta, limite=limite)
        salida = []
        for r in resultados:
            datos = r.item.to_dict()
            datos["puntaje"] = r.puntaje
            datos["razones"] = r.razones
            datos["emoji"] = emoji_para(r.item)
            salida.append(datos)
        return salida

    def obtener_item(self, id_item: str) -> Optional[CatalogoItem]:
        return self.catalogo.por_id(id_item)

    def limpiar_conversacion(self, chat_id: Optional[str] = None) -> None:
        self.memoria.limpiar(chat_id)
