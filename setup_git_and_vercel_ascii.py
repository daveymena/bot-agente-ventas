#!/usr/bin/env python3
"""
Setup completo para Git + Vercel (solo ASCII)
"""
import os
import sys
import subprocess
import json

def print_header():
    """Imprimir encabezado"""
    print("SETUP GIT + VERCEL - AGENTE DE VENTAS")
    print("=" * 60)
    print("Preparando todo para subir a Git y desplegar en Vercel")
    print("Vercel es gratis, confiable y profesional")
    print()

def check_git():
    """Verificar si Git esta instalado"""
    try:
        result = subprocess.run(['git', '--version'],
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("Git encontrado")
            return True
        else:
            print("Git no encontrado")
            return False
    except FileNotFoundError:
        print("Git no instalado")
        return False

def initialize_git():
    """Inicializar repositorio Git"""
    try:
        # Verificar si ya esta inicializado
        if os.path.exists('.git'):
            print("Repositorio Git ya inicializado")
            return True

        print("Inicializando repositorio Git...")
        subprocess.run(['git', 'init'], check=True)

        # Configurar usuario (si no esta configurado)
        try:
            subprocess.run(['git', 'config', 'user.name'], check=True,
                         capture_output=True)
        except subprocess.CalledProcessError:
            print("Configurando Git...")
            name = input("Nombre para Git: ")
            email = input("Email para Git: ")

            subprocess.run(['git', 'config', 'user.name', name], check=True)
            subprocess.run(['git', 'config', 'user.email', email], check=True)

        print("Repositorio Git inicializado")
        return True

    except subprocess.CalledProcessError as e:
        print(f"Error inicializando Git: {e}")
        return False

def create_vercel_files():
    """Crear archivos para Vercel"""
    print("Creando archivos para Vercel...")

    # vercel.json
    vercel_config = {
        "version": 2,
        "builds": [
            {
                "src": "api.py",
                "use": "@vercel/python"
            }
        ],
        "routes": [
            {
                "src": "/api/(.*)",
                "dest": "/api.py"
            },
            {
                "src": "/(.*)",
                "dest": "/api.py"
            }
        ],
        "env": {
            "GOOGLE_GEMINI_API_KEY": "@google-gemini-api-key",
            "WHATSAPP_SERVER_URL": "@whatsapp-server-url",
            "WHATSAPP_INSTANCE_NAME": "@whatsapp-instance-name",
            "WHATSAPP_API_KEY": "@whatsapp-api-key"
        }
    }

    with open('vercel.json', 'w') as f:
        json.dump(vercel_config, f, indent=2)

    # requirements.txt optimizado para Vercel
    requirements = """fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
aiohttp==3.9.1
google-generativeai==0.3.1
python-dotenv==1.0.0
beautifulsoup4==4.12.2
requests==2.31.0"""

    with open('requirements.txt', 'w') as f:
        f.write(requirements)

    # api.py wrapper para Vercel
    api_wrapper = '''import os
import sys
from fastapi import FastAPI, Request
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Agregar el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import app

# Vercel necesita un wrapper
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
'''

    with open('api.py', 'w') as f:
        f.write(api_wrapper)

    print("Archivos de Vercel creados")

def add_files_to_git():
    """Agregar archivos a Git"""
    try:
        print("Agregando archivos a Git...")

        # Archivos a incluir
        files_to_add = [
            '.gitignore',
            'main.py',
            'api.py',
            'requirements.txt',
            'vercel.json',
            'README.md',
            'config/',
            'models/',
            'services/',
            'utils/',
            'core/'
        ]

        for file in files_to_add:
            if os.path.exists(file):
                if os.path.isdir(file):
                    subprocess.run(['git', 'add', file], check=True)
                else:
                    subprocess.run(['git', 'add', file], check=True)

        # Hacer commit inicial
        subprocess.run(['git', 'commit', '-m', 'Initial commit: Agente de Ventas con Evolution API'], check=True)

        print("Archivos agregados y commited")
        return True

    except subprocess.CalledProcessError as e:
        print(f"Error con Git: {e}")
        return False

def create_github_deployment_script():
    """Crear script para desplegar en GitHub"""
    script = """#!/bin/bash

# ========================================
# DESPLIEGUE EN GITHUB + VERCEL
# ========================================

echo "Desplegando en GitHub + Vercel..."
echo "=" * 60

# Verificar si Git esta inicializado
if [ ! -d .git ]; then
    echo "Git no inicializado. Ejecuta setup_git_and_vercel.py primero"
    exit 1
fi

# Verificar si hay cambios
if git diff --quiet && git diff --staged --quiet; then
    echo "No hay cambios para commitear"
else
    echo "Agregando cambios..."
    git add .
    git commit -m "Actualizacion del Agente de Ventas"
fi

# Crear rama main si no existe
if ! git show-ref --verify --quiet refs/heads/main; then
    git branch -M main
fi

# Conectar con GitHub (si no esta conectado)
if ! git remote get-url origin > /dev/null 2>&1; then
    echo "Conectando con GitHub..."
    echo "Necesitas crear un repositorio en GitHub primero"
    echo "Ve a: https://github.com/new"
    echo "Crea un repositorio llamado: evolution-bot-python"
    echo ""
    read -p "URL del repositorio GitHub: " repo_url

    git remote add origin $repo_url
    git push -u origin main
else
    echo "Subiendo cambios a GitHub..."
    git push
fi

echo "Codigo subido a GitHub"
echo ""
echo "PROXIMOS PASOS EN VERCEL:"
echo "   1. Ve a: https://vercel.com"
echo "   2. Conecta tu cuenta de GitHub"
echo "   3. Importa el repositorio: evolution-bot-python"
echo "   4. Configura las variables de entorno:"
echo "      - GOOGLE_GEMINI_API_KEY"
echo "      - WHATSAPP_SERVER_URL"
echo "      - WHATSAPP_INSTANCE_NAME"
echo "      - WHATSAPP_API_KEY"
echo "   5. Despliega!"
echo ""
echo "Tu webhook sera:"
echo "   https://tu-app.vercel.app/webhook"
"""

    with open('deploy_to_github.sh', 'w') as f:
        f.write(script)

    # Hacer ejecutable
    os.chmod('deploy_to_github.sh', 0o755)

    print("Script de despliegue creado")

def create_vercel_deployment_guide():
    """Crear guia de despliegue en Vercel"""
    guide = """# DESPLIEGUE EN VERCEL

## Pasos para Desplegar

### 1. Preparar el Codigo
```bash
python setup_git_and_vercel.py
./deploy_to_github.sh
```

### 2. Configurar en Vercel
1. **Ve a Vercel**: https://vercel.com
2. **Conecta GitHub**: Autoriza tu cuenta de GitHub
3. **Importa el repositorio**: Busca "evolution-bot-python"
4. **Configura Variables de Entorno**:

| Variable | Valor |
|----------|-------|
| `GOOGLE_GEMINI_API_KEY` | `AIzaSyDxKos_L7EC2bsm2XACFlaRYSeVsKMwjQY` |
| `WHATSAPP_SERVER_URL` | `https://evoapi2-evolution-api.ovw3ar.easypanel.host` |
| `WHATSAPP_INSTANCE_NAME` | `03d935e9-4711-4011-9ead-4983e4f6b2b5` |
| `WHATSAPP_API_KEY` | `429683C4C977415CAAFCCE10F7D57E11` |

### 3. Desplegar
- Haz clic en **"Deploy"**
- Espera a que termine el despliegue
- Vercel te dara una URL como: `https://tu-app.vercel.app`

### 4. Configurar Webhook en Evolution API
1. Ve a tu Evolution API:
   ```
   https://evoapi2-evolution-api.ovw3ar.easypanel.host/manager/instance/03d935e9-4711-4011-9ead-4983e4f6b2b5/webhook
   ```
2. Configura el webhook:
   ```
   URL: https://tu-app.vercel.app/webhook
   Metodo: POST
   Eventos: messages.upsert
   ```

## URLs Importantes

- **Tu aplicacion**: `https://tu-app.vercel.app`
- **Webhook**: `https://tu-app.vercel.app/webhook`
- **Health check**: `https://tu-app.vercel.app/health`
- **Logs**: Vercel te mostrara logs en tiempo real

## Monitoreo

- **Logs**: Vercel Dashboard -> tu-app -> Functions -> Logs
- **Metricas**: Vercel Dashboard -> tu-app -> Analytics
- **Despliegues**: Vercel Dashboard -> tu-app -> Deployments

## Actualizaciones

```bash
# Hacer cambios
git add .
git commit -m "Nueva funcionalidad"
git push

# Vercel desplegara automaticamente
```

## Solucion de Problemas

### Error de Variables de Entorno
- Ve a Vercel Dashboard -> tu-app -> Settings -> Environment Variables
- Verifica que todas las variables esten configuradas

### Error de Despliegue
- Revisa los logs en Vercel Dashboard
- Verifica que requirements.txt este correcto
- Asegurate de que no haya errores de sintaxis

### Webhook no Funciona
- Prueba: `curl https://tu-app.vercel.app/health`
- Verifica la configuracion en Evolution API
- Revisa los logs en Vercel

## Listo!

Una vez desplegado en Vercel tendras:
- URL permanente
- SSL automatico
- Despliegue automatico desde Git
- Monitoreo integrado
- 100GB de ancho de banda gratis
"""

    with open('VERCEL_DEPLOY_GUIDE.md', 'w') as f:
        f.write(guide)

    print("Guia de despliegue en Vercel creada")

def main():
    """Funcion principal"""
    print_header()

    if not check_git():
        print("Git no esta instalado")
        print("Instala Git desde: https://git-scm.com/downloads")
        return

    print("Git verificado")

    # Inicializar Git
    if not initialize_git():
        return

    # Crear archivos para Vercel
    create_vercel_files()

    # Agregar a Git
    if not add_files_to_git():
        return

    # Crear scripts de despliegue
    create_github_deployment_script()
    create_vercel_deployment_guide()

    print()
    print("ARCHIVOS CREADOS:")
    print("   .gitignore - Archivos a ignorar")
    print("   vercel.json - Configuracion de Vercel")
    print("   api.py - Wrapper para Vercel")
    print("   requirements.txt - Dependencias")
    print("   deploy_to_github.sh - Script de despliegue")
    print("   VERCEL_DEPLOY_GUIDE.md - Guia completa")
    print()

    print("PROXIMOS PASOS:")
    print("   1. Crear repositorio en GitHub")
    print("   2. Ejecutar: ./deploy_to_github.sh")
    print("   3. Configurar en Vercel")
    print("   4. Desplegar!")
    print()

    print("VENTAJAS DE VERCEL:")
    print("   URL permanente")
    print("   SSL automatico")
    print("   Despliegue automatico desde Git")
    print("   100GB de ancho de banda gratis")
    print("   Monitoreo integrado")
    print("   Reinicio automatico")
    print()

    print("RECOMENDACION:")
    print("   Vercel es perfecto para tu bot")
    print("   Es gratis, profesional y confiable")

if __name__ == "__main__":
    main()