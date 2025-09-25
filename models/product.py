"""
Modelos de datos para productos
"""
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import re

@dataclass
class Product:
    """Representa un producto de las tiendas"""
    nombre: str
    tienda: str
    precio: str = "Consultar"
    disponibilidad: str = "Consultar"
    imagen: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario"""
        return {
            'nombre': self.nombre,
            'tienda': self.tienda,
            'precio': self.precio,
            'disponibilidad': self.disponibilidad,
            'imagen': self.imagen
        }

    @classmethod
    def from_html(cls, html: str, tienda: str) -> List['Product']:
        """Extraer productos desde HTML usando regex"""
        productos = []

        # Regex para encontrar títulos de productos (h1-h6)
        regex = r'<h[1-6][^>]*>([^<]{3,200})</h[1-6]>'
        matches = re.finditer(regex, html, re.IGNORECASE | re.DOTALL)

        for match in matches:
            nombre = match.group(1).strip()
            if nombre and len(nombre) > 3:  # Filtrar títulos muy cortos
                productos.append(cls(
                    nombre=nombre,
                    tienda=tienda
                ))

        return productos

    def matches_query(self, query: str) -> bool:
        """Verificar si el producto coincide con una consulta"""
        if not query:
            return False

        query_lower = query.lower()
        nombre_lower = self.nombre.lower()

        # Búsqueda exacta o parcial
        return query_lower in nombre_lower

    def get_display_info(self) -> str:
        """Obtener información formateada para mostrar"""
        return f"{self.nombre} - {self.tienda} 💻"

    def get_detailed_info(self) -> str:
        """Obtener información detallada del producto"""
        info = f"📱 {self.nombre}\n"
        info += f"🏪 Tienda: {self.tienda}\n"
        info += f"💰 Precio: {self.precio}\n"
        info += f"📦 Disponibilidad: {self.disponibilidad}"

        if self.imagen:
            info += f"\n🖼️ Imagen: {self.imagen}"

        return info