# 📱 Guía rápida: conectar WhatsApp con Baileys

Este proyecto **no usa Evolution API, ni ngrok, ni Vercel**. El WhatsApp se
conecta desde `baileys-bridge/` (Node + Baileys), que abre una sesión de
WhatsApp Web y muestra un **QR para escanear una sola vez**.

```
┌──────────────┐   Baileys (WhatsApp Web)   ┌────────────────────┐
│ Tu WhatsApp  │ ◄────────────────────────► │  baileys-bridge/   │
└──────────────┘                            │  panel en :3001    │
                                            └─────────┬──────────┘
                                                      │ HTTP local
                                            ┌─────────▼──────────┐
                                            │  Motor Python :8000 │
                                            └────────────────────┘
```

---

## 1. Arrancar los dos servicios

```bash
source .venv/bin/activate
python iniciar.py
```

Verás algo así:

```
[agente] Servidor del agente escuchando en http://0.0.0.0:8000
[bridge] Panel y QR ....: http://localhost:3001
[bridge] Baileys 2.3000.1043857760
[bridge] Escanea el QR en http://localhost:3001
```

## 2. Escanear el QR

1. Abre **http://localhost:3001** (el panel).
2. En el teléfono: **WhatsApp → Ajustes → Dispositivos vinculados → Vincular un
   dispositivo**.
3. Escanea el QR de la página.

Cuando conecte, el panel lo confirma:

```
✅ WhatsApp conectado como Mi Negocio (573001112233)
```

> El QR cambia cada ~20 segundos si no lo escaneas: la página se recarga sola.
> Si el navegador está en otra máquina, abre `http://IP-DEL-SERVIDOR:3001`.

## 3. Probar

- Escríbele al número vinculado desde **otro** teléfono: el agente responde solo.
- ¿Estás solo y sin otro teléfono? Pon `PERMITIR_MIS_MENSAJES=true` en `.env` y
  reinicia: así el agente también responde en tu chat "Mensajes contigo mismo"
  (útil para probar sin molestar a nadie).
- Panel del puente → **Probar envío** para mandar un mensaje manual.
- Sin WhatsApp: `http://localhost:8000/simulador`.

## 4. La sesión se recuerda

Las credenciales quedan en `baileys-bridge/auth/` (o en el volumen
`sesion_whatsapp` con Docker), así que no hay que escanear de nuevo en cada
reinicio. Ese directorio **es una credencial**: está en `.gitignore`, no lo
compartas ni lo subas al repositorio.

Para cerrar sesión y volver a empezar: en el panel, **Cerrar sesión (borrar QR)**,
o borra la carpeta `baileys-bridge/auth/` y reinicia.

---

## 🆘 Problemas comunes

| Síntoma | Qué hacer |
|---|---|
| "No aparece el QR" | Revisa la consola del puente (`docker compose logs -f puente`). Si dice `connection closed`, la red está bloqueando `web.whatsapp.com`: usa otra red/proxy o un VPS |
| `WebSocket Error / TLS` | Red con firewall o DNS filtrado. Prueba en otra red o servidor |
| "conexión cerrada (401)" | Sesión cerrada desde el teléfono: borra `baileys-bridge/auth/` y re-escanea |
| El bot no contesta | `curl localhost:8000/estado` → revisa `metricas` y `ultimos_eventos_whatsapp`; mira `logs/agente_ventas.log` |
| "el agente Python no responde" | Arranca el motor (`python main.py`) y verifica `AGENT_URL` en `.env` |
| Recibe pero no responde a nadie | Revisa el filtro de grupos (`RESPOND_TO_GROUPS`) y que no sean mensajes propios |
| Responde "Disculpa, tuve un problema técnico" | Mira el log del puente: suele ser una acción con URL de imagen rota |
| Se desconecta cada rato | Normalmente red inestable: el puente reconecta solo con espera progresiva. Para 24/7 usa Docker con `restart: unless-stopped` |

## 🔒 Recomendaciones para producción

1. Define `BRIDGE_TOKEN` y `WEBHOOK_TOKEN` en `.env` (el puente firma sus
   peticiones y el motor las exige).
2. No expongas el puerto 3001 a internet: es solo para escanear el QR. Ciérralo
   (o no lo publiques) cuando ya estés conectado.
3. Corre los dos servicios como servicio (systemd o Docker) para que se
   reinicien solos: ver la sección **24/7** del `README.md`.
4. Usa un número **dedicado** del negocio, no tu WhatsApp personal: si el
   teléfono se desconecta mucho o WhatsApp marca el número, puedes perderlo.
5. Haz copia de seguridad del directorio `auth/` si quieres migrar de servidor
   sin volver a escanear.
