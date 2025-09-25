#!/usr/bin/env python3
"""
Opciones de Despliegue - Elige la mejor para ti
"""
import os
import sys

def print_header():
    """Imprimir encabezado"""
    print("🚀 OPCIONES DE DESPLIEGUE - AGENTE DE VENTAS")
    print("=" * 60)
    print("🌐 Elige la mejor opción para exponer tu webhook")
    print("📱 Tu Evolution API necesita una URL pública permanente")
    print()

def show_options():
    """Mostrar opciones disponibles"""
    options = [
        {
            "id": "1",
            "name": "🏠 Local con Cloudflare Tunnel (Recomendado)",
            "description": "URL permanente gratis, SSL automático, más estable",
            "cost": "Gratis",
            "difficulty": "Media",
            "url_type": "Permanente"
        },
        {
            "id": "2",
            "name": "☁️ Vercel (Hosting Gratuito)",
            "description": "Despliegue automático, URL permanente, 100GB/mes gratis",
            "cost": "Gratis",
            "difficulty": "Baja",
            "url_type": "Permanente"
        },
        {
            "id": "3",
            "name": "🚂 Railway (Hosting Gratuito)",
            "description": "500MB RAM gratis, URL permanente, fácil de usar",
            "cost": "Gratis",
            "difficulty": "Baja",
            "url_type": "Permanente"
        },
        {
            "id": "4",
            "name": "📦 Docker + VPS Gratuito",
            "description": "Control total, VPS gratuito (Oracle, Google Cloud)",
            "cost": "Gratis",
            "difficulty": "Alta",
            "url_type": "Permanente"
        },
        {
            "id": "5",
            "name": "🔗 ngrok (Solo para pruebas)",
            "description": "Rápido para testing, URL cambia cada 8 horas",
            "cost": "Gratis",
            "difficulty": "Baja",
            "url_type": "Temporal"
        }
    ]

    print("🎯 OPCIONES DISPONIBLES:")
    print("-" * 60)

    for option in options:
        print(f"{option['id']}. {option['name']}")
        print(f"   💡 {option['description']}")
        print(f"   💰 Costo: {option['cost']}")
        print(f"   🔧 Dificultad: {option['difficulty']}")
        print(f"   🌐 URL: {option['url_type']}")
        print()

def get_option_details(choice):
    """Obtener detalles de la opción seleccionada"""
    details = {
        "1": {
            "name": "Cloudflare Tunnel",
            "script": "python deploy_to_cloudflare.py",
            "description": """
🏆 MEJOR OPCIÓN GENERAL

✅ Ventajas:
   • URL permanente (no expira)
   • SSL automático
   • Tráfico ilimitado gratis
   • Más estable que ngrok
   • Sin límites de tiempo

📋 Pasos:
   1. Instalar Docker y Cloudflare Tunnel
   2. Configurar tunnel con tu dominio
   3. Ejecutar: docker-compose up -d

🌐 Tu webhook será:
   https://tu-bot.tu-dominio.com/webhook
            """,
            "files": ["cloudflare-tunnel.yml", "Dockerfile", "docker-compose.yml", "CLOUDFLARE_DEPLOY.md"]
        },
        "2": {
            "name": "Vercel",
            "script": "python deploy_to_vercel.py",
            "description": """
☁️ HOSTING GRATUITO POPULAR

✅ Ventajas:
   • Despliegue automático desde Git
   • 100GB de ancho de banda gratis
   • URL permanente
   • SSL automático
   • Fácil de usar

📋 Pasos:
   1. Instalar Vercel CLI
   2. Hacer login: vercel login
   3. Desplegar: vercel --prod

🌐 Tu webhook será:
   https://tu-app.vercel.app/webhook
            """,
            "files": ["vercel.json", "api.py", "requirements.txt", "RAILWAY_DEPLOY.md"]
        },
        "3": {
            "name": "Railway",
            "script": "python deploy_to_railway.py",
            "description": """
🚂 HOSTING PYTHON ESPECIALIZADO

✅ Ventajas:
   • 500MB RAM gratis
   • 1GB almacenamiento gratis
   • URL permanente
   • Despliegue automático
   • Perfecto para Python

📋 Pasos:
   1. Instalar Railway CLI
   2. Hacer login: railway login
   3. Desplegar: railway up

🌐 Tu webhook será:
   https://tu-app.railway.app/webhook
            """,
            "files": ["railway.toml", "nixpacks.toml", "requirements.txt", "RAILWAY_DEPLOY.md"]
        },
        "4": {
            "name": "VPS Gratuito",
            "script": None,
            "description": """
📦 SERVIDOR VIRTUAL PRIVADO

✅ Ventajas:
   • Control total del servidor
   • Recursos dedicados
   • Configuración personalizada
   • Mejor rendimiento

🔧 Opciones de VPS Gratuito:
   • Oracle Cloud: 2 CPUs, 24GB RAM
   • Google Cloud: 1 CPU, 2GB RAM
   • AWS Free Tier: 1 CPU, 1GB RAM

📋 Pasos:
   1. Crear cuenta en Oracle/Google/AWS
   2. Crear instancia gratuita
   3. Instalar Docker
   4. Ejecutar el bot
            """,
            "files": ["Dockerfile", "docker-compose.yml"]
        },
        "5": {
            "name": "ngrok",
            "script": "python run_with_ngrok.py",
            "description": """
🔗 SOLO PARA PRUEBAS RÁPIDAS

⚠️ LIMITACIONES:
   • URL cambia cada 8 horas
   • No es para producción
   • Límite de conexiones
   • Menos estable

📋 Pasos:
   1. Instalar ngrok
   2. Ejecutar: python run_with_ngrok.py
   3. Copiar la URL que aparece
   4. Configurar en Evolution API

🌐 Tu webhook será:
   https://abc123.ngrok.io/webhook
   (cambia cada vez que reinicias)
            """,
            "files": ["run_with_ngrok.py"]
        }
    }

    return details.get(choice, {})

def main():
    """Función principal"""
    print_header()
    show_options()

    while True:
        try:
            choice = input("Selecciona una opción (1-5): ").strip()

            if choice in ['1', '2', '3', '4', '5']:
                details = get_option_details(choice)

                print(f"🎯 HAS ELEGIDO: {details['name']}")
                print("=" * 50)
                print(details['description'])

                if details['script']:
                    run = input(f"¿Ejecutar configuración para {details['name']}? (y/n): ").lower().strip()

                    if run == 'y':
                        print(f"🚀 Ejecutando: {details['script']}")
                        result = os.system(details['script'])

                        if result == 0:
                            print("✅ Configuración completada!")
                            print(f"📋 Archivos creados: {', '.join(details['files'])}")
                        else:
                            print("❌ Error en la configuración")
                else:
                    print("💡 Esta opción requiere configuración manual")
                    print("📖 Consulta la documentación específica")

                print()
                print("🔄 ¿Quieres ver otras opciones? (y/n): ", end="")
                again = input().lower().strip()

                if again != 'y':
                    break
            else:
                print("❌ Opción no válida. Elige 1-5.")

        except KeyboardInterrupt:
            print("\n👋 ¡Hasta luego!")
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}")

    print()
    print("🎉 ¡Elige la opción que mejor se adapte a tus necesidades!")
    print("💡 Recomendación: Cloudflare Tunnel para producción")

if __name__ == "__main__":
    main()