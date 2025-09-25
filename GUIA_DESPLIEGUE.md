# 🚀 Guía de Despliegue del Agente de Ventas

## Opciones de Despliegue

### 1. 🟢 Ngrok (Desarrollo - GRATUITO)
**Mejor para pruebas y desarrollo**

```bash
# Instalar pyngrok
pip install pyngrok

# Ejecutar con tunnel público
python run_with_ngrok.py
```

**Ventajas:**
- ✅ Fácil y rápido
- ✅ URL HTTPS automática
- ✅ Sin configuración compleja

**Desventajas:**
- ❌ Se cierra al cerrar terminal
- ❌ URL cambia cada vez
- ❌ Límite de tiempo gratuito

### 2. 🟡 Vercel (Producción - GRATUITO)
**Recomendado para producción**

```bash
# Instalar Vercel CLI
npm install -g vercel

# Desplegar
cd agente_ventas_python
vercel --prod

# Configurar variables de entorno
vercel env add WHATSAPP_SERVER_URL
vercel env add WHATSAPP_INSTANCE_NAME
vercel env add WHATSAPP_API_KEY
vercel env add GOOGLE_GEMINI_API_KEY
```

**Ventajas:**
- ✅ Completamente gratuito
- ✅ Despliegue automático desde Git
- ✅ HTTPS automático
- ✅ Escalado automático

### 3. 🟡 Railway (Alternativa - GRATUITO)
**Otra opción gratuita**

1. Crear cuenta en https://railway.app
2. Conectar tu repositorio de GitHub
3. Railway detectará automáticamente Python
4. Configurar variables de entorno en el dashboard
5. Desplegar automáticamente

### 4. 🟡 Render (Otra Opción - GRATUITO)
**Servicio gratuito confiable**

1. Crear cuenta en https://render.com
2. Crear nuevo "Web Service"
3. Conectar repositorio GitHub
4. Configurar como Python app
5. Agregar variables de entorno
6. Desplegar

### 5. 🔴 VPS (DigitalOcean/AWS - PAGO)
**Para máxima control y rendimiento**

```bash
# En Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip nginx certbot

# Clonar proyecto
git clone <tu-repo>
cd agente_ventas_python

# Instalar dependencias
pip install -r requirements.txt

# Configurar como servicio systemd
sudo nano /etc/systemd/system/agente-ventas.service

# Contenido del servicio:
[Unit]
Description=Agente de Ventas WhatsApp
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/agente_ventas_python
ExecStart=/home/ubuntu/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target

# Habilitar y iniciar
sudo systemctl enable agente-ventas
sudo systemctl start agente-ventas

# Configurar nginx como proxy reverso
sudo nano /etc/nginx/sites-available/agente-ventas

# Configurar SSL con Let's Encrypt
sudo certbot --nginx -d tu-dominio.com
```

## 📋 Checklist de Despliegue

### Para Cualquier Plataforma:
- [ ] Variables de entorno configuradas
- [ ] Webhook URL actualizada en Evolution API
- [ ] Puerto 8000 expuesto (o configurado)
- [ ] HTTPS habilitado
- [ ] Logs configurados
- [ ] Monitoreo básico

### Para Vercel/Railway/Render:
- [ ] `vercel.json` o configuración equivalente
- [ ] Variables de entorno en dashboard
- [ ] Build command correcto
- [ ] Start command: `python main.py`

### Para VPS:
- [ ] Firewall configurado
- [ ] SSL certificado
- [ ] Servicio systemd
- [ ] Nginx proxy reverso
- [ ] Monitoreo y logs

## 🔧 Solución de Problemas

### Webhook no recibe mensajes:
1. Verificar URL del webhook en Evolution API
2. Confirmar que el servidor está corriendo
3. Revisar logs del servidor
4. Probar endpoint manualmente: `curl https://tu-url/webhook`

### Error de conexión WhatsApp:
1. Verificar credenciales en Evolution API
2. Confirmar instancia activa
3. Revisar logs del agente

### Error de IA:
1. Verificar API keys
2. Confirmar cuotas disponibles
3. Revisar formato de respuestas

## 💡 Recomendaciones

- **Desarrollo**: Usa Ngrok para pruebas rápidas
- **Producción**: Vercel o Railway para simplicidad
- **Escalabilidad**: VPS para control total
- **Siempre**: Configura HTTPS y monitoreo básico
