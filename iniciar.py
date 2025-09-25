#!/usr/bin/env python3
"""
Script de Inicio Rápido del Agente de Ventas
"""
import os
import sys
import subprocess
import time
from pathlib import Path

def print_header():
    """Imprimir encabezado"""
    print("🚀 AGENTE DE VENTAS CON EVOLUTION API")
    print("=" * 50)
    print("🤖 Bot de WhatsApp con IA para ventas de productos")
    print("🔗 Sincronizado con Evolution API")
    print()

def check_requirements():
    """Verificar requisitos"""
    print("🔍 Verificando requisitos...")

    # Verificar Python
    if sys.version_info < (3, 8):
        print("❌ Se requiere Python 3.8 o superior")
        return False

    print("✅ Python 3.8+ encontrado")

    # Verificar archivos necesarios
    required_files = ['.env', 'main.py', 'start_bot.py']
    for file in required_files:
        if not os.path.exists(file):
            print(f"❌ Archivo requerido no encontrado: {file}")
            return False

    print("✅ Todos los archivos requeridos encontrados")
    return True

def show_status():
    """Mostrar estado actual"""
    print("📊 ESTADO ACTUAL:")
    print(f"   📁 Directorio: {os.getcwd()}")
    print(f"   🐍 Python: {sys.version}")
    print(f"   📄 .env: {'✅ Existe' if os.path.exists('.env') else '❌ No existe'}")
    print(f"   🌐 Puerto 8000: {'✅ Libre' if is_port_free(8000) else '❌ Ocupado'}")
    print()

def is_port_free(port):
    """Verificar si un puerto está libre"""
    try:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', port))
            return True
    except:
        return False

def show_menu():
    """Mostrar menú de opciones"""
    print("🎯 ¿QUÉ DESEAS HACER?")
    print("=" * 30)
    print("1. 🚀 Iniciar Bot Completo")
    print("2. 🧪 Probar Configuración")
    print("3. 🔧 Configurar Webhook en Evolution")
    print("4. 📊 Ver Estado del Sistema")
    print("5. 📚 Ver Documentación")
    print("6. ❌ Salir")
    print()

def run_bot():
    """Ejecutar el bot completo"""
    print("🚀 INICIANDO BOT COMPLETO...")
    print("=" * 40)

    try:
        # Ejecutar el sistema completo
        result = subprocess.run([
            sys.executable, 'run_complete_system.py'
        ], cwd=os.getcwd())

        if result.returncode == 0:
            print("✅ Bot ejecutado correctamente")
        else:
            print(f"❌ Error ejecutando bot (código: {result.returncode})")

    except KeyboardInterrupt:
        print("🛑 Bot detenido por usuario")
    except Exception as e:
        print(f"❌ Error inesperado: {str(e)}")

def test_config():
    """Probar configuración"""
    print("🧪 PROBANDO CONFIGURACIÓN...")
    print("=" * 40)

    try:
        result = subprocess.run([
            sys.executable, 'test_config.py'
        ], cwd=os.getcwd())

        if result.returncode == 0:
            print("✅ Configuración verificada")
        else:
            print(f"❌ Error en configuración (código: {result.returncode})")

    except Exception as e:
        print(f"❌ Error ejecutando prueba: {str(e)}")

def show_evolution_setup():
    """Mostrar instrucciones de Evolution"""
    print("🔧 CONFIGURACIÓN DE EVOLUTION API")
    print("=" * 40)
    print()
    print("📍 URL del Webhook:")
    print("   http://192.168.18.69:8000/webhook")
    print()
    print("🌐 URL de Evolution API:")
    print("   https://evoapi2-evolution-api.ovw3ar.easypanel.host")
    print()
    print("📋 PASOS:")
    print("   1. Ve a tu Evolution API")
    print("   2. Configura el webhook con la URL arriba")
    print("   3. Asegúrate de que la instancia esté conectada")
    print("   4. Envía un mensaje de prueba")
    print()
    print("📖 Consulta GUIA_EVOLUTION_API.md para detalles completos")

def show_system_status():
    """Mostrar estado del sistema"""
    print("📊 ESTADO DEL SISTEMA")
    print("=" * 40)
    print()

    # Verificar procesos
    try:
        result = subprocess.run([
            'netstat', '-an'
        ], capture_output=True, text=True, cwd=os.getcwd())

        if '8000' in result.stdout:
            print("🌐 Puerto 8000: ✅ En uso (posiblemente nuestro bot)")
        else:
            print("🌐 Puerto 8000: ✅ Libre")

    except:
        print("🌐 Puerto 8000: ❓ No se pudo verificar")

    # Verificar archivos de log
    log_files = ['logs/agente_ventas.log', 'logs/sync_evolution.log', 'logs/sistema_completo.log']
    for log_file in log_files:
        if os.path.exists(log_file):
            size = os.path.getsize(log_file)
            print(f"📄 {log_file}: ✅ {size} bytes")
        else:
            print(f"📄 {log_file}: ❌ No existe")

    print()
    print("💡 Para ver logs en tiempo real:")
    print("   tail -f logs/agente_ventas.log")

def show_documentation():
    """Mostrar documentación"""
    print("📚 DOCUMENTACIÓN DISPONIBLE")
    print("=" * 40)
    print()
    print("📖 Archivos de documentación:")
    print("   • README.md - Documentación principal")
    print("   • GUIA_EVOLUTION_API.md - Configuración Evolution")
    print("   • .env.example - Ejemplo de configuración")
    print()
    print("🧪 Scripts de prueba:")
    print("   • test_config.py - Verificar configuración")
    print("   • test_webhook.py - Probar webhook")
    print()
    print("🚀 Scripts de ejecución:")
    print("   • main.py - Servidor básico")
    print("   • start_bot.py - Bot con Evolution")
    print("   • run_complete_system.py - Sistema completo")
    print("   • sync_with_evolution.py - Sincronizador")

def main():
    """Función principal"""
    print_header()

    if not check_requirements():
        print("❌ Requisitos no cumplidos. Revisa la instalación.")
        return

    show_status()

    while True:
        show_menu()

        try:
            choice = input("Selecciona una opción (1-6): ").strip()

            if choice == '1':
                run_bot()
            elif choice == '2':
                test_config()
            elif choice == '3':
                show_evolution_setup()
            elif choice == '4':
                show_system_status()
            elif choice == '5':
                show_documentation()
            elif choice == '6':
                print("👋 ¡Hasta luego!")
                break
            else:
                print("❌ Opción no válida. Intenta de nuevo.")

            print("\n" + "="*50 + "\n")

        except KeyboardInterrupt:
            print("\n👋 ¡Hasta luego!")
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()