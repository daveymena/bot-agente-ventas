/**
 * Pruebas del puente (Node + Baileys) sin conectar a WhatsApp.
 *
 *   cd baileys-bridge && node --test
 *
 * Se prueba lo que puede romperse en silencio: leer el mensaje, decidir si se
 * atiende y ejecutar el plan de acciones que devuelve el agente.
 */
import { test } from 'node:test';
import assert from 'node:assert/strict';

import { esChatAtendible, extraerContenido, trocear, ejecutarAcciones } from '../src/whatsapp.js';
import { normalizarMensaje } from '../src/whatsapp.js';

// ------------------------------------------------------------------ lectura
test('extrae texto de conversation', () => {
  const msg = { message: { conversation: 'Hola, cuánto vale?' } };
  assert.deepEqual(extraerContenido(msg), { tipo: 'texto', texto: 'Hola, cuánto vale?', tipoContenido: 'conversation' });
});

test('extrae texto de extendedTextMessage', () => {
  const msg = { message: { extendedTextMessage: { text: '  buenas  ' } } };
  assert.equal(extraerContenido(msg).texto, 'buenas');
});

test('extrae el caption de una imagen', () => {
  const msg = { message: { imageMessage: { caption: 'mira esto' } } };
  const { tipo, texto } = extraerContenido(msg);
  assert.equal(tipo, 'imagen');
  assert.equal(texto, 'mira esto');
});

test('detecta audio aunque no tenga texto', () => {
  const msg = { message: { audioMessage: { mimetype: 'audio/ogg' } } };
  const { tipo, texto } = extraerContenido(msg);
  assert.equal(tipo, 'audio');
  assert.equal(texto, '');
});

test('detecta respuestas de botón y lista', () => {
  assert.equal(extraerContenido({ message: { buttonsResponseMessage: { selectedDisplayText: 'Sí' } } }).texto, 'Sí');
  assert.equal(extraerContenido({ message: { listResponseMessage: { title: 'Precios' } } }).texto, 'Precios');
});

// ------------------------------------------------------------- a quién atender
test('atiende chats directos', () => {
  assert.equal(esChatAtendible({ remoteJid: '573001112233@s.whatsapp.net' }), true);
});

test('ignora grupos, estados, canales y mensajes propios', () => {
  assert.equal(esChatAtendible({ remoteJid: '123-456@g.us' }), false);
  assert.equal(esChatAtendible({ remoteJid: 'status@broadcast' }), false);
  assert.equal(esChatAtendible({ remoteJid: '123@newsletter' }), false);
  assert.equal(esChatAtendible({ remoteJid: '573001112233@s.whatsapp.net', fromMe: true }), false);
  assert.equal(esChatAtendible({}), false);
});

// ------------------------------------------------------------------ payload
test('normaliza el mensaje al contrato del agente', async () => {
  const msg = {
    key: { id: 'ABC123', remoteJid: '573001112233@s.whatsapp.net', fromMe: false },
    pushName: 'Ana',
    messageTimestamp: 1700000000,
    message: { conversation: 'cuanto vale el corte' },
  };
  const payload = await normalizarMensaje({ updateMediaMessage: async () => {} }, msg, console);
  assert.equal(payload.id, 'ABC123');
  assert.equal(payload.numero, '573001112233');
  assert.equal(payload.texto, 'cuanto vale el corte');
  assert.equal(payload.nombre, 'Ana');
  assert.equal(payload.es_grupo, false);
  assert.equal(payload.tipo, 'texto');
});

// ------------------------------------------------------------------ división
test('no parte mensajes cortos', () => {
  assert.deepEqual(trocear('hola'), ['hola']);
});

test('parte mensajes largos sin perder contenido', () => {
  const parrafo = 'línea de prueba con contenido suficiente.';
  const texto = Array.from({ length: 120 }, () => parrafo).join('\n\n');
  const partes = trocear(texto, 900);
  assert.ok(partes.length > 1, 'debe dividirse en varias partes');
  for (const parte of partes) assert.ok(parte.length <= 900);
  // el texto completo se conserva (los saltos de bloque pasan a espacio)
  const normalizar = (t) => t.replace(/\s+/g, ' ').trim();
  assert.equal(normalizar(partes.join(' ')), normalizar(texto));
});

test('corta bloques gigantes sin dividir a la mitad de la nada', () => {
  const partes = trocear('x'.repeat(2500), 900);
  assert.equal(partes.length, 3);
  for (const parte of partes) assert.ok(parte.length <= 900);
});

// --------------------------------------------------------------- ejecución
function sockFalso() {
  const llamadas = [];
  return {
    llamadas,
    sendMessage: async (jid, contenido) => llamadas.push({ tipo: 'sendMessage', jid, contenido }),
    sendPresenceUpdate: async (estado, jid) => llamadas.push({ tipo: 'presence', estado, jid }),
    readMessages: async (keys) => llamadas.push({ tipo: 'read', keys }),
  };
}

test('ejecuta texto, presencia, imagen y leído en orden', async () => {
  const sock = sockFalso();
  await ejecutarAcciones(sock, [
    { tipo: 'leer' },
    { tipo: 'presencia', estado: 'composing', ms: 1 },
    { tipo: 'texto', texto: 'Hola 👋' },
    { tipo: 'imagen', url: 'https://ejemplo.com/foto.jpg', caption: 'foto' },
  ], { jid: '573001112233@s.whatsapp.net', key: { id: '1' }, logger: console, nombreNegocio: 'Prueba' });

  const tipos = sock.llamadas.map((l) => l.tipo);
  // se marca como leído, se muestra "escribiendo…" y luego se envían los mensajes
  assert.equal(tipos[0], 'read');
  assert.ok(tipos.includes('presence'));
  const enviados = sock.llamadas.filter((l) => l.tipo === 'sendMessage');
  assert.equal(enviados.length, 2);
  assert.equal(enviados[0].contenido.text, 'Hola 👋');
  assert.equal(enviados[1].contenido.image.url, 'https://ejemplo.com/foto.jpg');
  assert.equal(enviados[1].contenido.caption, 'foto');
  assert.ok(tipos.indexOf('read') < tipos.indexOf('sendMessage'));
});

test('avisa al dueño solo si hay número configurado', async () => {
  const sock = sockFalso();
  await ejecutarAcciones(sock, [
    { tipo: 'notificar', texto: 'Nueva cita', numero: '573009998877' },
    { tipo: 'ignorar' },
    { tipo: 'accion_inexistente' },
  ], { jid: '573001112233@s.whatsapp.net', logger: { error() {}, log() {} }, nombreNegocio: 'Prueba' });
  assert.equal(sock.llamadas.length, 1);
  assert.equal(sock.llamadas[0].jid, '573009998877@s.whatsapp.net');
});

test('si falla el envío, avisa al cliente en vez de morir en silencio', async () => {
  const sock = sockFalso();
  let fallos = 0;
  sock.sendMessage = async (jid, contenido) => {
    if (fallos === 0 && contenido.text) {
      fallos += 1;
      throw new Error('fallo simulado');
    }
    sock.llamadas.push({ tipo: 'sendMessage', jid, contenido });
  };
  await ejecutarAcciones(sock, [{ tipo: 'texto', texto: 'respuesta' }], {
    jid: '573001112233@s.whatsapp.net', logger: { error() {}, log() {} }, nombreNegocio: 'Mi Negocio',
  });
  const disculpas = sock.llamadas.filter(
    (l) => l.tipo === 'sendMessage' && /problema técnico/.test(l.contenido.text || ''),
  );
  assert.equal(disculpas.length, 1, 'debe enviarse exactamente una disculpa');
  assert.equal(disculpas[0].jid, '573001112233@s.whatsapp.net');
});

test('ignora acciones desconocidas sin romper', async () => {
  const sock = sockFalso();
  await ejecutarAcciones(sock, [{ tipo: 'no_existe', x: 1 }], {
    jid: '573001112233@s.whatsapp.net', logger: { error() {}, log() {} },
  });
  assert.equal(sock.llamadas.length, 0);
});
