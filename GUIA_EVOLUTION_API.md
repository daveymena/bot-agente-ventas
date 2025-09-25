# 🚀 Guía de Configuración - Evolution API

## 📋 Pasos para Configurar el Webhook en Evolution API

### **Paso 1: Acceder a tu Evolution API**
1. Abre tu navegador web
2. Ve a la URL de tu Evolution API:
   ```
   https://evoapi2-evolution-api.ovw3ar.easypanel.host/manager/instance/03d935e9-4711-4011-9ead-4983e4f6b2b5/webhook
   ```

### **Paso 2: Verificar Estado de la Instancia**
1. En la página, busca la sección **"Estado de la Instancia"**
2. Asegúrate de que la instancia esté **"Conectada"** ✅
3. Si dice **"Desconectada"** o **"QR Pendiente"**:
   - Ve a la pestaña **"Configuración"**
   - Haz clic en **"Generar QR"**
   - Escanea el QR con WhatsApp en tu teléfono

### **Paso 3: Configurar el Webhook**
1. Ve a la pestaña **"Webhook"** en la interfaz
2. Busca la sección **"Configurar Webhook"**
3. Haz clic en **"Nuevo Webhook"** o **"Agregar Webhook"**

### **Paso 4: Configurar los Parámetros del Webhook**

**URL del Webhook:**
```
http://TU-IP-LOCAL:8000/webhook
```
> ⚠️ **IMPORTANTE**: Reemplaza `TU-IP-LOCAL` con la IP real de tu servidor donde ejecutas el agente Python

**Método HTTP:**
```
POST
```

**Eventos a Escuchar:**
```
messages.upsert
```
> 💡 **Opcional**: Puedes seleccionar también `messages.update` si quieres recibir actualizaciones de mensajes

**Headers (Cabeceras):**
```
Content-Type: application/json
```

**Autenticación:**
- Si Evolution API requiere autenticación, configura:
  - **Tipo**: Bearer Token
  - **Token**: `429683C4C977415CAAFCCE10F7D57E11`

### **Paso 5: Activar el Webhook**
1. Haz clic en **"Guardar"** o **"Crear Webhook"**
2. Verifica que aparezca en la lista de webhooks activos
3. Asegúrate de que esté **"Habilitado"** ✅

### **Paso 6: Probar la Configuración**
1. Envía un mensaje de WhatsApp a tu número conectado
2. Ve al panel de Evolution API
3. En la pestaña **"Mensajes"** deberías ver el mensaje entrante
4. En la pestaña **"Logs"** o **"Webhook"** deberías ver las llamadas salientes

## 🔧 **Solución de Problemas**

### **Problema 1: "Error de conexión"**
**Síntoma**: El webhook no recibe mensajes
**Soluciones**:
1. Verifica que la instancia esté conectada
2. Confirma que la URL del webhook sea accesible desde internet
3. Revisa que el puerto 8000 esté abierto en tu firewall
4. Verifica la IP en `http://TU-IP-LOCAL:8000`

### **Problema 2: "Instancia desconectada"**
**Síntoma**: No se pueden enviar mensajes
**Soluciones**:
1. Ve a **Configuración > QR Code**
2. Genera un nuevo QR
3. Escanea con WhatsApp en tu teléfono
4. Espera a que aparezca **"Conectado"**

### **Problema 3: "URL no accesible"**
**Síntoma**: Error 404 o timeout en webhook
**Soluciones**:
1. Verifica que el agente Python esté ejecutándose: `python main.py`
2. Confirma que el puerto 8000 esté libre: `netstat -an | grep 8000`
3. Prueba la URL manualmente: `curl http://localhost:8000/health`

## 📊 **Verificación de Funcionamiento**

### **Método 1: Endpoint de Salud**
```bash
curl http://localhost:8000/health
```
**Respuesta esperada:**
```json
{
  "status": "healthy",
  "details": {
    "is_running": true,
    "products_cache_size": 50,
    "whatsapp_configured": true,
    "ai_configured": true
  }
}
```

### **Método 2: Logs del Agente**
1. Revisa el archivo `logs/agente_ventas.log`
2. Busca mensajes como:
   ```
   INFO - Mensaje recibido de WhatsApp
   INFO - Procesando mensaje de texto
   INFO - Respuesta enviada a WhatsApp
   ```

### **Método 3: Logs de Evolution API**
1. En la interfaz web, ve a **"Logs"**
2. Busca llamadas HTTP POST a tu webhook
3. Verifica que tengan código de respuesta 200

## 🚀 **Configuración Avanzada**

### **Múltiples Webhooks**
Si necesitas diferentes webhooks para diferentes eventos:
1. Crea un webhook para `messages.upsert` (mensajes nuevos)
2. Crea otro para `messages.update` (actualizaciones)
3. Crea otro para `messages.delete` (mensajes eliminados)

### **Filtrado de Mensajes**
En la configuración del webhook, puedes agregar filtros:
- **Solo mensajes de texto**: `messages.upsert` con filtro por tipo
- **Solo de grupos**: Filtrar por JID que contenga `@g.us`
- **Solo de contactos específicos**: Filtrar por número

### **Configuración de Timeouts**
- **Timeout de respuesta**: 30 segundos (por defecto)
- **Reintentos**: 3 veces (por defecto)
- **Intervalo entre reintentos**: 5 segundos

## 📱 **Prueba Final**

1. **Inicia el agente Python:**
   ```bash
   cd agente_ventas_python
   python main.py
   ```

2. **Envía un mensaje de prueba:**
   - Abre WhatsApp en tu teléfono
   - Envía: "Hola, ¿qué productos tienes?"
   - Deberías recibir una respuesta automática

3. **Verifica en los logs:**
   - Revisa `logs/agente_ventas.log`
   - Deberías ver el procesamiento del mensaje

## 🎯 **¡Listo!**

Una vez configurado correctamente, tu agente de ventas responderá automáticamente a todos los mensajes de WhatsApp con información sobre productos tecnológicos, manteniendo conversaciones contextuales y proporcionando información actualizada.

¿Necesitas ayuda con algún paso específico de la configuración?