"""
Pruebas del catálogo con DOS negocios distintos (barbería y restaurante) para
demostrar que el motor es agnóstico del rubro: mismo código, distinto JSON.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from config.business import Negocio  # noqa: E402
from models.catalog import CatalogoItem  # noqa: E402
from services.catalog_service import CatalogoService  # noqa: E402

EJEMPLOS = Path(__file__).resolve().parent.parent / "negocios" / "ejemplos"


def negocio_de(datos: dict) -> Negocio:
    return Negocio._desde_dict(datos, None)


@pytest.fixture
def barberia():
    negocio = negocio_de({
        "negocio": {
            "nombre": "Barbería El Rey",
            "tipo_negocio": "servicios",
            "moneda": "COP",
            "catalogo": [
                {"nombre": "Corte de cabello clásico", "tipo": "servicio", "categoria": "Cortes",
                 "precio": 25000, "duracion": "30 minutos", "etiquetas": ["corte", "cabello"],
                 "sinonimos": ["corte de pelo", "cortada"]},
                {"nombre": "Corte + barba", "tipo": "servicio", "categoria": "Combos",
                 "precio": 40000, "duracion": "50 minutos", "etiquetas": ["combo", "barba"]},
                {"nombre": "Diseño de cejas", "tipo": "servicio", "categoria": "Estética",
                 "precio": 12000, "etiquetas": ["cejas"]},
                {"nombre": "Tinte de barba", "tipo": "servicio", "categoria": "Estética",
                 "precio": 30000, "etiquetas": ["tinte", "barba"]},
            ],
        }
    })
    return CatalogoService(negocio)


@pytest.fixture
def restaurante():
    negocio = negocio_de({
        "negocio": {
            "nombre": "Sazón de la Abuela",
            "tipo_negocio": "productos",
            "moneda": "COP",
            "catalogo": [
                {"nombre": "Bandeja paisa", "tipo": "producto", "categoria": "Almuerzos",
                 "precio": 28000, "etiquetas": ["almuerzo", "tipico", "bandeja"], "destacado": True},
                {"nombre": "Ajiaco santafereño", "tipo": "producto", "categoria": "Almuerzos",
                 "precio": 26000, "etiquetas": ["sopa", "pollo", "ajiaco"]},
                {"nombre": "Limonada de coco", "tipo": "producto", "categoria": "Bebidas",
                 "precio": 9000, "etiquetas": ["bebida", "jugo"]},
                {"nombre": "Postre de natas", "tipo": "producto", "categoria": "Postres",
                 "precio": 12000, "etiquetas": ["postre", "dulce"]},
            ],
        }
    })
    return CatalogoService(negocio)


def test_catalogo_lee_items_y_categorias(barberia):
    assert barberia.total() == 4
    assert "Cortes" in barberia.categorias()
    assert barberia.resumen()["servicios"] == 4


def test_encuentra_servicio_por_nombre_exacto(barberia):
    mejor = barberia.mejor("cuanto vale el corte de cabello clasico")
    assert mejor is not None
    assert mejor.item.nombre == "Corte de cabello clásico"


def test_encuentra_por_sinonimo(barberia):
    mejor = barberia.mejor("me hago una cortada?")  # sinónimo raro pero declarado
    assert mejor is not None
    assert "Corte" in mejor.item.nombre


def test_encuentra_aunque_haya_typo(barberia):
    mejor = barberia.mejor("quiero un cortte de cabello")
    assert mejor is not None
    assert mejor.item.nombre.startswith("Corte")


def test_no_inventa_en_restaurante(restaurante):
    assert restaurante.mejor("tienen sushi") is None


def test_producto_agotado_sigue_siendo_encontrado(restaurante):
    restaurante.negocio.catalogo[0].disponibilidad = "agotado"
    restaurante.negocio.catalogo[0].stock = 0
    resultado = restaurante.mejor("bandeja paisa")
    assert resultado is not None
    assert resultado.item.disponible is False


def test_presupuesto_excluye_lo_muy_caro(barberia):
    resultados = barberia.buscar("corte", presupuesto=20000)
    assert all(r.item.precio is None or r.item.precio <= 30000 for r in resultados)


def test_orden_por_precio(barberia):
    resultados = barberia.buscar("corte barba cejas tinte", limite=4, orden="precio_asc")
    precios = [r.item.precio for r in resultados]
    assert precios == sorted(precios)


def test_ficha_de_servicio_incluye_duracion(barberia):
    item = barberia.mejor("corte de cabello").item
    assert "30 minutos" in item.ficha()
    assert "$25.000" in item.ficha()


def test_item_desde_dict_traduce_llaves_en_ingles():
    item = CatalogoItem.from_dict({
        "title": "Curso de inglés B1", "type": "servicio", "price": "450000",
        "duration": "8 semanas", "tags": "idiomas, curso",
    })
    assert item.nombre == "Curso de inglés B1"
    assert item.es_servicio is True
    assert item.precio == 450000
    assert item.duracion == "8 semanas"
    assert item.etiquetas == ["idiomas", "curso"]


def test_ejemplos_de_negocio_son_validos():
    """Todos los JSON de negocios/ejemplos/ deben cargar sin errores."""
    archivos = sorted(EJEMPLOS.glob("*.json"))
    assert archivos, "debe haber al menos un negocio de ejemplo"
    for archivo in archivos:
        negocio = Negocio.cargar(archivo)
        assert negocio.nombre != "Mi Negocio", f"{archivo.name} no define nombre"
        assert negocio.catalogo, f"{archivo.name} no tiene catálogo"
        servicio = CatalogoService(negocio)
        assert servicio.resumen()["total"] == len(negocio.catalogo)
