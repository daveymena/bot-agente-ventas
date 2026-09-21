"""
Utilidades generales del agente (sirven para cualquier rubro).
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional

from utils.texto import (  # noqa: F401  (reexportadas por comodidad)
    ahora,
    contiene_alguna,
    formatear_precio,
    normalizar,
    parsear_numero,
    raiz,
    recortar,
    similitud,
    sin_acentos,
    titulo,
    tokenizar,
    unir,
)

# Emojis por tipo/categoría: se eligen por palabras del propio catálogo, así
# funciona con cualquier negocio sin configuración extra.
EMOJIS_POR_PALABRA = [
    (("laptop", "portatil", "computador", "pc", "notebook", "monitor"), "💻"),
    (("celular", "telefono", "smartphone", "iphone", "galaxy", "tablet"), "📱"),
    (("audifono", "auricular", "parlante", "bocina", "sonido"), "🎧"),
    (("cargador", "cable", "adaptador", "usb", "bateria", "power"), "🔌"),
    (("camara", "foto", "video", "dron"), "📷"),
    (("impresora", "toner", "tinta", "escaner"), "🖨️"),
    (("teclado", "mouse", "gamer", "consola", "control"), "🎮"),
    (("corte", "cabello", "barber", "peluqueria", "uñas", "manicure", "estetica", "spa"), "💅"),
    (("comida", "plato", "almuerzo", "cena", "desayuno", "pizza", "hamburguesa", "restaurante"), "🍽️"),
    (("bebida", "cafe", "jugo", "cerveza", "postre", "helado"), "🥤"),
    (("carro", "moto", "vehiculo", "llanta", "motor", "aceite", "taller", "frenos"), "🚗"),
    (("casa", "apartamento", "inmueble", "arriendo", "lote", "oficina"), "🏠"),
    (("salud", "medico", "odontolog", "dental", "consulta", "terapia", "clinica", "examen"), "🩺"),
    (("curso", "clase", "taller de", "capacitacion", "certificacion", "idiomas"), "🎓"),
    (("instalacion", "mantenimiento", "reparacion", "soporte", "arreglo", "revision"), "🛠️"),
    (("envio", "domicilio", "entrega", "mensajeria"), "🚚"),
    (("gimnasio", "entrenamiento", "fitness", "yoga", "pilates"), "🏋️"),
    (("ropa", "camisa", "zapatos", "tenis", "moda", "vestido"), "👕"),
    (("abogado", "contador", "asesoria", "consultoria", "tramite", "notaria"), "⚖️"),
    (("viaje", "tour", "hotel", "tiquete", "vuelo", "pasadia"), "✈️"),
    (("evento", "fiesta", "catering", "sonido profesional", "decoracion", "dj"), "🎉"),
    (("seguro", "poliza", "financiero", "credito", "prestamo"), "🛡️"),
]


def emoji_para(item: Any) -> str:
    """Emoji razonable para un ítem del catálogo, según su texto."""
    texto = " ".join([
        getattr(item, "nombre", "") or "",
        getattr(item, "categoria", "") or "",
        getattr(item, "tipo", "") or "",
        " ".join(getattr(item, "etiquetas", []) or []),
    ])
    t = normalizar(texto)
    for palabras, emoji in EMOJIS_POR_PALABRA:
        for palabra in palabras:
            if normalizar(palabra) in t:
                return emoji
    return "🛠️" if getattr(item, "es_servicio", False) else "📦"


def limpiar_texto(texto: str) -> str:
    """Normaliza espacios y quita caracteres de control."""
    if not texto:
        return ""
    limpio = re.sub(r"[\u0000-\u0008\u000b\u000c\u000e-\u001f]", "", str(texto))
    return re.sub(r"[ \t]{2,}", " ", limpio).strip()


def url_valida(url: Optional[str]) -> bool:
    if not url:
        return False
    return bool(re.match(r"^https?://[^\s]+$", url.strip(), re.IGNORECASE))


def dividir_en_bloques(texto: str, maximo: int = 900) -> List[str]:
    """Divide un texto largo en bloques que WhatsApp pueda leer cómodo."""
    if not texto:
        return []
    if len(texto) <= maximo:
        return [texto]
    bloques: List[str] = []
    actual = ""
    for parrafo in texto.split("\n\n"):
        if len(actual) + len(parrafo) + 2 <= maximo:
            actual = f"{actual}\n\n{parrafo}" if actual else parrafo
        else:
            if actual:
                bloques.append(actual)
            actual = parrafo
    if actual:
        bloques.append(actual)
    return bloques


def resumir_para_aviso(texto: str, limite: int = 200) -> str:
    """Texto corto para el aviso que recibe el dueño del negocio."""
    return recortar(limpiar_texto(texto), limite)


def extraer_numero(texto: str, pais: str = "57") -> Optional[str]:
    """Extrae un teléfono de un texto libre ('mi numero es 300 111 2233')."""
    digitos = re.sub(r"\D", "", texto or "")
    if len(digitos) == 10:
        return f"{pais}{digitos}"
    if len(digitos) == 12 and digitos.startswith(pais):
        return digitos
    if 11 <= len(digitos) <= 15:
        return digitos
    return None


def deduplicar(items: Iterable[Any], clave=lambda x: x) -> List[Any]:
    vistos = set()
    salida = []
    for item in items:
        k = clave(item)
        if k in vistos:
            continue
        vistos.add(k)
        salida.append(item)
    return salida


def calcular_metricas_negocio(catalogo_items: List[Any]) -> Dict[str, Any]:
    """Resumen del catálogo útil para el panel y el endpoint /estado."""
    productos = [i for i in catalogo_items if not getattr(i, "es_servicio", False)]
    servicios = [i for i in catalogo_items if getattr(i, "es_servicio", False)]
    con_precio = [i for i in catalogo_items if getattr(i, "precio", None) is not None]
    precios = [i.precio for i in con_precio]

    def promedio(valores: List[float]) -> Optional[float]:
        return round(sum(valores) / len(valores), 2) if valores else None

    return {
        "total_items": len(catalogo_items),
        "productos": len(productos),
        "servicios": len(servicios),
        "con_precio": len(con_precio),
        "precio_promedio": promedio(precios),
        "precio_min": min(precios) if precios else None,
        "precio_max": max(precios) if precios else None,
    }
