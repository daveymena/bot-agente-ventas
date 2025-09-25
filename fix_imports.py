#!/usr/bin/env python3
"""
Script para arreglar imports relativos en todos los archivos Python
"""
import os
import re

def fix_imports_in_file(file_path):
    """Arreglar imports relativos en un archivo"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Patrones de import relativos a arreglar
    patterns = [
        (r'from \.\.config\.settings import settings', 'import sys\nimport os\nsys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))\n\nfrom config.settings import settings'),
        (r'from \.\.models\.message import WhatsAppMessage', 'from models.message import WhatsAppMessage'),
        (r'from \.\.models\.product import Product', 'from models.product import Product'),
        (r'from \.\.services\.whatsapp_service import WhatsAppService', 'from services.whatsapp_service import WhatsAppService'),
        (r'from \.\.services\.ai_service import AIService', 'from services.ai_service import AIService'),
        (r'from \.\.services\.audio_service import AudioService', 'from services.audio_service import AudioService'),
        (r'from \.\.services\.scraping_service import ScrapingService', 'from services.scraping_service import ScrapingService'),
        (r'from \.\.services\.message_processor import MessageProcessor', 'from services.message_processor import MessageProcessor'),
        (r'from \.\.core\.sales_agent import SalesAgent', 'from core.sales_agent import SalesAgent'),
        (r'from \.\.utils\.helpers import', 'from utils.helpers import'),
    ]

    modified = False
    for pattern, replacement in patterns:
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            modified = True

    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Arreglado: {file_path}")
        return True
    return False

def main():
    """Arreglar imports en todos los archivos Python"""
    project_root = os.path.dirname(os.path.abspath(__file__))

    # Archivos a procesar
    files_to_fix = [
        'config/settings.py',
        'models/message.py',
        'models/product.py',
        'services/whatsapp_service.py',
        'services/scraping_service.py',
        'services/ai_service.py',
        'services/audio_service.py',
        'services/message_processor.py',
        'core/sales_agent.py',
        'main.py',
        'utils/helpers.py',
        'test_config.py'
    ]

    print("Arreglando imports relativos...")
    print("=" * 50)

    fixed_count = 0
    for file_name in files_to_fix:
        file_path = os.path.join(project_root, file_name)
        if os.path.exists(file_path):
            if fix_imports_in_file(file_path):
                fixed_count += 1

    print(f"\nCompletado: {fixed_count} archivos arreglados")
    print("Ahora puedes ejecutar: python test_config.py")

if __name__ == "__main__":
    main()