/**
 * Cliente HTTP hacia el agente (motor de respuestas en Python).
 *
 * El agente NO sabe nada de Baileys: recibe un mensaje normalizado y devuelve
 * una lista de acciones ("texto", "imagen", "presencia", "notificar"...).
 * Este archivo se encarga del transporte y de reintentos.
 */
import config from './config.js';

const log = (...args) => console.log('[agente]', ...args);
const logError = (...args) => console.error('[agente]', ...args);

async function peticion(ruta, cuerpo, metodo = 'POST') {
  const url = `${config.agenteUrl}${ruta}`;
  const controlador = new AbortController();
  const temporizador = setTimeout(() => controlador.abort(), config.agenteTimeoutMs);
  const cabeceras = { 'Content-Type': 'application/json' };
  if (config.agenteToken) cabeceras['x-bridge-token'] = config.agenteToken;

  try {
    const respuesta = await fetch(url, {
      method: metodo,
      headers: cabeceras,
      body: cuerpo ? JSON.stringify(cuerpo) : undefined,
      signal: controlador.signal,
    });
    const texto = await respuesta.text();
    let datos = {};
    try {
      datos = texto ? JSON.parse(texto) : {};
    } catch {
      datos = { crudo: texto };
    }
    if (!respuesta.ok) {
      return { ok: false, status: respuesta.status, error: datos.detail || datos.error || texto };
    }
    return { ok: true, status: respuesta.status, datos };
  } catch (error) {
    const motivo = error.name === 'AbortError' ? `timeout tras ${config.agenteTimeoutMs}ms` : error.message;
    return { ok: false, error: motivo };
  } finally {
    clearTimeout(temporizador);
  }
}

/** Envía el mensaje al agente y devuelve las acciones a ejecutar. */
export async function pedirRespuesta(mensaje) {
  const cuerpo = { canal: 'baileys', mensaje, version_contrato: 2 };
  for (let intento = 0; intento <= config.agenteReintentos; intento += 1) {
    const respuesta = await peticion('/mensaje', cuerpo);
    if (respuesta.ok) {
      const datos = respuesta.datos || {};
      return {
        ok: true,
        ignorado: Boolean(datos.ignorado),
        motivo: datos.motivo || '',
        acciones: Array.isArray(datos.acciones) ? datos.acciones : [],
        intenciones: datos.intenciones || [],
        debug: datos.debug || null,
      };
    }
    logError(`intento ${intento + 1} falló:`, respuesta.error || respuesta.status);
    if (intento < config.agenteReintentos) {
      await new Promise((r) => setTimeout(r, 800 * (intento + 1)));
    }
  }
  return { ok: false, acciones: [], error: 'El agente no respondió' };
}

/** Avisa al agente de eventos de la sesión (conexión, QR, desconexión). */
export async function notificarEvento(evento, datos = {}) {
  const respuesta = await peticion('/evento-whatsapp', { evento, datos });
  if (!respuesta.ok) logError('no se pudo notificar el evento', evento, respuesta.error);
  return respuesta;
}

export async function verificarAgente() {
  const respuesta = await peticion('/health', null, 'GET');
  return respuesta.ok ? { ...respuesta.datos } : { ok: false, error: respuesta.error };
}

export { log, logError };
