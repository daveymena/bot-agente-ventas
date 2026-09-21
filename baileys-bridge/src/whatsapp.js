/**
 * Traduce un mensaje de Baileys al formato del agente y ejecuta las acciones
 * que el agente devuelve. Aquí vive TODO lo específico de WhatsApp.
 */
import { downloadMediaMessage, getContentType } from '@whiskeysockets/baileys';
import config from './config.js';
import { log, logError } from './agente.js';

const dormir = (ms) => new Promise((r) => setTimeout(r, ms));
const soloDigitos = (valor = '') => String(valor).replace(/\D/g, '');

// --------------------------------------------------------------------- lectura

/** ¿Es un chat que debemos atender? */
export function esChatAtendible(key) {
  const jid = key?.remoteJid || '';
  if (!jid) return false;
  if (jid === 'status@broadcast') return false;
  if (jid.endsWith('@broadcast')) return false;
  if (jid.endsWith('@newsletter')) return false;
  if (jid.endsWith('@g.us') && !config.responderGrupos) return false;
  if (key.fromMe && !config.responderMisMensajes) return false;
  return true;
}

/** Devuelve {tipo, texto} del mensaje entrante. */
export function extraerContenido(msg) {
  const tipoContenido = getContentType(msg.message || {}) || '';
  const m = msg.message || {};
  const texto =
    m.conversation ||
    m.extendedTextMessage?.text ||
    m.imageMessage?.caption ||
    m.videoMessage?.caption ||
    m.documentMessage?.caption ||
    m.buttonsResponseMessage?.selectedDisplayText ||
    m.buttonsResponseMessage?.selectedButtonId ||
    m.listResponseMessage?.title ||
    m.listResponseMessage?.singleSelectReply?.selectedRowId ||
    m.templateButtonReplyMessage?.selectedDisplayText ||
    '';

  const mapa = {
    conversation: 'texto',
    extendedTextMessage: 'texto',
    imageMessage: 'imagen',
    videoMessage: 'video',
    audioMessage: 'audio',
    documentMessage: 'documento',
    stickerMessage: 'sticker',
    locationMessage: 'ubicacion',
    contactMessage: 'contacto',
    contactsArrayMessage: 'contacto',
    buttonsResponseMessage: 'boton',
    listResponseMessage: 'lista',
    templateButtonReplyMessage: 'boton',
    reactionMessage: 'reaccion',
    ptvMessage: 'video',
  };
  const tipo = mapa[tipoContenido] || (texto ? 'texto' : 'desconocido');
  return { tipo, texto: (texto || '').trim(), tipoContenido };
}

/** Convierte el mensaje de Baileys en el payload que espera el agente Python. */
export async function normalizarMensaje(sock, msg, logger) {
  const key = msg.key || {};
  const jid = key.remoteJid || '';
  const { tipo, texto } = extraerContenido(msg);
  const esGrupo = jid.endsWith('@g.us');
  const nombre =
    msg.pushName ||
    (key.fromMe ? 'Cliente (yo)' : '') ||
    '';

  const payload = {
    id: key.id || '',
    chat_id: jid,
    numero: soloDigitos(jid.split('@')[0]),
    tipo,
    texto,
    nombre: nombre || 'Cliente',
    es_grupo: esGrupo,
    from_me: Boolean(key.fromMe),
    participante: key.participant || '',
    timestamp: Number(msg.messageTimestamp || Math.floor(Date.now() / 1000)),
    dispositivo: msg.key?.id && msg.message ? 'whatsapp' : 'desconocido',
  };

  // Media: descargamos y enviamos en base64 (audios para transcribir, etc.)
  if (config.descargarMedia && ['audio', 'imagen', 'video', 'documento', 'sticker'].includes(tipo)) {
    try {
      const buffer = await downloadMediaMessage(
        msg,
        'buffer',
        {},
        { logger, reuploadRequest: sock.updateMediaMessage },
      );
      if (buffer && buffer.length <= config.maxMediaBytes) {
        const mimetype =
          msg.message?.audioMessage?.mimetype ||
          msg.message?.imageMessage?.mimetype ||
          msg.message?.videoMessage?.mimetype ||
          msg.message?.documentMessage?.mimetype ||
          'application/octet-stream';
        payload.media = {
          base64: buffer.toString('base64'),
          mimetype,
          bytes: buffer.length,
          segundos: msg.message?.audioMessage?.seconds || null,
          nombre_archivo: msg.message?.documentMessage?.fileName || '',
          ptt: Boolean(msg.message?.audioMessage?.ptt),
        };
      } else {
        payload.media_error = 'archivo demasiado grande';
      }
    } catch (error) {
      payload.media_error = `no se pudo descargar: ${error.message}`;
      logError('descarga de media falló:', error.message);
    }
  }

  return payload;
}

// --------------------------------------------------------------------- envío

/** Divide textos largos en trozos legibles (WhatsApp corta ~4096). */
export function trocear(texto, limite = config.maxLargoMensaje) {
  const t = String(texto || '').trim();
  if (t.length <= limite) return t ? [t] : [];

  const bloques = t.split(/\n{2,}/);
  const salida = [];
  let actual = '';

  const empujar = () => {
    if (actual.trim()) salida.push(actual.trim());
    actual = '';
  };

  for (const bloque of bloques) {
    if ((actual + '\n\n' + bloque).trim().length <= limite) {
      actual = actual ? `${actual}\n\n${bloque}` : bloque;
      continue;
    }
    empujar();
    if (bloque.length <= limite) {
      actual = bloque;
      continue;
    }
    // bloque enorme: cortamos por líneas y, si hace falta, por caracteres
    let sobrante = bloque;
    while (sobrante.length > limite) {
      const corte = sobrante.lastIndexOf('\n', limite);
      const indice = corte > limite * 0.5 ? corte : limite;
      const trozo = sobrante.slice(0, indice);
      const resto = sobrante.slice(indice).trimStart();
      salida.push(trozo.trim());
      sobrante = resto;
    }
    actual = sobrante;
  }
  empujar();
  return salida;
}

/** Ejecuta la lista de acciones devuelta por el agente. */
export async function ejecutarAcciones(sock, acciones, contexto = {}) {
  const { jid, logger, key, nombreNegocio = '' } = contexto;
  if (!jid || !Array.isArray(acciones) || acciones.length === 0) return;

  for (const accion of acciones) {
    const tipo = (accion?.tipo || '').toLowerCase();
    try {
      switch (tipo) {
        case 'presencia': {
          if (!config.enviarEscribiendo) break;
          await sock.sendPresenceUpdate(accion.estado || 'composing', jid);
          await dormir(Math.min(Number(accion.ms) || 800, 8000));
          break;
        }
        case 'leer': {
          if (config.enviarLeido && key) await sock.readMessages([key]);
          break;
        }
        case 'texto': {
          const trozos = trocear(accion.texto);
          for (let i = 0; i < trozos.length; i += 1) {
            if (config.enviarEscribiendo) {
              // pausa proporcional al largo: da sensación humana
              const ms = Math.min(400 + trozos[i].length * 12, 4000);
              await sock.sendPresenceUpdate('composing', jid);
              await dormir(ms);
            }
            await sock.sendMessage(jid, { text: trozos[i] });
            if (i < trozos.length - 1) await dormir(config.delayEntreRespuestasMs);
          }
          break;
        }
        case 'imagen':
        case 'foto': {
          if (!accion.url && !accion.base64) break;
          const media = accion.base64
            ? Buffer.from(accion.base64, 'base64')
            : { url: accion.url };
          await sock.sendMessage(jid, {
            image: media,
            caption: accion.caption || accion.texto || '',
          });
          break;
        }
        case 'audio': {
          if (!accion.url && !accion.base64) break;
          const media = accion.base64 ? Buffer.from(accion.base64, 'base64') : { url: accion.url };
          await sock.sendMessage(jid, {
            audio: media,
            mimetype: accion.mimetype || 'audio/mpeg',
            ptt: accion.ptt !== false,
          });
          break;
        }
        case 'documento': {
          if (!accion.url && !accion.base64) break;
          const media = accion.base64 ? Buffer.from(accion.base64, 'base64') : { url: accion.url };
          await sock.sendMessage(jid, {
            document: media,
            mimetype: accion.mimetype || 'application/pdf',
            fileName: accion.nombre || 'documento.pdf',
            caption: accion.caption || '',
          });
          break;
        }
        case 'reaccion': {
          if (!key) break;
          await sock.sendMessage(jid, { react: { text: accion.emoji || '👍', key } });
          break;
        }
        case 'notificar': {
          const destino = accion.numero || config.numeroDueno;
          if (!destino) {
            log('aviso al dueño omitido: no hay HUMAN_ESCALATION_NUMBER configurado');
            break;
          }
          const jidDueno = `${soloDigitos(destino)}@s.whatsapp.net`;
          await sock.sendMessage(jidDueno, { text: accion.texto || 'Nuevo aviso' });
          log('aviso enviado al dueño del negocio');
          break;
        }
        case 'ignorar':
        case 'nada':
          break;
        default:
          log(`acción desconocida ignorada: ${tipo}`);
      }
    } catch (error) {
      logError(`falló la acción "${tipo}":`, error.message);
      if (['texto', 'imagen'].includes(tipo) && nombreNegocio) {
        try {
          await sock.sendMessage(jid, {
            text: `Disculpa, tuve un problema técnico enviando la información de ${nombreNegocio} 🙏 ¿Me repites la pregunta?`,
          });
        } catch { /* nada más que hacer */ }
      }
    }
    if (tipo !== 'presencia') await dormir(config.delayEntreRespuestasMs);
  }
}
