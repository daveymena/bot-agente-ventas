# 🤖 Agente de Ventas para WhatsApp · cualquier negocio (productos y servicios)

Agente que atiende WhatsApp automáticamente: entiende lo que pide el cliente,
busca en **tu catálogo real** (productos, servicios, planes o alquileres) y
responde con precios, disponibilidad, horarios y el paso siguiente (agendar,
separar, cotizar). Sin Evolution API, sin ngrok y sin webhooks públicos:
WhatsApp se conecta con **Baileys**.

Diseñado para ser **multi-rubro**: una tienda, un restaurante, una barbería, un
taller, un consultorio, una inmobiliaria o una agencia de servicios usan el
**mismo código** y solo cambian `config/negocio.json`.

---

## 🧠 Cómo funciona

```
   WhatsApp
       ↕  (Baileys: escucha y envía)
┌──────────────────────┐        HTTP local       ┌───────────────────────────┐
│  baileys-bridge/     │  ───────────────────►   │  Motor Python (main.py)   │
│  Node + Baileys      │   POST /mensaje         │  · intención del mensaje  │
│  · QR de vinculación │   ◄───────────────────  │  · búsqueda en el catálogo │
│  · envía las         │   plan de acciones      │  · respuesta con datos    │
│    respuestas        │   (texto, imagen, ...)  │    reales del negocio     │
└──────────────────────┘                         └───────────────────────────┘
        ▲                                                     ▲
        │ panel web con QR                                    │ simulador web
        └── http://localhost:3001                           └── /simulador
```

El motor **no sabe nada de WhatsApp**: recibe un mensaje normalizado y devuelve
una lista de acciones (`texto`, `imagen`, `notificar` al dueño, `presencia`…).
Así el mismo cerebro sirve para el puente de Baileys, para el simulador web o
para cualquier integración futura. Y **nunca inventa**: si un dato no está en el
catálogo o en el perfil del negocio, no aparece en la respuesta.

---

## 🚀 Arranque rápido

Requisitos: **Python 3.10+** y **Node.js 18+**.

```bash
# 1) instalación (crea .venv, instala dependencias y crea .env)
./setup.sh

# 2) arranca motor + puente de WhatsApp
source .venv/bin/activate
python iniciar.py
```

Luego:

| Qué | Dónde |
|---|---|
| Vincular WhatsApp (QR) | `http://localhost:3001` → escanea con WhatsApp › Dispositivos vinculados |
| Probar sin WhatsApp | `http://localhost:8000/simulador` |
| Estado del agente | `http://localhost:8000/estado` |

¿Solo quieres probar el motor sin WhatsApp? `python iniciar.py --solo-api`

---

## 🏪 Configurar tu negocio (esto es todo lo que hay que editar)

Todo vive en **`config/negocio.json`**: identidad, horarios, pagos, envíos,
políticas, preguntas frecuentes y el catálogo. El agente lo **recarga solo** al
guardar el archivo, sin reiniciar.

```jsonc
{
  "negocio": {
    "nombre": "Mi Negocio",
    "tipo_negocio": "mixto",              // productos | servicios | mixto
    "ciudad": "Cali", "direccion": "…", "telefono": "573001112233",
    "horarios": [ { "dia": "lunes", "abre": "08:00", "cierra": "18:00" },
                  { "dia": "domingo", "cerrado": true } ],
    "metodos_pago": ["Efectivo", "Nequi", "Tarjeta"],
    "envio": "Envío gratis en la ciudad desde $150.000",
    "cobertura": "Cali, Palmira, Yumbo",
    "politicas": ["Garantía de 12 meses…"],
    "promociones": ["10% pagando en efectivo"],
    "faqs": [ { "pregunta": "¿Dan factura?", "respuesta": "Sí, electrónica 🧾" } ],

    "catalogo": [
      { "nombre": "Portátil Lenovo IdeaPad 3", "tipo": "producto",
        "categoria": "Computadores", "precio": 2150000, "stock": 6,
        "descripcion": "Core i5, 8GB RAM, SSD 512GB",
        "etiquetas": ["portátil", "laptop", "oficina"], "destacado": true,
        "imagen": "https://…/foto.jpg" },

      { "nombre": "Mantenimiento preventivo", "tipo": "servicio",
        "categoria": "Servicio técnico", "precio": 90000,
        "duracion": "1 a 2 horas", "modalidad": "a domicilio o en el local",
        "incluye": ["Limpieza", "Pasta térmica"], "disponibilidad": "por_agenda",
        "agenda": "Citas de lunes a sábado" }
    ]
  }
}
```

**Claves del catálogo** (funcionan igual para productos y servicios):

| Campo | Para qué sirve |
|---|---|
| `tipo` | `producto`, `servicio`, `plan`, `inmueble`… cambia el tono y los emojis |
| `precio` | Número (permite filtrar por presupuesto). Si es variable usa `precio_texto` |
| `precio_texto` | "Desde $120.000 según el modelo", "10% del canon" |
| `disponibilidad` | `disponible`, `agotado`, `bajo_pedido`, `por_agenda`, `preventa`, `consultar` |
| `duracion`, `modalidad`, `incluye`, `requisitos`, `agenda` | Pensados para servicios y citas |
| `garantia`, `entrega`, `promocion` | Se muestran en la ficha del ítem |
| `etiquetas`, `sinonimos` | Mejoran la búsqueda ("portátil", "notebook", "cortada") |
| `imagen` | El agente la envía junto con la ficha del ítem |
| `atributos` | Ficha técnica libre: `{"Procesador": "Core i5"}` |

### Negocios de ejemplo listos para copiar

```bash
cp negocios/ejemplos/restaurante.json config/negocio.json
```

| Ejemplo | Rubro |
|---|---|
| `restaurante.json` | Platos, bebidas, catering por evento |
| `barberia.json` | Cortes, barba, productos de cuidado |
| `taller-automotriz.json` | Mantenimiento, llantas, revisión precompra |
| `consultorio-dental.json` | Consultas, ortodoncia, urgencias |
| `inmobiliaria.json` | Arriendos, ventas, administración de propiedades |
| `tienda-tecnologia.json` | Equipos, accesorios, servicios técnicos |
| `agencia-servicios.json` | Contabilidad, marca, marketing, jurídica |

También aceptan claves en inglés (`title`, `price`, `duration`…) y campos libres
en `atributos`, así que puedes reutilizar el catálogo que ya tengas.

---

## 💬 Qué entiende y cómo responde

| El cliente dice… | El agente responde con… |
|---|---|
| "hola" / "buenas" | Bienvenida del negocio + menú de categorías reales + destacados. Si está cerrado, lo dice |
| "¿qué venden / qué servicios ofrecen?" | Categorías con ejemplos y precios reales |
| "¿cuánto vale el portátil Lenovo?" | Ficha completa del ítem + alternativas + cierre para comprar |
| "busco un ipone 13" (con typo) | El iPhone real (coincidencia aproximada) |
| "¿tienen impresora disponible?" | Disponibilidad real: "quedan 6" o "está agotado por ahora" |
| "quiero agendar mantenimiento" | Detalle del servicio (duración, modalidad, qué incluye) + datos para agendar + **aviso al equipo** |
| "quiero cotizar redes para mi oficina" | Pide los datos necesarios y **avisa a un asesor** |
| "tengo 300 mil, ¿qué me alcanza?" | Solo opciones dentro del presupuesto |
| "eso está muy caro" | Alternativas más económicas reales + opciones de pago + aviso al equipo |
| "¿hacen envíos a Bogotá?" | Valida la cobertura: si no llega, lo dice y ofrece confirmarlo |
| "¿los domingos atienden?" / "¿dónde quedan?" | Horario (con si está abierto ahora) / dirección y mapa |
| "¿aceptan tarjeta?" / "¿tienen factura?" | Respuesta desde `metodos_pago` o tus `faqs` |
| "quiero hablar con una persona" / queja | Mensaje empático + **aviso inmediato al dueño** por WhatsApp |
| Nota de voz | La transcribe (si configuras OpenAI) y responde igual |

Los avisos al dueño (citas, cotizaciones, quejas, escalados) llegan al número de
`HUMAN_ESCALATION_NUMBER` (o `numero_escalado` del negocio).

---

## 🔌 IA: opcional, y nunca inventa

El agente **funciona sin IA** con el motor de respuestas propio (catálogo +
plantillas por intención). Si configuras un proveedor, la IA se usa solo para
**redactar mejor** la misma respuesta, con instrucciones estrictas de usar
únicamente los datos verificados:

```bash
./.venv/bin/pip install -r requirements-ia.txt   # Gemini y/o OpenAI
```

```env
GOOGLE_GEMINI_API_KEY=...     # prioridad 1
OPENAI_API_KEY=...            # prioridad 2 (también transcribe audios con Whisper)
OLLAMA_BASE_URL=...           # prioridad 3 (modelos locales, sin costo)
```

Prioridad: `gemini → openai → ollama → motor propio`. Puedes forzarla con
`AI_PROVIDER=gemini|openai|ollama|rules`.

---

## 🌐 API

| Método | Ruta | Para qué |
|---|---|---|
| `POST` | `/mensaje` | Recibe un mensaje y devuelve el plan de acciones (lo usa el puente y el simulador) |
| `POST` | `/webhook` | Misma lógica, compatible con payloads antiguos (Evolution/n8n) |
| `POST` | `/evento-whatsapp` | El puente reporta conexión, desconexión o QR pendiente |
| `GET` | `/estado` | Negocio, catálogo, IA, memoria y métricas |
| `GET` | `/negocio` | Perfil del negocio cargado |
| `GET` | `/catalogo?q=&categoria=&tipo=` | Buscar en el catálogo |
| `POST` | `/catalogo/recargar` | Releer `config/negocio.json` |
| `POST` | `/catalogo/importar-web` | Importar ítems desde las webs del negocio (`fuentes_scraping`) |
| `GET` | `/simulador` | Interfaz de chat para probar sin WhatsApp |
| `GET` | `/health` | Salud del servicio |

Ejemplo:

```bash
curl -X POST http://localhost:8000/mensaje -H 'Content-Type: application/json' -d '{
  "mensaje": {"id":"1","chat_id":"573001112233@s.whatsapp.net","texto":"cuanto vale el corte","tipo":"texto","nombre":"Ana"}
}'
```

Respuesta:

```json
{
  "ok": true, "ignorado": false, "intenciones": ["consulta_item"],
  "acciones": [
    {"tipo": "leer"},
    {"tipo": "presencia", "estado": "composing", "ms": 700},
    {"tipo": "texto", "texto": "📦 *Corte de cabello clásico*\n💰 $25.000…"},
    {"tipo": "imagen", "url": "https://…", "caption": "…"}
  ],
  "debug": {"negocio": "Barbería El Rey", "ia": "motor-propio", "escalar": false}
}
```

---

## ✅ Pruebas

```bash
./.venv/bin/python -m pytest tests/ -q
```

53 pruebas cubren: utilidades de texto y precios, ranking del catálogo con dos
rubros distintos, tipologías de negocio, y el flujo completo del agente
(respuestas con datos reales, duplicados, grupos, presupuestos, escalado a
humano, audios sin transcribir y mensajes raros).

---

## 🕓 24/7

**Opción recomendada (Docker):**

```bash
cp .env.example .env      # edita BRIDGE_TOKEN, HUMAN_ESCALATION_NUMBER…
docker compose up -d --build
docker compose logs -f puente    # aquí ves el QR la primera vez
```

**Opción VPS / servidor propio (systemd):** dos servicios, el motor y el puente.

```ini
# /etc/systemd/system/agente-ventas.service
[Unit]
Description=Agente de ventas (motor)
After=network.target

[Service]
WorkingDirectory=/opt/bot-agente-ventas
ExecStart=/opt/bot-agente-ventas/.venv/bin/python main.py
Restart=always
EnvironmentFile=/opt/bot-agente-ventas/.env

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/agente-whatsapp.service
[Unit]
Description=Puente WhatsApp (Baileys)
After=network.target agente-ventas.service

[Service]
WorkingDirectory=/opt/bot-agente-ventas/baileys-bridge
ExecStart=/usr/bin/node index.js
Restart=always
EnvironmentFile=/opt/bot-agente-ventas/.env

[Install]
WantedBy=multi-user.target
```

> 💡 El QR se escanea **una sola vez**: la sesión queda en
> `baileys-bridge/auth/` (o en el volumen `sesion_whatsapp` con Docker). Ese
> directorio es una credencial: no lo subas al repositorio.

---

## 🔐 Seguridad

- `.env` y `baileys-bridge/auth/` están en `.gitignore`: nunca los subas.
- Define `BRIDGE_TOKEN` y `WEBHOOK_TOKEN` en producción: el puente autentica
  contra el motor y el motor exige el token en `/mensaje`.
- **Rota las credenciales que quedaron expuestas en el historial del
  repositorio** (URL de Evolution API, API key de WhatsApp y la API key de
  Gemini de los documentos antiguos): considera esas claves comprometidas.
- Si el WhatsApp se desvincula, vuelve a escanear el QR en el panel del puente.

---

## 📁 Estructura

```
bot-agente-ventas/
├── baileys-bridge/          # Puente WhatsApp (Node + Baileys)
│   ├── index.js             # conexión, QR, escucha de mensajes
│   └── src/                 # config, cliente del agente, envío, panel web
├── config/
│   ├── business.py          # perfil del negocio (horarios, cobertura…)
│   ├── negocio.json         # ⬅️ TU negocio y tu catálogo
│   └── settings.py          # configuración técnica (env)
├── core/
│   ├── sales_agent.py       # orquesta intención → catálogo → respuesta → acciones
│   └── memoria.py           # contexto por conversación
├── models/
│   ├── catalog.py           # producto/servicio (mismo modelo para todo rubro)
│   └── message.py           # normalización de mensajes entrantes
├── services/
│   ├── catalog_service.py   # búsqueda y ranking en el catálogo
│   ├── intent_service.py    # qué quiere el cliente
│   ├── response_builder.py  # plantillas de respuesta por intención
│   ├── ai_service.py        # IA opcional (redacción con datos verificados)
│   ├── audio_service.py     # transcripción de notas de voz
│   └── scraping_service.py  # importar catálogo desde la web (opcional)
├── negocios/ejemplos/       # 7 negocios listos para copiar
├── web/simulador.html       # chat de pruebas
├── tests/                   # 53 pruebas
├── main.py                  # API + simulador
├── iniciar.py               # arranca motor + puente
└── docker-compose.yml       # despliegue 24/7
```

---

## 🆘 Problemas comunes

| Síntoma | Solución |
|---|---|
| No aparece el QR | Revisa `docker compose logs -f puente` o la consola de `iniciar.py`; abre `http://localhost:3001` |
| El bot no contesta | Mira `/estado` → `metricas` y el log. Si `whatsapp` está desconectado, vuelve a escanear el QR |
| Responde cualquier cosa | Completa `etiquetas`/`sinonimos` del ítem y ajusta `MATCH_THRESHOLD` (más alto = más estricto) |
| Dice "no tengo registrado X" | Que el ítem exista en `config/negocio.json` con `disponibilidad` correcta |
| Los avisos no llegan al dueño | Define `HUMAN_ESCALATION_NUMBER` con indicativo de país (ej: `573001112233`) |
| No transcribe audios | Instala `requirements-ia.txt` y configura `OPENAI_API_KEY` |

---

Hecho para vender y atender mejor, sin depender de plataformas externas. 💬
