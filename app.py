#!/usr/bin/env python3
"""
Servidor Flask para procesar CSVs y ejecutar descargas masivas.
Integra tu código Python existente con la interfaz web.
"""

from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
import csv
import json
import os
import tempfile
import zipfile
import io
import requests
import threading
import time
import uuid
from urllib.parse import urlparse
from pathlib import Path
import toml
from dataclasses import dataclass
import toml
from dataclasses import dataclass
import logging
from earthcare_downloader import EarthCAREDownloader, DownloadConfig
from earthcare_downloader import EarthCAREDownloader, DownloadConfig

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Permitir peticiones desde el frontend

# Directorio temporal para archivos
TEMP_DIR = Path("temp_downloads")
TEMP_DIR.mkdir(exist_ok=True)

# Estado de trabajos en progreso
jobs_status = {}

class EarthCAREProcessor:
    """Clase que encapsula la lógica de descarga EarthCARE."""
    
    def __init__(self, job_id, collection, products, baseline, job_dir):
        self.job_id = job_id
        self.collection = collection
        self.products = products
        self.baseline = baseline
        self.job_dir = Path(job_dir)
        self.status = {
            'total': 0,
            'completed': 0,
            'errors': [],
            'current_file': '',
            'finished': False,
            'collection': collection,
            'baseline': baseline,
            'products': products
        }
        jobs_status[job_id] = self.status
    
    def process_earthcare_csv(self, csv_path):
        """Procesar CSV usando EarthCARE downloader"""
        try:
            # Verificar credenciales
            credentials_file = Path('oads_credentials.toml')
            if not credentials_file.exists():
                # Crear archivo de credenciales ejemplo si no existe
                self._create_default_credentials()
                raise Exception('Credentials file not found. Please configure oads_credentials.toml')
            
            # Configurar EarthCARE downloader
            download_dir = self.job_dir / 'earthcare_downloads'
            
            config = DownloadConfig(
                collection=self.collection,
                products=self.products,
                baseline=self.baseline,
                download_directory=str(download_dir),
                credentials_file=str(credentials_file),
                max_retries=3,
                time_tolerance_minutes=11,
                override_existing=False,
                log_file=f'earthcare_{self.job_id}.log'
            )
            
            # Crear descargador
            downloader = EarthCAREDownloader(config)
            
            # Estimar total desde CSV
            import pandas as pd
            df = pd.read_csv(csv_path)
            self.status['total'] = len(df) * len(self.products)
            
            self.status['current_file'] = f'Initializing EarthCARE downloader...'
            
            # Ejecutar descarga con monitoreo personalizado
            stats = self._download_with_monitoring(downloader, csv_path)
            
            # Crear paquete resultado
            self._create_earthcare_result_package(download_dir, stats)
            
            self.status['finished'] = True
            self.status['current_file'] = 'Download completed'
            
        except Exception as e:
            self.status['errors'].append({'error': str(e)})
            self.status['finished'] = True
            self.status['current_file'] = f'Error: {str(e)}'
            logger.error(f'EarthCARE processing error: {e}')
    
    def _create_default_credentials(self):
        """Crear archivo de credenciales por defecto"""
        default_creds = '''
# EarthCARE OADS Credentials
# Please update with your actual credentials

[credentials]
username = "your_email@example.com"
password = "your_password"

[settings]
max_retries = 3
time_tolerance_minutes = 11
'''
        with open('oads_credentials.toml', 'w') as f:
            f.write(default_creds)
    
    def _download_with_monitoring(self, downloader, csv_path):
        """Ejecutar descarga con monitoreo de progreso"""
        # Monkey patch para monitoreo de progreso
        original_download_method = downloader._download_product_for_datetime
        
        def monitored_download(*args, **kwargs):
            product = args[0] if args else 'Unknown'
            date_str = args[1] if len(args) > 1 else 'Unknown'
            
            self.status['current_file'] = f'Downloading {product} for {date_str}'
            self.status['completed'] += 1
            
            return original_download_method(*args, **kwargs)
        
        downloader._download_product_for_datetime = monitored_download
        
        # Ejecutar descarga
        return downloader.download_from_csv(csv_path)
    
    def _create_earthcare_result_package(self, download_dir, stats):
        """Crear paquete ZIP con resultados EarthCARE"""
        zip_path = TEMP_DIR / f"{self.job_id}_earthcare_result.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Añadir archivos descargados
            if download_dir.exists():
                for file_path in download_dir.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(download_dir)
                        zipf.write(file_path, arcname)
            
            # Añadir log de descarga
            log_file = download_dir / f'earthcare_{self.job_id}.log'
            if log_file.exists():
                zipf.write(log_file, 'download_log.txt')
            
            # Crear resumen de descarga
            summary = self._create_download_summary(stats)
            zipf.writestr('download_summary.txt', summary)
        
        return zip_path
    
    def _create_download_summary(self, stats):
        """Crear resumen de la descarga"""
        summary_lines = [
            "EarthCARE Download Summary",
            "=" * 50,
            f"Job ID: {self.job_id}",
            f"Collection: {self.collection}",
            f"Baseline: {self.baseline}",
            f"Products: {', '.join(self.products)}",
            f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "Statistics:",
            f"- Total requests: {stats.get('total_requests', 0)}",
            f"- Successful downloads: {stats.get('successful_downloads', 0)}",
            f"- Failed downloads: {stats.get('failed_downloads', 0)}",
            f"- Skipped existing: {stats.get('skipped_existing', 0)}",
            ""
        ]
        
        if stats.get('errors'):
            summary_lines.append("Errors:")
            for error in stats['errors'][:20]:  # Primeros 20 errores
                summary_lines.append(f"- {error}")
        
        return "\n".join(summary_lines)
    """Clase que encapsula la lógica de descarga EarthCARE."""
    
    def __init__(self, job_id, collection, products, baseline, job_dir):
        self.job_id = job_id
        self.collection = collection
        self.products = products
        self.baseline = baseline
        self.job_dir = Path(job_dir)
        self.status = {
            'total': 0,
            'completed': 0,
            'errors': [],
            'current_file': '',
            'finished': False,
            'collection': collection,
            'baseline': baseline,
            'products': products
        }
        jobs_status[job_id] = self.status
    
    def process_earthcare_csv(self, csv_path):
        """Procesar CSV usando EarthCARE downloader"""
        try:
            # Verificar credenciales
            credentials_file = Path('oads_credentials.toml')
            if not credentials_file.exists():
                # Crear archivo de credenciales ejemplo si no existe
                self._create_default_credentials()
                raise Exception('Credentials file not found. Please configure oads_credentials.toml')
            
            # Configurar EarthCARE downloader
            download_dir = self.job_dir / 'earthcare_downloads'
            
            config = DownloadConfig(
                collection=self.collection,
                products=self.products,
                baseline=self.baseline,
                download_directory=str(download_dir),
                credentials_file=str(credentials_file),
                max_retries=3,
                time_tolerance_minutes=11,
                override_existing=False,
                log_file=f'earthcare_{self.job_id}.log'
            )
            
            # Crear descargador
            downloader = EarthCAREDownloader(config)
            
            # Estimar total desde CSV
            import pandas as pd
            df = pd.read_csv(csv_path)
            self.status['total'] = len(df) * len(self.products)
            
            self.status['current_file'] = f'Initializing EarthCARE downloader...'
            
            # Ejecutar descarga con monitoreo personalizado
            stats = self._download_with_monitoring(downloader, csv_path)
            
            # Crear paquete resultado
            self._create_earthcare_result_package(download_dir, stats)
            
            self.status['finished'] = True
            self.status['current_file'] = 'Download completed'
            
        except Exception as e:
            self.status['errors'].append({'error': str(e)})
            self.status['finished'] = True
            self.status['current_file'] = f'Error: {str(e)}'
            logger.error(f'EarthCARE processing error: {e}')
    
    def _create_default_credentials(self):
        """Crear archivo de credenciales por defecto"""
        default_creds = '''
# EarthCARE OADS Credentials
# Please update with your actual credentials

[credentials]
username = "your_email@example.com"
password = "your_password"

[settings]
max_retries = 3
time_tolerance_minutes = 11
'''
        with open('oads_credentials.toml', 'w') as f:
            f.write(default_creds)
    
    def _download_with_monitoring(self, downloader, csv_path):
        """Ejecutar descarga con monitoreo de progreso"""
        # Monkey patch para monitoreo de progreso
        original_download_method = downloader._download_product_for_datetime
        
        def monitored_download(*args, **kwargs):
            product = args[0] if args else 'Unknown'
            date_str = args[1] if len(args) > 1 else 'Unknown'
            
            self.status['current_file'] = f'Downloading {product} for {date_str}'
            self.status['completed'] += 1
            
            return original_download_method(*args, **kwargs)
        
        downloader._download_product_for_datetime = monitored_download
        
        # Ejecutar descarga
        return downloader.download_from_csv(csv_path)
    
    def _create_earthcare_result_package(self, download_dir, stats):
        """Crear paquete ZIP con resultados EarthCARE"""
        zip_path = TEMP_DIR / f"{self.job_id}_earthcare_result.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Añadir archivos descargados
            if download_dir.exists():
                for file_path in download_dir.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(download_dir)
                        zipf.write(file_path, arcname)
            
            # Añadir log de descarga
            log_file = download_dir / f'earthcare_{self.job_id}.log'
            if log_file.exists():
                zipf.write(log_file, 'download_log.txt')
            
            # Crear resumen de descarga
            summary = self._create_download_summary(stats)
            zipf.writestr('download_summary.txt', summary)
        
        return zip_path
    
    def _create_download_summary(self, stats):
        """Crear resumen de la descarga"""
        summary_lines = [
            "EarthCARE Download Summary",
            "=" * 50,
            f"Job ID: {self.job_id}",
            f"Collection: {self.collection}",
            f"Baseline: {self.baseline}",
            f"Products: {', '.join(self.products)}",
            f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "Statistics:",
            f"- Total requests: {stats.get('total_requests', 0)}",
            f"- Successful downloads: {stats.get('successful_downloads', 0)}",
            f"- Failed downloads: {stats.get('failed_downloads', 0)}",
            f"- Skipped existing: {stats.get('skipped_existing', 0)}",
            ""
        ]
        
        if stats.get('errors'):
            summary_lines.append("Errors:")
            for error in stats['errors'][:20]:  # Primeros 20 errores
                summary_lines.append(f"- {error}")
        
        return "\n".join(summary_lines)

@app.route('/')
def index():
    """Sirve la página principal."""
    return send_file('index.html')

@app.route('/process-csv', methods=['POST'])
def process_csv():
    """Endpoint principal para procesar CSV EarthCARE y iniciar descargas."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No CSV file found'}), 400
        
        csv_file = request.files['file']
        if csv_file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not csv_file.filename.endswith('.csv'):
            return jsonify({'error': 'Only CSV files are allowed'}), 400
        
        # Obtener configuración EarthCARE del frontend
        collection = request.form.get('collection', 'OPER')
        baseline = request.form.get('baseline', 'B01')
        
        # Obtener productos seleccionados de checkboxes
        products = []
        for key, value in request.form.items():
            if key.startswith('product_') and value == 'on':
                product_code = key.replace('product_', '')
                products.append(product_code)
        
        if not products:
            return jsonify({'error': 'Please select at least one product'}), 400
        
        # Guardar CSV temporalmente
        job_id = str(uuid.uuid4())[:8]
        job_dir = TEMP_DIR / job_id
        job_dir.mkdir(exist_ok=True)
        
        csv_path = job_dir / 'input.csv'
        csv_file.save(csv_path)
        
        logger.info(f'EarthCARE Job {job_id}: Starting - Collection: {collection}, Baseline: {baseline}, Products: {products}')
        
        # Crear procesador EarthCARE
        processor = EarthCAREProcessor(job_id, collection, products, baseline, str(job_dir))
        
        # Iniciar procesamiento en hilo separado
        def process_job():
            try:
                processor.process_earthcare_csv(str(csv_path))
            except Exception as e:
                logger.error(f"Error in EarthCARE job {job_id}: {str(e)}")
                processor.status['errors'].append({'error': f'General error: {str(e)}'})
                processor.status['finished'] = True
        
        thread = threading.Thread(target=process_job)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'job_id': job_id,
            'collection': collection,
            'baseline': baseline,
            'products': products,
            'message': 'EarthCARE processing started',
            'status_url': f'/status/{job_id}'
        })
        
    except Exception as e:
        logger.error(f"Error in process_csv: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/job-status/<job_id>')
def job_status(job_id):
    """Obtiene el estado actual de un job."""
    if job_id not in jobs_status:
        return jsonify({'error': 'Job no encontrado'}), 404
    
    return jsonify(jobs_status[job_id])

@app.route('/download-result/<job_id>')
def download_result(job_id):
    """Descarga el resultado (ZIP) de un job completado."""
    if job_id not in jobs_status:
        return jsonify({'error': 'Job no encontrado'}), 404
    
    if not jobs_status[job_id]['finished']:
        return jsonify({'error': 'Job aún no completado'}), 400
    
    zip_path = TEMP_DIR / f"{job_id}_result.zip"
    
    if not zip_path.exists():
        return jsonify({'error': 'Archivo de resultado no encontrado'}), 404
    
    return send_file(
        zip_path,
        as_attachment=True,
        download_name=f'descarga_masiva_{job_id[:8]}.zip',
        mimetype='application/zip'
    )

# Servir archivos estáticos (CSS, JS, imágenes)
@app.route('/<path:filename>')
def static_files(filename):
    """Sirve archivos estáticos."""
    try:
        return send_file(filename)
    except:
        return "Archivo no encontrado", 404

def cleanup_old_files():
    """Limpia archivos temporales antiguos (más de 1 hora)."""
    current_time = time.time()
    for item in TEMP_DIR.iterdir():
        if item.stat().st_mtime < current_time - 3600:  # 1 hora
            try:
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    import shutil
                    shutil.rmtree(item)
                logger.info(f"Limpiado archivo temporal: {item}")
            except Exception as e:
                logger.error(f"Error limpiando {item}: {e}")

def start_cleanup_timer():
    """Inicia timer para limpiar archivos temporales."""
    cleanup_old_files()
    threading.Timer(1800, start_cleanup_timer).start()  # Cada 30 minutos

if __name__ == '__main__':
    print("🚀 Iniciando servidor Flask para descargas masivas...")
    print("📁 Directorio temporal:", TEMP_DIR.absolute())
    print("🌐 Servidor disponible en: http://localhost:5000")
    print("\n📋 Para usar:")
    print("1. Abre http://localhost:5000 en tu navegador")
    print("2. Sube un CSV con URLs en la primera columna o columna 'url'")
    print("3. Haz clic en 'Procesar CSV y descargar'")
    print("4. Espera a que termine y descarga el ZIP resultado")
    
    start_cleanup_timer()
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)