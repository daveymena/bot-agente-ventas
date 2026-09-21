"""
Servidor del agente.

Expone el motor de respuestas por HTTP. Lo consumen:
  - el puente Baileys (baileys-bridge/) para atender WhatsApp
  - el simulador web (/simulador) para probar el negocio sin WhatsApp
  - cualquier integración propia (CRM, panel, etc.)

Arranque:  python main.py        ->  http://localhost:8000
"""
from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Optional

import uvicorn
from fastapi import Body, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from config.settings import settings  # noqa: E402
from core.sales_agent import SalesAgent  # noqa: E402

# ------------------------------------------------------------------- logging
def configurar_logging() -> None:
    """Crea la carpeta de logs y cae a solo-consola si el disco es de solo lectura."""
    nivel = getattr(logging, settings.LOG_LEVEL, logging.INFO)
    formato = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    manejadores: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    try:
        ruta = settings.log_file_path()
        ruta.parent.mkdir(parents=True, exist_ok=True)
        manejadores.append(logging.FileHandler(ruta, encoding="utf-8"))
    except OSError as error:  # entornos serverless / solo lectura
        print(f"[aviso] no se pudo escribir el archivo de log ({error}); solo consola")
    logging.basicConfig(level=nivel, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                       handlers=manejadores, force=True)
    for nombre in ("httpx", "httpcore", "uvicorn.access"):
        logging.getLogger(nombre).setLevel(logging.WARNING)


configurar_logging()
logger = logging.getLogger("agente")

agente: Optional[SalesAgent] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global agente
    agente = SalesAgent()
    await agente.initialize()
    avisos = settings.validate_config()
    for aviso in avisos.get("warnings", []):
        logger.warning(aviso)
    logger.info(
        "Agente listo · negocio=%s · %s ítems en catálogo · IA=%s",
        agente.negocio.nombre, len(agente.negocio.catalogo), agente.ia.proveedor,
    )
    yield
    await agente.stop()


app = FastAPI(
    title="Agente de Ventas multi-rubro",
    description=(
        "Motor de respuestas para cualquier negocio (productos y servicios). "
        "Recibe mensajes del puente Baileys o del simulador y devuelve las acciones a enviar."
    ),
    version="2.0.0",
    lifespan=lifespan,
)


# --------------------------------------------------------------------- helpers
def _agente() -> SalesAgent:
    if agente is None:
        raise HTTPException(status_code=503, detail="Agente no inicializado")
    return agente


def verificar_token(
    x_bridge_token: Optional[str] = Header(default=None, alias="x-bridge-token"),
    token: Optional[str] = Query(default=None),
) -> None:
    """Si WEBHOOK_TOKEN está definido, exige el token (header o query)."""
    if not settings.WEBHOOK_TOKEN:
        return
    if settings.WEBHOOK_TOKEN in {x_bridge_token, token}:
        return
    raise HTTPException(status_code=401, detail="Token inválido")


def _portada(a: SalesAgent) -> str:
    """Página simple de bienvenida (la que ves al abrir la raíz en el navegador)."""
    categorias = "".join(
        f"<li>{c} <span>({n})</span></li>" for c, n in a.negocio.categorias_con_items().items()
    )
    ia = a.ia.estado()
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{a.negocio.nombre} · Agente de ventas</title><style>
 body{{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
 background:#0b141a;color:#e9edef;display:grid;place-items:center;min-height:100vh;padding:24px}}
 .caja{{max-width:640px;width:100%}}
 h1{{font-size:22px;margin:0 0 6px}} .sub{{color:#8696a0;margin:0 0 22px;font-size:14px}}
 .tarjeta{{background:#111b21;border:1px solid #222d34;border-radius:14px;padding:20px;margin-bottom:14px}}
 a.boton{{display:block;text-align:center;background:#00a884;color:#04211c;font-weight:700;
 text-decoration:none;padding:13px;border-radius:10px;margin-bottom:10px}}
 a.sec{{display:block;text-align:center;color:#e9edef;text-decoration:none;border:1px solid #2a3942;
 padding:11px;border-radius:10px;font-size:14px}}
 ul{{margin:0;padding-left:18px;color:#d1d7db;font-size:14px;line-height:1.7}} li span{{color:#8696a0}}
 .dato{{display:flex;justify-content:space-between;font-size:13.5px;padding:5px 0;color:#8696a0}}
 .dato b{{color:#e9edef;font-weight:600}}
</style></head><body><div class="caja">
 <h1>🤖 {a.negocio.nombre}</h1>
 <p class="sub">Agente de ventas para WhatsApp · {a.negocio.tipo_negocio} · {a.negocio.ciudad}</p>
 <div class="tarjeta">
  <a class="boton" href="/simulador">Probar el agente (simulador) →</a>
  <a class="sec" href="/estado">Ver estado y métricas</a>
 </div>
 <div class="tarjeta">
  <div class="dato"><span>Ítems en catálogo</span><b>{len(a.negocio.catalogo)}</b></div>
  <div class="dato"><span>Redacción</span><b>{ia['proveedor'] if ia['disponible'] else 'motor propio (sin IA)'}</b></div>
  <div class="dato"><span>Horario</span><b>{'abierto ahora' if a.negocio.esta_abierto() else 'cerrado ahora' if a.negocio.esta_abierto() is False else 'sin horario cargado'}</b></div>
  <hr style="border:0;border-top:1px solid #222d34;margin:14px 0">
  <ul>{categorias or '<li>Sin categorías cargadas</li>'}</ul>
 </div>
 <div class="tarjeta" style="font-size:13.5px;color:#8696a0">
  WhatsApp se conecta con Baileys: abre el panel del puente y escanea el QR.
  <br><br>API: <code>/mensaje</code> · <code>/estado</code> · <code>/catalogo</code> · <code>/negocio</code>
 </div>
</div></body></html>"""


# --------------------------------------------------------------------- básicos
@app.get("/")
async def raiz(request: Request):
    """JSON para integraciones; página de bienvenida si la abres en el navegador."""
    a = _agente()
    if "text/html" in request.headers.get("accept", ""):
        return HTMLResponse(_portada(a))
    return {
        "servicio": "Agente de Ventas multi-rubro",
        "estado": "activo" if a.is_running else "inactivo",
        "negocio": a.negocio.nombre,
        "tipo_negocio": a.negocio.tipo_negocio,
        "catalogo": a.catalogo.resumen(),
        "ia": a.ia.estado(),
        "canal": "Baileys (baileys-bridge/)",
        "endpoints": [
            "GET  /health", "GET  /estado", "GET  /negocio", "GET  /catalogo?q=",
            "POST /mensaje", "POST /webhook (compatibilidad)", "GET  /simulador",
        ],
    }


@app.get("/health")
async def health() -> Dict[str, Any]:
    if agente is None:
        raise HTTPException(status_code=503, detail="Agente no inicializado")
    estado_wa = agente.metricas.get("eventos_whatsapp") or []
    ultimo = estado_wa[-1] if estado_wa else None
    return {
        "status": "healthy" if agente.is_running else "unhealthy",
        "negocio": agente.negocio.nombre,
        "items": len(agente.negocio.catalogo),
        "ia": agente.ia.proveedor,
        "whatsapp": {
            "canal": "Baileys (baileys-bridge/)",
            "ultimo_evento": ultimo["evento"] if ultimo else "sin eventos todavía",
        },
        "uptime_segundos": agente.estado()["uptime_segundos"],
    }


@app.get("/estado")
async def estado() -> Dict[str, Any]:
    a = _agente()
    a.recargar_si_cambio()
    return a.estado()


@app.get("/negocio")
async def negocio() -> Dict[str, Any]:
    a = _agente()
    return {
        **a.negocio.to_dict(),
        "descripcion": a.negocio.descripcion,
        "direccion": a.negocio.direccion,
        "metodos_pago": a.negocio.metodos_pago,
        "envio": a.negocio.envio,
        "politicas": a.negocio.politicas,
        "promociones": a.negocio.promociones,
        "faqs": a.negocio.faqs,
        "tono": a.negocio.tono,
    }


@app.get("/catalogo")
async def catalogo(
    q: Optional[str] = Query(default=None, description="Texto a buscar (opcional)"),
    categoria: Optional[str] = Query(default=None),
    tipo: Optional[str] = Query(default=None, description="producto | servicio"),
    limite: int = Query(default=20, ge=1, le=100),
) -> Dict[str, Any]:
    a = _agente()
    if q:
        return {"consulta": q, "total": len(a.buscar_en_catalogo(q, limite=limite)),
                "resultados": a.buscar_en_catalogo(q, limite=limite)}
    items = a.catalogo.todos()
    if categoria:
        items = a.catalogo.por_categoria(categoria, limite=limite)
    if tipo:
        items = [i for i in a.catalogo.por_tipo(tipo) if i in items]
    return {"total": len(items), "resumen": a.catalogo.resumen(),
            "items": [i.to_dict() for i in items[:limite]]}


@app.post("/catalogo/recargar")
async def recargar_catalogo() -> Dict[str, Any]:
    a = _agente()
    a.recargar_si_cambio(forzar=True)
    return {"ok": True, "resumen": a.catalogo.resumen(), "negocio": a.negocio.nombre}


@app.post("/catalogo/importar-web")
async def importar_catalogo_web(
    guardar: bool = Query(default=True, description="Guardar lo importado en config/catalogo-importado.json"),
    x_bridge_token: Optional[str] = Header(default=None, alias="x-bridge-token"),
) -> Dict[str, Any]:
    """
    Refresca el catálogo leyendo las fuentes web del negocio (`fuentes_scraping`).
    Solo agrega ítems nuevos: no modifica precios ya cargados a mano.
    """
    verificar_token(x_bridge_token)
    return await _agente().importar_catalogo_web(guardar=guardar)


# ------------------------------------------------------------------ mensajería
@app.post("/mensaje")
async def recibir_mensaje(
    payload: Dict[str, Any] = Body(...),
    canal: str = Query(default="baileys"),
    x_bridge_token: Optional[str] = Header(default=None, alias="x-bridge-token"),
) -> Dict[str, Any]:
    """
    Recibe un mensaje y devuelve el plan de respuesta (acciones).

    Formato del puente Baileys:
      {"mensaje": {"id","chat_id","numero","texto","tipo","nombre","es_grupo","from_me","media":{...}}}
    También acepta payloads antiguos (Evolution API / n8n) para no romper nada.
    """
    verificar_token(x_bridge_token)
    a = _agente()
    datos = payload.get("mensaje") if isinstance(payload.get("mensaje"), dict) else payload
    canal_real = payload.get("canal") or canal
    return await a.procesar_mensaje(datos, canal=canal_real)


@app.post("/webhook")
async def webhook_legado(
    payload: Dict[str, Any] = Body(...),
    token: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    """
    Compatibilidad con el webhook anterior (Evolution API / n8n).

    OJO: aquí ya NO se envía nada por WhatsApp; devuelve el mismo plan de
    acciones. El envío lo hace el puente Baileys (o tu propia integración).
    """
    verificar_token(token=token)
    a = _agente()
    return await a.procesar_mensaje(payload, canal="webhook")


@app.post("/evento-whatsapp")
async def evento_whatsapp(
    payload: Dict[str, Any] = Body(default_factory=dict),
    x_bridge_token: Optional[str] = Header(default=None, alias="x-bridge-token"),
) -> Dict[str, Any]:
    """El puente Baileys reporta aquí conexiones, desconexiones y QR pendientes."""
    verificar_token(x_bridge_token)
    a = _agente()
    registro = a.registrar_evento_whatsapp(
        str(payload.get("evento") or "desconocido"), payload.get("datos") or {}
    )
    if registro["evento"] == "conectado":
        logger.info("✅ WhatsApp conectado: %s", registro["datos"].get("numero"))
    return {"ok": True, "registrado": registro["evento"]}


@app.post("/conversacion/limpiar")
async def limpiar_conversacion(chat_id: Optional[str] = Body(default=None, embed=True)) -> Dict[str, Any]:
    a = _agente()
    a.limpiar_conversacion(chat_id)
    return {"ok": True, "chat_id": chat_id or "todas"}


# ------------------------------------------------------------------ simulador
@app.get("/simulador", response_class=HTMLResponse)
async def simulador() -> HTMLResponse:
    ruta = BASE_DIR / "web" / "simulador.html"
    if not ruta.exists():
        raise HTTPException(status_code=404, detail="Falta web/simulador.html")
    return HTMLResponse(ruta.read_text(encoding="utf-8"))


@app.exception_handler(Exception)
async def error_general(request: Request, exc: Exception) -> JSONResponse:  # pragma: no cover
    logger.error("Error no manejado en %s: %s", request.url.path, exc)
    return JSONResponse(status_code=500, content={"ok": False, "error": str(exc)})


def main() -> None:
    logger.info("Servidor del agente escuchando en http://%s:%s", settings.HOST, settings.PORT)
    logger.info("Simulador: http://localhost:%s/simulador", settings.PORT)
    uvicorn.run(app, host=settings.HOST, port=settings.PORT, log_level=settings.LOG_LEVEL.lower())


if __name__ == "__main__":
    main()
