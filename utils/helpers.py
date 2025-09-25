"""
Utilidades y funciones auxiliares
"""
import re
import logging
from typing import Dict, Any, Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    """
    Limpiar y normalizar texto

    Args:
        text: Texto a limpiar

    Returns:
        str: Texto limpio
    """
    if not text:
        return ""

    # Remover caracteres especiales pero mantener emojis
    text = re.sub(r'[^\w\s\u00C0-\u017F\u2000-\u206F\u2600-\u27FF]', '', text)

    # Normalizar espacios
    text = ' '.join(text.split())

    return text.strip()

def extract_urls(text: str) -> list:
    """
    Extraer URLs de un texto

    Args:
        text: Texto que puede contener URLs

    Returns:
        list: Lista de URLs encontradas
    """
    url_pattern = r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?)'
    return re.findall(url_pattern, text)

def format_phone_number(phone: str) -> str:
    """
    Formatear número de teléfono

    Args:
        phone: Número de teléfono

    Returns:
        str: Número formateado
    """
    if not phone:
        return ""

    # Remover caracteres no numéricos
    cleaned = re.sub(r'\D', '', phone)

    # Asegurar que tenga código de país
    if len(cleaned) == 10:  # Solo número local
        cleaned = f"57{cleaned}"  # Agregar código Colombia
    elif len(cleaned) == 12 and cleaned.startswith('57'):
        pass  # Ya tiene código correcto
    else:
        logger.warning(f"Formato de teléfono inesperado: {phone}")

    return cleaned

def validate_webhook_data(data: Dict[str, Any]) -> bool:
    """
    Validar estructura básica de datos del webhook

    Args:
        data: Datos del webhook

    Returns:
        bool: True si la estructura es válida
    """
    try:
        # Verificar estructura básica
        if not isinstance(data, dict):
            return False

        # Verificar que tenga body o data
        if 'body' not in data and 'data' not in data:
            return False

        # Si tiene body, verificar que tenga data
        if 'body' in data and not isinstance(data['body'], dict):
            return False

        return True

    except Exception as e:
        logger.error(f"Error validando webhook data: {str(e)}")
        return False

def safe_get(data: Dict[str, Any], keys: list, default: Any = None) -> Any:
    """
    Obtener valor de diccionario de forma segura

    Args:
        data: Diccionario
        keys: Lista de claves a probar
        default: Valor por defecto

    Returns:
        Any: Valor encontrado o default
    """
    for key in keys:
        if key in data:
            return data[key]
    return default

def encode_url_param(text: str) -> str:
    """
    Codificar texto para URL

    Args:
        text: Texto a codificar

    Returns:
        str: Texto codificado
    """
    return quote(str(text), safe='')

def format_currency(amount: float, currency: str = "COP") -> str:
    """
    Formatear cantidad como moneda

    Args:
        amount: Cantidad numérica
        currency: Código de moneda

    Returns:
        str: Cantidad formateada
    """
    try:
        if currency.upper() == "COP":
            return f"${amount:,.0f}".replace(",", ".")
        elif currency.upper() == "USD":
            return f"${amount:,.2f}"
        else:
            return f"{amount:.2f} {currency}"
    except (ValueError, TypeError):
        return str(amount)

def calculate_similarity(text1: str, text2: str) -> float:
    """
    Calcular similitud entre dos textos (simple)

    Args:
        text1: Primer texto
        text2: Segundo texto

    Returns:
        float: Similitud entre 0 y 1
    """
    if not text1 or not text2:
        return 0.0

    text1 = text1.lower()
    text2 = text2.lower()

    # Contar palabras en común
    words1 = set(text1.split())
    words2 = set(text2.split())

    if not words1 or not words2:
        return 0.0

    intersection = words1.intersection(words2)
    union = words1.union(words2)

    return len(intersection) / len(union)

def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncar texto a longitud máxima

    Args:
        text: Texto a truncar
        max_length: Longitud máxima
        suffix: Sufijo para texto truncado

    Returns:
        str: Texto truncado
    """
    if not text or len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix

def is_valid_json(data: Any) -> bool:
    """
    Verificar si los datos son JSON válidos

    Args:
        data: Datos a verificar

    Returns:
        bool: True si son JSON válidos
    """
    try:
        import json
        json.dumps(data)
        return True
    except (TypeError, ValueError):
        return False

def get_nested_value(data: Dict[str, Any], path: str, default: Any = None) -> Any:
    """
    Obtener valor anidado de diccionario usando notación de punto

    Args:
        data: Diccionario
        path: Ruta (ej: "body.data.message")
        default: Valor por defecto

    Returns:
        Any: Valor encontrado o default
    """
    keys = path.split('.')
    current = data

    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default

    return current