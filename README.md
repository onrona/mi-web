# Instrucciones para personalizar tu página de compartir archivos

## 📝 Cómo personalizar la información

### Paso 1: Editar información general

Abre `index.html` y busca la sección "Información General" para cambiar:

- Nombre del proyecto
- Tu nombre
- Estado del proyecto
- Información de contacto

### Paso 2: Actualizar anuncios

En la sección "Anuncios y Notas" puedes:

- Cambiar horarios de reuniones
- Actualizar fechas límite
- Agregar recordatorios importantes

### Paso 3: Añadir archivos reales

1. Coloca tus archivos en la carpeta `files/`
2. En el HTML, busca la sección "Archivos Compartidos"
3. Actualiza cada elemento `.file-item` con:
   - Nombre correcto del archivo
   - Icono apropiado (📄 para PDFs, 📊 para Excel, etc.)
   - Tamaño real del archivo
   - Nombre correcto en la función `downloadFile()`

### Paso 4: Activar descargas reales

Descomenta las líneas en la función `downloadFile()` y elimina el `alert()` de prueba.

### Paso 5: Estilizar tu página

Puedes cambiar:

- Colores en el CSS (busca los códigos de color como `#3498db`)
- Fuentes en la sección `font-family`
- Espaciado y tamaños

## 🚀 Para poner en funcionamiento

1. Coloca todos tus archivos en la carpeta `files/`
2. Abre `index.html` en cualquier navegador web
3. ¡Tu página estará lista para compartir!

## 📱 Características incluidas

- ✅ Diseño responsivo (se adapta a móviles)
- ✅ Animaciones suaves
- ✅ Iconos intuitivos
- ✅ Fácil de actualizar
- ✅ No requiere servidor especial (funciona como archivo HTML)
