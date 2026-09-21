"""
Constructor de respuestas: el corazón de "responder según los productos y
servicios del negocio".

Cada intención tiene su plantilla, y todas se alimentan del perfil del negocio
(nombre, horarios, ubicación, políticas, métodos de pago...) y del catálogo real
(precios, disponibilidad, duración, imágenes). Nunca inventa datos: si algo no
está en el catálogo o en el perfil, no aparece en la respuesta.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from config.business import Negocio
from config.settings import settings
from core.memoria import Conversacion
from models.catalog import CatalogoItem
from services.catalog_service import CatalogoService, Resultado
from services.intent_service import Intencion
from utils.texto import normalizar, recortar, titulo, unir

logger = logging.getLogger(__name__)

# Ciudades que el agente reconoce al hablar de envíos/cobertura (ampliable desde
# el JSON del negocio con "ciudades_cobertura").
CIUDADES_CONOCIDAS = {
    "bogota", "medellin", "cali", "barranquilla", "cartagena", "bucaramanga", "cucuta",
    "pereira", "manizales", "armenia", "ibague", "villavicencio", "pasto", "neiva",
    "popayan", "monteria", "sincelejo", "valledupar", "santa marta", "tunja", "quibdo",
    "riohacha", "yopal", "mocoa", "florencia", "arauca", "san andres", "palmira",
    "yumbo", "jamundi", "candelaria", "tulua", "buenaventura", "buga", "cartago",
    "guadalajara de buga", "roldanillo", "pradera", "florida", "dagua", "la cumbre",
    "medellin", "bello", "itagui", "envigado", "sabaneta", "rionegro", "soacha",
    "chia", "zipaquira", "facatativa", "mosquera", "funza", "madrid", "cota",
}


@dataclass
class Respuesta:
    """Respuesta lista para enviar (texto + acciones opcionales)."""

    texto: str = ""
    intencion: str = ""
    item: Optional[CatalogoItem] = None
    acciones: List[Dict[str, Any]] = field(default_factory=list)
    escalar: bool = False
    avisar_dueno: bool = False
    notas: str = ""
    sugerencias: List[str] = field(default_factory=list)

    def agregar_imagen(self, item: Optional[CatalogoItem]) -> None:
        if item and item.imagen:
            self.acciones.append({
                "tipo": "imagen",
                "url": item.imagen,
                "caption": f"{item.nombre} · {item.precio_legible()}",
            })

    def es_util(self) -> bool:
        return bool(self.texto.strip())


class ConstructorRespuestas:
    """Genera el texto de la respuesta según la intención y el negocio."""

    def __init__(self, negocio: Negocio, catalogo: CatalogoService):
        self.negocio = negocio
        self.catalogo = catalogo

    # ------------------------------------------------------------------ público
    def construir(self, intencion: Intencion, mensaje_texto: str, conversacion: Conversacion) -> Respuesta:
        manejador = getattr(self, f"_r_{intencion.nombre}", None)
        if manejador is None:
            manejador = self._r_general
        respuesta = manejador(intencion, mensaje_texto, conversacion) or Respuesta(intencion=intencion.nombre)
        respuesta.intencion = intencion.nombre

        # recomendaciones de seguimiento (se usan en el simulador y en el plan)
        if not respuesta.sugerencias:
            respuesta.sugerencias = self.sugerencias(respuesta, intencion)

        # firma del negocio si el mensaje es largo o es la primera vez
        if not respuesta.texto.strip():
            respuesta.texto = self.negocio.mensaje_error or self._fallback_texto()
        respuesta.texto = recortar(respuesta.texto.strip(), settings.MAX_RESPONSE_LENGTH)
        return respuesta

    def sugerencias(self, respuesta: Respuesta, intencion: Intencion) -> List[str]:
        """Preguntas cortas que el cliente podría hacer después."""
        base: List[str] = []
        if respuesta.item:
            base.append("¿Está disponible hoy?")
            if respuesta.item.es_servicio:
                base.append("¿Cómo agendo una cita?")
                base.append("¿Cuánto dura?")
            else:
                base.append("¿Cuánto vale el envío?")
                base.append("¿Qué garantía tiene?")
            if respuesta.item.categoria:
                base.append(f"¿Qué más tienen en {respuesta.item.categoria}?")
        else:
            base.extend([self._pregunta_catalogo(), "¿Cuáles son los precios?", "Quiero hablar con un asesor"])
        return base[:4]

    # ------------------------------------------------------------- intenciones
    def _r_saludo(self, intencion: Intencion, texto: str, conv: Conversacion) -> Respuesta:
        nombre = self.negocio.nombre
        saludo = self.negocio.mensaje_bienvenida
        if not saludo:
            estado = self.negocio.esta_abierto()
            if estado is False:
                saludo = (
                    f"¡Hola! 👋 Gracias por escribir a *{nombre}*. En este momento estamos fuera de "
                    f"horario de atención, pero puedo ayudarte con información y dejamos tu solicitud lista."
                )
            else:
                saludo = f"¡Hola! 👋 Bienvenido(a) a *{nombre}*."
            if self.negocio.descripcion:
                saludo += f" {self.negocio.descripcion}"
            saludo += " ¿En qué te puedo ayudar?"

        respuesta = Respuesta(texto=saludo)
        # Ofrecer un menú natural con lo que realmente ofrece el negocio
        categorias = self.catalogo.categorias(limite=5)
        if categorias:
            respuesta.texto += "\n\n" + self._lineas_menu(categorias)
        destacados = self.catalogo.destacados(limite=3)
        if destacados:
            respuesta.texto += "\n\n" + self._titulo_destacados() + "\n" + "\n".join(
                f"• {item.nombre} — {item.precio_legible()}" for item in destacados
            )
        if conv.es_cliente_conocido() and conv.datos.get("nombre"):
            respuesta.texto = f"¡Hola de nuevo, {conv.datos['nombre']}! 👋\n" + respuesta.texto.split("\n", 1)[-1]
        return respuesta

    def _r_catalogo(self, intencion: Intencion, texto: str, conv: Conversacion) -> Respuesta:
        total = self.catalogo.total()
        if total == 0:
            return Respuesta(
                texto=self.negocio.mensaje_error
                or f"Aún no tengo el catálogo de *{self.negocio.nombre}* cargado. Un asesor te ayuda enseguida 🙌",
                escalar=True,
            )

        if total <= settings.MAX_ITEMS_IN_REPLY:
            return self._lista_items(self.catalogo.destacados(limite=total), intro=self._intro_catalogo())

        lineas = [self._intro_catalogo()]
        presupuesto_texto = settings.MAX_RESPONSE_LENGTH - 260  # espacio para el cierre
        for categoria, cantidad in list(self.negocio.categorias_con_items().items())[:8]:
            ejemplos = self.catalogo.por_categoria(categoria, limite=2)
            detalle = " · ".join(f"{i.nombre} ({i.precio_legible()})" for i in ejemplos)
            linea = f"• *{categoria}* ({cantidad})" + (f": {detalle}" if detalle else "")
            if sum(len(x) + 1 for x in lineas) + len(linea) > presupuesto_texto:
                lineas.append("• …y más categorías disponibles")
                break
            lineas.append(linea)

        if sum(len(x) + 1 for x in lineas) < presupuesto_texto - 200:
            destacados = self.catalogo.destacados(limite=3)
            if destacados:
                lineas.append("")
                lineas.append(self._titulo_destacados())
                lineas.extend(f"• {i.nombre} — {i.precio_legible()}" for i in destacados)
        lineas.append("")
        lineas.append(self._cierre_catalogo())
        return Respuesta(texto="\n".join(lineas), sugerencias=self._preguntas_de_categorias())

    def _r_categoria(self, intencion: Intencion, texto: str, conv: Conversacion) -> Respuesta:
        categoria = intencion.datos.get("categoria") or ""
        items = self.catalogo.por_categoria(categoria, limite=settings.MAX_ITEMS_IN_REPLY)
        if not items:
            return self._r_no_encontrado(intencion, texto, conv)
        return self._lista_items(items, intro=f"Esto tenemos en *{categoria}*:")

    def _r_consulta_item(self, intencion: Intencion, texto: str, conv: Conversacion) -> Respuesta:
        item: Optional[CatalogoItem] = intencion.datos.get("item")
        otros: List[CatalogoItem] = list(intencion.datos.get("otros") or [])
        if not item:
            return self._r_no_encontrado(intencion, texto, conv)

        conv.ultimo_item_id = item.id
        lineas = [item.ficha()]

        # Alternativas útiles (sin repetir el mismo)
        alternativas = [o for o in otros if o.id != item.id][:3]
        if alternativas:
            lineas.append("")
            lineas.append("También podría interesarte:")
            lineas.extend(
                f"• {o.nombre} — {o.precio_legible()}"
                + (f" ({o.etiqueta_disponibilidad()})" if not o.disponible else "")
                for o in alternativas
            )

        lineas.append("")
        lineas.append(self._cierre_item(item))

        respuesta = Respuesta(texto="\n".join(lineas), item=item)
        respuesta.agregar_imagen(item)
        if not item.disponible and item.stock is not None and item.stock <= 0:
            respuesta.escalar = True
        return respuesta

    def _r_sugerencia(self, intencion: Intencion, texto: str, conv: Conversacion) -> Respuesta:
        resultados: List[Resultado] = intencion.datos.get("resultados") or []
        items = [r.item for r in resultados][:settings.MAX_ITEMS_IN_REPLY]
        if not items:
            return self._r_no_encontrado(intencion, texto, conv)
        presupuesto = intencion.datos.get("presupuesto")
        dentro = [
            i for i in items
            if presupuesto and i.precio is not None and i.precio <= presupuesto
        ]
        intro = "Estas opciones se acercan a lo que buscas:"
        if presupuesto:
            intro = f"Con un presupuesto de {self._moneda(presupuesto)} tengo estas opciones:"
            if dentro:
                intro = (
                    f"Con {self._moneda(presupuesto)} te alcanza para estas opciones "
                    f"(todas por debajo de tu presupuesto):"
                )
            elif items:
                intro = (
                    f"Con {self._moneda(presupuesto)} no tengo nada exacto, pero esto es lo más "
                    f"cercano que manejamos:"
                )
        respuesta = self._lista_items(items, intro=intro)
        if presupuesto and not dentro:
            respuesta.escalar = True
            respuesta.avisar_dueno = True
        return respuesta

    def _r_no_encontrado(self, intencion: Intencion, texto: str, conv: Conversacion) -> Respuesta:
        tokens = intencion.datos.get("tokens") or []
        presupuesto = intencion.datos.get("presupuesto")
        pedido = " ".join(tokens) if tokens else texto.strip()

        # Existe algo parecido, pero se pasa del presupuesto: se dice con claridad
        # en vez de ofrecer algo que el cliente no puede pagar sin avisar.
        cercano = self.catalogo.mejor(pedido or texto)
        if cercano and presupuesto and cercano.item.precio and cercano.item.precio > presupuesto:
            lineas = [
                f"*{cercano.item.nombre}* está en {cercano.item.precio_legible()}, "
                f"algo por encima de {self._moneda(presupuesto)} 😕"
            ]
            dentro = [
                r.item for r in self.catalogo.buscar(
                    pedido or texto, limite=4, presupuesto=presupuesto
                )
            ]
            if dentro:
                lineas.append("")
                lineas.append("Dentro de tu presupuesto te puedo ofrecer:")
                lineas.extend(f"• {i.nombre} — {i.precio_legible()}" for i in dentro)
            else:
                lineas.append("")
                lineas.append(
                    "Con ese monto no tengo algo equivalente. ¿Quieres que un asesor revise opciones "
                    "o te avisamos si baja de precio?"
                )
            respuesta = Respuesta(texto="\n".join(lineas), item=cercano.item, escalar=True, avisar_dueno=True)
            respuesta.acciones.append({
                "tipo": "notificar",
                "texto": (
                    f"💸 *Cliente con presupuesto ajustado*\n"
                    f"Cliente: {conv.datos.get('nombre') or conv.chat_id}\n"
                    f"Buscaba: {pedido} | presupuesto: {self._moneda(presupuesto)}\n"
                    f"Lo más cercano: {cercano.item.nombre} ({cercano.item.precio_legible()})"
                ),
            })
            return respuesta

        lineas = [
            f"No tengo registrado *{pedido}* en este momento 😕",
        ]
        parecidos = (
            self.catalogo.buscar(pedido or texto, limite=3, presupuesto=presupuesto)
            if pedido else []
        )
        items = [r.item for r in parecidos] or self.catalogo.destacados(limite=3)
        if items:
            lineas.append("")
            lineas.append("Lo más parecido que manejamos:")
            lineas.extend(f"• {i.nombre} — {i.precio_legible()}" for i in items)
        if self.negocio.tipo_negocio.lower() in {"servicios", "servicio"} or self.catalogo.por_tipo("servicio"):
            lineas.append("")
            lineas.append("También podemos prepararte una propuesta a la medida: cuéntame qué necesitas.")
        lineas.append("")
        lineas.append("¿Quieres que un asesor te confirme disponibilidad y tiempos? Puedo dejarle tu solicitud.")
        respuesta = Respuesta(texto="\n".join(lineas), escalar=True, avisar_dueno=True)
        respuesta.acciones.append({
            "tipo": "notificar",
            "texto": (
                f"🔎 *Solicitud no encontrada en el catálogo*\n"
                f"Cliente: {conv.datos.get('nombre') or 'Nuevo'}\n"
                f"Pidió: {pedido}\nChat: {conv.chat_id}"
            ),
        })
        return respuesta

    def _r_precio(self, intencion: Intencion, texto: str, conv: Conversacion) -> Respuesta:
        orden = self.catalogo.interpretar_orden(texto)
        mejor = self.catalogo.mejor(texto)
        item = mejor.item if mejor else None
        if not item and conv.ultimo_item_id and self._habla_del_mismo(texto):
            item = self.catalogo.por_id(conv.ultimo_item_id)

        # "¿tienen algo más barato?" -> opciones económicas, no una lista de precios
        if orden == "precio_asc":
            base = [item] if item else []
            candidatos = (
                self.catalogo.por_categoria(item.categoria, limite=20) if item and item.categoria
                else self.catalogo.todos()
            )
            mas_baratos = [
                c for c in candidatos
                if c.id not in {b.id for b in base}
                and c.precio is not None
                and (not item or item.precio is None or (c.precio or 0) < (item.precio or 0))
            ]
            mas_baratos.sort(key=lambda c: c.precio or 0)
            if mas_baratos:
                referencia = (
                    f"más económicas que *{item.nombre}* ({item.precio_legible()})"
                    if item else "más económicas"
                )
                return self._lista_items(mas_baratos, intro=f"Estas son las opciones {referencia}:")
            if item:
                return Respuesta(
                    texto=f"En esa línea, *{item.nombre}* ({item.precio_legible()}) ya es la opción "
                          f"más económica que tenemos 💰 ¿Te cuento qué incluye?",
                    item=item,
                )

        if item:
            return Respuesta(
                texto=f"💰 *{item.nombre}*: {item.precio_legible()}\n"
                      f"{'📦 ' + item.etiqueta_disponibilidad() if not item.disponible else '✅ Disponible'}\n\n"
                      f"{self._cierre_item(item)}",
                item=item,
            )

        con_precio = [i for i in self.catalogo.todos() if i.precio is not None]
        if not con_precio:
            return Respuesta(
                texto="Los precios de nuestros productos y servicios se cotizan según lo que necesites. "
                      "Cuéntame qué buscas y te preparo el valor exacto 🙌",
                escalar=True,
                avisar_dueno=True,
            )

        minimo = min(con_precio, key=lambda i: i.precio or 0)
        maximo = max(con_precio, key=lambda i: i.precio or 0)
        lineas = [f"Estos son los rangos de *{self.negocio.nombre}*:"]
        for categoria, _ in list(self.negocio.categorias_con_items().items())[:5]:
            items = [i for i in self.catalogo.por_categoria(categoria, limite=10) if i.precio is not None]
            if not items:
                continue
            bajo = min(items, key=lambda i: i.precio or 0)
            alto = max(items, key=lambda i: i.precio or 0)
            if bajo.precio == alto.precio:
                lineas.append(f"• *{categoria}*: {bajo.precio_legible()}")
            else:
                lineas.append(f"• *{categoria}*: desde {bajo.precio_legible()} hasta {alto.precio_legible()}")
        lineas.append("")
        lineas.append(
            f"Lo más económico es *{minimo.nombre}* ({minimo.precio_legible()}) y lo más alto "
            f"*{maximo.nombre}* ({maximo.precio_legible()})."
        )
        lineas.append("Dime qué producto o servicio te interesa y te doy el precio exacto 👌")
        return Respuesta(texto="\n".join(lineas), sugerencias=self._preguntas_de_categorias())

    def _r_objecion_precio(self, intencion: Intencion, texto: str, conv: Conversacion) -> Respuesta:
        """El cliente dice que está caro: escuchamos, ofrecemos alternativas reales."""
        mejor = self.catalogo.mejor(texto)
        item = mejor.item if mejor else None
        if not item and conv.ultimo_item_id:
            item = self.catalogo.por_id(conv.ultimo_item_id)

        candidatos = (
            self.catalogo.por_categoria(item.categoria, limite=20)
            if item and item.categoria else self.catalogo.todos()
        )
        mas_baratos = [
            c for c in candidatos
            if (not item or c.id != item.id) and c.precio is not None
            and (not item or item.precio is None or (c.precio or 0) < (item.precio or 0))
        ]
        mas_baratos.sort(key=lambda c: c.precio or 0)

        lineas = ["Te entiendo 🙌 Busquemos la opción que mejor te sirva."]
        if item:
            lineas.append("")
            lineas.append(f"Lo que viste era *{item.nombre}* ({item.precio_legible()}).")
        if mas_baratos:
            lineas.append("")
            lineas.append("Opciones más económicas que sí tenemos:")
            lineas.extend(
                f"• {c.nombre} — {c.precio_legible()}"
                + (f" ({c.etiqueta_disponibilidad()})" if not c.disponible else "")
                for c in mas_baratos[:3]
            )
        if self.negocio.promociones:
            lineas.append("")
            lineas.append(f"🎉 {self.negocio.promociones[0]}")
        if self.negocio.metodos_pago:
            lineas.append("")
            lineas.append(
                "Puedo pedirle a un asesor que revise si hay una mejor condición para ti "
                f"(también manejamos: {unir(self.negocio.metodos_pago[:3])})."
            )

        respuesta = Respuesta(texto="\n".join(lineas), item=item, escalar=True, avisar_dueno=True)
        respuesta.acciones.append({
            "tipo": "notificar",
            "texto": (
                "💸 *El cliente considera que está caro*\n"
                f"Cliente: {conv.datos.get('nombre') or conv.chat_id}\n"
                f"Ítem: {item.nombre if item else 'sin identificar'}\n"
                f"Mensaje: {texto[:160]}"
            ),
        })
        return respuesta

    def _r_disponibilidad(self, intencion: Intencion, texto: str, conv: Conversacion) -> Respuesta:
        # Primero lo que el cliente menciona ahora; solo si no menciona nada
        # concreto usamos el último ítem de la conversación.
        mejor = self.catalogo.mejor(texto if self._menciona_algo(texto) else "")
        item = mejor.item if mejor else None
        if not item and conv.ultimo_item_id and self._habla_del_mismo(texto):
            item = self.catalogo.por_id(conv.ultimo_item_id)
        if not item:
            return Respuesta(
                texto="Claro 🙌 ¿De cuál producto o servicio quieres que confirme disponibilidad?",
                sugerencias=self._preguntas_de_categorias(),
            )
        conv.ultimo_item_id = item.id
        disponible = item.disponible
        texto_disp = (
            f"✅ *{item.nombre}* está {item.etiqueta_disponibilidad().lower()}."
            if disponible
            else f"⚠️ *{item.nombre}* está {item.etiqueta_disponibilidad().lower()} en este momento."
        )
        if item.stock is not None and disponible:
            texto_disp += f" Quedan {item.stock}."
        if item.es_servicio and item.agenda:
            texto_disp += f"\n🗓️ {item.agenda}"
        texto_disp += f"\n💰 {item.precio_legible()}\n\n{self._cierre_item(item)}"
        respuesta = Respuesta(texto=texto_disp, item=item)
        respuesta.agregar_imagen(item)
        return respuesta

    def _r_horario(self, intencion: Intencion, texto: str, conv: Conversacion) -> Respuesta:
        horario = self.negocio.horario_legible()
        estado = self.negocio.esta_abierto()
        if not horario:
            return Respuesta(
                texto=f"Con gusto te confirmo el horario de atención de *{self.negocio.nombre}* 🙌 "
                      f"Un asesor te responde en breve.",
                escalar=True,
                avisar_dueno=True,
            )
        encabezado = "🕒 *Horario de atención*"
        if estado is False:
            encabezado += " · ahora estamos cerrados"
        elif estado is True:
            encabezado += " · ahora estamos abiertos"
        return Respuesta(texto=f"{encabezado}\n{horario}\n\n{self._cierre_general()}")

    def _r_ubicacion(self, intencion: Intencion, texto: str, conv: Conversacion) -> Respuesta:
        lineas = []
        if self.negocio.direccion:
            lineas.append(f"📍 *{self.negocio.nombre}*")
            lineas.append(self.negocio.direccion + (f" ({self.negocio.zona})" if self.negocio.zona else ""))
            if self.negocio.ciudad:
                lineas.append(self.negocio.ciudad)
            if self.negocio.mapa_url:
                lineas.append(f"🗺️ Ubicación: {self.negocio.mapa_url}")
        if self.negocio.cobertura:
            lineas.append(f"🚚 Cobertura: {self.negocio.cobertura}")
        if not lineas:
            return Respuesta(
                texto="¿Quieres saber cómo llegar? Escríbenos la ciudad donde estás y te indico la sede "
                      "o la cobertura más cercana 🙌",
                escalar=True,
                avisar_dueno=True,
            )
        ofrecer_servicio = bool(self.catalogo.por_tipo("servicio")) or bool(self.negocio.cobertura)
        if ofrecer_servicio:
            lineas.append("")
            lineas.append("Si prefieres, también vamos hasta donde estés: cuéntame qué necesitas y la zona.")
        else:
            lineas.append("")
            lineas.append("¿Te esperamos en el local o prefieres que te enviemos el pedido?")
        return Respuesta(texto="\n".join(lineas))

    def _r_pago(self, intencion: Intencion, texto: str, conv: Conversacion) -> Respuesta:
        metodos = self.negocio.metodos_pago
        if not metodos:
            return Respuesta(
                texto="Con gusto te confirmo los medios de pago disponibles 🙌 Un asesor te responde en un momento.",
                escalar=True,
                avisar_dueno=True,
            )
        lineas = [f"💳 *Medios de pago* ({self.negocio.nombre}):"]
        lineas.extend(f"• {m}" for m in metodos)
        if self.negocio.acepta_presupuesto:
            lineas.append("")
            lineas.append("Si quieres, te paso el valor exacto con la forma de pago que prefieras 👌")
        return Respuesta(texto="\n".join(lineas))

    def _r_envio(self, intencion: Intencion, texto: str, conv: Conversacion) -> Respuesta:
        # Si el cliente nombra una ciudad donde no llegamos, lo decimos con claridad
        ciudad = self._ciudad_mencionada(texto)
        if ciudad and not self.negocio.cubre_ciudad(ciudad):
            cobertura = (self.negocio.cobertura or self.negocio.ciudad).rstrip(". ")
            respuesta = Respuesta(
                texto=(
                    f"No tengo confirmada cobertura en *{titulo(ciudad)}* 😕 Nuestra zona actual es "
                    f"{cobertura}. ¿Quieres que un asesor revise si podemos llevarlo hasta allá?"
                ),
                escalar=True,
                avisar_dueno=True,
            )
            respuesta.acciones.append({
                "tipo": "notificar",
                "texto": (
                    f"🚚 *Pedido de envío fuera de cobertura*\n"
                    f"Cliente: {conv.datos.get('nombre') or conv.chat_id}\n"
                    f"Ciudad pedida: {ciudad}\nMensaje: {texto[:150]}"
                ),
            })
            return respuesta

        lineas = []
        if self.negocio.envio:
            lineas.append(f"🚚 {self.negocio.envio}")
        if self.negocio.cobertura:
            lineas.append(f"📍 Cobertura: {self.negocio.cobertura}")
        con_envio = [i for i in self.catalogo.todos() if i.entrega]
        if con_envio:
            ejemplo = con_envio[0]
            lineas.append(f"• Ejemplo: {ejemplo.nombre} → {ejemplo.entrega}")
        if not lineas:
            return Respuesta(
                texto="Te confirmo costos y tiempos de envío según tu ciudad 🙌 ¿Me dices dónde estás?",
                escalar=True,
                avisar_dueno=True,
            )
        lineas.append("")
        lineas.append("¿A qué ciudad o barrio sería el envío? Así te confirmo el valor exacto.")
        return Respuesta(texto="\n".join(lineas))

    def _r_garantia(self, intencion: Intencion, texto: str, conv: Conversacion) -> Respuesta:
        lineas = []
        if self.negocio.politicas:
            lineas.append("🛡️ *Nuestras políticas*:")
            lineas.extend(f"• {p}" for p in self.negocio.politicas)
        con_garantia = [i for i in self.catalogo.todos() if i.garantia]
        if con_garantia:
            lineas.append("")
            lineas.append("Garantías por ítem:")
            lineas.extend(f"• {i.nombre}: {i.garantia}" for i in con_garantia[:4])
        if not lineas:
            return Respuesta(
                texto="Con gusto te explico garantías y cambios 🙌 Un asesor te confirma los detalles enseguida.",
                escalar=True,
                avisar_dueno=True,
            )
        lineas.append("")
        lineas.append("¿Quieres que te confirme la garantía de un producto en particular?")
        return Respuesta(texto="\n".join(lineas))

    def _r_promocion(self, intencion: Intencion, texto: str, conv: Conversacion) -> Respuesta:
        lineas = []
        if self.negocio.promociones:
            lineas.append("🎉 *Promociones vigentes*:")
            lineas.extend(f"• {p}" for p in self.negocio.promociones)
        con_promo = [i for i in self.catalogo.todos() if i.promocion][:4]
        if con_promo:
            lineas.append("")
            lineas.append("En el catálogo:")
            lineas.extend(f"• {i.nombre} — {i.precio_legible()} · {i.promocion}" for i in con_promo)
        if not lineas:
            return Respuesta(
                texto="¿Quieres que te avise de las promociones vigentes? Un asesor te cuenta las ofertas del mes 🎉",
                escalar=True,
                avisar_dueno=True,
            )
        lineas.append("")
        lineas.append("¿Te interesa alguna o te cuento más de algún producto?")
        return Respuesta(texto="\n".join(lineas))

    def _r_cita(self, intencion: Intencion, texto: str, conv: Conversacion) -> Respuesta:
        servicios = self.catalogo.por_tipo("servicio")
        pistas = intencion.datos.get("pistas") or {}

        # ¿mencionó un servicio concreto? Lo ponemos primero, con su detalle
        mejor = self.catalogo.mejor(texto)
        servicio = mejor.item if mejor and mejor.item.es_servicio else None
        lineas: List[str] = []

        if servicio:
            conv.ultimo_item_id = servicio.id
            lineas.append(f"🗓️ ¡Claro! Te agendo *{servicio.nombre}* — {servicio.precio_legible()}")
            detalle = []
            if servicio.duracion:
                detalle.append(f"⏱️ Duración: {servicio.duracion}")
            if servicio.modalidad:
                detalle.append(f"📍 Modalidad: {servicio.modalidad}")
            if servicio.incluye:
                detalle.append("✅ Incluye: " + ", ".join(servicio.incluye))
            if servicio.agenda:
                detalle.append(f"🗓️ {servicio.agenda}")
            lineas.extend(detalle)
            otros = [s for s in servicios if s.id != servicio.id][:3]
            if otros:
                lineas.append("")
                lineas.append("Otros servicios que puedes agendar: " + unir([s.nombre for s in otros]))
        elif servicios:
            lineas.append("🗓️ ¡Claro! Agendamos tu cita. Estos son los servicios disponibles:")
            lineas.extend(
                f"• {s.nombre} — {s.precio_legible()}" + (f" ({s.duracion})" if s.duracion else "")
                for s in servicios[: settings.MAX_ITEMS_IN_REPLY]
            )
        else:
            lineas.append("🗓️ ¡Claro! Coordinamos tu atención.")

        if self.negocio.horario_legible():
            lineas.append("")
            lineas.append(f"🕒 {self.negocio.horario_legible()}")

        lineas.append("")
        lineas.append("Para dejarla lista necesito:")
        lineas.append("1️⃣ Servicio que necesitas")
        lineas.append("2️⃣ Día y hora que prefieres")
        lineas.append("3️⃣ Tu nombre")
        if pistas.get("dias") or pistas.get("hora"):
            mencionado = unir(list(pistas.get("dias") or []) + ([pistas["hora"]] if pistas.get("hora") else []))
            if mencionado:
                lineas.append("")
                lineas.append(f"📌 Mencionaste: {mencionado}. Lo confirmo con el equipo.")
        lineas.append("")
        lineas.append("Un asesor confirma el cupo en minutos ✅")

        respuesta = Respuesta(texto="\n".join(lineas), escalar=True, avisar_dueno=True)
        respuesta.acciones.append({
            "tipo": "notificar",
            "texto": (
                "🗓️ *Solicitud de cita*\n"
                f"Cliente: {conv.datos.get('nombre') or 'Nuevo'}\n"
                f"Pidió: {texto[:180]}\nChat: {conv.chat_id}"
            ),
        })
        return respuesta

    def _r_cotizacion(self, intencion: Intencion, texto: str, conv: Conversacion) -> Respuesta:
        mejor = self.catalogo.mejor(texto)
        item = mejor.item if mejor else None
        lineas = ["📝 Con gusto te preparo la cotización."]

        if item:
            conv.ultimo_item_id = item.id
            lineas.append("")
            lineas.append(f"Lo más cercano que manejamos es *{item.nombre}*: {item.precio_legible()}")
            if item.descripcion:
                lineas.append(f"{recortar(item.descripcion, 160)}")
            if item.requisitos:
                lineas.append(f"📋 Para cotizarlo necesito: {item.requisitos}")
        elif self.catalogo.todos():
            ejemplos = self.catalogo.destacados(limite=3)
            lineas.append("")
            lineas.append("Trabajamos con:")
            lineas.extend(f"• {i.nombre} — {i.precio_legible()}" for i in ejemplos)

        lineas.append("")
        lineas.append("Cuéntame estos datos para darte el valor exacto:")
        lineas.extend([
            "1️⃣ Qué necesitas exactamente",
            "2️⃣ Cantidad o tamaño",
            "3️⃣ Ciudad o zona",
            "4️⃣ Cuándo lo necesitas",
        ])
        lineas.append("")
        lineas.append("Con eso te paso la propuesta y un asesor la revisa ✅")
        respuesta = Respuesta(texto="\n".join(lineas), escalar=True, avisar_dueno=True)
        respuesta.acciones.append({
            "tipo": "notificar",
            "texto": (
                "📝 *Solicitud de cotización*\n"
                f"Cliente: {conv.datos.get('nombre') or 'Nuevo'}\n"
                f"Mensaje: {texto[:180]}\nChat: {conv.chat_id}"
            ),
        })
        return respuesta

    def _r_pedido(self, intencion: Intencion, texto: str, conv: Conversacion) -> Respuesta:
        item: Optional[CatalogoItem] = intencion.datos.get("item")
        if not item:
            mejor = self.catalogo.mejor(texto)
            item = mejor.item if mejor else None
        if not item and conv.ultimo_item_id:
            item = self.catalogo.por_id(conv.ultimo_item_id)

        lineas = []
        if item:
            conv.ultimo_item_id = item.id
            lineas.append(f"¡Excelente elección! 🎉 *{item.nombre}* — {item.precio_legible()}")
            if item.es_servicio:
                lineas.append("")
                lineas.append("Para dejarlo agendado envíame:")
            else:
                lineas.append("")
                lineas.append("Para separarlo envíame:")
            lineas.extend([
                "1️⃣ Tu nombre",
                "2️⃣ Ciudad y dirección (o sede donde lo recoges)",
                f"3️⃣ Forma de pago: {unir(self.negocio.metodos_pago[:3]) or 'la que prefieras'}",
            ])
            if item.es_servicio and item.agenda:
                lineas.append(f"🗓️ {item.agenda}")
        else:
            lineas.append("¡Perfecto! 🙌 Cuéntame qué producto o servicio quieres y lo dejamos listo.")
            lineas.append("")
            lineas.append(f"Puedes ver el catálogo así: {self._pregunta_catalogo()}")

        respuesta = Respuesta(texto="\n".join(lineas), item=item, avisar_dueno=True)
        respuesta.acciones.append({
            "tipo": "notificar",
            "texto": (
                "🛒 *Intención de compra*\n"
                f"Cliente: {conv.datos.get('nombre') or conv.chat_id}\n"
                f"Ítem: {item.nombre if item else 'sin identificar'}\n"
                f"Mensaje: {texto[:160]}"
            ),
        })
        return respuesta

    def _r_humano(self, intencion: Intencion, texto: str, conv: Conversacion) -> Respuesta:
        aviso = self.negocio.mensaje_humano or settings.HUMAN_ESCALATION_TEXT or (
            "¡Claro que sí! 🙌 Ya avisé a una persona del equipo y te escribe por aquí en un momento. "
            "Si quieres adelantar, cuéntame en una línea qué necesitas."
        )
        respuesta = Respuesta(texto=aviso, escalar=True, avisar_dueno=True)
        if not conv.avisado_al_dueno:
            respuesta.acciones.append({
                "tipo": "notificar",
                "texto": (
                    "🙋 *Un cliente pide hablar con una persona*\n"
                    f"Cliente: {conv.datos.get('nombre') or 'Nuevo'} ({conv.chat_id})\n"
                    f"Último mensaje: {texto[:180]}"
                ),
            })
        respuesta.acciones.append({"tipo": "presencia", "estado": "paused", "ms": 200})
        return respuesta

    def _r_queja(self, intencion: Intencion, texto: str, conv: Conversacion) -> Respuesta:
        texto_respuesta = (
            "Lamento mucho esta situación 🙏 Gracias por contármelo: ya pasé tu caso a una persona del "
            "equipo para que lo revise con prioridad. Si puedes, cuéntame qué pasó y tu número de pedido "
            "o cita para agilizarlo."
        )
        respuesta = Respuesta(texto=texto_respuesta, escalar=True, avisar_dueno=True)
        respuesta.acciones.append({
            "tipo": "notificar",
            "texto": (
                "⚠️ *POSIBLE QUEJA - revisar ya*\n"
                f"Cliente: {conv.datos.get('nombre') or conv.chat_id}\n"
                f"Mensaje: {texto[:220]}"
            ),
        })
        return respuesta

    def _r_faq(self, intencion: Intencion, texto: str, conv: Conversacion) -> Respuesta:
        respuesta = str(intencion.datos.get("respuesta") or "")
        return Respuesta(texto=respuesta, notas=f"FAQ: {intencion.datos.get('pregunta')}")

    def _r_agradecimiento(self, intencion: Intencion, texto: str, conv: Conversacion) -> Respuesta:
        # "gracias, me llevo el samsung" es una compra, no una despedida
        mejor = self.catalogo.mejor(texto)
        if mejor and mejor.coincide_fuerte:
            return self._r_pedido(
                Intencion("pedido", 0.8, {"item": mejor.item}), texto, conv
            )
        base = self.negocio.mensaje_post_venta or "¡Con gusto! 🙌 Estoy aquí si necesitas algo más."
        if self.negocio.tiempo_respuesta:
            base += f" {self.negocio.tiempo_respuesta}"
        return Respuesta(texto=base)

    def _r_despedida(self, intencion: Intencion, texto: str, conv: Conversacion) -> Respuesta:
        return Respuesta(texto=self.negocio.mensaje_despedida or "¡Gracias por escribirnos! 🙌 Que tengas un excelente día.")

    def _r_afirmacion(self, intencion: Intencion, texto: str, conv: Conversacion) -> Respuesta:
        # El cliente acepta algo que ofrecimos: seguimos con el ítem en curso
        item = self.catalogo.por_id(conv.ultimo_item_id) if conv.ultimo_item_id else None
        if item:
            return Respuesta(
                texto=f"¡Perfecto! 🙌 Dejamos entonces *{item.nombre}*. "
                      f"{self._cierre_item(item)}",
                item=item,
            )
        ultima = conv.ultima_intencion
        if ultima in {"cita", "cotizacion", "pedido"}:
            return Respuesta(
                texto="¡Listo! Cuéntame nombre, ciudad y el día que prefieres y lo dejo confirmado ✅",
                escalar=True,
                avisar_dueno=True,
            )
        return Respuesta(texto="¡Genial! 🙌 ¿Te ayudo con algún producto o servicio en particular?")

    def _r_negacion(self, intencion: Intencion, texto: str, conv: Conversacion) -> Respuesta:
        return Respuesta(
            texto="Sin problema 😊 Si más adelante necesitas algo, aquí estoy. "
                  "¿Quieres que te muestre otras opciones?",
            sugerencias=self._preguntas_de_categorias(),
        )

    def _r_general(self, intencion: Intencion, texto: str, conv: Conversacion) -> Respuesta:
        lineas = [self.negocio.mensaje_error or self._fallback_texto()]
        categorias = self.catalogo.categorias(limite=5)
        if categorias:
            lineas.append("")
            lineas.append(self._lineas_menu(categorias))
        lineas.append("")
        lineas.append("¿Prefieres que te contacte un asesor del equipo? Solo dime que sí y lo aviso de inmediato.")
        respuesta = Respuesta(texto="\n".join(lineas), escalar=True, avisar_dueno=True)
        return respuesta

    # ------------------------------------------------------------- formateadores
    def _lista_items(self, items: List[CatalogoItem], intro: str = "") -> Respuesta:
        lineas = [intro] if intro else []
        for item in items[: settings.MAX_ITEMS_IN_REPLY]:
            etiqueta = item.precio_legible()
            extra = []
            if item.es_servicio and item.duracion:
                extra.append(item.duracion)
            if item.modalidad:
                extra.append(item.modalidad)
            if not item.disponible:
                extra.append(item.etiqueta_disponibilidad())
            sufijo = f" · {', '.join(extra)}" if extra else ""
            lineas.append(f"• *{item.nombre}* — {etiqueta}{sufijo}")
            if item.descripcion:
                lineas.append(f"  {recortar(item.descripcion, 110)}")
        lineas.append("")
        lineas.append(f"¿Cuál te interesa? Dime el nombre y te doy todos los detalles 😉")
        return Respuesta(texto="\n".join(lineas))

    def _intro_catalogo(self) -> str:
        if self.negocio.es_servicios:
            return f"Estos son los servicios que ofrece *{self.negocio.nombre}*:"
        if self.negocio.es_mixto:
            return f"Esto es lo que manejamos en *{self.negocio.nombre}* (productos y servicios):"
        return f"Estos son nuestros productos y servicios en *{self.negocio.nombre}*:"

    def _titulo_destacados(self) -> str:
        return "⭐ Lo más pedido:" if self.negocio.es_servicios else "⭐ Destacados:"

    def _cierre_catalogo(self) -> str:
        return "Dime el nombre de lo que te interesa y te paso precio, disponibilidad y fotos 📸"

    def _cierre_item(self, item: CatalogoItem) -> str:
        if item.es_servicio:
            cierre = "¿Quieres agendarlo? Dime día y hora y lo coordino 🗓️"
        else:
            cierre = "¿Te lo separo? Dime tu nombre y ciudad 🛒"
        if item.url:
            cierre += f"\n🔗 Más info: {item.url}"
        return cierre

    def _cierre_general(self) -> str:
        return "¿Quieres que te ayude con algo más?"

    def _fallback_texto(self) -> str:
        return (
            f"Gracias por escribir a *{self.negocio.nombre}* 🙌 Cuéntame qué producto o servicio "
            f"necesitas y te ayudo enseguida."
        )

    def _pregunta_catalogo(self) -> str:
        if self.negocio.es_servicios:
            return "¿Qué servicios ofrecen?"
        return "¿Qué productos y servicios tienen?"

    def _lineas_menu(self, categorias: List[str]) -> str:
        conteo = self.negocio.categorias_con_items()
        partes = [f"{c} ({conteo.get(c, 0)})" for c in categorias]
        return "Manejamos: " + " · ".join(partes) + "."

    def _preguntas_de_categorias(self) -> List[str]:
        return [f"¿Qué tienen en {c}?" for c in self.catalogo.categorias(limite=3)] + [
            "¿Cuáles son los precios?", "Quiero hablar con un asesor",
        ]

    def _moneda(self, valor: float) -> str:
        from utils.texto import formatear_precio

        return formatear_precio(valor, self.negocio.moneda)

    def _ciudad_mencionada(self, texto: str) -> Optional[str]:
        """Detecta si el cliente nombró una ciudad (para validar cobertura)."""
        if not texto:
            return None
        t = f" {normalizar(texto)} "
        candidatos = CIUDADES_CONOCIDAS | {c.lower() for c in self.negocio.ciudades_cobertura}
        for ciudad in sorted(candidatos, key=len, reverse=True):
            if f" {normalizar(ciudad)} " in t:
                return ciudad
        return None

    def _menciona_algo(self, texto: str) -> bool:
        """¿El mensaje trae algún término buscable (más allá de cortesía)?"""
        from utils.texto import tokenizar

        return bool(tokenizar(texto))

    def _habla_del_mismo(self, texto: str) -> bool:
        """
        Mensajes cortos y de seguimiento ("¿y cuánto vale?", "¿está disponible?")
        siguen refiriéndose al último ítem del que hablamos.
        """
        from utils.texto import tokenizar

        t = normalizar(texto)
        tokens = tokenizar(texto)
        if len(tokens) <= 2:
            return True
        referencias = ("eso", "ese", "esa", "este", "esta", "mismo", "misma", "tambien",
                       "otro", "otra", "aquel", "aquella")
        return any(f" {r} " in f" {t} " for r in referencias)
