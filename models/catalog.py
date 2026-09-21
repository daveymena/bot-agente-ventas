"""
Modelo de catálogo universal.

Un mismo objeto representa un PRODUCTO (físico o digital) o un SERVICIO
(consulta, corte de cabello, mantenimiento, asesoría, alquiler, plan...).
El campo `tipo` y los atributos libres hacen que sirva para cualquier negocio.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from utils.texto import formatear_precio, normalizar, raiz, tokenizar

# Valores canónicos de disponibilidad y su etiqueta legible
DISPONIBILIDAD_ETIQUETAS = {
    "disponible": "Disponible",
    "agotado": "Agotado por ahora",
    "bajo_pedido": "Bajo pedido",
    "por_agenda": "Se agenda cita",
    "preventa": "Preventa",
    "consultar": "A consultar",
}
DISPONIBLES_OK = {"disponible", "bajo_pedido", "por_agenda", "preventa", "consultar"}

TIPOS_SERVICIO = {"servicio", "plan", "suscripcion", "suscripción", "cita", "asesoria", "asesoría"}


@dataclass
class CatalogoItem:
    """Un producto o servicio del negocio."""

    nombre: str
    id: str = ""
    tipo: str = "producto"          # producto | servicio | plan | inmueble | plato | curso...
    categoria: str = ""
    descripcion: str = ""

    # Precio: usa `precio` (numérico) para poder filtrar por presupuesto.
    # Si el precio es variable ("desde", "según medidas"), usa precio_texto.
    precio: Optional[float] = None
    precio_texto: str = ""
    moneda: str = "COP"

    disponibilidad: str = "disponible"
    stock: Optional[int] = None

    # Propios de servicios
    duracion: str = ""
    modalidad: str = ""             # presencial | virtual | domicilio | mixta
    incluye: List[str] = field(default_factory=list)
    requisitos: str = ""
    agenda: str = ""                # nota de agenda: "citas de lunes a viernes"

    # Comercial
    imagen: Optional[str] = None
    url: str = ""
    promocion: str = ""
    garantia: str = ""
    entrega: str = ""
    etiquetas: List[str] = field(default_factory=list)
    sinonimos: List[str] = field(default_factory=list)
    atributos: Dict[str, str] = field(default_factory=dict)
    destacado: bool = False
    fuente: str = "local"           # local | scraping:<url> | manual
    extra: Dict[str, Any] = field(default_factory=dict)
    # compatibilidad con versiones anteriores del proyecto
    tienda: str = ""

    # ------------------------------------------------------------------ init
    def __post_init__(self) -> None:
        self.tipo = (self.tipo or "producto").lower().strip()
        self.disponibilidad = (self.disponibilidad or "disponible").lower().strip().replace(" ", "_")
        self.etiquetas = [str(e) for e in (self.etiquetas or [])]
        self.sinonimos = [str(s) for s in (self.sinonimos or [])]
        self.incluye = [str(i) for i in (self.incluye or [])]
        self.atributos = {str(k): str(v) for k, v in (self.atributos or {}).items()}
        if not self.id:
            self.id = self._generar_id()

    def _generar_id(self) -> str:
        base = normalizar(self.nombre).replace(" ", "-")[:40] or "item"
        sufijo = str(abs(hash((self.nombre, self.tipo))) % 10_000).zfill(4)
        return f"{base}-{sufijo}"

    # ------------------------------------------------------------- propiedades
    @property
    def es_servicio(self) -> bool:
        return self.tipo in TIPOS_SERVICIO

    @property
    def disponible(self) -> bool:
        return self.disponibilidad in DISPONIBLES_OK

    def etiqueta_disponibilidad(self) -> str:
        return DISPONIBILIDAD_ETIQUETAS.get(self.disponibilidad, self.disponibilidad.replace("_", " ").title())

    # ---------------------------------------------------------------- texto
    def precio_legible(self) -> str:
        """
        '$45.000' | 'Desde $45.000' | 'Sin costo' | 'Precio a consultar'.

        Si hay precio numérico manda ese (así el cliente puede filtrar por
        presupuesto), salvo que sea 0 con un texto explicativo (gratis/incluido)
        o que el texto describa un precio variable ('desde...').
        """
        texto = (self.precio_texto or "").strip()
        if self.precio is None:
            return texto or "Precio a consultar"
        if texto and (
            self.precio == 0
            or texto.lower().startswith(("desde", "a partir", "sin costo", "gratis", "incluido"))
        ):
            return texto
        return formatear_precio(self.precio, self.moneda)

    def texto_busqueda(self) -> str:
        """Todo el texto indexable del ítem (para puntuar coincidencias)."""
        partes = [
            self.nombre, self.categoria, self.descripcion, self.tipo,
            " ".join(self.etiquetas), " ".join(self.sinonimos),
            " ".join(f"{k} {v}" for k, v in self.atributos.items()),
            " ".join(self.incluye), self.duracion, self.modalidad,
        ]
        return normalizar(" ".join(p for p in partes if p))

    def tokens(self) -> List[str]:
        return tokenizar(self.texto_busqueda(), quitar_stopwords=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "nombre": self.nombre,
            "tipo": self.tipo,
            "categoria": self.categoria,
            "descripcion": self.descripcion,
            "precio": self.precio,
            "precio_texto": self.precio_texto,
            "precio_legible": self.precio_legible(),
            "moneda": self.moneda,
            "disponibilidad": self.disponibilidad,
            "disponibilidad_legible": self.etiqueta_disponibilidad(),
            "stock": self.stock,
            "duracion": self.duracion,
            "modalidad": self.modalidad,
            "incluye": self.incluye,
            "requisitos": self.requisitos,
            "agenda": self.agenda,
            "imagen": self.imagen,
            "url": self.url,
            "promocion": self.promocion,
            "garantia": self.garantia,
            "entrega": self.entrega,
            "etiquetas": self.etiquetas,
            "sinonimos": self.sinonimos,
            "atributos": self.atributos,
            "destacado": self.destacado,
            "fuente": self.fuente,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], **overrides: Any) -> "CatalogoItem":
        """Acepta claves en español e inglés y descarta las desconocidas."""
        if not isinstance(data, dict):
            raise TypeError(f"Se esperaba un objeto para el ítem del catálogo, llegó: {type(data)}")

        alias = {
            "title": "nombre", "name": "nombre", "titulo": "nombre", "producto": "nombre",
            "servicio": "nombre", "item": "nombre",
            "type": "tipo", "kind": "tipo",
            "category": "categoria", "rubro": "categoria", "seccion": "categoria",
            "description": "descripcion", "detalle": "descripcion", "resumen": "descripcion",
            "price": "precio", "valor": "precio", "precio_cop": "precio",
            "precioTexto": "precio_texto", "precio_string": "precio_texto",
            "currency": "moneda",
            "available": "disponibilidad", "status": "disponibilidad",
            "talla": "atributos", "color": "atributos",
            "duration": "duracion", "tiempo": "duracion",
            "mode": "modalidad",
            "image": "imagen", "foto": "imagen", "imagen_url": "imagen",
            "link": "url", "enlace": "url", "permalink": "url",
            "discount": "promocion", "promo": "promocion", "oferta": "promocion",
            "warranty": "garantia",
            "shipping": "entrega", "envio": "entrega",
            "tags": "etiquetas", "keywords": "etiquetas", "palabras_clave": "etiquetas",
            "synonyms": "sinonimos", "alias": "sinonimos", "variantes": "sinonimos",
            "attributes": "atributos", "specs": "atributos", "caracteristicas": "atributos",
            "featured": "destacado", "popular": "destacado",
            "store": "tienda",
        }
        plano: Dict[str, Any] = {}
        for clave, valor in data.items():
            clave_norm = alias.get(clave, clave)
            if clave_norm == "atributos" and not isinstance(valor, dict):
                continue
            plano[clave_norm] = valor
        plano.update({k: v for k, v in overrides.items() if v is not None})

        # Coerción de tipos
        if plano.get("precio") is not None:
            from utils.texto import parsear_numero

            valor = plano["precio"]
            if isinstance(valor, str):
                plano["precio"] = parsear_numero(valor) if not valor.strip().lower().startswith(
                    ("desde", "a partir", "segun", "según", "consultar", "variable")
                ) else None
                if plano["precio"] is None and not plano.get("precio_texto"):
                    plano["precio_texto"] = valor.strip()
            else:
                try:
                    plano["precio"] = float(valor)
                except (TypeError, ValueError):
                    plano["precio"] = None
        for lista in ("etiquetas", "sinonimos", "incluye"):
            valor = plano.get(lista)
            if isinstance(valor, str):
                plano[lista] = [v.strip() for v in valor.split(",") if v.strip()]
            elif valor is None:
                plano[lista] = []
        for campo in ("atributos",):
            if not isinstance(plano.get(campo), dict):
                plano[campo] = {}
        if isinstance(plano.get("destacado"), str):
            plano["destacado"] = plano["destacado"].strip().lower() in {"1", "true", "si", "sí", "yes"}
        if isinstance(plano.get("stock"), str) and plano["stock"].isdigit():
            plano["stock"] = int(plano["stock"])
        if not plano.get("nombre"):
            raise ValueError(f"Ítem del catálogo sin nombre: {data}")

        campos_validos = {
            "id", "nombre", "tipo", "categoria", "descripcion", "precio", "precio_texto",
            "moneda", "disponibilidad", "stock", "duracion", "modalidad", "incluye",
            "requisitos", "agenda", "imagen", "url", "promocion", "garantia", "entrega",
            "etiquetas", "sinonimos", "atributos", "destacado", "fuente", "extra", "tienda",
        }
        limpio = {k: v for k, v in plano.items() if k in campos_validos}
        sobrantes = {k: v for k, v in plano.items() if k not in campos_validos and k not in {"precio_legible", "disponibilidad_legible"}}
        if sobrantes:
            limpio.setdefault("extra", {})
            if isinstance(limpio["extra"], dict):
                limpio["extra"].update(sobrantes)
        return cls(**limpio)

    # ------------------------------------------------------------- búsqueda
    def coincide_con_texto(self, texto: str) -> bool:
        """¿Algún token del texto aparece en el nombre/etiquetas del ítem?"""
        tokens_item = {raiz(t) for t in tokenizar(self.texto_busqueda(), quitar_stopwords=False)}
        for t in tokenizar(texto):
            if t in tokens_item:
                return True
        return False

    def get_display_info(self) -> str:
        """Una línea para listados: '💻 Laptop X — $2.500.000'"""
        from utils.helpers import emoji_para

        partes = [f"{emoji_para(self)} {self.nombre}"]
        partes.append(f"— {self.precio_legible()}")
        if self.es_servicio and self.duracion:
            partes.append(f"· {self.duracion}")
        if not self.disponible:
            partes.append(f"· {self.etiqueta_disponibilidad()}")
        return " ".join(partes)

    def get_detailed_info(self) -> str:
        """Ficha completa en texto plano (histórico del proyecto)."""
        return self.ficha()

    def ficha(self, max_descripcion: int = 320) -> str:
        """Ficha formateada para WhatsApp, adaptada a producto o servicio."""
        lineas: List[str] = []
        encabezado = "🛠️" if self.es_servicio else "📦"
        lineas.append(f"{encabezado} *{self.nombre}*")
        if self.categoria:
            lineas.append(f"🏷️ {self.categoria}")
        if self.descripcion:
            desc = self.descripcion.strip()
            if len(desc) > max_descripcion:
                desc = desc[:max_descripcion].rsplit(" ", 1)[0] + "…"
            lineas.append(desc)
        lineas.append(f"💰 {self.precio_legible()}")
        if self.promocion:
            lineas.append(f"🎉 {self.promocion}")
        icono_disp = "📅" if self.es_servicio else "📦"
        lineas.append(f"{icono_disp} {self.etiqueta_disponibilidad()}")
        if self.stock is not None and self.stock > 0:
            lineas.append(f"🔢 Quedan {self.stock}")
        if self.duracion:
            lineas.append(f"⏱️ Duración: {self.duracion}")
        if self.modalidad:
            lineas.append(f"📍 Modalidad: {self.modalidad}")
        if self.incluye:
            lineas.append("✅ Incluye: " + ", ".join(self.incluye))
        if self.requisitos:
            lineas.append(f"📋 Requisitos: {self.requisitos}")
        if self.garantia:
            lineas.append(f"🛡️ Garantía: {self.garantia}")
        if self.entrega:
            lineas.append(f"🚚 Entrega: {self.entrega}")
        if self.atributos:
            detalles = ", ".join(f"{k}: {v}" for k, v in list(self.atributos.items())[:6])
            lineas.append(f"ℹ️ {detalles}")
        return "\n".join(lineas)


# Alias para compatibilidad con el código/documentación anterior
Product = CatalogoItem
