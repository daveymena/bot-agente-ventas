# 🤖 AGENTE DE VENTAS WHATSAPP - PYTHON

Agente de ventas profesional completo transformado desde n8n a Python con arquitectura modular y escalable.

## ✨ Características

- **WhatsApp Integration**: Evolution API para mensajería 24/7
- **AI Inteligente**: Google Gemini para respuestas contextuales
- **Procesamiento de Audio**: Transcripción automática de mensajes de voz
- **Scraping de Productos**: Búsqueda en MegaPack y MegaComputer
- **Memoria de Conversación**: Contexto mantenido durante la charla
- **Manejo de Errores**: Sistema robusto con logging completo
- **Despliegue Profesional**: Configurado para Vercel

## 🏗️ Arquitectura

```
agente_ventas_python/
├── main.py                 # Aplicación FastAPI principal
├── api.py                  # Wrapper para Vercel
├── config/
│   └── settings.py         # Configuración centralizada
├── models/
│   ├── message.py          # Modelos de datos
│   └── product.py          # Modelos de productos
├── services/
│   ├── whatsapp_service.py # Integración WhatsApp
│   ├── ai_service.py       # Servicio de IA
│   ├── scraping_service.py # Scraping de productos
│   ├── audio_service.py    # Procesamiento de audio
│   └── message_processor.py# Procesador de mensajes
├── utils/
│   └── helpers.py          # Utilidades generales
├── core/
│   └── sales_agent.py      # Agente principal
└── tests/                  # Tests y validaciones
```

## 🚀 Despliegue en Vercel

### 1. Preparar GitHub
```bash
# Crear repositorio en GitHub
# URL: https://github.com/new
# Nombre: evolution-bot-python
```

### 2. Configurar en Vercel
1. Ve a [vercel.com](https://vercel.com)
2. Conecta tu cuenta de GitHub
3. Importa el repositorio `evolution-bot-python`
4. Configura las variables de entorno:

| Variable | Valor |
|----------|-------|
| `GOOGLE_GEMINI_API_KEY` | `AIzaSyDxKos_L7EC2bsm2XACFlaRYSeVsKMwjQY` |
| `WHATSAPP_SERVER_URL` | `https://evoapi2-evolution-api.ovw3ar.easypanel.host` |
| `WHATSAPP_INSTANCE_NAME` | `03d935e9-4711-4011-9ead-4983e4f6b2b5` |
| `WHATSAPP_API_KEY` | `429683C4C977415CAAFCCE10F7D57E11` |

### 3. Desplegar
- Haz clic en **"Deploy"**
- Espera 2-3 minutos
- Obtén tu URL: `https://tu-app.vercel.app`

### 4. Configurar Webhook
En tu Evolution API:
```
URL: https://tu-app.vercel.app/webhook
Método: POST
Eventos: messages.upsert
```

## 📋 Funcionalidades Implementadas

### ✅ Mensajería WhatsApp
- Recepción de mensajes de texto y audio
- Envío de respuestas automáticas
- Manejo de múltiples conversaciones

### ✅ Procesamiento de Audio
- Transcripción con OpenAI Whisper
- Conversión de voz a texto
- Soporte para múltiples idiomas

### ✅ Scraping de Productos
- Búsqueda en MegaPack
- Búsqueda en MegaComputer
- Formateo de resultados profesionales

### ✅ Agente de IA
- Google Gemini para respuestas inteligentes
- Memoria de conversación
- Contexto mantenido
- Respuestas personalizadas

### ✅ Sistema de Logging
- Logs estructurados
- Manejo de errores
- Debug y monitoreo

## 🔧 Configuración

### Variables de Entorno
```env
GOOGLE_GEMINI_API_KEY=tu-api-key
WHATSAPP_SERVER_URL=https://tu-evolution-api.com
WHATSAPP_INSTANCE_NAME=tu-instance-id
WHATSAPP_API_KEY=tu-api-key
```

### Dependencias
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
aiohttp==3.9.1
google-generativeai==0.3.1
python-dotenv==1.0.0
beautifulsoup4==4.12.2
requests==2.31.0
```

## 🌐 URLs Importantes

- **Aplicación**: `https://tu-app.vercel.app`
- **Webhook**: `https://tu-app.vercel.app/webhook`
- **Health Check**: `https://tu-app.vercel.app/health`
- **Logs**: Vercel Dashboard

## 📊 Monitoreo

- **Logs en Tiempo Real**: Vercel Dashboard
- **Métricas**: Analytics integradas
- **Despliegues**: Historial automático
- **Errores**: Notificaciones automáticas

## 🔄 Actualizaciones

```bash
# Hacer cambios
git add .
git commit -m "Nueva funcionalidad"
git push

# Vercel despliega automáticamente
```

## 🆘 Solución de Problemas

### Error de Variables de Entorno
- Verifica en Vercel Dashboard → Settings → Environment Variables
- Asegúrate de que todas las variables estén configuradas

### Error de Despliegue
- Revisa los logs en Vercel Dashboard
- Verifica `requirements.txt`
- Comprueba errores de sintaxis

### Webhook no Funciona
- Prueba: `curl https://tu-app.vercel.app/health`
- Verifica configuración en Evolution API
- Revisa logs en Vercel

## 🎯 Beneficios de Vercel

- ✅ **URL Permanente**: Nunca cambia
- ✅ **SSL Automático**: Certificado gratis
- ✅ **Despliegue Automático**: Desde Git
- ✅ **100GB de Ancho de Banda**: Gratis
- ✅ **Monitoreo Integrado**: Logs y métricas
- ✅ **Reinicio Automático**: Si falla
- ✅ **Escalabilidad**: Se adapta al tráfico

## 📈 Próximas Mejoras

- [ ] Dashboard web para monitoreo
- [ ] Base de datos para historial
- [ ] Sistema de reportes
- [ ] Integración con CRM
- [ ] Soporte multi-idioma
- [ ] Análisis de sentimientos

## 🎉 ¡Listo para Producción!

Tu agente de ventas está completamente configurado y listo para:

- ✅ Responder mensajes 24/7
- ✅ Procesar consultas de productos
- ✅ Transcribir mensajes de voz
- ✅ Mantener contexto de conversación
- ✅ Funcionar sin interrupciones
- ✅ Escalar automáticamente

## 📞 Contacto

Para soporte o consultas:
- Revisa los logs en Vercel Dashboard
- Verifica la configuración de variables de entorno
- Consulta la documentación en `DEPLOY_FINAL_GUIDE.md`

---

**¡Tu bot de ventas profesional está listo para conquistar clientes! 🚀**