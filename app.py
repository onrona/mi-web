#!/usr/bin/env python3
"""
Servidor Flask para procesar CSVs y ejecutar descargas masivas.
Integra tu código Python existente con la interfaz web.
"""

from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
import csv
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
import logging

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

class DownloadProcessor:
    """Clase que encapsula la lógica de descarga masiva."""
    
    def __init__(self, job_id):
        self.job_id = job_id
        self.status = {
            'total': 0,
            'completed': 0,
            'errors': [],
            'current_file': '',
            'finished': False
        }
        jobs_status[job_id] = self.status
    
    def parse_csv_content(self, csv_content):
        """
        Parsea el contenido del CSV y extrae las URLs.
        Adapta este método según el formato de tu CSV.
        """
        urls = []
        csv_reader = csv.reader(io.StringIO(csv_content))
        
        # Leer primera línea para detectar si hay header
        first_row = next(csv_reader, None)
        if not first_row:
            return urls
        
        # Buscar columna de URL (case insensitive)
        header_map = {col.lower(): idx for idx, col in enumerate(first_row)}
        url_col = None
        
        for possible_name in ['url', 'link', 'enlace', 'archivo', 'file']:
            if possible_name in header_map:
                url_col = header_map[possible_name]
                break
        
        # Si no encontramos header, asumir que la primera columna son URLs
        if url_col is None:
            urls.append(first_row[0].strip())
            url_col = 0
        
        # Procesar resto de filas
        for row in csv_reader:
            if len(row) > url_col and row[url_col].strip():
                urls.append(row[url_col].strip())
        
        return [url for url in urls if url and ('http' in url or url.endswith(('.pdf', '.zip', '.doc', '.xlsx', '.txt')))]
    
    def download_file(self, url, session, timeout=30):
        """
        Descarga un archivo individual.
        Aquí puedes integrar tu lógica Python existente.
        """
        try:
            # Determinar nombre del archivo
            parsed = urlparse(url)
            filename = os.path.basename(parsed.path) or 'download'
            if '.' not in filename:
                filename += '.file'
            
            # Realizar descarga
            response = session.get(url, timeout=timeout, stream=True)
            response.raise_for_status()
            
            # Guardar archivo
            file_path = TEMP_DIR / self.job_id / filename
            file_path.parent.mkdir(exist_ok=True)
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return {'success': True, 'filename': filename, 'path': file_path}
            
        except Exception as e:
            logger.error(f"Error descargando {url}: {str(e)}")
            return {'success': False, 'error': str(e), 'url': url}
    
    def process_downloads(self, urls):
        """
        Procesa todas las descargas.
        Integra aquí tu código Python existente.
        """
        self.status['total'] = len(urls)
        self.status['completed'] = 0
        self.status['errors'] = []
        
        # Crear directorio temporal para este job
        job_dir = TEMP_DIR / self.job_id
        job_dir.mkdir(exist_ok=True)
        
        downloaded_files = []
        
        # Sesión para reutilizar conexiones
        with requests.Session() as session:
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            for i, url in enumerate(urls):
                self.status['current_file'] = url
                self.status['completed'] = i
                
                logger.info(f"Descargando {i+1}/{len(urls)}: {url}")
                
                result = self.download_file(url, session)
                
                if result['success']:
                    downloaded_files.append(result)
                else:
                    self.status['errors'].append({
                        'url': result['url'],
                        'error': result['error']
                    })
                
                # Pequeña pausa para no sobrecargar servidores
                time.sleep(0.1)
        
        self.status['completed'] = len(urls)
        self.status['finished'] = True
        
        return self.create_result_package(downloaded_files)
    
    def create_result_package(self, downloaded_files):
        """Crea un ZIP con todos los archivos descargados + reporte de errores."""
        zip_path = TEMP_DIR / f"{self.job_id}_result.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Añadir archivos descargados
            for file_info in downloaded_files:
                if file_info['path'].exists():
                    zipf.write(file_info['path'], file_info['filename'])
            
            # Crear reporte de errores si hay errores
            if self.status['errors']:
                error_report = []
                error_report.append("REPORTE DE ERRORES DE DESCARGA")
                error_report.append("=" * 50)
                error_report.append(f"Fecha: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                error_report.append(f"Total URLs: {self.status['total']}")
                error_report.append(f"Exitosas: {len(downloaded_files)}")
                error_report.append(f"Errores: {len(self.status['errors'])}")
                error_report.append("")
                
                for error in self.status['errors']:
                    error_report.append(f"URL: {error['url']}")
                    error_report.append(f"Error: {error['error']}")
                    error_report.append("-" * 30)
                
                zipf.writestr("errores_descarga.txt", "\n".join(error_report))
        
        return zip_path

@app.route('/')
def index():
    """Sirve la página principal."""
    return send_file('index.html')

@app.route('/process-csv', methods=['POST'])
def process_csv():
    """Endpoint principal para procesar CSV y iniciar descargas."""
    try:
        if 'csv' not in request.files:
            return jsonify({'error': 'No se encontró archivo CSV'}), 400
        
        csv_file = request.files['csv']
        if csv_file.filename == '':
            return jsonify({'error': 'No se seleccionó archivo'}), 400
        
        # Leer contenido del CSV
        csv_content = csv_file.read().decode('utf-8')
        
        # Crear job único
        job_id = str(uuid.uuid4())
        processor = DownloadProcessor(job_id)
        
        # Parsear URLs del CSV
        urls = processor.parse_csv_content(csv_content)
        
        if not urls:
            return jsonify({'error': 'No se encontraron URLs válidas en el CSV'}), 400
        
        # Iniciar procesamiento en hilo separado
        def process_job():
            try:
                processor.process_downloads(urls)
            except Exception as e:
                logger.error(f"Error en job {job_id}: {str(e)}")
                processor.status['errors'].append({'error': f'Error general: {str(e)}'})
                processor.status['finished'] = True
        
        thread = threading.Thread(target=process_job)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'job_id': job_id,
            'total_urls': len(urls),
            'message': 'Procesamiento iniciado'
        })
        
    except Exception as e:
        logger.error(f"Error en process_csv: {str(e)}")
        return jsonify({'error': f'Error del servidor: {str(e)}'}), 500

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