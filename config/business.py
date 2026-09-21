"""
Perfil del NEGOCIO (no de la infraestructura).

Carga config/negocio.json: identidad, contacto, horarios, políticas, tono de
respuesta y el catálogo de productos/servicios. Está pensado para que el mismo
agente sirva a una tienda, un restaurante, una barbería, un taller, un
consultorio, una inmobiliaria o una empresa de servicios: solo cambia el JSON.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import settings
from models.catalog import CatalogoItem

logger = logging.getLogger(__name__)

DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
DIAS_ES = {
    "lunes": "Lunes", "martes": "Martes", "miercoles": "Miércoles", "jueves": "Jueves",
    "viernes": "Viernes", "sabado": "Sábado", "domingo": "Domingo",
}
# normalización de variantes con tilde para el JSON
_ALIAS_DIA = {
    "miércoles": "miercoles", "sábado": "sabado", "sabados": "sabado", "lun": "lunes",
    "mar": "martes", "mie": "miercoles", "jue": "jueves", "vie": "viernes", "sab": "sabado",
    "dom": "domingo", "weekend": "sabado",
}


@dataclass
class Horario:
    dia: str
    abre: str = ""
    cierra: str = ""
    cerrado: bool = False
    nota: str = ""

    def legible(self) -> str:
        if self.cerrado or (not self.abre and not self.cierra):
            return f"{DIAS_ES.get(self.dia, self.dia)}: cerrado"
        base = f"{DIAS_ES.get(self.dia, self.dia)}: {self.abre} - {self.cierra}"
        return f"{base} ({self.nota})" if self.nota else base

    def to_dict(self) -> Dict[str, Any]:
        return {"dia": self.dia, "abre": self.abre, "cierra": self.cierra,
                "cerrado": self.cerrado, "nota": self.nota, "legible": self.legible()}


@dataclass
class Negocio:
    """Perfil del negocio + su catálogo."""

    # Identidad
    nombre: str = "Mi Negocio"
    tipo_negocio: str = "mixto"          # productos | servicios | mixto | restaurante | salud...
    descripcion: str = ""
    slogan: str = ""
    ciudad: str = ""
    direccion: str = ""
    zona: str = ""
    telefono: str = ""
    email: str = ""
    sitio_web: str = ""
    redes: Dict[str, str] = field(default_factory=dict)
    mapa_url: str = ""

    # Operación
    horarios: List[Horario] = field(default_factory=list)
    horario_texto: str = ""
    metodos_pago: List[str] = field(default_factory=list)
    envio: str = ""
    cobertura: str = ""
    # Ciudades donde el negocio atiende (se deduce de `cobertura` si no se define)
    ciudades_cobertura: List[str] = field(default_factory=list)
    tiempo_respuesta: str = ""

    # Tono y políticas
    tono: str = "cercano y profesional"
    mensaje_bienvenida: str = ""
    mensaje_despedida: str = ""
    mensaje_error: str = ""
    mensaje_humano: str = ""
    politicas: List[str] = field(default_factory=list)
    promociones: List[str] = field(default_factory=list)
    faqs: List[Dict[str, str]] = field(default_factory=list)
    palabras_humano: List[str] = field(default_factory=list)
    palabras_servicio: List[str] = field(default_factory=list)

    # Comercial
    moneda: str = "COP"
    acepta_presupuesto: bool = True
    mensaje_post_venta: str = ""
    numero_escalado: str = ""

    # Datos para marketing / seguimiento
    propuesta_valor: List[str] = field(default_factory=list)

    # Catálogo
    catalogo: List[CatalogoItem] = field(default_factory=list)
    categorias: List[str] = field(default_factory=list)
    fuentes_scraping: List[Dict[str, Any]] = field(default_factory=list)

    # Crudo por si el negocio define campos propios
    crudo: Dict[str, Any] = field(default_factory=dict)
    ruta: Optional[Path] = None
    version_archivo: float = 0.0

    # ------------------------------------------------------------------ carga
    @classmethod
    def cargar(cls, ruta: Optional[Path] = None) -> "Negocio":
        ruta = Path(ruta or settings.BUSINESS_CONFIG)
        if not ruta.exists():
            logger.warning(
                "No se encontró el perfil del negocio en %s. Copia un ejemplo de "
                "%s/ a config/negocio.json", ruta, settings.BUSINESS_EXAMPLES_DIR,
            )
            return cls(ruta=ruta)

        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            logger.error("El archivo de negocio %s tiene un JSON inválido: %s", ruta, e)
            return cls(ruta=ruta)

        return cls._desde_dict(datos, ruta)

    @classmethod
    def _desde_dict(cls, d: Dict[str, Any], ruta: Optional[Path]) -> "Negocio":
        ident = d.get("negocio") or d.get("business") or d.get("empresa") or {}
        if not ident and any(k in d for k in ("nombre", "ciudad", "direccion")):
            ident = d  # formato plano: todo en la raíz

        catalogo_raw = (
            ident.get("catalogo") or ident.get("catalog") or ident.get("productos")
            or ident.get("items") or d.get("catalogo") or d.get("productos") or d.get("items") or []
        )
        items: List[CatalogoItem] = []
        for crudo_item in catalogo_raw:
            try:
                item = CatalogoItem.from_dict(crudo_item)
                if not item.tienda:
                    item.tienda = ident.get("nombre", "")
                if item.moneda == "COP" and ident.get("moneda"):
                    item.moneda = ident["moneda"]
                items.append(item)
            except (TypeError, ValueError) as e:
                logger.warning("Ítem de catálogo ignorado: %s", e)

        horarios: List[Horario] = []
        for h in (ident.get("horarios") or ident.get("schedule") or []):
            if not isinstance(h, dict):
                continue
            dia = str(h.get("dia") or h.get("day") or "").strip().lower()
            dia = _ALIAS_DIA.get(dia, dia)
            if not dia:
                continue
            horarios.append(Horario(
                dia=dia,
                abre=str(h.get("abre") or h.get("abre") or h.get("open") or ""),
                cierra=str(h.get("cierra") or h.get("close") or ""),
                cerrado=bool(h.get("cerrado") or h.get("closed") or False),
                nota=str(h.get("nota") or h.get("note") or ""),
            ))

        def lista(*claves: str) -> List[Any]:
            for k in claves:
                v = ident.get(k)
                if isinstance(v, list):
                    return v
                if isinstance(v, str) and v.strip():
                    return [x.strip() for x in v.split(",") if x.strip()]
            return []

        obj = cls(
            nombre=str(ident.get("nombre") or ident.get("name") or "Mi Negocio"),
            tipo_negocio=str(ident.get("tipo_negocio") or ident.get("tipo") or ident.get("sector") or "mixto"),
            descripcion=str(ident.get("descripcion") or ident.get("description") or ""),
            slogan=str(ident.get("slogan") or ident.get("lema") or ""),
            ciudad=str(ident.get("ciudad") or ident.get("city") or ""),
            direccion=str(ident.get("direccion") or ident.get("address") or ""),
            zona=str(ident.get("zona") or ident.get("barrio") or ""),
            telefono=str(ident.get("telefono") or ident.get("phone") or ident.get("whatsapp") or ""),
            email=str(ident.get("email") or ident.get("correo") or ""),
            sitio_web=str(ident.get("sitio_web") or ident.get("web") or ident.get("website") or ""),
            redes={str(k): str(v) for k, v in (ident.get("redes") or {}).items()},
            mapa_url=str(ident.get("mapa_url") or ident.get("maps") or ""),
            horarios=horarios,
            horario_texto=str(ident.get("horario_texto") or ident.get("horario") or ""),
            metodos_pago=[str(x) for x in lista("metodos_pago", "pagos", "payment_methods")],
            envio=str(ident.get("envio") or ident.get("shipping") or ""),
            cobertura=str(ident.get("cobertura") or ident.get("coverage") or ""),
            ciudades_cobertura=[str(x).lower() for x in lista("ciudades_cobertura", "ciudades")],
            tiempo_respuesta=str(ident.get("tiempo_respuesta") or ""),
            tono=str(ident.get("tono") or ident.get("tone") or "cercano y profesional"),
            mensaje_bienvenida=str(ident.get("mensaje_bienvenida") or ident.get("saludo") or ""),
            mensaje_despedida=str(ident.get("mensaje_despedida") or ""),
            mensaje_error=str(ident.get("mensaje_error") or ""),
            mensaje_humano=str(ident.get("mensaje_humano") or ""),
            politicas=[str(x) for x in lista("politicas", "policies")],
            promociones=[str(x) for x in lista("promociones", "promos")],
            faqs=[f for f in (ident.get("faqs") or ident.get("preguntas") or []) if isinstance(f, dict)],
            palabras_humano=[str(x) for x in lista("palabras_humano")],
            palabras_servicio=[str(x) for x in lista("palabras_servicio")],
            moneda=str(ident.get("moneda") or ident.get("currency") or "COP"),
            acepta_presupuesto=bool(ident.get("acepta_presupuesto", True)),
            mensaje_post_venta=str(ident.get("mensaje_post_venta") or ""),
            numero_escalado=str(ident.get("numero_escalado") or settings.HUMAN_ESCALATION_NUMBER or ""),
            propuesta_valor=[str(x) for x in lista("propuesta_valor", "beneficios")],
            catalogo=items,
            categorias=[str(x) for x in lista("categorias", "categories")],
            fuentes_scraping=[f for f in (ident.get("fuentes_scraping") or []) if isinstance(f, dict)],
            crudo=d,
            ruta=ruta,
            version_archivo=ruta.stat().st_mtime if ruta and ruta.exists() else 0.0,
        )
        if not obj.categorias:
            obj.categorias = sorted({i.categoria for i in items if i.categoria})
        if not obj.ciudades_cobertura:
            obj.ciudades_cobertura = obj._deducir_ciudades()
        if not obj.palabras_humano:
            obj.palabras_humano = [
                "humano", "persona", "asesor", "asesora", "vendedor", "agente real",
                "hablar con alguien", "atencion al cliente", "que me llame", "operador",
                "supervisor", "gerente", "dueño", "alguien real",
            ]
        return obj

    # --------------------------------------------------------------- consultas
    @property
    def es_servicios(self) -> bool:
        return self.tipo_negocio.lower() in {"servicios", "servicio", "salud", "educacion"}

    @property
    def es_mixto(self) -> bool:
        return self.tipo_negocio.lower() in {"mixto", "mixta", "hibrido", "híbrido"}

    def horario_legible(self) -> str:
        if self.horario_texto:
            return self.horario_texto
        if not self.horarios:
            return ""
        por_dia = {h.dia: h for h in self.horarios}
        return " | ".join(por_dia[d].legible() for d in DIAS if d in por_dia)

    def horario_de_hoy(self) -> str:
        from datetime import datetime

        dia = DIAS[datetime.now().weekday()]
        for h in self.horarios:
            if h.dia == dia:
                return h.legible()
        return self.horario_legible()

    def esta_abierto(self) -> Optional[bool]:
        """True/False si se puede determinar con los horarios, None si no hay datos."""
        if not self.horarios:
            return None
        from datetime import datetime

        ahora = datetime.now()
        dia = DIAS[ahora.weekday()]
        for h in self.horarios:
            if h.dia != dia or h.cerrado or not h.abre or not h.cierra:
                continue
            try:
                h_abre = datetime.strptime(h.abre.strip(), "%H:%M").replace(
                    year=ahora.year, month=ahora.month, day=ahora.day
                )
                h_cierra = datetime.strptime(h.cierra.strip(), "%H:%M").replace(
                    year=ahora.year, month=ahora.month, day=ahora.day
                )
                if h_cierra <= h_abre:  # cierra después de medianoche
                    h_cierra = h_cierra.replace(day=h_cierra.day + 1)
                    if ahora < h_abre:
                        h_abre = h_abre.replace(day=h_abre.day - 1)
                return h_abre <= ahora <= h_cierra
            except ValueError:
                return None
        return False

    def datos_contacto(self) -> List[str]:
        partes = []
        if self.direccion:
            partes.append(self.direccion + (f" ({self.zona})" if self.zona else ""))
        if self.ciudad:
            partes.append(self.ciudad)
        if self.telefono:
            partes.append(f"Tel/WhatsApp: {self.telefono}")
        if self.email:
            partes.append(self.email)
        if self.sitio_web:
            partes.append(self.sitio_web)
        for red, usuario in self.redes.items():
            partes.append(f"{red}: {usuario}")
        return partes

    def categorias_con_items(self) -> Dict[str, int]:
        conteo: Dict[str, int] = {}
        for item in self.catalogo:
            clave = item.categoria or ("Servicios" if item.es_servicio else "Productos")
            conteo[clave] = conteo.get(clave, 0) + 1
        return dict(sorted(conteo.items(), key=lambda kv: kv[0].lower()))

    def _deducir_ciudades(self) -> List[str]:
        """Saca las ciudades del texto de `cobertura` (o de la ciudad base)."""
        import re

        if not self.cobertura:
            return [self.ciudad.lower()] if self.ciudad else []
        texto = self.cobertura
        # cortamos las aclaraciones entre paréntesis antes de partir por comas
        texto = re.sub(r"\([^)]*\)", "", texto)
        partes = re.split(r"[,;/]|\sy\s|\se\s", texto)
        ciudades = []
        for parte in partes:
            limpio = parte.strip().lower()
            limpio = re.sub(r"^(cobertura|envios?|servicio tecnico|servicio técnico|a)\s*:?\s*", "", limpio)
            limpio = re.sub(r"(y municipios|municipios|alrededores|resto del?)\s*", "", limpio).strip()
            if limpio and 3 <= len(limpio) <= 30 and not any(c.isdigit() for c in limpio):
                if limpio not in ciudades:
                    ciudades.append(limpio)
        if self.ciudad and self.ciudad.lower() not in ciudades:
            ciudades.insert(0, self.ciudad.lower())
        return ciudades

    def cubre_ciudad(self, ciudad: str) -> bool:
        """¿El negocio atiende en esa ciudad? (búsqueda flexible por texto)"""
        from utils.texto import normalizar

        if not ciudad:
            return True
        if not self.ciudades_cobertura:
            return self.cobertura == "" or normalizar(ciudad) in normalizar(self.cobertura)
        ciudad_norm = normalizar(ciudad)
        return any(ciudad_norm in normalizar(c) or normalizar(c) in ciudad_norm
                   for c in self.ciudades_cobertura)

    def es_horario_valido(self, texto: str) -> bool:
        return bool(texto)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nombre": self.nombre,
            "tipo_negocio": self.tipo_negocio,
            "descripcion": self.descripcion,
            "ciudad": self.ciudad,
            "direccion": self.direccion,
            "telefono": self.telefono,
            "horario": self.horario_legible(),
            "categorias": self.categorias_con_items(),
            "items": len(self.catalogo),
            "servicios": sum(1 for i in self.catalogo if i.es_servicio),
            "productos": sum(1 for i in self.catalogo if not i.es_servicio),
        }
