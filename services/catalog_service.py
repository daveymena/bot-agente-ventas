"""
Búsqueda y ranking en el catálogo del negocio.

Aquí está la pieza que hace que las respuestas "peguen" con lo que el cliente
pregunta: puntúa cada producto/servicio contra el texto del cliente mezclando
coincidencia exacta, tokens, sinónimos, etiquetas, categoría, descripción y
similitud aproximada (para errores de tipeo). Funciona igual para productos y
para servicios, porque el modelo es el mismo.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence

from config.business import Negocio
from config.settings import settings
from models.catalog import CatalogoItem
from utils.texto import normalizar, raiz, similitud, tokenizar

logger = logging.getLogger(__name__)

# Palabras que indican que el cliente quiere un servicio (aunque el negocio sea mixto)
PISTAS_SERVICIO = {
    "servicio", "cita", "agendar", "agenda", "turno", "reserva", "reservar", "consulta",
    "asesoria", "asesoría", "instalacion", "instalación", "mantenimiento", "reparacion",
    "reparación", "arreglo", "domicilio", "visita", "atencion", "atención", "presupuesto",
    "cotizacion", "cotización", "plan", "mensualidad",
}
PISTAS_PRODUCTO = {
    "comprar", "compra", "precio", "vale", "cuanto", "cuánto", "stock", "unidad",
    "unidades", "envio", "envío", "producto", "referencia", "modelo",
}
ORDEN_PRECIO_ASC = {"barato", "barata", "baratos", "economico", "económico", "economicos",
                    "mas barato", "más barato", "menor precio", "rango bajo", "lowcost"}
ORDEN_PRECIO_DESC = {"caro", "caros", "premium", "mas caro", "más caro", "mayor precio",
                     "alta gama", "top", "gama alta"}


@dataclass
class Resultado:
    """
    Ítem con su puntaje de coincidencia.

    `puntaje` mide SOLO qué tan bien encaja con lo que pidió el cliente (frase,
    tokens, sinónimos, typos, cobertura).
    `ajuste` son señales comerciales (destacado, promoción, presupuesto,
    agotado). Se separan para que un ítem agotado siga siendo "encontrado" y el
    agente pueda responder "está agotado" en vez de "no lo tengo".
    """

    item: CatalogoItem
    puntaje: float
    razones: List[str]
    ajuste: float = 0.0
    # True si el cliente nombró una palabra que está literalmente en el nombre
    exacto: bool = False

    @property
    def orden(self) -> float:
        return round(self.puntaje + self.ajuste, 4)

    @property
    def coincide_fuerte(self) -> bool:
        return self.exacto or self.puntaje >= settings.MATCH_THRESHOLD


class CatalogoService:
    """Acceso y búsqueda sobre el catálogo del negocio."""

    def __init__(self, negocio: Negocio):
        self.negocio = negocio
        self._indice: Dict[str, Dict[str, set]] = {}
        self._reconstruir()

    # ------------------------------------------------------------- indexación
    def _reconstruir(self) -> None:
        self._indice = {}
        for item in self.negocio.catalogo:
            self._indice[item.id] = {
                "nombre": {raiz(t) for t in tokenizar(item.nombre, quitar_stopwords=False)},
                "etiquetas": {
                    raiz(t)
                    for t in tokenizar(" ".join(item.etiquetas + item.sinonimos), quitar_stopwords=False)
                },
                "categoria": {raiz(t) for t in tokenizar(item.categoria or "", quitar_stopwords=False)},
                "descripcion": {raiz(t) for t in tokenizar(item.descripcion or "")},
                "atributos": {
                    raiz(t)
                    for t in tokenizar(
                        " ".join(f"{k} {v}" for k, v in item.atributos.items()) or "",
                        quitar_stopwords=False,
                    )
                },
            }

    def recargar(self, negocio: Optional[Negocio] = None) -> bool:
        """Vuelve a indexar (tras editar negocio.json o refrescar por scraping)."""
        if negocio is not None:
            self.negocio = negocio
        self._reconstruir()
        logger.info("Catálogo indexado: %s ítems", len(self.negocio.catalogo))
        return True

    # ------------------------------------------------------------------ acceso
    def todos(self) -> List[CatalogoItem]:
        return list(self.negocio.catalogo)

    def total(self) -> int:
        return len(self.negocio.catalogo)

    def por_id(self, id_item: str) -> Optional[CatalogoItem]:
        id_norm = normalizar(id_item).replace(" ", "-")
        for item in self.negocio.catalogo:
            if item.id == id_item or normalizar(item.id) == id_norm:
                return item
        return None

    def por_tipo(self, tipo: str) -> List[CatalogoItem]:
        tipo = (tipo or "").lower()
        if tipo in {"servicio", "servicios"}:
            return [i for i in self.negocio.catalogo if i.es_servicio]
        if tipo in {"producto", "productos"}:
            return [i for i in self.negocio.catalogo if not i.es_servicio]
        return self.todos()

    def destacados(self, limite: int = 5) -> List[CatalogoItem]:
        marcados = [i for i in self.negocio.catalogo if i.destacado and i.disponible]
        if len(marcados) >= limite:
            return marcados[:limite]
        # Si no hay marcados, mezcla de productos y servicios disponibles
        resto = [i for i in self.negocio.catalogo if i.disponible and i not in marcados]
        return (marcados + resto)[:limite]

    def categorias(self, limite: int = 12) -> List[str]:
        conteo = self.negocio.categorias_con_items()
        return list(conteo.keys())[:limite]

    def por_categoria(self, categoria: str, limite: int = 6) -> List[CatalogoItem]:
        cat_norm = normalizar(categoria)
        salida = []
        for item in self.negocio.catalogo:
            if cat_norm and (cat_norm in normalizar(item.categoria) or cat_norm in normalizar(item.nombre)):
                salida.append(item)
        return salida[:limite]

    def mas_economico(self, tipo: Optional[str] = None, limite: int = 3) -> List[CatalogoItem]:
        items = [i for i in self.por_tipo(tipo or "todos") if i.precio is not None and i.disponible]
        return sorted(items, key=lambda i: i.precio or 0)[:limite]

    # ------------------------------------------------------------------ búsqueda
    def _puntuar(self, item: CatalogoItem, consulta: str, tokens: Sequence[str]) -> Resultado:
        idx = self._indice.get(item.id, {})
        nombre_norm = normalizar(item.nombre)
        consulta_norm = normalizar(consulta)
        puntaje = 0.0
        ajuste = 0.0
        razones: List[str] = []
        aciertos = 0
        aciertos_nombre = 0

        # 1) coincidencia de frase completa en el nombre (lo más fuerte)
        if consulta_norm and consulta_norm in nombre_norm:
            puntaje += 0.60
            aciertos = len(tokens)
            aciertos_nombre = len(tokens)
            razones.append("nombre contiene la frase")
        elif nombre_norm and nombre_norm in consulta_norm:
            puntaje += 0.45
            aciertos_nombre = 1
            razones.append("nombre completo mencionado")

        # 2) por token
        for token in tokens:
            if token in idx.get("nombre", set()):
                puntaje += 0.45
                aciertos += 1
                aciertos_nombre += 1
                razones.append(f"nombre~{token}")
                continue
            if token in idx.get("etiquetas", set()):
                puntaje += 0.34
                aciertos += 1
                aciertos_nombre += 1
                razones.append(f"etiqueta~{token}")
                continue
            if token in idx.get("categoria", set()):
                puntaje += 0.24
                aciertos += 1
                continue
            if token in idx.get("atributos", set()):
                puntaje += 0.16
                aciertos += 1
                continue
            if token in idx.get("descripcion", set()):
                puntaje += 0.12
                aciertos += 1
                continue
            # 3) similitud aproximada (typos: "ipone" -> "iphone")
            for candidato in list(idx.get("nombre", set())) + list(idx.get("etiquetas", set())):
                if similitud(token, candidato) >= 0.82:
                    puntaje += 0.25
                    aciertos += 1
                    aciertos_nombre += 1
                    razones.append(f"parecido~{token}≈{candidato}")
                    break

        # 4) cobertura: qué proporción de lo que pidió se cubrió (suave, para desempatar)
        if tokens:
            cobertura = aciertos / len(tokens)
            puntaje *= 0.72 + 0.28 * cobertura
            if cobertura < 0.25 and aciertos_nombre == 0:
                puntaje *= 0.7
            # varios ítems tocados: sube si acertó más de una palabra del nombre
            if aciertos_nombre > 1:
                puntaje += 0.06 * (aciertos_nombre - 1)

        # 5) señales comerciales (no afectan "se encontró o no")
        if item.destacado:
            ajuste += 0.10
        if item.promocion:
            ajuste += 0.06
        if not item.disponible:
            ajuste -= 0.12
        if item.stock is not None and item.stock <= 0:
            ajuste -= 0.08

        return Resultado(
            item=item,
            puntaje=round(min(puntaje, 1.0), 4),
            razones=razones,
            ajuste=round(ajuste, 4),
            exacto=aciertos_nombre > 0,
        )

    def buscar(
        self,
        consulta: str,
        limite: Optional[int] = None,
        presupuesto: Optional[float] = None,
        tipo_preferido: Optional[str] = None,
        orden: str = "relevancia",
        incluir_agotados: bool = True,
    ) -> List[Resultado]:
        """
        Devuelve los ítems más parecidos a lo que pidió el cliente.

        orden: relevancia | precio_asc | precio_desc
        """
        limite = limite or settings.MAX_ITEMS_IN_REPLY
        tokens = tokenizar(consulta)
        if not tokens and not consulta.strip():
            return []

        resultados: List[Resultado] = []
        for item in self.negocio.catalogo:
            if not incluir_agotados and not item.disponible:
                continue
            resultado = self._puntuar(item, consulta, tokens)
            if resultado.puntaje <= 0:
                continue

            # Filtro por tipo (servicio vs producto) cuando el cliente lo pide
            if tipo_preferido == "servicio" and item.es_servicio:
                resultado.ajuste += 0.10
            elif tipo_preferido == "producto" and not item.es_servicio:
                resultado.ajuste += 0.10

            # Ajuste por presupuesto: si se pasa mucho del monto, no se ofrece
            if presupuesto is not None and presupuesto > 0 and item.precio is not None:
                if item.precio <= presupuesto:
                    resultado.ajuste += 0.12
                    resultado.razones.append("dentro del presupuesto")
                elif item.precio <= presupuesto * 1.2:
                    resultado.razones.append("apenas sobre el presupuesto")
                elif item.precio > presupuesto * 1.5:
                    continue  # ni se muestra: está claramente fuera de rango
                else:
                    resultado.ajuste -= 0.25
                    resultado.razones.append("sobre el presupuesto")

            if resultado.puntaje >= 0.08 or resultado.coincide_fuerte:
                resultados.append(resultado)

        if orden == "precio_asc":
            resultados.sort(key=lambda r: (r.item.precio is None, r.item.precio or 0))
        elif orden == "precio_desc":
            resultados.sort(key=lambda r: (r.item.precio is None, -(r.item.precio or 0)))
        else:
            resultados.sort(key=lambda r: (-r.orden, r.item.precio if r.item.precio is not None else 0))

        return resultados[:limite]

    # ---------------------------------------------------------------- atajos
    def mejor(self, consulta: str, presupuesto: Optional[float] = None) -> Optional[Resultado]:
        resultados = self.buscar(consulta, limite=3, presupuesto=presupuesto)
        if not resultados:
            return None
        mejor = resultados[0]
        return mejor if mejor.coincide_fuerte else None

    def coincidencias_fuertes(self, consulta: str, limite: int = 5) -> List[Resultado]:
        return [r for r in self.buscar(consulta, limite=limite) if r.coincide_fuerte]

    def interpretar_orden(self, consulta: str) -> str:
        t = normalizar(consulta)
        if any(p in t for p in ORDEN_PRECIO_ASC):
            return "precio_asc"
        if any(p in t for p in ORDEN_PRECIO_DESC):
            return "precio_desc"
        return "relevancia"

    def tipo_sugerido(self, consulta: str) -> Optional[str]:
        t = normalizar(consulta)
        pistas_servicio = {normalizar(p) for p in PISTAS_SERVICIO}
        pistas_producto = {normalizar(p) for p in PISTAS_PRODUCTO}
        if any(p in t for p in pistas_servicio):
            return "servicio"
        if any(p in t for p in pistas_producto):
            return "producto"
        return None

    # ------------------------------------------------------------- estadísticas
    def resumen(self) -> Dict[str, object]:
        servicios = [i for i in self.negocio.catalogo if i.es_servicio]
        productos = [i for i in self.negocio.catalogo if not i.es_servicio]
        return {
            "total": len(self.negocio.catalogo),
            "servicios": len(servicios),
            "productos": len(productos),
            "categorias": self.negocio.categorias_con_items(),
            "agotados": sum(1 for i in self.negocio.catalogo if not i.disponible),
            "con_precio": sum(1 for i in self.negocio.catalogo if i.precio is not None),
        }

    def contexto_para_ia(self, resultados: Iterable[Resultado], maximo: int = 6) -> str:
        """Bloque de datos verificados que se le pasa a la IA (evita inventos)."""
        lineas = []
        for r in list(resultados)[:maximo]:
            item = r.item
            detalles = [f"{item.nombre} ({item.tipo})", f"precio: {item.precio_legible()}",
                        f"disponibilidad: {item.etiqueta_disponibilidad()}"]
            if item.categoria:
                detalles.append(f"categoría: {item.categoria}")
            if item.duracion:
                detalles.append(f"duración: {item.duracion}")
            if item.descripcion:
                detalles.append(f"descripción: {item.descripcion[:160]}")
            lineas.append("- " + " | ".join(detalles))
        return "\n".join(lineas)
