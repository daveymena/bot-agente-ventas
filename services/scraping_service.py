"""
Importación del catálogo desde la web del negocio (OPCIONAL).

El agente funciona sin esto: el catálogo normalmente vive en config/negocio.json.
Si el negocio ya tiene su catálogo publicado en una web, se pueden declarar
fuentes en el JSON (`fuentes_scraping`) y refrescar la lista de ítems con:

    POST /catalogo/importar-web

Cada fuente se describe así (sin programar nada específico de un rubro):

    {
      "nombre": "MegaComputer",
      "url": "https://megacomputer.com.co/",
      "selector": "h2, h3, .product-title, .producto h3",   // opcional
      "paginas": 1,                                          // opcional
      "tipo": "producto"                                     // o "servicio"
    }

Solo se importan nombres (y precio si logra detectarse en la tarjeta del
producto). Es a propósito conservador: preferimos no inventar precios.
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

from config.settings import settings
from models.catalog import CatalogoItem

logger = logging.getLogger(__name__)

try:
    import aiohttp
except Exception:  # pragma: no cover
    aiohttp = None  # type: ignore

try:
    from bs4 import BeautifulSoup
    _TIENE_BS4 = True
except Exception:  # pragma: no cover
    BeautifulSoup = None  # type: ignore
    _TIENE_BS4 = False

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
)

# Palabras de navegación que NO son productos
RUIDO = {
    "inicio", "home", "contacto", "nosotros", "servicios", "productos", "categorias",
    "categorías", "blog", "carrito", "mi cuenta", "buscar", "menu", "menú", "ofertas",
    "quienes somos", "preguntas frecuentes", "politica", "política", "terminos",
    "términos", "envios", "envíos", "siguenos", "síguenos",
}

# Precio tipo $45.000 / 45.000 / $45,000.00 / USD 45
PRECIO_RE = re.compile(
    r"(?:US\$|USD|\$|COP|MXN|ARS|CLP|PEN)\s?([\d][\d.,]{2,})|([\d][\d.,]{3,})\s?(?:COP|USD|pesos)",
    re.IGNORECASE,
)


def _limpiar(texto: str) -> str:
    return re.sub(r"\s+", " ", (texto or "")).strip()


def _precio_de(texto: str) -> Optional[float]:
    coincidencia = PRECIO_RE.search(texto or "")
    if not coincidencia:
        return None
    crudo = coincidencia.group(1) or coincidencia.group(2) or ""
    from utils.texto import parsear_numero

    valor = parsear_numero(crudo)
    return valor if valor and valor > 0 else None


def _es_producto(nombre: str) -> bool:
    if not nombre:
        return False
    letras = re.sub(r"[^A-Za-zÁÉÍÓÚÑáéíóúñ]", "", nombre)
    if len(letras) < 3:
        return False
    if nombre.strip().lower() in RUIDO:
        return False
    if len(nombre) > 160:
        return False
    return True


class ScrapingService:
    """Lee las fuentes declaradas por el negocio y devuelve ítems de catálogo."""

    def __init__(self) -> None:
        self.timeout = settings.SCRAPE_TIMEOUT
        self.session: Optional["aiohttp.ClientSession"] = None

    @property
    def disponible(self) -> bool:
        return aiohttp is not None and _TIENE_BS4

    async def _sesion(self) -> "aiohttp.ClientSession":
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={"User-Agent": USER_AGENT, "Accept-Language": "es-CO,es;q=0.9"}
            )
        return self.session

    async def cerrar(self) -> None:
        if self.session and not self.session.closed:
            await self.session.close()
        self.session = None

    # ------------------------------------------------------------------ lectura
    async def _html(self, url: str) -> str:
        sesion = await self._sesion()
        async with sesion.get(url, timeout=self.timeout) as respuesta:
            if respuesta.status != 200:
                logger.warning("La fuente %s respondió %s", url, respuesta.status)
                return ""
            return await respuesta.text(errors="ignore")

    def _extraer(self, html: str, fuente: Dict[str, Any]) -> List[CatalogoItem]:
        sopa = BeautifulSoup(html, "html.parser")
        selector = fuente.get("selector") or fuente.get("selectores")
        if selector:
            nodos = sopa.select(selector)
        else:
            # sin selector: títulos de producto típicos
            nodos = sopa.select("h1, h2, h3, .product-title, .producto, [class*=product] h2")

        nombre_fuente = fuente.get("nombre") or urlparse(fuente.get("url", "")).netloc
        tipo = str(fuente.get("tipo") or "producto").lower()
        items: List[CatalogoItem] = []
        vistos = set()

        for nodo in nodos[:120]:
            nombre = _limpiar(nodo.get_text(" "))
            if not _es_producto(nombre):
                continue
            clave = nombre.lower()
            if clave in vistos:
                continue
            vistos.add(clave)

            # Buscamos el precio en la tarjeta contenedora (sin inventar nada)
            contenedor = nodo.find_parent(class_=re.compile(r"product|card|item|producto", re.I)) or nodo
            precio = _precio_de(contenedor.get_text(" ")) or _precio_de(nombre)

            enlace = ""
            ancla = nodo if nodo.name == "a" else nodo.find("a")
            if ancla is not None and ancla.get("href"):
                enlace = urljoin(fuente.get("url", ""), ancla["href"])

            imagen = None
            img = contenedor.find("img") if hasattr(contenedor, "find") else None
            if img is not None:
                candidato = img.get("src") or img.get("data-src") or ""
                if candidato and not candidato.startswith("data:"):
                    imagen = urljoin(fuente.get("url", ""), candidato)

            items.append(CatalogoItem(
                nombre=nombre[:160],
                tipo=tipo if tipo in {"producto", "servicio"} else "producto",
                precio=precio,
                precio_texto="" if precio else "Precio a consultar en tienda",
                imagen=imagen,
                url=enlace,
                tienda=nombre_fuente,
                fuente=f"scraping:{fuente.get('url','')}",
                etiquetas=[nombre_fuente.lower()] if nombre_fuente else [],
            ))
        logger.info("Fuente %s: %s ítems importados", nombre_fuente, len(items))
        return items

    async def importar_fuentes(self, fuentes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Importa todas las fuentes declaradas por el negocio en paralelo."""
        if not fuentes:
            return {"ok": False, "motivo": "el negocio no tiene 'fuentes_scraping' configuradas", "items": []}
        if not self.disponible:
            return {"ok": False, "motivo": "faltan dependencias (aiohttp/beautifulsoup4)", "items": []}

        tareas = [self._leer_fuente(f) for f in fuentes]
        resultados = await asyncio.gather(*tareas, return_exceptions=True)

        items: List[CatalogoItem] = []
        detalle = []
        for fuente, resultado in zip(fuentes, resultados):
            nombre = fuente.get("nombre") or fuente.get("url", "?")
            if isinstance(resultado, Exception):
                detalle.append({"fuente": nombre, "error": str(resultado), "items": 0})
                continue
            items.extend(resultado)
            detalle.append({"fuente": nombre, "items": len(resultado), "url": fuente.get("url")})

        return {"ok": True, "total": len(items), "detalle": detalle, "items": items}

    async def _leer_fuente(self, fuente: Dict[str, Any]) -> List[CatalogoItem]:
        url = fuente.get("url")
        if not url:
            return []
        html = await self._html(url)
        if not html:
            return []
        items = self._extraer(html, fuente)

        paginas = int(fuente.get("paginas") or 1)
        for numero in range(2, min(paginas, 5) + 1):
            siguiente = fuente.get("url_paginada") or f"{url.rstrip('/')}/page/{numero}"
            html = await self._html(siguiente)
            if not html:
                break
            items.extend(self._extraer(html, fuente))
        return items
