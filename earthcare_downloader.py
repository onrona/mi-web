#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EarthCARE Product Downloader
Author: GitHub Copilot
Created: 2024-11-17
Version: 1.0
Description:
    Clase para descargar productos EarthCARE desde OADS basado en archivos CSV
    con información de fechas/horas y configuración flexible de productos.
"""

import os
import re
import requests
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Union, Tuple
from urllib.parse import urlparse
from xml.etree import ElementTree
from bs4 import BeautifulSoup
from lxml import html
import toml
from dataclasses import dataclass
import logging


@dataclass
class DownloadConfig:
    """Configuración para la descarga de productos EarthCARE"""
    collection: str
    products: List[str]
    baseline: str
    download_directory: str
    credentials_file: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    max_retries: int = 3
    time_tolerance_minutes: int = 11
    override_existing: bool = False
    log_file: str = "earthcare_downloader.log"


class EarthCAREDownloader:
    """
    Clase para descargar productos EarthCARE desde OADS.
    
    Ejemplo de uso:
    
    # Configurar descargador
    config = DownloadConfig(
        collection="EarthCAREL2InstChecked",
        products=["ATL_ALD_2A", "ATL_FM__2A"],
        baseline="BA",
        download_directory="./downloads",
        credentials_file="credentials.toml"
    )
    
    downloader = EarthCAREDownloader(config)
    
    # Descargar desde CSV
    downloader.download_from_csv("overpasses.csv")
    """
    
    # Colecciones disponibles
    COLLECTIONS = {
        'EarthCAREAuxiliary': 'EarthCARE Auxiliary Data for Cal/Val Users',
        'EarthCAREL2Validated': 'EarthCARE ESA L2 Products',
        'EarthCAREL2InstChecked': 'EarthCARE ESA L2 Products for Cal/Val Users',
        'EarthCAREL2Products': 'EarthCARE ESA L2 Products for the Commissioning Team',
        'JAXAL2Validated': 'EarthCARE JAXA L2 Products',
        'JAXAL2InstChecked': 'EarthCARE JAXA L2 Products for Cal/Val Users',
        'JAXAL2Products': 'EarthCARE JAXA L2 Products for the Commissioning Team',
        'EarthCAREL0L1Products': 'EarthCARE L0 and L1 Products for the Commissioning Team',
        'EarthCAREL1Validated': 'EarthCARE L1 Products',
        'EarthCAREL1InstChecked': 'EarthCARE L1 Products for Cal/Val Users',
        'EarthCAREOrbitData': 'EarthCARE Orbit Data'
    }
    
    # Productos disponibles
    PRODUCTS = [
        # ATLID level 1b
        'ATL_NOM_1B', 'ATL_DCC_1B', 'ATL_CSC_1B', 'ATL_FSC_1B',
        # MSI level 1b
        'MSI_NOM_1B', 'MSI_BBS_1B', 'MSI_SD1_1B', 'MSI_SD2_1B',
        # BBR level 1b
        'BBR_NOM_1B', 'BBR_SNG_1B', 'BBR_SOL_1B', 'BBR_LIN_1B',
        # CPR level 1b
        'CPR_NOM_1B',
        # MSI level 1c
        'MSI_RGR_1C',
        # level 1d
        'AUX_MET_1D', 'AUX_JSG_1D',
        # ATLID level 2a
        'ATL_FM__2A', 'ATL_AER_2A', 'ATL_ICE_2A', 'ATL_TC__2A',
        'ATL_EBD_2A', 'ATL_CTH_2A', 'ATL_ALD_2A',
        # MSI level 2a
        'MSI_CM__2A', 'MSI_COP_2A', 'MSI_AOT_2A',
        # CPR level 2a
        'CPR_FMR_2A', 'CPR_CD__2A', 'CPR_TC__2A', 'CPR_CLD_2A', 'CPR_APC_2A',
        # ATLID-MSI level 2b
        'AM__MO__2B', 'AM__CTH_2B', 'AM__ACD_2B',
        # ATLID-CPR level 2b
        'AC__TC__2B',
        # BBR-MSI-(ATLID) level 2b
        'BM__RAD_2B', 'BMA_FLX_2B',
        # ATLID-CPR-MSI level 2b
        'ACM_CAP_2B', 'ACM_COM_2B', 'ACM_RT__2B',
        # ATLID-CPR-MSI-BBR
        'ALL_DF__2B', 'ALL_3D__2B',
        # Orbit data
        'MPL_ORBSCT', 'AUX_ORBPRE', 'AUX_ORBRES'
    ]
    
    # Baselines disponibles
    BASELINES = ['AC', 'AD', 'AE', 'BA', 'BB']
    
    def __init__(self, config: DownloadConfig):
        """
        Inicializar el descargador de EarthCARE.
        
        Args:
            config: Configuración de descarga
        """
        self.config = config
        self._validate_config()
        self._setup_logging()
        self._setup_directories()
        self._load_credentials()
        
        # Estadísticas de descarga
        self.stats = {
            'total_requests': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'skipped_existing': 0,
            'errors': []
        }
    
    def _validate_config(self):
        """Validar la configuración proporcionada"""
        # Validar colección
        if self.config.collection not in self.COLLECTIONS:
            raise ValueError(f"Colección no válida: {self.config.collection}. "
                           f"Disponibles: {list(self.COLLECTIONS.keys())}")
        
        # Validar productos
        invalid_products = [p for p in self.config.products if p not in self.PRODUCTS]
        if invalid_products:
            raise ValueError(f"Productos no válidos: {invalid_products}. "
                           f"Disponibles: {self.PRODUCTS}")
        
        # Validar baseline
        if self.config.baseline not in self.BASELINES:
            raise ValueError(f"Baseline no válida: {self.config.baseline}. "
                           f"Disponibles: {self.BASELINES}")
    
    def _setup_logging(self):
        """Configurar el sistema de logging"""
        log_file = Path(self.config.download_directory) / self.config.log_file
        
        # Configurar logging para guardar solo en archivo
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Iniciando EarthCARE Downloader")
        self.logger.info(f"Colección: {self.config.collection}")
        self.logger.info(f"Productos: {self.config.products}")
        self.logger.info(f"Baseline: {self.config.baseline}")
    
    def _setup_directories(self):
        """Crear directorios necesarios"""
        self.download_path = Path(self.config.download_directory)
        self.download_path.mkdir(parents=True, exist_ok=True)
        
        # Crear subdirectorios por producto
        for product in self.config.products:
            product_dir = self.download_path / product
            product_dir.mkdir(exist_ok=True)
    
    def _load_credentials(self):
        """Cargar credenciales de OADS"""
        if self.config.credentials_file:
            try:
                with open(self.config.credentials_file, 'r') as f:
                    creds = toml.load(f)
                    self.username = creds.get('username')
                    self.password = creds.get('password')
            except Exception as e:
                self.logger.error(f"Error cargando credenciales: {e}")
                raise
        else:
            self.username = self.config.username
            self.password = self.config.password
        
        if not (self.username and self.password):
            raise ValueError("Credenciales de OADS no proporcionadas")
    
    def download_from_csv(self, csv_path: str, 
                         date_column: str = 'yyyy-mm-dd',
                         time_column: Optional[str] = 'hh:mm:ss.sss',
                         orbit_column: Optional[str] = 'Absolute_Orbit',
                         station_column: Optional[str] = 'Zone') -> Dict:
        """
        Descargar productos basado en un archivo CSV.
        
        Args:
            csv_path: Ruta del archivo CSV con información de overpasses
            date_column: Nombre de la columna con fechas
            time_column: Nombre de la columna con horas (opcional)
            orbit_column: Nombre de la columna con órbitas (opcional)
            station_column: Nombre de la columna con estaciones (opcional)
            
        Returns:
            Diccionario con estadísticas de descarga
        """
        try:
            df = pd.read_csv(csv_path)
            self.logger.info(f"Cargado CSV con {len(df)} filas")
            
            for index, row in df.iterrows():
                try:
                    # Extraer información de la fila
                    date_str = row[date_column]
                    time_str = row.get(time_column, None) if time_column else None
                    orbit = row.get(orbit_column, None) if orbit_column else None
                    station = row.get(station_column, None) if station_column else None
                    
                    # Procesar cada producto
                    for product in self.config.products:
                        self._download_product_for_datetime(
                            product, date_str, time_str, orbit, station, index
                        )
                        
                except Exception as e:
                    self.logger.error(f"Error procesando fila {index}: {e}")
                    self.stats['errors'].append(f"Fila {index}: {str(e)}")
                    self.stats['failed_downloads'] += 1
            
            self._log_final_stats()
            return self.stats
            
        except Exception as e:
            self.logger.error(f"Error cargando CSV {csv_path}: {e}")
            raise
    
    def _download_product_for_datetime(self, product: str, date_str: str, 
                                     time_str: Optional[str] = None,
                                     orbit: Optional[int] = None,
                                     station: Optional[str] = None,
                                     row_index: Optional[int] = None):
        """Descargar producto para fecha/hora específica"""
        try:
            self.stats['total_requests'] += 1
            
            # Formatear fecha/hora
            if time_str:
                datetime_str = f"{date_str}T{time_str}"
                search_datetime = self._parse_datetime(datetime_str)
            else:
                search_datetime = self._parse_datetime(date_str)
            
            # Buscar productos
            products_found = self._search_products(
                product, search_datetime, orbit, station
            )
            
            if not products_found:
                self.logger.warning(f"No se encontraron productos para {product} en {date_str}")
                return
            
            # Filtrar por baseline
            filtered_products = self._filter_by_baseline(products_found)
            
            if not filtered_products:
                self.logger.warning(f"No se encontraron productos con baseline {self.config.baseline}")
                return
            
            # Descargar productos
            for product_info in filtered_products:
                self._download_single_product(product_info, product)
                
        except Exception as e:
            self.logger.error(f"Error descargando {product} para {date_str}: {e}")
            self.stats['errors'].append(f"{product} {date_str}: {str(e)}")
            self.stats['failed_downloads'] += 1
    
    def _parse_datetime(self, datetime_str: str) -> datetime:
        """Convertir string de fecha/hora a objeto datetime"""
        formats = [
            '%Y-%m-%d',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(datetime_str, fmt)
            except ValueError:
                continue
        
        raise ValueError(f"Formato de fecha no reconocido: {datetime_str}")
    
    def _search_products(self, product: str, search_datetime: datetime,
                        orbit: Optional[int] = None,
                        station: Optional[str] = None) -> List[Dict]:
        """Buscar productos en OADS"""
        try:
            # Obtener template de búsqueda
            template = self._get_product_search_template()
            
            # Construir parámetros de búsqueda
            search_params = self._build_search_params(
                product, search_datetime, orbit, station
            )
            
            # Realizar búsqueda
            response = self._execute_search(template, search_params)
            
            # Procesar respuesta
            return self._parse_search_response(response)
            
        except Exception as e:
            self.logger.error(f"Error en búsqueda de productos: {e}")
            return []
    
    def _get_product_search_template(self) -> str:
        """Obtener template de búsqueda de productos"""
        collection_url_map = {
            'EarthCAREAuxiliary': 'https://eocat.esa.int/eo-catalogue/collections/EarthCAREAuxiliary/describe',
            'EarthCAREL2Validated': 'https://eocat.esa.int/eo-catalogue/collections/EarthCAREL2Validated/describe',
            'EarthCAREL2InstChecked': 'https://eocat.esa.int/eo-catalogue/collections/EarthCAREL2InstChecked/describe',
            'EarthCAREL2Products': 'https://eocat.esa.int/eo-catalogue/collections/EarthCAREL2Products/describe',
            'JAXAL2Validated': 'https://eocat.esa.int/eo-catalogue/collections/JAXAL2Validated/describe',
            'JAXAL2InstChecked': 'https://eocat.esa.int/eo-catalogue/collections/JAXAL2InstChecked/describe',
            'JAXAL2Products': 'https://eocat.esa.int/eo-catalogue/collections/JAXAL2Products/describe',
            'EarthCAREL0L1Products': 'https://eocat.esa.int/eo-catalogue/collections/EarthCAREL0L1Products/describe',
            'EarthCAREL1Validated': 'https://eocat.esa.int/eo-catalogue/collections/EarthCAREL1Validated/describe',
            'EarthCAREL1InstChecked': 'https://eocat.esa.int/eo-catalogue/collections/EarthCAREL1InstChecked/describe',
            'EarthCAREOrbitData': 'https://eocat.esa.int/eo-catalogue/collections/EarthCAREOrbitData/describe'
        }
        
        url = collection_url_map.get(self.config.collection)
        if not url:
            raise ValueError(f"URL no encontrada para colección: {self.config.collection}")
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Extraer template de la respuesta XML
            root = ElementTree.fromstring(response.content)
            
            # Buscar el template URL
            namespaces = {
                'os': 'http://a9.com/-/spec/opensearch/1.1/',
                'param': 'http://a9.com/-/spec/opensearch/extensions/parameters/1.0/'
            }
            
            url_elem = root.find('.//os:Url[@type="application/atom+xml"]', namespaces)
            if url_elem is not None:
                return url_elem.get('template')
            
            raise ValueError("Template no encontrado en respuesta")
            
        except Exception as e:
            self.logger.error(f"Error obteniendo template: {e}")
            raise
    
    def _build_search_params(self, product: str, search_datetime: datetime,
                           orbit: Optional[int] = None,
                           station: Optional[str] = None) -> Dict:
        """Construir parámetros de búsqueda"""
        # Mapeo de productos a códigos de búsqueda
        product_map = {
            'ATL_ALD_2A': 'AALD', 'ATL_FM__2A': 'AFM', 'ATL_EBD_2A': 'AEBD',
            'ATL_CTH_2A': 'ACTH', 'AUX_JSG_1D': 'AUX_JSG_1D'
        }
        
        product_code = product_map.get(product, product)
        
        # Calcular ventana de tiempo
        start_time = search_datetime - timedelta(minutes=self.config.time_tolerance_minutes)
        end_time = search_datetime + timedelta(minutes=self.config.time_tolerance_minutes)
        
        params = {
            'productType': product_code,
            'startDate': start_time.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
            'endDate': end_time.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
            'maximumRecords': 100
        }
        
        if orbit:
            params['orbitNumber'] = orbit
        
        return params
    
    def _execute_search(self, template: str, params: Dict) -> requests.Response:
        """Ejecutar búsqueda en OADS"""
        # Construir URL de búsqueda
        search_url = template
        for param, value in params.items():
            placeholder = f"{{{param}}}"
            if placeholder in search_url:
                search_url = search_url.replace(placeholder, str(value))
        
        # Remover parámetros no utilizados
        search_url = re.sub(r'\{[^}]*\}', '', search_url)
        
        # Hacer la petición
        response = requests.get(search_url, timeout=60)
        response.raise_for_status()
        
        return response
    
    def _parse_search_response(self, response: requests.Response) -> List[Dict]:
        """Procesar respuesta de búsqueda"""
        try:
            root = ElementTree.fromstring(response.content)
            
            namespaces = {
                'atom': 'http://www.w3.org/2005/Atom',
                'dc': 'http://purl.org/dc/elements/1.1/',
                'georss': 'http://www.georss.org/georss',
                'os': 'http://a9.com/-/spec/opensearch/1.1/',
            }
            
            products = []
            entries = root.findall('.//atom:entry', namespaces)
            
            for entry in entries:
                try:
                    title_elem = entry.find('atom:title', namespaces)
                    title = title_elem.text if title_elem is not None else ""
                    
                    # Extraer enlaces de descarga
                    links = []
                    for link in entry.findall('atom:link', namespaces):
                        rel = link.get('rel', '')
                        if rel in ['enclosure', 'alternate']:
                            links.append({
                                'href': link.get('href', ''),
                                'rel': rel,
                                'type': link.get('type', ''),
                                'title': link.get('title', '')
                            })
                    
                    # Extraer fecha/hora
                    date_elem = entry.find('dc:date', namespaces)
                    date_str = date_elem.text if date_elem is not None else ""
                    
                    products.append({
                        'title': title,
                        'links': links,
                        'date': date_str,
                        'entry': entry
                    })
                    
                except Exception as e:
                    self.logger.warning(f"Error procesando entrada: {e}")
                    continue
            
            return products
            
        except Exception as e:
            self.logger.error(f"Error procesando respuesta XML: {e}")
            return []
    
    def _filter_by_baseline(self, products: List[Dict]) -> List[Dict]:
        """Filtrar productos por baseline"""
        filtered = []
        
        for product in products:
            title = product.get('title', '')
            
            # Buscar baseline en el título
            baseline_pattern = r'_(\w{2})\d{4}[A-Z]?\.ZIP'
            match = re.search(baseline_pattern, title)
            
            if match and match.group(1) == self.config.baseline:
                filtered.append(product)
        
        return filtered
    
    def _download_single_product(self, product_info: Dict, product_type: str):
        """Descargar un producto individual"""
        try:
            title = product_info.get('title', '')
            
            # Buscar enlace de descarga
            download_link = None
            for link in product_info.get('links', []):
                if link.get('rel') == 'enclosure':
                    download_link = link.get('href')
                    break
            
            if not download_link:
                self.logger.warning(f"No se encontró enlace de descarga para {title}")
                return
            
            # Definir ruta de destino
            filename = Path(download_link).name
            if not filename.endswith('.zip'):
                filename = title + '.zip'
            
            destination = self.download_path / product_type / filename
            
            # Verificar si ya existe
            if destination.exists() and not self.config.override_existing:
                self.logger.info(f"Archivo ya existe: {destination}")
                self.stats['skipped_existing'] += 1
                return
            
            # Descargar archivo
            success = self._download_file_with_retry(download_link, destination)
            
            if success:
                self.stats['successful_downloads'] += 1
                self.logger.info(f"Descargado exitosamente: {destination}")
            else:
                self.stats['failed_downloads'] += 1
                
        except Exception as e:
            self.logger.error(f"Error descargando producto: {e}")
            self.stats['failed_downloads'] += 1
    
    def _download_file_with_retry(self, url: str, destination: Path) -> bool:
        """Descargar archivo con reintentos"""
        for attempt in range(self.config.max_retries):
            try:
                response = requests.get(
                    url,
                    auth=(self.username, self.password),
                    stream=True,
                    timeout=300
                )
                response.raise_for_status()
                
                # Escribir archivo
                with open(destination, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                return True
                
            except Exception as e:
                self.logger.warning(f"Intento {attempt + 1} fallido para {url}: {e}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(2 ** attempt)  # Backoff exponencial
                else:
                    self.logger.error(f"Falló descarga después de {self.config.max_retries} intentos: {url}")
                    
        return False
    
    def _log_final_stats(self):
        """Registrar estadísticas finales"""
        self.logger.info("=== Estadísticas Finales ===")
        self.logger.info(f"Total peticiones: {self.stats['total_requests']}")
        self.logger.info(f"Descargas exitosas: {self.stats['successful_downloads']}")
        self.logger.info(f"Descargas fallidas: {self.stats['failed_downloads']}")
        self.logger.info(f"Archivos existentes omitidos: {self.stats['skipped_existing']}")
        self.logger.info(f"Total errores: {len(self.stats['errors'])}")
        
        if self.stats['errors']:
            self.logger.info("Errores detallados:")
            for error in self.stats['errors'][:10]:  # Mostrar solo primeros 10
                self.logger.error(f"  - {error}")


# Funciones de conveniencia para uso simple
def download_earthcare_products(collection: str,
                               products: Union[str, List[str]],
                               csv_path: str,
                               baseline: str = "BA",
                               download_directory: str = "./downloads",
                               credentials_file: Optional[str] = None,
                               username: Optional[str] = None,
                               password: Optional[str] = None) -> Dict:
    """
    Función de conveniencia para descargar productos EarthCARE.
    
    Args:
        collection: Colección de EarthCARE
        products: Producto(s) a descargar
        csv_path: Ruta del archivo CSV con overpasses
        baseline: Baseline a usar (default: BA)
        download_directory: Directorio de descarga
        credentials_file: Archivo TOML con credenciales
        username: Usuario OADS (si no se usa archivo de credenciales)
        password: Contraseña OADS (si no se usa archivo de credenciales)
        
    Returns:
        Diccionario con estadísticas de descarga
    """
    if isinstance(products, str):
        products = [products]
    
    config = DownloadConfig(
        collection=collection,
        products=products,
        baseline=baseline,
        download_directory=download_directory,
        credentials_file=credentials_file,
        username=username,
        password=password
    )
    
    downloader = EarthCAREDownloader(config)
    return downloader.download_from_csv(csv_path)


if __name__ == "__main__":
    # Ejemplo de uso
    config = DownloadConfig(
        collection="EarthCAREL2InstChecked",
        products=["ATL_ALD_2A"],
        baseline="BA",
        download_directory="./earthcare_downloads",
        credentials_file="oads_credentials.toml"
    )
    
    downloader = EarthCAREDownloader(config)
    stats = downloader.download_from_csv("combined_sorted_overpasses_20240810_20250731.csv")