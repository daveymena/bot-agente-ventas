"""Pruebas de las utilidades de texto (base de todas las respuestas)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from utils.texto import (  # noqa: E402
    formatear_precio,
    normalizar,
    parsear_numero,
    recortar,
    similitud,
    tokenizar,
    unir,
)


@pytest.mark.parametrize("entrada,esperado", [
    ("Portátil Lenovo", "portatil lenovo"),
    ("  iPhone  13  PRO  ", "iphone 13 pro"),
    ("¿Cuánto vale?", "cuanto vale"),
    ("MANTENIMIENTO (preventivo)", "mantenimiento preventivo"),
])
def test_normalizar(entrada, esperado):
    assert normalizar(entrada) == esperado


@pytest.mark.parametrize("entrada,esperado", [
    ("45000", 45000.0),
    ("$45.000", 45000.0),
    ("1.499.000", 1499000.0),
    ("2 millones", 2000000.0),
    ("300 mil", 300000.0),
    ("45k", 45000.0),
    ("1.200,50", 1200.5),
])
def test_parsear_numero(entrada, esperado):
    assert parsear_numero(entrada) == pytest.approx(esperado)


@pytest.mark.parametrize("valor,moneda,esperado", [
    (45000, "COP", "$45.000"),
    (2150000, "COP", "$2.150.000"),
    (1200.5, "USD", "US$1,200.50"),
    (None, "COP", ""),
])
def test_formatear_precio(valor, moneda, esperado):
    assert formatear_precio(valor, moneda, decimales=2 if moneda == "USD" else 0) == esperado


def test_tokenizar_quita_palabras_vacias_y_plurales():
    tokens = tokenizar("Hola, quisiera saber el precio de los cortes de cabello")
    assert "hola" not in tokens
    assert "precio" not in tokens  # palabra de cortesía/consulta, no de catálogo
    assert "corte" in tokens
    assert "cabello" in tokens


def test_similitud_tolera_typos():
    assert similitud("ipone", "iphone") > 0.8
    assert similitud("iphone", "iphone") == 1.0
    assert similitud("mesa", "avion") < 0.5


def test_recortar_respeta_palabras():
    texto = "Esto es una respuesta bastante larga que debe quedar cortada"
    recortado = recortar(texto, 30)
    assert len(recortado) <= 30
    assert recortado.endswith("…")


def test_unir_en_lenguaje_natural():
    assert unir(["a", "b", "c"]) == "a, b y c"
    assert unir(["a"]) == "a"
    assert unir([]) == ""
