/**
 * Puente WhatsApp (Baileys) <-> Agente de ventas (Python).
 *
 *   WhatsApp  <--Baileys-->  este puente  <--HTTP local-->  agente Python
 *
 *  - Genera el QR y muestra un panel web en http://localhost:3001
 *  - Escucha los mensajes entrantes y se los pasa al agente
 *  - Ejecuta las respuestas (texto, imágenes, audios, avisos al dueño)
 *
 * Arranque:  npm start     (dentro de baileys-bridge/)
 */
import makeWASocket, {
  DisconnectReason,
  fetchLatestBaileysVersion,
  makeCacheableSignalKeyStore,
  useMultiFileAuthState,
  Browsers,
} from '@whiskeysockets/baileys';
import { Boom } from '@hapi/boom';
import pino from 'pino';
import QRCode from 'qrcode';
import fs from 'node:fs';
import path from 'node:path';

import config from './src/config.js';
import { pedirRespuesta, notificarEvento, verificarAgente, log, logError } from './src/agente.js';
import { crearServidor } from './src/servidor.js';
import { esChatAtendible, ejecutarAcciones, extraerContenido, normalizarMensaje } from './src/whatsapp.js';

const logger = pino({ level: config.logLevel });

// ------------------------------------------------------------------- estado
const estado = {
  estado: 'iniciando', // iniciando | esperando_qr | conectado | desconectado | cerrado
  qrDataUrl: null,
  numero: '',
  nombre: '',
  motivo: '',           // por qué está desconectado (ayuda a diagnosticar la red)
  agente: { ok: false },
  metricas: { atendidos: 0, respuestas: 0, errores: 0, ultimoMensaje: '', ultimoError: '' },
  iniciadoEn: new Date().toISOString(),
};

/** Traduce el error de conexión a algo que el usuario pueda accionar. */
function explicarDesconexion(codigo, motivo) {
  const texto = String(motivo || '').toLowerCase();
  if (texto.includes('tls') || texto.includes('socket') || texto.includes('econnreset')) {
    return 'No se pudo abrir la conexión con los servidores de WhatsApp (TLS/red). ' +
      'Revisa firewall, proxy o DNS de esta red; el QR aparece cuando la conexión funciona.';
  }
  if (codigo === 401) return 'La sesión se cerró desde el teléfono. Hay que escanear el QR otra vez.';
  if (codigo === 408 || codigo === 428) return 'Sin respuesta de WhatsApp. Reintentando…';
  if (codigo === 440) return 'Sesión reemplazada por otro dispositivo vinculado.';
  if (codigo === 515) return 'WhatsApp pidió reiniciar la sesión; reconectando…';
  return motivo || 'Reintentando la conexión…';
}

let sock = null;
let reintentos = 0;
let cerrando = false;
const vistos = new Set(); // ids ya procesados (evita dobles respuestas)

const snapshot = () => ({
  ...estado,
  metricas: { ...estado.metricas },
  agente: { ...estado.agente },
  uptimeSegundos: Math.round((Date.now() - new Date(estado.iniciadoEn).getTime()) / 1000),
});

// ------------------------------------------------------------------ sesión
async function iniciarSesion({ cerrarSesion = false } = {}) {
  if (cerrarSesion && fs.existsSync(config.authDir)) {
    fs.rmSync(config.authDir, { recursive: true, force: true });
    log('sesión anterior eliminada (habrá que escanear el QR otra vez)');
  }

  const { state, saveCreds } = await useMultiFileAuthState(config.authDir);
  const { version, isLatest } = await fetchLatestBaileysVersion().catch(() => ({ version: undefined }));
  log(`Baileys ${Array.isArray(version) ? version.join('.') : 'desconocida'}${isLatest ? ' (última)' : ''}`);

  sock = makeWASocket({
    version,
    auth: { creds: state.creds, keys: makeCacheableSignalKeyStore(state.keys, logger) },
    logger,
    printQRInTerminal: false,
    browser: Browsers.appropriate(config.nombreDispositivo),
    markOnlineOnConnect: false,
    syncFullHistory: false,
    generateHighQualityLinkPreview: true,
    defaultQueryTimeoutMs: 30000,
  });

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('connection.update', async (actualizacion) => {
    const { connection, lastDisconnect, qr } = actualizacion;

    if (qr) {
      estado.estado = 'esperando_qr';
      estado.motivo = '';
      try {
        estado.qrDataUrl = await QRCode.toDataURL(qr, { margin: 1, width: 320 });
        log(`Escanea el QR en http://localhost:${config.puerto} (o revisa el aviso de la consola)`);
      } catch (error) {
        logError('no se pudo generar la imagen del QR', error.message);
      }
      await notificarEvento('esperando_qr');
    }

    if (connection === 'open') {
      estado.estado = 'conectado';
      estado.qrDataUrl = null;
      estado.motivo = '';
      reintentos = 0;
      const id = sock.user?.id || '';
      estado.numero = String(id).split(':')[0].split('@')[0];
      estado.nombre = sock.user?.name || sock.user?.verifiedName || '';
      log(`✅ WhatsApp conectado como ${estado.nombre} (${estado.numero})`);
      log(`   Panel: http://localhost:${config.puerto}  ·  Agente: ${config.agenteUrl}`);
      await notificarEvento('conectado', { numero: estado.numero, nombre: estado.nombre });
      estado.agente = await verificarAgente().catch(() => ({ ok: false, error: 'sin respuesta' }));
      if (!estado.agente.ok) {
        logError('el agente Python no responde en ' + config.agenteUrl + ' (arráncalo con: python main.py)');
      }
    }

    if (connection === 'close') {
      const codigo = new Boom(lastDisconnect?.error)?.output?.statusCode;
      const motivo = lastDisconnect?.error?.message || 'desconocido';
      estado.qrDataUrl = null;
      await notificarEvento('desconectado', { codigo, motivo });

      if (codigo === DisconnectReason.loggedOut) {
        estado.estado = 'cerrado';
        estado.motivo = explicarDesconexion(401, motivo);
        logError(estado.motivo);
        return;
      }
      if (cerrando) return;

      reintentos += 1;
      const espera = Math.min(3000 * reintentos, 60000);
      estado.estado = 'desconectado';
      estado.motivo = explicarDesconexion(codigo, motivo);
      if (reintentos === 1 || reintentos % 5 === 0) {
        log(`conexión cerrada (${codigo}): ${estado.motivo} Reintento en ${Math.round(espera / 1000)}s`);
      }
      setTimeout(() => iniciarSesion().catch((e) => logError('reconexión falló', e.message)), espera);
    }
  });

  // ---------------------------------------------------------- mensajes
  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    if (type !== 'notify') return;

    for (const msg of messages || []) {
      try {
        await manejarMensaje(msg);
      } catch (error) {
        estado.metricas.errores += 1;
        estado.metricas.ultimoError = error.message;
        logError('error procesando mensaje:', error.stack || error.message);
      }
    }
  });
}

async function manejarMensaje(msg) {
  if (!msg?.message || !msg.key) return;
  if (msg.messageStubType) return; // entradas/salidas de grupo, etc.
  if (!esChatAtendible(msg.key)) return;
  if (msg.key.id && vistos.has(msg.key.id)) return;
  if (msg.key.id) {
    vistos.add(msg.key.id);
    if (vistos.size > 5000) vistos.clear();
  }

  const contenido = extraerContenido(msg);
  if (contenido.tipo === 'reaccion') return; // no respondemos a reacciones

  const payload = await normalizarMensaje(sock, msg, logger);
  if (!payload.texto && !payload.media) return; // nada que procesar

  estado.metricas.atendidos += 1;
  estado.metricas.ultimoMensaje = `${payload.nombre}: ${(payload.texto || `[${payload.tipo}]`).slice(0, 60)}`;
  log(`⬅️  ${payload.nombre} (${payload.numero}): ${payload.texto || `[${payload.tipo}]`}`);

  const respuesta = await pedirRespuesta(payload);
  if (!respuesta.ok) {
    estado.metricas.errores += 1;
    estado.metricas.ultimoError = respuesta.error || 'agente sin respuesta';
    logError('el agente no respondió:', respuesta.error);
    return;
  }
  if (respuesta.ignorado || respuesta.acciones.length === 0) {
    log(`   (sin respuesta: ${respuesta.motivo || 'el agente decidió no contestar'})`);
    return;
  }

  await ejecutarAcciones(sock, respuesta.acciones, {
    jid: payload.chat_id,
    key: msg.key,
    logger,
    nombreNegocio: respuesta.debug?.negocio || '',
  });
  estado.metricas.respuestas += 1;
  log(`➡️  respuesta enviada a ${payload.numero} (${respuesta.intenciones.join(', ') || 'general'})`);
}

// ------------------------------------------------------------------- panel
const estadoBridge = {
  snapshot,
  enviarManual: async ({ numero, texto, jid }) => {
    if (estado.estado !== 'conectado' || !sock) {
      throw new Error('WhatsApp no está conectado todavía');
    }
    const destino = jid || `${String(numero || '').replace(/\D/g, '')}@s.whatsapp.net`;
    if (!destino || destino === '@s.whatsapp.net') throw new Error('número inválido');
    await sock.sendMessage(destino, { text: texto || 'Prueba del puente Baileys ✅' });
    return { ok: true, detalle: `Enviado a ${destino}` };
  },
  gestionarSesion: async (accion) => {
    if (accion === 'cerrar') {
      try {
        await sock?.logout();
      } catch { /* puede fallar si ya está cerrada */ }
      estado.estado = 'cerrado';
      estado.qrDataUrl = null;
      estado.numero = '';
      fs.rmSync(config.authDir, { recursive: true, force: true });
      setTimeout(() => iniciarSesion().catch(() => {}), 1500);
      return { ok: true, detalle: 'Sesión cerrada. Escanea el nuevo QR.' };
    }
    setTimeout(() => iniciarSesion().catch(() => {}), 500);
    return { ok: true, detalle: 'Reconectando…' };
  },
};

crearServidor(estadoBridge);

// ------------------------------------------------------------------ arranque
fs.mkdirSync(config.authDir, { recursive: true });

process.on('SIGINT', () => {
  cerrando = true;
  log('cerrando puente…');
  process.exit(0);
});
process.on('unhandledRejection', (error) => logError('promesa sin manejar:', error?.message || error));

console.log('══════════════════════════════════════════════════════');
console.log('  Puente WhatsApp (Baileys) · Agente de Ventas');
console.log(`  Panel y QR ....: http://localhost:${config.puerto}`);
console.log(`  Agente Python .: ${config.agenteUrl}`);
console.log(`  Mensajes propios: ${config.responderMisMensajes ? 'se responden (modo pruebas)' : 'ignorados'}`);
console.log(`  Grupos .........: ${config.responderGrupos ? 'se responden' : 'ignorados'}`);
console.log('══════════════════════════════════════════════════════');

estado.agente = await verificarAgente().catch(() => ({ ok: false, error: 'sin respuesta' }));
await iniciarSesion();
