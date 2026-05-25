# Conversión de Archivos Tabulares a Shapefile y GeoJSON

## Resumen

Script en Python que convierte archivos tabulares (`.csv`, `.txt`, `.xlsx`, `.xls`) con columnas de coordenadas geográficas a formatos espaciales **Shapefile** (`.shp`) y **GeoJSON** (`.geojson`), asignando automáticamente el sistema de coordenadas WGS84 (EPSG:4326).

El script es interactivo y continuo: permite procesar múltiples carpetas sin reiniciar, refresca las subcarpetas en cada iteración, detecta automáticamente el separador y las columnas de coordenadas, y sobrescribe archivos existentes.

## Requisitos

- Python 3.12+
- `uv` como gestor de ambiente
- Librerías: `geopandas`, `pandas`, `shapely`, `openpyxl`

```bash
uv pip install -r requirements.txt
```

## Ejecución

```bash
uv run Proceso_conversion_GD/geospatial/csv_xlx_to_shape.py
```

## Flujo del proceso

```
┌─────────────────────────────────────────────┐
│  1. Solicitar ruta de carpeta principal     │
│     (cualquier ruta absoluta o relativa)    │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│  2. Listar contenido de la carpeta:         │
│     - Opción 0: trabajar aquí (si tiene     │
│       archivos válidos directamente)        │
│     - Opciones 1-N: subcarpetas             │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│  3. Detectar archivos válidos               │
│     (.csv, .txt, .xlsx, .xls)               │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│  4. Confirmar conversión (s/n)              │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│  5. Crear carpetas de salida:               │
│     - shape_[nombre_carpeta]                │
│     - geojson_[nombre_carpeta]              │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│  6. Por cada archivo:                       │
│     a. Detectar separador (,  ;  \t)        │
│     b. Leer datos con quoting correcto      │
│     c. Eliminar duplicados (todas cols)     │
│     d. Mostrar únicos vs duplicados         │
│     e. Detectar columnas lat/lon            │
│     f. Crear geometría de puntos            │
│     g. Sobrescribir archivos existentes     │
│     h. Exportar a .shp y .geojson           │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│  7. Generar log_errores.txt (si aplica)     │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│  8. Mostrar resumen final en consola        │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│  9. Menú: otra subcarpeta / cambiar         │
│     carpeta principal / salir               │
└─────────────────────────────────────────────┘
```

## Deduplicación automática

Antes de convertir, el script elimina registros donde **todas las columnas son idénticas**. En consola muestra:

```
  📄 Procesando: comparendos_2023.csv
    📊 Registros leídos: 61680 | Únicos: 15420 | Duplicados eliminados: 46260
```

Si no hay duplicados:

```
  📄 Procesando: accidentes_2024.xlsx
    📊 Registros leídos: 3200 (sin duplicados)
```

Solo los registros únicos se exportan a los archivos de salida.

### Reporte de duplicados

Se genera un archivo `log_errores.txt` con el detalle de duplicados eliminados por archivo:

```
REPORTE DE CONVERSIÓN ESPACIAL
Fecha: 2026-05-25 14:30:00
======================================================================

REGISTROS DUPLICADOS ELIMINADOS:
----------------------------------------
  comparendos_2023.csv: 46260 duplicados eliminados (de 61680 → 15420 únicos)
  accidentes_2024.xlsx: 50 duplicados eliminados (de 3250 → 3200 únicos)

ERRORES:
----------------------------------------
  1. No se detectaron coordenadas: archivo_sin_coords.txt
```

## Detección automática de separador

El script analiza la primera línea del archivo (header) ignorando contenido entre comillas dobles para determinar el separador real:

| Separador | Ejemplo |
|-----------|---------|
| Coma `,` | `"campo1","campo2","campo3"` |
| Punto y coma `;` | `campo1;campo2;campo3` |
| Tabulador `\t` | `campo1\tcampo2\tcampo3` |

Los archivos con campos entrecomillados (`"valor con, coma"`) se manejan correctamente sin confundir comas internas con separadores.

## Detección automática de columnas

El script busca coordenadas en dos formatos:

### Formato 1: Columnas lat/lon separadas

Busca coincidencias (sin importar mayúsculas/minúsculas) con estos nombres:

| Coordenada | Nombres aceptados |
|------------|-------------------|
| Latitud | latitud, lat, latitude, y |
| Longitud | longitud, lon, long, longitude, lng, x |

### Formato 2: Columna de geometría WKT

Si no encuentra columnas lat/lon, busca una columna con geometría en formato WKT:

| Columna detectada | Ejemplo de contenido |
|-------------------|---------------------|
| geometry, geom, wkt, the_geom, shape | `POINT (1066557.6 858049.9)` |

**Reproyección automática:** Si las coordenadas son planas (valores > 10.000), el script detecta que son MAGNA-SIRGAS y reproyecta automáticamente a WGS84:

- Coordenadas X entre 1.000.000 y 1.200.000 → EPSG:3115 (Colombia Oeste / Cali)
- Otras coordenadas planas → EPSG:3116 (Colombia Bogotá)

```
  📄 Procesando: estaciones_mecal.csv
    Geometría WKT detectada en columna: 'geometry'
    🌐 Coordenadas planas detectadas → CRS origen: EPSG:3115
    🌐 Reproyectado a WGS84 (EPSG:4326)
    ✓ Convertido exitosamente (45 registros)
```

## Codificaciones soportadas

Para archivos `.csv` y `.txt`, el script intenta leer con las siguientes codificaciones en orden:

1. UTF-8
2. Latin-1
3. CP1252 (Windows)

## Sobrescritura de archivos

El script **siempre sobrescribe** archivos de salida existentes. Antes de exportar:
- Elimina archivos Shapefile previos (`.shp`, `.shx`, `.dbf`, `.prj`, `.cpg`, `.fix`)
- Elimina el GeoJSON previo

Esto garantiza que no se acumulen datos de ejecuciones anteriores.

## Estructura de carpetas generada

```
Carpeta_Principal/
├── Subcarpeta_Seleccionada/
│   ├── archivo1.csv
│   ├── archivo2.xlsx
│   ├── archivo3.txt
│   ├── shape_Subcarpeta_Seleccionada/      ← Shapefiles
│   │   ├── archivo1.shp (+ .shx, .dbf, .prj, .cpg)
│   │   ├── archivo2.shp
│   │   └── archivo3.shp
│   ├── geojson_Subcarpeta_Seleccionada/    ← GeoJSON
│   │   ├── archivo1.geojson
│   │   ├── archivo2.geojson
│   │   └── archivo3.geojson
│   └── log_errores.txt                     ← Solo si hubo errores
```

## Ejemplo de uso

```
======================================================================
  CONVERSIÓN DE ARCHIVOS TABULARES A SHAPEFILE Y GEOJSON
======================================================================

📂 Ingresa la ruta de la carpeta principal (o 'salir' para terminar)
   (puede ser ruta absoluta o relativa al directorio actual)
   > C:\Users\Jorge\Documents\GOBIERNO_DE_DATOS\Data_Steward

✅ Carpeta encontrada: C:\Users\Jorge\Documents\GOBIERNO_DE_DATOS\Data_Steward

📁 Subcarpetas encontradas en 'Data_Steward':

   1. Observatorio_Seguridad_2026
   2. Catastro_2025
   3. Movilidad_datos

   Selecciona el número de la carpeta (1-3)
   o escribe 'cambiar' para otra carpeta principal, 'salir' para terminar:
   > 1

✅ Carpeta seleccionada: Observatorio_Seguridad_2026

📄 Se encontraron 5 archivos para procesar:
   - comparendos_2023.csv (.csv)
   - accidentes_2024.xlsx (.xlsx)
   - puntos_control.txt (.txt)

¿Deseas continuar con la conversión? (s/n)
   > s

----------------------------------------------------------------------
Iniciando conversión...

  📄 Procesando: comparendos_2023.csv
    📊 Registros leídos: 15420 (sin duplicados)
    Coordenadas detectadas: lat='lat', lon='lon'
    ✓ Convertido exitosamente (15420 registros)

  📄 Procesando: accidentes_2024.xlsx
    📊 Registros leídos: 3250 | Únicos: 3200 | Duplicados eliminados: 50
    Coordenadas detectadas: lat='LATITUD', lon='LONGITUD'
    ✓ Convertido exitosamente (3200 registros)

======================================================================
  RESUMEN DE CONVERSIÓN
======================================================================
  📊 Total de archivos encontrados:  5
  ✅ Convertidos exitosamente:        4
  ❌ Archivos con errores:            1
  📍 Total de registros procesados:   22150
======================================================================

----------------------------------------------------------------------
  ¿Qué deseas hacer ahora?
   1. Procesar otra subcarpeta (misma carpeta principal)
   2. Cambiar carpeta principal
   3. Salir
   > 1
```

## Navegación interactiva

El script se mantiene activo hasta que el usuario decida salir:

| Acción | Cómo |
|--------|------|
| Procesar otra subcarpeta | Opción `1` en el menú final |
| Cambiar carpeta principal | Opción `2` o escribir `cambiar` |
| Salir | Opción `3` o escribir `salir` / `exit` / `q` en cualquier momento |

Las subcarpetas se **refrescan** en cada iteración, detectando carpetas nuevas o eliminadas sin reiniciar el script.

## Manejo de errores

El script NO se detiene ante errores. Si un archivo:
- Está vacío o corrupto
- No tiene columnas de coordenadas reconocibles
- Tiene coordenadas no numéricas
- Tiene líneas malformadas (se saltan con `on_bad_lines="skip"`)

Se registra en `log_errores.txt` y continúa con el siguiente archivo.

## Notas técnicas

- El formato GeoJSON conserva todos los nombres de columna completos y todos los atributos.
- El formato Shapefile tiene limitación de 10 caracteres en nombres de columna. El script trunca automáticamente y avisa cuáles se truncaron.
- Los archivos Excel con múltiples hojas se concatenan automáticamente.
- Los registros con coordenadas nulas o no numéricas se filtran automáticamente antes de la conversión.
- Los archivos de salida conservan el nombre original, solo cambia la extensión.
- Archivos CSV con campos entrecomillados (`"campo"`) se parsean correctamente.
- Se hace `reset_index()` antes de exportar para evitar problemas con índices.

## Librerías del ambiente

Ambiente: Python 3.12.13

| Paquete | Versión | Función |
|---------|---------|---------|
| geopandas | 1.1.3 | Lectura/escritura de formatos geoespaciales |
| pandas | 3.0.2 | Lectura de archivos tabulares |
| shapely | 2.1.2 | Creación de geometrías (Point) |
| pyproj | 3.7.2 | Manejo de sistemas de coordenadas (dependencia de geopandas) |
| pyogrio | 0.12.1 | Motor de I/O geoespacial (dependencia de geopandas) |
| openpyxl | 3.1.5 | Lectura de archivos Excel (.xlsx) |
| numpy | 2.4.4 | Operaciones numéricas (dependencia de pandas) |
