"""
Servicio para hacer scraping de productos de las tiendas
"""
import asyncio
import aiohttp
import logging
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from models.product import Product

logger = logging.getLogger(__name__)

class ScrapingService:
    """Servicio para hacer scraping de sitios web"""

    def __init__(self):
        self.megapack_url = settings.MEGAPACK_URL
        self.megacomputer_url = settings.MEGACOMPUTER_URL
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Inicializar sesión HTTP"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cerrar sesión HTTP"""
        if self.session:
            await self.session.close()

    async def scrape_megapack(self) -> List[Product]:
        """
        Hacer scraping de productos de MegaPack

        Returns:
            List[Product]: Lista de productos encontrados
        """
        return await self._scrape_website(self.megapack_url, "MegaPack")

    async def scrape_megacomputer(self) -> List[Product]:
        """
        Hacer scraping de productos de MegaComputer

        Returns:
            List[Product]: Lista de productos encontrados
        """
        return await self._scrape_website(self.megacomputer_url, "MegaComputer")

    async def scrape_all_stores(self) -> Dict[str, List[Product]]:
        """
        Hacer scraping de todas las tiendas

        Returns:
            Dict[str, List[Product]]: Diccionario con productos por tienda
        """
        if not self.session:
            await self.__aenter__()

        try:
            # Hacer scraping en paralelo
            megapack_task = asyncio.create_task(self.scrape_megapack())
            megacomputer_task = asyncio.create_task(self.scrape_megacomputer())

            megapack_products, megacomputer_products = await asyncio.gather(
                megapack_task, megacomputer_task, return_exceptions=True
            )

            # Manejar excepciones
            if isinstance(megapack_products, Exception):
                logger.error(f"Error scraping MegaPack: {str(megapack_products)}")
                megapack_products = []

            if isinstance(megacomputer_products, Exception):
                logger.error(f"Error scraping MegaComputer: {str(megacomputer_products)}")
                megacomputer_products = []

            return {
                "MegaPack": megapack_products,
                "MegaComputer": megacomputer_products
            }

        except Exception as e:
            logger.error(f"Error en scraping general: {str(e)}")
            return {"MegaPack": [], "MegaComputer": []}

    async def _scrape_website(self, url: str, store_name: str) -> List[Product]:
        """
        Hacer scraping de un sitio web específico

        Args:
            url: URL del sitio web
            store_name: Nombre de la tienda

        Returns:
            List[Product]: Lista de productos encontrados
        """
        if not self.session:
            await self.__aenter__()

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            async with self.session.get(url, headers=headers, timeout=30) as response:
                if response.status != 200:
                    logger.error(f"Error HTTP {response.status} para {url}")
                    return []

                html = await response.text()
                return self._extract_products_from_html(html, store_name)

        except asyncio.TimeoutError:
            logger.error(f"Timeout scraping {url}")
            return []
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return []

    def _extract_products_from_html(self, html: str, store_name: str) -> List[Product]:
        """
        Extraer productos desde HTML usando regex (método simple)

        Args:
            html: Contenido HTML
            store_name: Nombre de la tienda

        Returns:
            List[Product]: Lista de productos encontrados
        """
        import re

        productos = []

        # Regex para encontrar títulos de productos (h1-h6)
        # Busca patrones como <h1>Nombre del Producto</h1>
        regex = r'<h[1-6][^>]*>([^<]{3,200})</h[1-6]>'
        matches = re.finditer(regex, html, re.IGNORECASE | re.DOTALL)

        for match in matches:
            nombre = match.group(1).strip()

            # Filtrar títulos que parezcan productos
            if self._is_product_title(nombre):
                productos.append(Product(
                    nombre=nombre,
                    tienda=store_name
                ))

        logger.info(f"Encontrados {len(productos)} productos en {store_name}")
        return productos

    def _is_product_title(self, title: str) -> bool:
        """
        Determinar si un título parece ser de un producto

        Args:
            title: Título a evaluar

        Returns:
            bool: True si parece un título de producto
        """
        if not title or len(title) < 3:
            return False

        # Palabras que indican que es un producto
        product_keywords = [
            'laptop', 'computador', 'pc', 'notebook', 'portátil',
            'iphone', 'samsung', 'xiaomi', 'huawei', 'motorola',
            'tablet', 'ipad', 'galaxy', 'pro', 'max', 'plus',
            'ssd', 'hdd', 'ram', 'memoria', 'procesador', 'cpu',
            'monitor', 'pantalla', 'teclado', 'mouse', 'auricular',
            'cargador', 'batería', 'adaptador', 'cable', 'usb'
        ]

        title_lower = title.lower()

        # Verificar si contiene palabras clave de productos
        has_product_keyword = any(keyword in title_lower for keyword in product_keywords)

        # Verificar que no sea un título de navegación o footer
        navigation_words = ['inicio', 'contacto', 'nosotros', 'servicios', 'productos', 'categorías']
        is_navigation = any(word in title_lower for word in navigation_words)

        # Longitud razonable para un nombre de producto
        reasonable_length = 3 <= len(title) <= 150

        return has_product_keyword and not is_navigation and reasonable_length

    def find_product_by_query(self, products: List[Product], query: str) -> Optional[Product]:
        """
        Buscar producto que coincida con una consulta

        Args:
            products: Lista de productos
            query: Consulta de búsqueda

        Returns:
            Optional[Product]: Producto encontrado o None
        """
        if not query or not products:
            return None

        query_lower = query.lower()

        # Búsqueda exacta primero
        for product in products:
            if product.matches_query(query):
                return product

        # Si no hay coincidencia exacta, buscar alternativas
        alternatives = []
        for product in products[:5]:  # Limitar a 5 alternativas
            if query_lower in product.nombre.lower():
                alternatives.append(product)

        return alternatives[0] if alternatives else None

    def get_all_products(self, store_data: Dict[str, List[Product]]) -> List[Product]:
        """
        Obtener todos los productos de todas las tiendas

        Args:
            store_data: Diccionario con productos por tienda

        Returns:
            List[Product]: Lista combinada de productos
        """
        all_products = []
        for products in store_data.values():
            all_products.extend(products)
        return all_products