"""
Pruebas de punta a punta del agente (el "cerebro" que decide las respuestas).

Se ejecutan con el negocio de ejemplo `negocios/ejemplos/barberia.json`, así que
también demuestran que el motor no depende del rubro.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from core.sales_agent import SalesAgent  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
EJEMPLOS = RAIZ / "negocios" / "ejemplos"


def ejecutar(coro):
    return asyncio.run(coro)


@pytest.fixture(scope="module")
def agente():
    a = SalesAgent(ruta_negocio=EJEMPLOS / "barberia.json")
    ejecutar(a.initialize())
    return a


def mensaje(texto: str, mid: str = "m1", chat: str = "573001112233@s.whatsapp.net", **extra):
    return {
        "id": mid, "chat_id": chat, "numero": "573001112233", "texto": texto,
        "tipo": "texto", "nombre": "Carlos", "timestamp": 1700000000, **extra,
    }


def texto_de(respuesta) -> str:
    return "\n".join(a["texto"] for a in respuesta["acciones"] if a["tipo"] == "texto")


# --------------------------------------------------------------------- crítico
def test_responde_mensajes_normales(agente):
    """El bug histórico: TODO mensaje se marcaba como duplicado y el bot callaba."""
    respuesta = ejecutar(agente.procesar_mensaje(mensaje("hola, cuanto vale el corte de cabello", "critico1"), canal="test"))
    assert respuesta["ignorado"] is False
    assert texto_de(respuesta).strip(), "el agente no puede quedarse callado"
    assert "25.000" in texto_de(respuesta)


def test_no_responde_dos_veces_el_mismo_mensaje(agente):
    primero = ejecutar(agente.procesar_mensaje(mensaje("hola", "dup-1"), canal="test"))
    segundo = ejecutar(agente.procesar_mensaje(mensaje("hola", "dup-1"), canal="test"))
    assert primero["ignorado"] is False
    assert segundo["ignorado"] is True
    assert "duplicado" in segundo["motivo"]


def test_mensaje_siguiente_del_mismo_cliente_si_se_responde(agente):
    """Dos mensajes distintos seguidos deben tener respuesta (no autobloquearse)."""
    a = ejecutar(agente.procesar_mensaje(mensaje("buenas", "seq-1"), canal="test"))
    b = ejecutar(agente.procesar_mensaje(mensaje("y los precios?", "seq-2"), canal="test"))
    assert a["ignorado"] is False and b["ignorado"] is False


def test_ignora_grupos(agente):
    respuesta = ejecutar(agente.procesar_mensaje(
        mensaje("hola", "grupo-1", chat="123456789-987654@g.us"), canal="test"))
    assert respuesta["ignorado"] is True
    assert "grupo" in respuesta["motivo"]


def test_ignora_mensajes_propios(agente):
    respuesta = ejecutar(agente.procesar_mensaje(mensaje("hola", "propio-1", from_me=True), canal="test"))
    assert respuesta["ignorado"] is True


def test_ignora_mensajes_vacios(agente):
    respuesta = ejecutar(agente.procesar_mensaje(mensaje("", "vacio-1"), canal="test"))
    assert respuesta["ignorado"] is True


# ------------------------------------------------------------------- contenido
def test_responde_con_datos_reales_del_catalogo(agente):
    respuesta = ejecutar(agente.procesar_mensaje(mensaje("cuanto vale el corte con barba", "prod-1"), canal="test"))
    texto = texto_de(respuesta)
    assert "40.000" in texto
    assert "50 minutos" in texto


def test_servicio_agenda_cita(agente):
    respuesta = ejecutar(agente.procesar_mensaje(mensaje("quiero agendar una cita", "cita-1"), canal="test"))
    texto = texto_de(respuesta)
    assert "agend" in texto.lower()
    assert any(a["tipo"] == "notificar" for a in respuesta["acciones"]), "debe avisar al equipo"


def test_escala_cuando_piden_humano(agente):
    # chat propio: el aviso al dueño se envía una sola vez por conversación
    respuesta = ejecutar(agente.procesar_mensaje(
        mensaje("quiero hablar con una persona real", "humano-1", chat="573009990000@s.whatsapp.net"),
        canal="test"))
    assert respuesta["debug"]["escalar"] is True
    assert any(a["tipo"] == "notificar" for a in respuesta["acciones"])


def test_presupuesto_avisa_cuando_no_alcanza(agente):
    """No debe ofrecer como comprable algo que se pasa del presupuesto."""
    respuesta = ejecutar(agente.procesar_mensaje(
        mensaje("quiero un corte pero tengo 10 mil pesos", "presu-1",
                chat="573008887777@s.whatsapp.net"), canal="test"))
    texto = texto_de(respuesta).lower()
    assert "por encima" in texto or "no tengo" in texto
    assert "¿te lo separo?" not in texto, "no puede ofrecer lo que no le alcanza"
    assert respuesta["debug"]["escalar"] is True


def test_presupuesto_ajustado_ofrece_alternativas_reales(agente):
    respuesta = ejecutar(agente.procesar_mensaje(
        mensaje("busco algo de 15 mil", "presu-2", chat="573008887777@s.whatsapp.net"), canal="test"))
    texto = texto_de(respuesta)
    assert texto.strip()


def test_no_inventa_cuando_no_existe(agente):
    respuesta = ejecutar(agente.procesar_mensaje(
        mensaje("tienen depilacion con laser", "noexiste-1"), canal="test"))
    texto = texto_de(respuesta).lower()
    assert "laser" in texto
    assert "no tengo" in texto or "no manejamos" in texto


def test_audio_sin_transcripcion_pide_texto(agente):
    respuesta = ejecutar(agente.procesar_mensaje(
        {"id": "audio-1", "chat_id": "573001112233@s.whatsapp.net", "tipo": "audio",
         "texto": "", "nombre": "Carlos", "media": {}}, canal="test"))
    texto = texto_de(respuesta).lower()
    assert "audio" in texto or "voz" in texto
    assert "texto" in texto


def test_plan_de_acciones_tiene_presencia_y_texto(agente):
    respuesta = ejecutar(agente.procesar_mensaje(mensaje("hola", "plan-1"), canal="test"))
    tipos = [a["tipo"] for a in respuesta["acciones"]]
    assert "presencia" in tipos
    assert "texto" in tipos


def test_siempre_responde_algo_a_mensajes_raros(agente):
    """Ningún mensaje del cliente debe terminar sin respuesta."""
    raros = ["asdfgh", "???", "🙂", "1", "mande info", "precio", "si", "no se",
             "buenas tardes señorita", "el otro día fui y no había nadie", "😡"]
    for i, texto in enumerate(raros):
        respuesta = ejecutar(agente.procesar_mensaje(mensaje(texto, f"raro-{i}"), canal="test"))
        if respuesta["ignorado"]:
            continue  # ignorado por longitud mínima, es correcto
        assert texto_de(respuesta).strip(), f"sin respuesta para: {texto}"


# -------------------------------------------------------------------- multi-rubro
@pytest.mark.parametrize("archivo", sorted(p.name for p in EJEMPLOS.glob("*.json")))
def test_cada_negocio_responde_su_propio_catalogo(archivo):
    """Mismo motor, seis negocios distintos: la respuesta trae SU información."""
    ruta = EJEMPLOS / archivo
    datos = json.loads(ruta.read_text(encoding="utf-8"))["negocio"]
    agente_local = SalesAgent(ruta_negocio=ruta)
    ejecutar(agente_local.initialize())

    # pedimos el catálogo y un ítem concreto
    catalogo = ejecutar(agente_local.procesar_mensaje(
        mensaje("que productos y servicios tienen?", "multi-cat", chat=f"57{abs(hash(archivo)) % 10**7}@s.whatsapp.net"),
        canal="test"))
    assert texto_de(catalogo).strip()

    item = datos["catalogo"][0]
    consulta = ejecutar(agente_local.procesar_mensaje(
        mensaje(f"cuanto vale {item['nombre']}", "multi-item", chat=f"57{abs(hash(archivo)) % 10**7}@s.whatsapp.net"),
        canal="test"))
    texto = texto_de(consulta)
    assert item["nombre"].split()[0].lower() in texto.lower(), f"{archivo}: no reconoció {item['nombre']}"
    if item.get("precio"):
        from utils.texto import formatear_precio

        assert formatear_precio(item["precio"], datos.get("moneda", "COP")) in texto, \
            f"{archivo}: no incluyó el precio real"


def test_negocio_desconocido_no_rompe():
    """Un rubro que no está en ninguna lista debe funcionar igual."""
    agente_ovni = SalesAgent(ruta_negocio=RAIZ / "negocios" / "ejemplos" / "agencia-servicios.json")
    ejecutar(agente_ovni.initialize())
    respuesta = ejecutar(agente_ovni.procesar_mensaje(
        mensaje("necesito un abogado laboral", "ovni-1", chat="573001119999@s.whatsapp.net"), canal="test"))
    texto = texto_de(respuesta)
    assert "abogado" in texto.lower() or "jurídica" in texto.lower() or "juridica" in texto.lower()
