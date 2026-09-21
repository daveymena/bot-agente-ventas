/**
 * Configuración del puente Baileys.
 * Todo se controla con variables de entorno (.env en la raíz del proyecto o
 * baileys-bridge/.env). No requiere exponer ningún webhook público.
 */
import 'dotenv/config';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const raizProyecto = path.resolve(__dirname, '..');

const bool = (valor, porDefecto = false) => {
  if (valor === undefined || valor === null || valor === '') return porDefecto;
  return ['1', 'true', 'yes', 'si', 'sí', 'on', 'y'].includes(String(valor).trim().toLowerCase());
};
const num = (valor, porDefecto) => {
  const n = Number(valor);
  return Number.isFinite(n) ? n : porDefecto;
};

export const config = {
  // ---- A dónde hablarle al agente Python
  agenteUrl: (process.env.AGENT_URL || 'http://127.0.0.1:8000').replace(/\/$/, ''),
  agenteToken: process.env.BRIDGE_TOKEN || '',
  agenteTimeoutMs: num(process.env.AGENT_TIMEOUT_MS, 45000),
  agenteReintentos: num(process.env.AGENT_REINTENTOS, 1),

  // ---- Servidor HTTP del puente (panel con QR y estado)
  puerto: num(process.env.BRIDGE_PORT, 3001),
  host: process.env.BRIDGE_HOST || '0.0.0.0',

  // ---- Sesión de WhatsApp
  authDir: process.env.BAILEYS_AUTH_DIR
    ? path.resolve(process.env.BAILEYS_AUTH_DIR)
    : path.join(__dirname, 'auth'),
  nombreDispositivo: process.env.BAILEYS_DEVICE_NAME || 'Agente de Ventas',
  logLevel: (process.env.BAILEYS_LOG_LEVEL || 'warn').toLowerCase(),

  // ---- Comportamiento con los mensajes
  responderGrupos: bool(process.env.RESPOND_TO_GROUPS, false),
  responderMisMensajes: bool(process.env.PERMITIR_MIS_MENSAJES, false),
  enviarLeido: bool(process.env.ENVIAR_LEIDO, true),
  enviarEscribiendo: bool(process.env.SEND_PRESENCE, true),
  ignorarPropios: !bool(process.env.PERMITIR_MIS_MENSAJES, false),

  // ---- Entrega de respuestas
  delayEntreRespuestasMs: num(process.env.DELAY_ENTRE_RESPUESTAS_MS, 900),
  maxLargoMensaje: num(process.env.MAX_LARGO_MENSAJE, 3500),
  maxMediaBytes: num(process.env.MAX_MEDIA_MB, 16) * 1024 * 1024,
  descargarMedia: bool(process.env.DESCARGAR_MEDIA, true),

  // ---- Notificaciones al dueño del negocio
  numeroDueno: (process.env.HUMAN_ESCALATION_NUMBER || '').replace(/\D/g, ''),

  raizProyecto,
  bridgeDir: __dirname,
};

export default config;
