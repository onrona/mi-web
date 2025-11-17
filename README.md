# EarthCARE Web Downloader

Sistema web para descargar datos satelitales de EarthCARE desde OADS (Optical Science Data Archive).

## Características

- **Interfaz web intuitiva** con tema oscuro
- **Selección de productos** por categorías (ATLID, CPR, MSI, Combined)
- **Configuración flexible** de colección y baseline
- **Monitoreo en tiempo real** del progreso de descarga
- **Descarga automática en ZIP** con logs y resúmenes
- **Gestión de credenciales** segura mediante archivo TOML

## Instalación

1. Clona o descarga este repositorio
2. Instala las dependencias:

```bash
pip install -r requirements.txt
```

3.Configura tus credenciales OADS:

```bash
cp oads_credentials_example.toml oads_credentials.toml

```Edita `oads_credentials.toml` con tus credenciales reales.

## Uso

1. **Inicia el servidor**:
```bash
python app.py
```

2.**Abre tu navegador** en: [http://localhost:5000](http://localhost:5000)

3.**Configura la descarga**:

- Selecciona la **Colección** (OPER, RPRO, OFFL, etc.)
- Selecciona el **Baseline** (B01, B02, etc.)
- Marca los **Productos** que deseas descargar

4.**Sube tu archivo CSV**:

- El CSV debe tener una columna **datetime** con timestamps en formato ISO
- Ejemplo: **2024-06-15T12:00:00**

5.**Inicia la descarga** y monitorea el progreso en tiempo real

6.**Descarga el resultado** cuando termine (archivo ZIP)

## Formato del CSV

Tu archivo CSV debe tener al menos una columna `datetime`:

```csv
datetime
2024-06-15T12:00:00
2024-06-15T12:30:00
2024-06-15T13:00:00
```

## Productos Disponibles

### ATLID (Atmospheric Lidar)

- `ATL_L1B_HR`: ATLID Level 1B High Resolution
- `ATL_L1B_LR`: ATLID Level 1B Low Resolution
- `ATL_L2A_AER`: ATLID Level 2A Aerosol
- `ATL_L2A_CLD`: ATLID Level 2A Cloud
- Y más...

### CPR (Cloud Profiling Radar)

- `CPR_L1A`: CPR Level 1A
- `CPR_L1B`: CPR Level 1B
- `CPR_L2A_CLD`: CPR Level 2A Cloud
- Y más...

### MSI (Multispectral Imager)

- `MSI_L1C_RAD`: MSI Level 1C Radiance
- `MSI_L2A_CLD`: MSI Level 2A Cloud
- Y más...

### Combined Products

- `COM_L2A_CLD`: Combined Level 2A Cloud
- `COM_L2A_AER`: Combined Level 2A Aerosol
- Y más...

## Archivos Generados

El sistema generará un archivo ZIP con:

- **Datos descargados**: archivos NetCDF organizados por producto
- **Log de descarga**: registro detallado del proceso
- **Resumen**: estadísticas de la descarga (éxitos/errores)

## Solución de Problemas

### Error de credenciales

- Verifica que `oads_credentials.toml` existe y tiene las credenciales correctas
- Asegúrate de que tu cuenta OADS esté activa

### Error de formato CSV

- Verifica que tu CSV tiene una columna `datetime`
- Los timestamps deben estar en formato ISO: `YYYY-MM-DDTHH:MM:SS`

### Error de productos

- Algunos productos pueden no estar disponibles para todas las fechas
- Revisa el log de descarga para detalles específicos

## Desarrollo

Este sistema integra:

- **Frontend**: HTML5/CSS3/JavaScript con tema oscuro
- **Backend**: Flask con CORS habilitado
- **Downloader**: Módulo Python personalizado para OADS
- **Monitoring**: Polling en tiempo real del progreso

## Licencia

Código desarrollado para uso científico y educativo.
