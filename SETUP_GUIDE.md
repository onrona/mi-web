# 🚀 Guía de Instalación y Uso - Descarga Masiva con Python

## 📋 ¿Qué hace esta aplicación?

Esta aplicación web permite:

- ✅ Subir un archivo CSV con URLs
- ✅ Procesar las URLs con tu código Python personalizado
- ✅ Descargar todos los archivos automáticamente
- ✅ Generar un reporte de errores para URLs que fallaron
- ✅ Descargar un ZIP con todos los resultados

## 🛠️ Instalación

### 1. Instalar dependencias Python

```bash
pip install -r requirements.txt
```

### 2. Verificar estructura de archivos

```mi-web/
├── app.py              # Servidor Flask
├── index.html          # Interfaz web
├── requirements.txt    # Dependencias Python
├── temp_downloads/     # Carpeta temporal (se crea automáticamente)
└── files/             # Archivos estáticos existentes
```

## 🚀 Cómo usar

### 1. Iniciar el servidor

```bash
python app.py
```

Verás algo como:

```🚀 Iniciando servidor Flask para descargas masivas...
📁 Directorio temporal: D:\onel\python\mi-web\temp_downloads
🌐 Servidor disponible en: http://localhost:5000
```

### 2. Abrir la aplicación web

Abre tu navegador y ve a: **[http://localhost:5000](http://localhost:5000)**

### 3. Preparar tu archivo CSV

El CSV debe tener una de estas estructuras:

**Opción A - Solo URLs (una por línea):**

```csv
https://example.com/document1.pdf
https://example.com/data.xlsx
https://example.com/report.zip
```

**Opción B - CSV con columnas (debe tener header 'url'):**

```csv
name,url,description
Doc1,https://example.com/document1.pdf,Manual técnico
Data,https://example.com/data.xlsx,Hoja de cálculo
Report,https://example.com/report.zip,Informe mensual
```

### 4. Procesar el CSV

1. Haz clic en **"Elegir archivo"** y selecciona tu CSV
2. Haz clic en **"Procesar CSV y descargar"**
3. El proceso iniciará automáticamente
4. Verás el progreso en tiempo real
5. Al finalizar, se descargará un ZIP con todos los archivos

## 🔧 Personalizar para tu código Python

### Integrar tu código existente

En `app.py`, busca la clase `DownloadProcessor` y modifica estos métodos:

```python
def parse_csv_content(self, csv_content):
    """
    🎯 PERSONALIZA AQUÍ: Adapta según tu formato CSV
    """
    # Tu lógica para extraer URLs/rutas del CSV
    pass

def download_file(self, url, session, timeout=30):
    """
    🎯 PERSONALIZA AQUÍ: Integra tu código de descarga
    """
    # Tu lógica existente para descargar archivos
    pass
```

### Ejemplo de integración

Si tienes un módulo `mi_descargador.py`:

```python
# En app.py, añadir al inicio:
import mi_descargador

# En download_file():
def download_file(self, url, session, timeout=30):
    try:
        # Usar tu código existente
        result = mi_descargador.descargar_archivo(url, timeout)
        return {'success': True, 'filename': result['filename'], 'path': result['path']}
    except Exception as e:
        return {'success': False, 'error': str(e), 'url': url}
```

## 📁 Gestión de archivos

### Archivos temporales

- Se crean en `temp_downloads/`
- Se limpian automáticamente cada 30 minutos
- Archivos más antiguos de 1 hora se eliminan

### Resultado final

- ZIP con todos los archivos descargados
- Archivo `errores_descarga.txt` con URLs que fallaron (si las hay)

## ⚠️ Limitaciones y soluciones

### CORS y restricciones

- ✅ **Solucionado**: El servidor Python no tiene restricciones CORS
- ✅ **Archivos grandes**: Se procesan por chunks, no hay límite de memoria del navegador
- ✅ **Autenticación**: Puedes añadir headers personalizados en `download_file()`

### Configuración avanzada

```python
# En app.py, puedes modificar:
CONCURRENT_DOWNLOADS = 3  # Descargas simultáneas
TIMEOUT_SECONDS = 30      # Timeout por archivo
CLEANUP_INTERVAL = 1800   # Limpieza cada 30 min
```

## 🐛 Troubleshooting

### El servidor no inicia

```bash
# Verificar Python y dependencias
python --version
pip list | grep flask
```

### "Job no encontrado"

- Reinicia el servidor: `Ctrl+C` y luego `python app.py`

### CSV no se procesa

- Verifica que tenga URLs válidas
- Asegúrate que use comas como separador
- Revisa que tenga columna 'url' o URLs en primera columna

### Archivos no se descargan

- Revisa logs en la consola del servidor
- Verifica conectividad a las URLs
- Algunos sitios bloquean descargas automáticas

## 🔄 Actualizar tu código

1. Modifica `app.py` con tu lógica
2. Reinicia el servidor: `Ctrl+C` → `python app.py`
3. Recarga la página web

## 📞 Soporte

Si necesitas ayuda integrando tu código Python específico:

1. Comparte tu código existente
2. Describe el formato de tu CSV
3. Explica qué tipo de autenticación/headers necesitas

¡La aplicación está lista para usar! 🎉
