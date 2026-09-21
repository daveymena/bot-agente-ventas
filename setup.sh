#!/usr/bin/env bash
# ============================================================
#  Instalación del agente de ventas (motor Python + puente Baileys)
# ============================================================
set -e

cd "$(dirname "$0")"

echo "==> Verificando requisitos"
python3 --version || { echo "Falta Python 3.10+"; exit 1; }
node --version   || echo "⚠️  Falta Node.js 18+ (necesario para WhatsApp con Baileys)"

echo "==> Entorno virtual de Python"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
./.venv/bin/pip install --upgrade pip -q
./.venv/bin/pip install -r requirements.txt -q

echo "==> ¿Instalar proveedores de IA? (Gemini/OpenAI: opcional)"
read -r -p "    Instalar IA generativa y transcripción de audios? [s/N] " respuesta
if [[ "$respuesta" =~ ^[sSyY]$ ]]; then
  ./.venv/bin/pip install -r requirements-ia.txt -q
  echo "    ✓ IA instalada. Configura las API keys en .env"
fi

echo "==> Dependencias del puente de WhatsApp (Baileys)"
if command -v npm >/dev/null 2>&1; then
  (cd baileys-bridge && npm install --no-audit --no-fund)
else
  echo "    ⚠️  npm no está disponible: instala Node.js y luego corre 'cd baileys-bridge && npm install'"
fi

echo "==> Configuración"
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "    ✓ Creado .env (revísalo y ajusta lo que necesites)"
fi
if [ ! -f "config/negocio.json" ]; then
  echo "    ⚠️  No hay config/negocio.json: copia un ejemplo de negocios/ejemplos/"
fi

mkdir -p logs temp

cat <<'FIN'

============================================================
  ¡Listo! Para arrancar todo:

      source .venv/bin/activate
      python iniciar.py

  - Escanea el QR para vincular WhatsApp (panel del puente)
  - Prueba sin WhatsApp en:  http://localhost:8000/simulador
  - Pruebas automáticas:     ./.venv/bin/python -m pytest tests/ -q
============================================================
FIN
