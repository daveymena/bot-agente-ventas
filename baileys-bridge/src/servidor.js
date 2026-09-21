/**
 * Panel web del puente: muestra el QR para escanear, el estado de la sesión y
 * permite enviar mensajes de prueba. Se sirve en http://localhost:3001
 */
import express from 'express';
import QRCode from 'qrcode';
import config from './config.js';

const escapar = (t = '') =>
  String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

const ESTILOS = `
:root { color-scheme: dark; }
* { box-sizing: border-box; }
body { margin:0; font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  background:#0b141a; color:#e9edef; min-height:100vh; padding:24px; }
.contenedor { max-width:820px; margin:0 auto; }
h1 { font-size:22px; margin:0 0 4px; }
p.sub { color:#8696a0; margin:0 0 24px; font-size:14px; }
.tarjeta { background:#111b21; border:1px solid #222d34; border-radius:14px; padding:20px; margin-bottom:16px; }
.estado { display:inline-flex; align-items:center; gap:8px; font-weight:600; }
.punto { width:10px; height:10px; border-radius:50%; display:inline-block; }
.verde { background:#25d366; } .rojo { background:#f15c6d; } .ambar { background:#f0b90b; }
.qr { display:flex; justify-content:center; padding:16px; background:#fff; border-radius:12px; }
.qr img { width:min(320px, 80vw); height:auto; image-rendering:pixelated; }
.pasos { line-height:1.7; font-size:14px; color:#d1d7db; }
.pasos code { background:#1f2c33; padding:2px 6px; border-radius:6px; font-size:13px; }
input, button { font:inherit; padding:10px 12px; border-radius:10px; border:1px solid #2a3942;
  background:#202c33; color:#e9edef; }
input { width:100%; margin-bottom:8px; }
button { cursor:pointer; background:#00a884; border-color:#00a884; color:#04211c; font-weight:600; }
button.sec { background:transparent; color:#e9edef; border-color:#2a3942; }
table { width:100%; font-size:13px; border-collapse:collapse; }
td { padding:4px 0; color:#8696a0; } td:last-child { color:#e9edef; text-align:right; }
a { color:#53bdeb; }
`;

const pagina = (titulo, cuerpo) => `<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${escapar(titulo)}</title><style>${ESTILOS}</style>
${cuerpo.includes('id="qr-auto"') ? '<meta http-equiv="refresh" content="20">' : ''}
</head><body><div class="contenedor">${cuerpo}</div></body></html>`;

function htmlPanel(estado) {
  const conectado = estado.estado === 'conectado';
  const clase = conectado ? 'verde' : estado.estado === 'esperando_qr' ? 'ambar' : 'rojo';
  const qr = estado.qrDataUrl
    ? `<div class="tarjeta"><h3 style="margin-top:0">Escanea con WhatsApp</h3>
        <div class="qr"><img src="${estado.qrDataUrl}" alt="Código QR de WhatsApp"></div>
        <div class="pasos"><p>Esta página se recarga sola cada 20 segundos si el QR expira.</p></div></div>`
    : '';

  return pagina('Puente WhatsApp - Agente de Ventas', `
    <h1>Puente WhatsApp (Baileys)</h1>
    <p class="sub">Conecta tu WhatsApp con el agente de ventas. Sin webhooks públicos ni túneles.</p>

    <div class="tarjeta">
      <div class="estado"><span class="punto ${clase}"></span>
        ${conectado ? 'Conectado' : estado.estado === 'esperando_qr' ? 'Esperando escaneo del QR' : 'Desconectado'}
      </div>
      <table style="margin-top:12px">
        <tr><td>Número conectado</td><td>${escapar(estado.numero || '—')}</td></tr>
        <tr><td>Nombre</td><td>${escapar(estado.nombre || '—')}</td></tr>
        <tr><td>Agente (Python)</td><td>${escapar(estado.agente?.ok ? 'conectado' : `sin respuesta: ${estado.agente?.error || ''}`)}</td></tr>
        <tr><td>Mensajes atendidos</td><td>${estado.metricas?.atendidos ?? 0}</td></tr>
        <tr><td>Respuestas enviadas</td><td>${estado.metricas?.respuestas ?? 0}</td></tr>
        <tr><td>Grupos</td><td>${config.responderGrupos ? 'se responden' : 'ignorados'}</td></tr>
        <tr><td>Último mensaje</td><td>${escapar(estado.metricas?.ultimoMensaje || '—')}</td></tr>
      </table>
    </div>
    ${qr}
    ${!conectado && estado.motivo ? `<div class="tarjeta"><strong>¿Por qué no hay QR todavía?</strong>
      <p class="pasos" style="margin-bottom:0">${escapar(estado.motivo)}</p></div>` : ''}
    ${!conectado && !estado.qrDataUrl && !estado.motivo ? '<div class="tarjeta"><div class="pasos">Iniciando sesión de WhatsApp… recarga en unos segundos. Si no aparece el QR, revisa la consola del puente.</div></div>' : ''}

    <div class="tarjeta">
      <h3 style="margin-top:0">Probar envío</h3>
      <form method="POST" action="/enviar">
        <input name="numero" placeholder="Número destino (ej: 573001112233)" required>
        <input name="texto" placeholder="Mensaje de prueba" required>
        <button type="submit">Enviar por WhatsApp</button>
      </form>
    </div>

    <div class="tarjeta">
      <h3 style="margin-top:0">Sesión</h3>
      <form method="POST" action="/sesion" style="display:flex; gap:8px; flex-wrap:wrap">
        <button class="sec" name="accion" value="reconectar">Reconectar</button>
        <button class="sec" name="accion" value="cerrar">Cerrar sesión (borrar QR)</button>
      </form>
      <p class="pasos" style="margin-bottom:0">API: <code>GET /estado</code> · <code>GET /health</code> · <code>POST /enviar</code> · <code>POST /sesion</code></p>
    </div>
  `);
}

export function crearServidor(estadoBridge) {
  const app = express();
  app.use(express.urlencoded({ extended: true }));
  app.use(express.json());

  app.get('/', (_req, res) => res.type('html').send(htmlPanel(estadoBridge.snapshot())));

  app.get('/qr', async (_req, res) => {
    const estado = estadoBridge.snapshot();
    if (estado.qrDataUrl) {
      res.type('html').send(pagina('QR WhatsApp', `<div class="tarjeta">
        <h1>Vincula tu WhatsApp</h1>
        <p class="sub">Abre WhatsApp → Dispositivos vinculados → Vincular dispositivo.</p>
        <div class="qr"><img src="${estado.qrDataUrl}" alt="QR"></div>
      </div>`));
      return;
    }
    res.type('html').send(pagina('QR WhatsApp', `<div class="tarjeta"><h1>${estado.estado === 'conectado' ? 'Ya está conectado ✅' : 'Generando QR…'}</h1>
      <p class="sub">${escapar(estado.numero || '')}</p><p><a href="/">Volver al panel</a></p></div>`));
  });

  app.get('/estado', (_req, res) => res.json(estadoBridge.snapshot()));

  app.get('/health', (_req, res) => {
    const estado = estadoBridge.snapshot();
    res.json({
      ok: estado.estado === 'conectado',
      estado: estado.estado,
      numero: estado.numero,
      agente: estado.agente,
      metricas: estado.metricas,
    });
  });

  app.post('/enviar', async (req, res) => {
    const { numero, texto, jid } = req.body || {};
    try {
      const resultado = await estadoBridge.enviarManual({ numero, texto, jid });
      if (req.is('application/json')) return res.json(resultado);
      return res.type('html').send(pagina('Enviado', `<div class="tarjeta"><h1>${resultado.ok ? 'Mensaje enviado ✅' : 'No se pudo enviar'}</h1>
        <p class="sub">${escapar(resultado.detalle || '')}</p><p><a href="/">Volver</a></p></div>`));
    } catch (error) {
      return res.status(400).json({ ok: false, error: error.message });
    }
  });

  app.post('/sesion', async (req, res) => {
    const accion = (req.body || {}).accion || 'reconectar';
    const resultado = await estadoBridge.gestionarSesion(accion);
    if (req.is('application/json')) return res.json(resultado);
    return res.type('html').send(pagina('Sesión', `<div class="tarjeta"><h1>${escapar(resultado.detalle || 'Listo')}</h1>
      <p><a href="/">Volver al panel</a></p></div>`));
  });

  return app.listen(config.puerto, config.host, () => {
    console.log(`[panel] QR y estado en http://localhost:${config.puerto}`);
  });
}
