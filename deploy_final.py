#!/usr/bin/env python3
"""
DEPLOYMENT FINAL - GitHub + Vercel
"""
import os
import sys
import subprocess

def print_header():
    """Imprimir encabezado"""
    print("DEPLOYMENT FINAL - AGENTE DE VENTAS")
    print("=" * 50)
    print("Subir a GitHub y desplegar en Vercel")
    print()

def check_git_status():
    """Verificar estado de Git"""
    try:
        result = subprocess.run(['git', 'status', '--porcelain'],
                              capture_output=True, text=True)
        if result.returncode == 0:
            if result.stdout.strip():
                print("Hay cambios sin commitear")
                return False
            else:
                print("Git esta limpio")
                return True
        else:
            print("Error verificando Git")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def create_github_repo():
    """Crear repositorio en GitHub"""
    print("CREANDO REPOSITORIO EN GITHUB")
    print("=" * 40)
    print()
    print("PASOS PARA CREAR REPOSITORIO:")
    print("1. Ve a: https://github.com/new")
    print("2. Nombre del repositorio: evolution-bot-python")
    print("3. Descripcion: Agente de Ventas WhatsApp con Python")
    print("4. Hazlo PUBLICO")
    print("5. NO marques 'Add a README file'")
    print("6. Crea el repositorio")
    print()
    print("Luego copia la URL del repositorio")
    print("Ejemplo: https://github.com/tu-usuario/evolution-bot-python.git")
    print()

    repo_url = input("URL del repositorio GitHub: ").strip()

    if not repo_url:
        print("URL no valida")
        return False

    try:
        # Agregar remote
        subprocess.run(['git', 'remote', 'add', 'origin', repo_url], check=True)

        # Subir a GitHub
        print("Subiendo a GitHub...")
        subprocess.run(['git', 'push', '-u', 'origin', 'main'], check=True)

        print("Codigo subido a GitHub exitosamente!")
        return True

    except subprocess.CalledProcessError as e:
        print(f"Error subiendo a GitHub: {e}")
        return False

def create_vercel_deployment_guide():
    """Crear guia de despliegue en Vercel"""
    guide = """# DESPLIEGUE EN VERCEL - PASOS FINALES

## 1. Conectar con Vercel
1. Ve a: https://vercel.com
2. Regístrate o inicia sesión
3. Haz clic en "Import Project"
4. Conecta tu cuenta de GitHub
5. Busca "evolution-bot-python" y selecciónalo

## 2. Configurar Variables de Entorno
En Vercel, ve a tu proyecto -> Settings -> Environment Variables

Agrega estas variables:

| Variable | Valor |
|----------|-------|
| `GOOGLE_GEMINI_API_KEY` | `AIzaSyDxKos_L7EC2bsm2XACFlaRYSeVsKMwjQY` |
| `WHATSAPP_SERVER_URL` | `https://evoapi2-evolution-api.ovw3ar.easypanel.host` |
| `WHATSAPP_INSTANCE_NAME` | `03d935e9-4711-4011-9ead-4983e4f6b2b5` |
| `WHATSAPP_API_KEY` | `429683C4C977415CAAFCCE10F7D57E11` |

## 3. Desplegar
1. Haz clic en "Deploy"
2. Espera a que termine (2-3 minutos)
3. Vercel te dara una URL como: https://tu-app.vercel.app

## 4. Configurar Webhook en Evolution API
1. Ve a tu Evolution API:
   https://evoapi2-evolution-api.ovw3ar.easypanel.host/manager/instance/03d935e9-4711-4011-9ead-4983e4f6b2b5/webhook

2. Configura el webhook:
   - URL: https://tu-app.vercel.app/webhook
   - Metodo: POST
   - Eventos: messages.upsert
   - Headers: Content-Type: application/json

## 5. Probar el Bot
1. Envía un mensaje a tu numero de WhatsApp
2. El bot deberia responder automaticamente
3. Revisa los logs en Vercel si hay errores

## URLs IMPORTANTES

- Tu aplicacion: https://tu-app.vercel.app
- Webhook: https://tu-app.vercel.app/webhook
- Health check: https://tu-app.vercel.app/health
- Logs: Vercel Dashboard -> tu-app -> Functions -> Logs

## VENTAJAS DE VERCEL

- URL permanente
- SSL automatico
- Despliegue automatico desde Git
- 100GB de ancho de banda gratis
- Monitoreo integrado
- Reinicio automatico si falla

## SOLUCION DE PROBLEMAS

### Error de Variables de Entorno
- Verifica que todas las variables esten configuradas
- Copia exactamente los valores de arriba

### Error de Despliegue
- Revisa los logs en Vercel Dashboard
- Verifica que requirements.txt este correcto

### Webhook no Funciona
- Prueba: curl https://tu-app.vercel.app/health
- Verifica la configuracion en Evolution API

## ACTUALIZACIONES FUTURAS

Para actualizar el bot:
1. Haz cambios en el codigo
2. git add .
3. git commit -m "Nueva funcionalidad"
4. git push
5. Vercel desplegara automaticamente

## ¡LISTO!

Tu bot estara funcionando 24/7 en Vercel con:
- Respuestas automaticas
- Procesamiento de audio
- Scraping de productos
- Memoria de conversacion
- Manejo de errores
"""

    with open('DEPLOY_FINAL_GUIDE.md', 'w') as f:
        f.write(guide)

    print("Guia de despliegue creada: DEPLOY_FINAL_GUIDE.md")

def main():
    """Funcion principal"""
    print_header()

    # Verificar estado de Git
    if not check_git_status():
        print("Hay cambios sin commitear. Commiteando...")
        subprocess.run(['git', 'add', '.'], check=True)
        subprocess.run(['git', 'commit', '-m', 'Update: Preparando para despliegue'], check=True)

    # Crear repositorio en GitHub
    if not create_github_repo():
        print("No se pudo crear el repositorio en GitHub")
        return

    # Crear guia de despliegue
    create_vercel_deployment_guide()

    print()
    print("¡TODO LISTO PARA DESPLEGAR!")
    print("=" * 40)
    print()
    print("ARCHIVOS CREADOS:")
    print("  - DEPLOY_FINAL_GUIDE.md (guia completa)")
    print("  - vercel.json (configuracion Vercel)")
    print("  - api.py (wrapper para Vercel)")
    print("  - requirements.txt (dependencias)")
    print()
    print("PROXIMOS PASOS:")
    print("  1. Crea repositorio en GitHub")
    print("  2. Ve a Vercel y conecta GitHub")
    print("  3. Importa el repositorio")
    print("  4. Configura variables de entorno")
    print("  5. ¡Despliega!")
    print()
    print("Tu bot estara funcionando 24/7")
    print("con todas las funcionalidades!")

if __name__ == "__main__":
    main()