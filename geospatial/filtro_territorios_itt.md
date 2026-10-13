# Filtrado Automático ITT por Territorio

## Resumen

`filtro_territorios_itt.py` es un pipeline **automático** (sin interacción por
consola) que filtra toda la data del ITT por cada polígono de territorio de
estudio y organiza las salidas `.geojson` dentro de una estructura fija de **6
dimensiones temáticas** por cada zona.

Combina dos lógicas ya existentes en el repositorio:

- Detección de coordenadas y lectura robusta de tabulares → `csv_xlx_to_shape.py`
- Recorte espacial por polígono (`sjoin within`) → `filtro_espacial_geojson.py`

A diferencia de los scripts previos, **no pide datos por consola**: todas las
rutas y el mapeo de fuentes están en la sección `CONFIGURACIÓN` del script. Esto
garantiza reproducibilidad y permite ejecutarlo en lote o en la nube.

## Características principales

1. **Automático y reproducible:** cero `input()`, todo parametrizado.
2. **Multi-formato de entrada:** CSV, TXT, XLSX, XLS y SHP.
3. **Regla de coordenadas del proyecto:**
   - **Validar** (nulos, textos tipo "NO APLICA", corruptos, fuera de área).
   - **Detectar SRC** (geográfico WGS84 vs plano MAGNA-SIRGAS).
   - **Reproyectar a WGS84 (EPSG:4326)** cuando el origen no lo esté.
4. **Auto-detección de orientación lat/lon por rango** (no por nombre de columna):
   corrige automáticamente columnas `x`/`y`/`lat`/`lon` invertidas.
5. **Validación por bounding box de Cali/Valle:** descarta coordenadas corruptas o
   fuera del área y contabiliza los descartes en el reporte.
6. **Deduplicación** por atributos + geometría.
7. **Estructura fija de 6 dimensiones** creada SIEMPRE en cada territorio.
8. **Predicado espacial según geometría:** puntos → `within`; líneas/polígonos →
   `intersects` (una vía que cruza el borde del territorio se incluye).
9. **Saneamiento de atributos** antes de exportar: columnas de tipo `object` con
   tipos mixtos u objetos no serializables (p.ej. `datetime.time`) se pasan a
   texto, evitando fallos del driver GeoJSON.
10. **Procesamiento fuente por fuente:** cada archivo se lee una vez, se filtra
    contra los 14 territorios y se libera de memoria antes del siguiente. Permite
    manejar fuentes de cientos de miles de registros sin agotar memoria.

## Configuración (editar en el script)

| Parámetro | Descripción |
|-----------|-------------|
| `RUTA_POLIGONOS` | Carpeta con los `.shp` de territorio (cada `.shp` = una zona) |
| `RUTA_DATOS` | Carpeta raíz con la data a filtrar |
| `RUTA_SALIDA` | Carpeta de salida (una subcarpeta por territorio) |
| `REGLAS_DIMENSION` | Mapeo patrón-de-nombre → dimensión (archivos de la raíz) |
| `FUENTES_EXPLICITAS` | Lista `(ruta_relativa, dimensión)` de fuentes en subcarpetas |
| `PROCESAR_RECURSIVO` | `False` = solo archivos de la raíz; `True` = incluye subcarpetas |
| `CALI_LAT_MIN/MAX`, `CALI_LON_MIN/MAX` | Bounding box de validación de coords |

### Fuentes en subcarpetas (`FUENTES_EXPLICITAS`)

Para evitar un barrido ciego que lea decenas de archivos sin coordenadas, las
fuentes anidadas se declaran una por una. Actualmente:

| Fuente | Dimensión | Geometría |
|--------|-----------|-----------|
| `Camara_de_Comercio/camara_comercio_geocodificado_13102026.csv` | 4 Desarrollo Económico | Point |
| `Observatorio_de_Infraestructura/2025_Consolidado.shp` | 5 Entorno Urbano | LineString (EPSG:6249 → WGS84) |
| `Observatorio_de_Infraestructura/2026_Consolidado_proyect.shp` | 5 Entorno Urbano | LineString |
| `Observatorio_de_Infraestructura/2024/Infraestructura_2024.shp` | 5 Entorno Urbano | LineString |
| `Educacion/.../Información geográfica sedes.shp` | 6 Educación | Point |

### Rutas actuales

- Polígonos: `Data_Steward/ITT_geo/geo_poligonos_territorio`
- Datos: `Data_Steward/ITT_geo/data_general/data_2025_2026`
- Salida: `Data_Steward/ITT_geo/filtro_itt_territorios`

## Mapeo fuente → dimensión

| Dimensión | Patrones de nombre de archivo |
|-----------|-------------------------------|
| `1_Dimension_Seguridad` | `homicidio`, `hurto`, `comparendo` |
| `2_Dimension_Cohesion_Social` | `violencia_intrafamiliar`, `vif`, `vbg` |
| `3_Dimension_Movilidad` | `siniestro` |
| `4_Dimension_Desarrollo_Economico` | `registro_mercantil`, `mercantil` |
| `5_Dimension_Entorno_Urbano` | rásters (placeholder) |
| `6_Dimension_Educacion` | fuera de alcance (placeholder) |

## Estructura de salida

```
filtro_itt_territorios/
├── <Territorio>/
│   ├── 1_Dimension_Seguridad/            <fuente>.geojson ...
│   ├── 2_Dimension_Cohesion_Social/      <fuente>.geojson ...
│   ├── 3_Dimension_Movilidad/            <fuente>.geojson ...
│   ├── 4_Dimension_Desarrollo_Economico/ (pendiente de carga)
│   ├── 5_Dimension_Entorno_Urbano/       README.txt (placeholder)
│   └── 6_Dimension_Educacion/            README.txt (placeholder)
├── _reporte_global.md       tabla territorio × dimensión × fuente × registros
└── _sin_coordenadas.txt     fuentes sin coords + descartes por validación
```

## Flujo interno

```
1. Preparar territorios: cargar polígonos (14) y crear la estructura de 6
   dimensiones en cada zona.
2. Por cada fuente de datos (una lectura, luego se libera):
     leer → VALIDAR coordenadas → detectar SRC → reproyectar a WGS84 →
     por cada territorio: recorte espacial (within/intersects según geometría) →
     deduplicar → sanear atributos → exportar .geojson en su dimensión.
3. Generar _reporte_global.md y _sin_coordenadas.txt.
```

El orden "fuente externa, territorio interno" mantiene bajo el pico de memoria:
nunca se retienen todas las fuentes a la vez (relevante con fuentes de 200k+
registros como la cámara de comercio).

## Ejecución

```bash
uv run Proceso_conversion_GD/geospatial/filtro_territorios_itt.py
```

## Estado por dimensión

- **1 Seguridad, 2 Cohesión Social, 3 Movilidad:** operativas (CSV/XLSX de DATIC y
  siniestros).
- **4 Desarrollo Económico:** operativa con `camara_comercio_geocodificado`.
- **5 Entorno Urbano:** operativa con las obras de infraestructura (LineString,
  predicado `intersects`). Los rásters NDVI / censo arbóreo siguen pendientes
  (requieren recorte raster con `rasterio`/`gdalwarp`, no vectorial).
- **6 Educación:** operativa con las sedes educativas (Point). Si un territorio no
  contiene sedes dentro del polígono, no se genera archivo para esa zona.

## Pendientes conocidos

- **Fuentes VBG** (`DATIC_vbg_2025.xlsx`, `DATIC_vbg_2026.csv`) y
  `BD Comparendos Abril - Junio 2026.xlsx`: no tienen coordenadas, solo
  barrio/dirección → requieren geocodificación. Quedan listadas en
  `_sin_coordenadas.txt`.
- **Dimensión 5 (rásters NDVI / censo arbóreo):** pendiente de un flujo de recorte
  raster aparte.

## Notas técnicas

- **Reproyección:** las coordenadas planas MAGNA-SIRGAS se detectan por magnitud
  (X ~1.000.000-1.200.000 → EPSG:3115 Cali; otras → EPSG:3116) y se reproyectan a
  WGS84. Las fuentes ITT actuales ya vienen en grados WGS84; no se reproyectan.
- **Columnas invertidas:** varias fuentes DATIC traen la latitud en la columna
  llamada `x`/`longitud` y viceversa. La orientación se decide por el rango de
  valores de Cali, no por el nombre, corrigiendo el problema automáticamente.
- **Lectura única por fuente:** cada archivo se lee y se prepara una sola vez, y
  luego se recorta contra los 14 territorios (eficiente para fuentes grandes).

## Dependencias

```
geopandas
pandas
shapely
openpyxl   (para .xlsx)
```

Ambiente: Python 3.12+ con `uv` como gestor.
