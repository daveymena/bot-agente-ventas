"""
Utilidades de texto: normalización, tokenización, números y moneda.

Sirven para cualquier rubro: no hay listas de palabras "tecnológicas" ni
supuestos sobre el tipo de negocio.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Iterable, List, Optional, Sequence

# Palabras vacías del español (no aportan a la búsqueda de un producto/servicio)
STOPWORDS = {
    "a", "al", "algo", "algun", "alguna", "algunas", "alguno", "algunos", "ante", "antes",
    "aquel", "aquella", "aquello", "aquellos", "aquí", "asi", "así", "aun", "aunque",
    "bajo", "bastante", "bien", "buen", "buena", "buenas", "bueno", "buenos",
    "cada", "casi", "cierta", "ciertas", "cierto", "ciertos", "como", "cómo", "con",
    "conmigo", "contigo", "cual", "cuál", "cuales", "cuáles", "cualquier", "cuando",
    "cuánto", "cuanto", "cuanta", "cuantos", "de", "del", "demasiado", "desde", "donde",
    "dónde", "dos", "el", "él", "ella", "ellas", "ello", "ellos", "en", "entonces", "entre",
    "era", "eran", "eres", "es", "esa", "esas", "ese", "eso", "esos", "esta", "está",
    "estan", "están", "estar", "estas", "este", "esto", "estos", "estoy", "fue", "ha",
    "han", "has", "hasta", "hay", "la", "las", "le", "les", "lo", "los", "mas", "más",
    "me", "menos", "mi", "mis", "mucho", "muchos", "muy", "nada", "ni", "no", "nos",
    "nosotros", "nuestra", "nuestro", "o", "os", "otra", "otras", "otro", "otros", "para",
    "pero", "poco", "por", "porque", "que", "qué", "quien", "quién", "se", "sea", "según",
    "ser", "si", "sí", "sin", "sobre", "soy", "su", "sus", "tal", "también", "tan", "te",
    "tener", "tengo", "ti", "tiene", "tienen", "todo", "todos", "tu", "tú", "tus", "un",
    "una", "uno", "unos", "usted", "ustedes", "va", "vamos", "van", "varios", "ver", "y",
    "ya", "yo",
    # términos de cortesía/navegación que no identifican un ítem del catálogo
    "hola", "buenas", "buenos", "buen", "dias", "días", "tardes", "noches", "gracias",
    "favor", "podria", "podría", "puede", "pueden", "quisiera", "quiero", "necesito",
    "busco", "buscar", "tienen", "tiene", "haber", "hay", "info", "informacion",
    "información", "precio", "precios", "costo", "costos", "vale", "valen", "cuanto",
    "cuánto", "disponible", "disponibilidad", "stock", "existe", "existencia",
    "opciones", "opcion", "opción", "manejan", "venden", "trabajan", "ofrecen",
}

# Sufijos que se recortan para comparar ("cortes" ~ "corte", "rapados" ~ "rapado")
_SUFIJOS = ("es", "s", "as", "os")


def sin_acentos(texto: str) -> str:
    """Quita tildes/diéresis conservando el resto de caracteres."""
    if not texto:
        return ""
    descompuesto = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


def normalizar(texto: str) -> str:
    """minúsculas, sin acentos, sin signos, espacios simples."""
    if not texto:
        return ""
    t = sin_acentos(str(texto)).lower()
    t = re.sub(r"[^a-z0-9\s\+#\.]", " ", t)  # + y # viven en "corte+", "iphone#13"
    t = re.sub(r"\.(?=\s|$)", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def raiz(palabra: str) -> str:
    """
    Canoniza plurales para que "cortes" y "corte" sean el mismo token.

    Se quita solo la "s" final (la variante "-es" -> "-e" es más segura en
    español: "dientes"->"diente", "cortes"->"corte"). Los casos irregulares
    ("flores" vs "flor") los cubre la coincidencia aproximada.
    """
    if len(palabra) > 3 and palabra.endswith("s") and not palabra.endswith("ss"):
        return palabra[:-1]
    return palabra


def tokenizar(texto: str, quitar_stopwords: bool = True, min_len: int = 2) -> List[str]:
    """Devuelve tokens normalizados y sin duplicados, preservando el orden."""
    tokens: List[str] = []
    for bruto in normalizar(texto).split():
        if bruto.isdigit():
            tokens.append(bruto)
            continue
        if len(bruto) < min_len:
            continue
        if quitar_stopwords and bruto in STOPWORDS:
            continue
        r = raiz(bruto)
        if quitar_stopwords and r in STOPWORDS:
            continue
        tokens.append(r)
    # sin duplicados manteniendo orden
    vistos = set()
    salida = []
    for t in tokens:
        if t not in vistos:
            vistos.add(t)
            salida.append(t)
    return salida


def similitud(a: str, b: str) -> float:
    """Similitud 0..1 entre dos palabras (difflib, tolerante a errores de tipeo)."""
    from difflib import SequenceMatcher

    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if len(a) > 3 and len(b) > 3 and (a.startswith(b) or b.startswith(a)):
        return 0.85
    return SequenceMatcher(None, a, b).ratio()


def contiene_alguna(texto: str, agujas: Iterable[str]) -> Optional[str]:
    """Primera aguja presente en el texto normalizado (o None)."""
    norm = f" {normalizar(texto)} "
    for aguja in agujas:
        if f" {normalizar(aguja)} " in norm:
            return aguja
    return None


# --------------------------------------------------------------------- moneda
_MONEDA_SIMBOLO = {
    "COP": "$", "USD": "US$", "MXN": "$", "ARS": "$", "CLP": "$", "PEN": "S/",
    "BRL": "R$", "EUR": "€", "GBP": "£", "DOP": "RD$", "UYU": "$U",
}

_FORMATO_MILES = {
    "COP": ".", "CLP": ".", "EUR": ".", "ARS": ".", "DOP": ".", "UYU": ".",
    "USD": ",", "MXN": ",", "PEN": ",", "BRL": ".", "GBP": ",",
}


def formatear_precio(valor: Optional[float], moneda: str = "COP", decimales: int = 0) -> str:
    """45000 -> '$45.000' (COP). 1200.5 en USD -> 'US$1,200.50'."""
    if valor is None:
        return ""
    moneda = (moneda or "COP").upper()
    sep_miles = _FORMATO_MILES.get(moneda, ".")
    sep_decimal = "," if sep_miles == "." else "."
    numero = f"{abs(float(valor)):,.{decimales}f}"
    entero, _, decimal = numero.partition(".")
    entero = entero.replace(",", sep_miles)
    texto = f"{entero}{sep_decimal}{decimal}" if (decimales and decimal) else entero
    signo = "-" if valor < 0 else ""
    simbolo = _MONEDA_SIMBOLO.get(moneda, "")
    return f"{signo}{simbolo}{texto}".strip()


_NUM_RE = re.compile(r"(\d+(?:[.,]\d+)*)")


def parsear_numero(texto: str) -> Optional[float]:
    """
    Interpreta montos escritos por un cliente, con puntos o comas:
    '45.000' -> 45000 | '1.200,50' -> 1200.5 | '2 millones' -> 2000000
    '500 mil' -> 500000 | '45k' -> 45000 | '$1,200.50' -> 1200.5

    OJO: se trabaja sobre el texto crudo (sin normalizar) porque normalizar()
    borra las comas y con ellas la información decimal.
    """
    if not texto:
        return None
    t = sin_acentos(str(texto)).lower()

    mult = 1.0
    if re.search(r"millon|millón|millone|millo\b", t):
        mult = 1_000_000.0
    elif re.search(r"\bmil\b|\d\s*k\b|\bk\b", t):
        mult = 1_000.0

    coincidencia = re.search(r"(\d[\d.,]*)", t)
    if not coincidencia:
        return None
    crudo: str = coincidencia.group(1).rstrip(".,")

    if "," in crudo and "." in crudo:
        # el separador que aparece de último es el decimal
        if crudo.rfind(",") > crudo.rfind("."):
            crudo = crudo.replace(".", "").replace(",", ".")
        else:
            crudo = crudo.replace(",", "")
    elif "," in crudo:
        partes = crudo.split(",")
        crudo = crudo.replace(",", ".") if len(partes[-1]) <= 2 else crudo.replace(",", "")
    elif "." in crudo:
        partes = crudo.split(".")
        if all(len(p) == 3 for p in partes[1:]):
            crudo = crudo.replace(".", "")  # 45.000 -> miles
        elif len(partes) > 2:
            crudo = "".join(partes[:-1]) + "." + partes[-1]

    try:
        return float(crudo) * mult
    except ValueError:
        return None


def recortar(texto: str, limite: int, sufijo: str = "…") -> str:
    """Recorta respetando palabras y sin partir emojis/url de forma brusca."""
    if not texto or len(texto) <= limite:
        return texto or ""
    corte = texto[: limite - len(sufijo)]
    if " " in corte:
        corte = corte[: corte.rfind(" ")]
    return corte.rstrip() + sufijo


def titulo(texto: str) -> str:
    """'corte de cabello' -> 'Corte de cabello' (solo primera letra)."""
    if not texto:
        return ""
    return texto[0].upper() + texto[1:]


def ahora() -> datetime:
    return datetime.now()


def unir(items: Sequence[str], sep: str = ", ", ultimo: str = " y ") -> str:
    """Une listas en lenguaje natural: 'a, b y c'."""
    items = [i for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return sep.join(items[:-1]) + ultimo + items[-1]
