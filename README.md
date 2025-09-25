# Agente de Ventas Profesional para WhatsApp

Un agente de ventas automatizado desarrollado en Python que utiliza inteligencia artificial para responder consultas de clientes sobre productos tecnológicos a través de WhatsApp.

## 🚀 Características

- **Procesamiento de Mensajes**: Maneja mensajes de texto y audio (con transcripción automática)
- **Scraping Inteligente**: Extrae información de productos de múltiples tiendas automáticamente
- **IA Avanzada**: Utiliza Google Gemini o OpenAI GPT para generar respuestas naturales
- **Memoria de Conversación**: Mantiene contexto de conversaciones anteriores
- **Respuestas Multimedia**: Envía texto e imágenes de productos
- **API RESTful**: Interfaz web completa para integración
- **Configuración Flexible**: Variables de entorno para fácil despliegue

## 📋 Requisitos

- Python 3.8+
- Conexión a internet
- Cuentas API de servicios externos (opcionales)

## 🛠️ Instalación

1. **Clonar el repositorio**
   ```bash
   git clone <url-del-repositorio>
   cd agente-ventas-python
   ```

2. **Crear entorno virtual**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # o
   venv\\Scripts\\activate  # Windows
   ```

3. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar variables de entorno**
   ```bash
   cp .env.example .env
   # Editar .env con tus configuraciones
   ```

## ⚙️ Configuración

### Variables de Entorno Obligatorias

```env
# WhatsApp (Evolution API)
WHATSAPP_SERVER_URL=https://tu-evolution-api.com
WHATSAPP_INSTANCE_NAME=tu_instancia
WHATSAPP_API_KEY=tu_api_key

# IA (al menos una opción)
GOOGLE_GEMINI_API_KEY=tu_google_gemini_api_key
# o
OPENAI_API_KEY=tu_openai_api_key
# o configurar Ollama (ver sección Ollama)
```

### Variables de Entorno Opcionales

```env
# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/agente_ventas.log

# Sistema
TEMP_DIR=temp
LOGS_DIR=logs
MAX_RESPONSE_LENGTH=500
CONTEXT_WINDOW_LENGTH=10
DELAY_BETWEEN_MESSAGES=2.0
```

## 🚀 Uso

### Iniciar el Agente

```bash
python main.py
```

El servidor se iniciará en `http://localhost:8000`

### Endpoints Disponibles

- `GET /` - Información básica del agente
- `GET /health` - Verificación de salud
- `POST /webhook` - Procesar mensajes de WhatsApp
- `POST /refresh-products` - Actualizar caché de productos
- `GET /products` - Obtener lista de productos

### Formato del Webhook

El endpoint `/webhook` espera un payload JSON con la siguiente estructura:

```json
{
  "body": {
    "URL del servidor": "https://tu-servidor.com",
    "nombreInstancia": "tu_instancia",
    "clave API": "tu_api_key",
    "data": {
      "id": "mensaje_id",
      "remoteJid": "1234567890@c.us",
      "message": {
        "conversation": "Mensaje del cliente"
      },
      "pushName": "Nombre del Cliente"
    }
  }
}
```

## 🏗️ Arquitectura

```
agente_ventas_python/
├── config/
│   └── settings.py          # Configuración centralizada
├── core/
│   └── sales_agent.py       # Agente principal
├── models/
│   ├── message.py           # Modelo de mensaje
│   └── product.py           # Modelo de producto
├── services/
│   ├── whatsapp_service.py  # Servicio de WhatsApp
│   ├── scraping_service.py  # Servicio de scraping
│   ├── ai_service.py        # Servicio de IA
│   ├── audio_service.py     # Servicio de audio
│   └── message_processor.py # Procesador de mensajes
├── utils/
│   └── helpers.py           # Utilidades auxiliares
├── main.py                  # Punto de entrada
├── .env.example            # Ejemplo de configuración
└── README.md               # Esta documentación
```

## 🔧 Servicios

### WhatsApp Service
- Envío de mensajes de texto e imágenes
- Descarga de archivos multimedia
- Validación de conexión
- **Compatible con Evolution API** (igual que n8n)

### Scraping Service
- Extracción de productos de múltiples tiendas
- Búsqueda inteligente de productos
- Caché de productos

### AI Service
- Generación de respuestas con IA
- Memoria de conversación
- Soporte para Google Gemini, OpenAI y Ollama (local)
- Priorización automática: Gemini → OpenAI → Ollama

### Audio Service
- Transcripción de mensajes de voz
- Soporte para múltiples formatos
- Validación de archivos de audio

### Message Processor
- Normalización de datos
- Validación de mensajes
- Extracción de palabras clave

## 📝 Ejemplo de Uso

### Mensaje de Cliente
```
"Hola, estoy buscando un iPhone 13 Pro Max"
```

### Respuesta del Agente
```
💻 ¡Hola! Claro, tenemos el iPhone 13 Pro Max disponible 📱
Características principales:
• Pantalla Super Retina XDR de 6.7"
• Chip A15 Bionic
• Cámara Pro de 12MP
• Almacenamiento desde 128GB

¿Te gustaría conocer precios y disponibilidad? 🛒
```

## 🔍 Monitoreo y Logs

El agente genera logs detallados en el archivo especificado en `LOG_FILE`. Los logs incluyen:

- Procesamiento de mensajes
- Errores y excepciones
- Actualizaciones de caché
- Interacciones con servicios externos

## 🛡️ Manejo de Errores

El agente incluye manejo robusto de errores:

- Validación de datos de entrada
- Reintentos automáticos para servicios externos
- Fallback para respuestas cuando la IA no está disponible
- Logging detallado de errores

## 🚀 Despliegue

### Producción

1. **Configurar servidor web** (Nginx, Apache, etc.)
2. **Configurar variables de entorno**
3. **Usar un proceso manager** (PM2, Supervisor, etc.)
4. **Configurar SSL** (recomendado)

### Docker (Futuro)

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8000
CMD ["python", "main.py"]
```

## 🤝 Contribuir

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo `LICENSE` para más detalles.

## 🆘 Soporte

Para soporte técnico o preguntas:

- Crear un issue en GitHub
- Revisar la documentación
- Verificar los logs del sistema

## 🦙 Configuración de Ollama (Local)

Para usar modelos de IA locales con Ollama:

1. **Instalar Ollama**
   ```bash
   # En Linux/Mac
   curl -fsSL https://ollama.ai/install.sh | sh

   # En Windows
   # Descargar desde https://ollama.ai/download
   ```

2. **Descargar un modelo**
   ```bash
   ollama pull llama2
   ollama pull mistral
   ollama pull codellama
   ```

3. **Configurar variables de entorno**
   ```env
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama2
   ```

4. **Verificar funcionamiento**
   ```bash
   curl http://localhost:11434/api/tags
   ```

### Modelos Recomendados

- `llama2:13b` - Bueno para chat general
- `mistral:7b` - Rápido y eficiente
- `codellama:13b` - Especializado en código
- `vicuna:13b` - Similar a ChatGPT

## 📚 Guías y Documentación

- [Guía de Configuración Evolution API](GUIA_EVOLUTION_API.md) - Configuración paso a paso del webhook
- [Script de Prueba de Configuración](test_config.py) - Verificar que todo esté configurado
- [Script de Prueba de Webhook](test_webhook.py) - Probar el webhook manualmente

## 🚀 Inicio Rápido

### **Opción 1: Script de Inicio Interactivo (Recomendado)**
```bash
python iniciar.py
```
Menú interactivo con todas las opciones disponibles.

### **Opción 2: Sistema Completo**
```bash
python run_complete_system.py
```
Ejecuta todos los componentes sincronizados.

### **Opción 3: Bot con Evolution**
```bash
python start_bot.py
```
Bot optimizado para trabajar con Evolution API.

### **Opción 4: Solo Servidor Webhook**
```bash
python main.py
```
Servidor básico para recibir webhooks.

## 🔧 Scripts de Utilidad

### Prueba de Configuración
```bash
python test_config.py
```
Verifica que todas las credenciales estén configuradas correctamente.

### Prueba de Webhook
```bash
python test_webhook.py
```
Envía un mensaje de prueba al webhook para verificar funcionamiento.

### Setup Automático
```bash
./setup.sh
```
Instalación y configuración automática del proyecto.

## 🔄 Roadmap

- [ ] Interfaz web de administración
- [ ] Soporte para más tiendas
- [ ] Análisis de sentimientos
- [ ] Integración con CRM
- [ ] Dashboard de métricas
- [ ] Soporte multi-idioma

---

**Desarrollado con ❤️ para automatizar ventas y mejorar la experiencia del cliente**