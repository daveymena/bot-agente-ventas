#!/usr/bin/env python3
"""
Arranque completo del agente: motor Python + puente Baileys.

    python iniciar.py            # levanta los dos servicios
    python iniciar.py --solo-api # solo el motor (sin WhatsApp)
    python iniciar.py --qr       # muestra la URL del QR apenas inicia

El puente Baileys necesita Node.js 18+ y `npm install` (se hace solo la primera
vez). No requiere ngrok, Vercel ni ningún webhook público: el puente escucha los
mensajes y le pasa cada uno al motor por HTTP local.
"""
from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
BRIDGE = RAIZ / "baileys-bridge"
sys.path.insert(0, str(RAIZ))

AZUL, VERDE, AMARILLO, ROJO, RESET = "\033[94m", "\033[92m", "\033[93m", "\033[91m", "\033[0m"


def log(etiqueta: str, color: str, linea: str) -> None:
    print(f"{color}[{etiqueta}]{RESET} {linea}", flush=True)


def leer_salida(proceso: subprocess.Popen, etiqueta: str, color: str) -> None:
    assert proceso.stdout is not None
    for linea in proceso.stdout:
        log(etiqueta, color, linea.rstrip())


def instalar_dependencias_node() -> bool:
    """Instala las dependencias de Baileys si hace falta."""
    if (BRIDGE / "node_modules" / "@whiskeysockets" / "baileys").exists():
        return True
    log("bridge", AMARILLO, "Instalando dependencias de Baileys (solo la primera vez)…")
    resultado = subprocess.run(["npm", "install", "--no-audit", "--no-fund"], cwd=BRIDGE)
    if resultado.returncode != 0:
        log("bridge", ROJO, "La instalación falló. Ejecuta 'npm install' dentro de baileys-bridge/")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Arranca el agente de ventas y el puente de WhatsApp")
    parser.add_argument("--solo-api", action="store_true", help="no arrancar el puente Baileys")
    parser.add_argument("--sin-qr-web", action="store_true", help="no mostrar la URL del panel QR")
    argumentos = parser.parse_args()

    from config.settings import settings

    procesos: list[tuple[str, subprocess.Popen]] = []

    def arrancar(nombre: str, comando: list[str], cwd: Path, color: str) -> subprocess.Popen:
        proceso = subprocess.Popen(
            comando, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        procesos.append((nombre, proceso))
        threading.Thread(target=leer_salida, args=(proceso, nombre, color), daemon=True).start()
        return proceso

    print(f"\n{AZUL}════════════════════════════════════════════════════════════{RESET}")
    print(f"{AZUL}  AGENTE DE VENTAS · productos y servicios de cualquier negocio{RESET}")
    print(f"{AZUL}════════════════════════════════════════════════════════════{RESET}\n")

    # 1) motor de respuestas
    python = sys.executable
    arrancar("agente", [python, "main.py"], RAIZ, VERDE)
    time.sleep(1.5)

    # 2) puente Baileys
    if not argumentos.solo_api:
        if shutil.which("node") is None:
            log("bridge", ROJO, "No encontré Node.js. Instálalo (nodejs.org) o usa --solo-api")
        elif instalar_dependencias_node():
            arrancar("bridge", ["node", "index.js"], BRIDGE, AZUL)

    time.sleep(2)
    puerto = settings.PORT
    print()
    log("info", VERDE, f"Simulador web ....: http://localhost:{puerto}/simulador")
    log("info", VERDE, f"Estado del agente : http://localhost:{puerto}/estado")
    if not argumentos.solo_api and not argumentos.sin_qr_web:
        log("info", AMARILLO, "Panel del QR ......: revisa la línea del puente más arriba (o abre el puerto del panel)")
        log("info", AMARILLO, "Escanea el QR: WhatsApp > Dispositivos vinculados > Vincular dispositivo")
    log("info", VERDE, "Detén todo con Ctrl+C")

    deteniendo = False

    def detener(*_):
        nonlocal deteniendo
        if deteniendo:
            return
        deteniendo = True
        print()
        log("info", AMARILLO, "Cerrando servicios…")
        for nombre, proceso in procesos:
            if proceso.poll() is None:
                proceso.terminate()
        for nombre, proceso in procesos:
            try:
                proceso.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proceso.kill()
        log("info", VERDE, "Listo. ¡Hasta luego!")
        sys.exit(0)

    signal.signal(signal.SIGINT, detener)
    signal.signal(signal.SIGTERM, detener)

    while True:
        time.sleep(1)
        for nombre, proceso in procesos:
            codigo = proceso.poll()
            if codigo is not None:
                log(nombre, ROJO, f"el proceso terminó con código {codigo}. Cerrando el resto…")
                detener()


if __name__ == "__main__":
    raise SystemExit(main())
