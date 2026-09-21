"""
Detección de intención del mensaje.

Clasifica lo que el cliente quiere (precio, catálogo, horario, cita, cotización,
soporte, hablar con una persona, queja...) usando patrones generales y, cuando
existe, el catálogo y el perfil del negocio. No hay nada atado a un rubro: las
palabras concretas salen de config/negocio.json y del propio catálogo.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from config.business import Negocio
from models.catalog import CatalogoItem
from services.catalog_service import CatalogoService, Resultado
from utils.texto import normalizar, similitud, tokenizar

logger = logging.getLogger(__name__)


@dataclass
class Intencion:
    nombre: str
    confianza: float = 0.5
    datos: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"intencion": self.nombre, "confianza": round(self.confianza, 2), "datos": self.datos}


# Patrones generales (se comparan contra el texto normalizado, sin acentos)
PATRONES: List[tuple[str, str]] = [
    ("humano", r"\b(humano|persona real|asesor|asesora|agente real|un humano|alguien real|"
               r"hablar con (alguien|una persona|el dueno|el encargado)|supervisor|gerente|"
               r"que me llamen|que me llame|telefono de contacto directo)\b"),
    ("queja", r"\b(queja|reclamo|mal servicio|muy malo|pesimo|estafa|no me responden|"
              r"me cobraron|devolucion del dinero|hablar con el dueno|puse una queja|"
              r"demora|no ha llegado mi pedido|nunca llego)\b"),
    ("cita", r"\b(cita|citas|agendar|agenda|agendame|turno|turnos|reservar|reserva|"
             r"apartar|cita previa|disponibilidad de horario|cuando puedo ir|"
             r"quiero ir|puedo ir|me atienden hoy|visita tecnica|a domicilio)\b"),
    ("cotizacion", r"\b(cotizacion|cotizar|cotizame|presupuesto para|cuanto me sale|"
                    r"cuanto costaria|cuanto me costaria|valor aproximado|me pasas el valor)\b"),
    ("horario", r"\b(horario|horarios|a que hora|abren|cierran|abierto|cerrado|"
                r"atienden hoy|atienden manana|domingos|festivo|que horas)\b"),
    ("ubicacion", r"\b(donde (estan|están|queda|quedan|es|los encuentro|se ubican)|ubicacion|"
                  r"ubicación|direccion|dirección|como llego|cómo llego|sede|local|"
                  r"punto de venta|mapa|ubicados|queda en|quedan en|tienen local)\b"),
    ("pago", r"\b(pago|pagos|pagar|tarjeta|transferencia|nequi|daviplata|bancolombia|"
             r"efectivo|contra entrega|financiacion|cuotas|credito|abono|anticipo|"
             r"pse|paypal|mercado pago|link de pago|factura)\b"),
    ("envio", r"\b(envio|envios|enviar|domicilio|entrega|entregas|despacho|mensajeria|"
              r"llega a|hacen envios|cuanto vale el envio|demora la entrega)\b"),
    ("garantia", r"\b(garantia|garantias|devolucion|devoluciones|cambio del producto|"
                 r"se dana|averia|reparacion gratis|posventa|postventa|soporte tecnico)\b"),
    ("promocion", r"\b(promocion|promociones|descuento|descuentos|oferta|ofertas|"
                  r"rebaja|promo|cupon|black friday|liquidacion|plan de descuento)\b"),
    ("catalogo", r"\b(que (venden|ofrecen|manejan|tienen|hacen|prestan)|"
                 r"catalogo|productos|servicios|menu|lista de precios|que hay|"
                 r"que me recomiendas|que me ofreces|opciones tienen|portafolio)\b"),
    ("objecion_precio", r"\b(muy caro|muy cara|esta caro|está caro|es caro|es caro|sale caro|muy costoso|"
                        r"muy costosa|se me sale|no me alcanza|no tengo tanto|es mucho dinero|"
                        r"es mucha plata|muy elevado|fuera de mi presupuesto|no puedo pagar eso|"
                        r"esta por encima|me parece costoso|muy carito)\b"),
    ("precio", r"\b(precio|precios|cuanto (vale|cuesta|sale|esta|es)|cuanto|valor|"
               r"costos|costo|tarifa|tarifas|vale|precio unitario|precio al detal|"
               r"algo mas (barato|economico)|mas (barato|economico)|opciones economicas|"
               r"algo economico|de menor precio|lo mas barato que tengan)\b"),
    ("disponibilidad", r"\b(disponible|disponibilidad|hay (stock|existencia|unidades)|"
                       r"tienen (stock|disponibles|en existencia)|esta disponible|"
                       r"me queda|queda disponible|ultimas unidades)\b"),
    ("pedido", r"\b(quiero (comprar|pedir|llevar|adquirir|reservar|encargar)|"
               r"lo quiero|la quiero|me lo llevo|me la llevo|me llevo (el|la|un|una|los|las|\d)|"
               r"lo tomo|la tomo|hagamos el pedido|como compro|quiero apartar|separame|"
               r"encargame|apartame|reservame|me interesa el|me interesa la|"
               r"lo compro|quiero ese|quiero esa)\b"),
    # Los cierres de conversación van al final y anclados al inicio: así
    # "gracias, me llevo el samsung" se trata como compra, no como despedida.
    ("saludo", r"^(hola|holaa+|buenas|buenos dias|buenas tardes|buenas noches|"
               r"que tal|hey|hello|hi|saludos|aloha|ola)\b"),
    ("despedida", r"^(ok |listo |bueno |gracias )?(adios|chao|bye|hasta luego|nos vemos|"
                  r"hasta pronto|hablamos luego|feliz dia|buen dia|que estes bien)\b"),
    ("agradecimiento", r"^(ok |listo |bueno |perfecto |dale |muchas |mil |muy bien )?gracias"
                       r"(\b|$)|^te agradezco\b"),
    ("afirmacion", r"^(si|sí|claro|listo|ok|okay|dale|perfecto|de acuerdo|va|vale|"
                   r"de one|hagale|hágale|confirmo|sip)\b"),
    ("negacion", r"^(no|nop|nel|todavia no|aun no|no gracias|despues|después)\b"),
]

# Verbos de acción: si aparecen, el cliente quiere hacer algo y no leer una FAQ
PALABRAS_ACCION = (
    "quiero agendar", "agendar", "agendame", "reservar", "reservame", "apartar",
    "apartame", "quiero comprar", "comprar", "quiero pedir", "pedir", "encargar",
    "cotizar", "cotizame", "quiero ir", "puedo ir", "llevo", "me llevo",
)


# Palabras de pregunta sobre el negocio en general (si no queda ningún término
# buscable después de quitarlas, es una consulta abierta y no un ítem perdido)
PALABRAS_PREGUNTA = {
    "que", "cual", "cuales", "como", "cuando", "donde", "quien", "cuanto", "hay",
    "tienen", "tiene", "manejan", "venden", "ofrecen", "hacen", "prestan", "puede",
    "sera", "seria", "tendran", "habra", "existe", "alguno", "algun",
}

PATRONES_COMPILADOS = [(nombre, re.compile(patron, re.IGNORECASE)) for nombre, patron in PATRONES]


class IntentService:
    """Clasifica el mensaje y devuelve la intención principal + secundarias."""

    def __init__(self, negocio: Negocio, catalogo: CatalogoService):
        self.negocio = negocio
        self.catalogo = catalogo

    def detectar(self, texto: str, presupuesto: Optional[float] = None) -> Intencion:
        t = normalizar(texto)
        if not t:
            return Intencion("vacio", 0.1)

        # 0) ¿Pidió hablar con una persona? (palabras propias del negocio primero)
        for palabra in self.negocio.palabras_humano:
            if palabra and normalizar(palabra) in t:
                return Intencion("humano", 0.95, {"disparador": palabra})

        # 1) Preguntas frecuentes del negocio, PERO sin robarle el turno a una
        #    acción explícita ("quiero agendar una cita" no es la FAQ "¿necesito cita?")
        if not any(p in t for p in PALABRAS_ACCION):
            faq = self._buscar_faq(texto)
            if faq:
                return Intencion("faq", 0.9, {"pregunta": faq["pregunta"], "respuesta": faq["respuesta"]})

        # 2) Patrones generales (gana el primero que aparezca con más fuerza)
        for nombre, patron in PATRONES_COMPILADOS:
            if patron.search(t):
                datos: Dict[str, Any] = {}
                if nombre == "cita":
                    datos["pistas"] = self._pistas_cita(texto)
                return Intencion(nombre, 0.8, datos)

        # 3) ¿Menciona algo concreto del catálogo?
        resultados = self.catalogo.buscar(texto, limite=5, presupuesto=presupuesto)
        fuertes = [r for r in resultados if r.coincide_fuerte]
        if fuertes:
            mejor = fuertes[0]
            otras = [r for r in resultados if r.item.id != mejor.item.id and r.coincide_fuerte]
            return Intencion(
                "consulta_item",
                0.9 if len(fuertes) == 1 else 0.75,
                {"item": mejor.item, "otros": [r.item for r in otras][:4],
                 "resultados": resultados, "presupuesto": presupuesto},
            )

        if resultados and resultados[0].puntaje > 0.18:
            return Intencion("sugerencia", 0.5, {"resultados": resultados, "presupuesto": presupuesto})

        # 4) Categorías del negocio
        for categoria in self.negocio.categorias:
            if normalizar(categoria) and normalizar(categoria) in t:
                return Intencion("categoria", 0.7, {"categoria": categoria})

        # 5) Pregunta abierta sobre el negocio (sin un ítem concreto detrás)
        tokens = tokenizar(texto)
        resta = [tok for tok in tokens if tok not in PALABRAS_PREGUNTA]
        if not resta and re.search(r"\b(que|cual|como|cuando|donde|quien|hay|se puede)\b", t):
            return Intencion("general", 0.45, {"consulta_abierta": True})

        # 6) Parece que busca algo concreto del catálogo y no lo tenemos
        if tokens and len(tokens) <= 5:
            return Intencion("no_encontrado", 0.4, {"tokens": tokens, "presupuesto": presupuesto})

        return Intencion("general", 0.3)

    # ------------------------------------------------------------------ apoyo
    def _buscar_faq(self, texto: str) -> Optional[Dict[str, str]]:
        mejor: Optional[Dict[str, str]] = None
        mejor_puntaje = 0.0
        t = normalizar(texto)
        for faq in self.negocio.faqs:
            pregunta = normalizar(str(faq.get("pregunta") or faq.get("question") or ""))
            respuesta = str(faq.get("respuesta") or faq.get("answer") or "")
            if not pregunta or not respuesta:
                continue
            if pregunta in t:
                return {"pregunta": pregunta, "respuesta": respuesta}
            tokens_pregunta = tokenizar(pregunta)
            tokens_texto = set(tokenizar(texto))
            if not tokens_pregunta:
                continue
            coinciden = sum(1 for tok in tokens_pregunta if tok in tokens_texto)
            puntaje = coinciden / len(tokens_pregunta)
            # parecido global con la pregunta (frases reformuladas)
            puntaje = max(puntaje, similitud(t, pregunta) * 0.9)
            if puntaje > mejor_puntaje and puntaje >= 0.72:
                mejor_puntaje = puntaje
                mejor = {"pregunta": str(faq.get("pregunta")), "respuesta": respuesta}
        return mejor

    def _pistas_cita(self, texto: str) -> Dict[str, Any]:
        """Extrae horarios/fechas mencionados para agendar (muy simple y sin supuestos)."""
        t = normalizar(texto)
        dias = re.findall(
            r"\b(lunes|martes|miercoles|jueves|viernes|sabado|domingo|hoy|manana|"
            r"pasado manana|esta semana|la otra semana)\b", t
        )
        horas = re.findall(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm|a m|p m|horas|hs)?\b", t)
        hora_legible = None
        if horas:
            h, m, sufijo = horas[0]
            hora_legible = f"{h}:{m or '00'} {sufijo or ''}".strip()
        return {"dias": dias, "hora": hora_legible}

    def es_consulta_de_servicio(self, texto: str) -> bool:
        return self.catalogo.tipo_sugerido(texto) == "servicio"

    def explicar(self, intencion: Intencion) -> str:
        """Texto corto para los logs."""
        if intencion.nombre == "consulta_item":
            item: CatalogoItem = intencion.datos.get("item")
            return f"consulta_item:{item.nombre if item else '?'}"
        if intencion.nombre == "categoria":
            return f"categoria:{intencion.datos.get('categoria')}"
        return intencion.nombre

    @staticmethod
    def resultados_de(intencion: Intencion) -> List[Resultado]:
        return list(intencion.datos.get("resultados") or [])
