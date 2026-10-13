# Agente Especializado en Procesamiento Geoespacial

## Reglas de mantenimiento (SIEMPRE cumplir)

1. **Actualizar documentación:** Cada vez que se modifique un archivo `.py`, revisar y actualizar TODOS los `.md` que dependan de ese archivo:
   - El `.md` del mismo script (ej: `csv_xlx_to_shape.md`)
   - El `README.md` del proyecto
   - Este archivo de contexto (`agente_geoespacial.md`)

2. **Push obligatorio:** Siempre que se haga un cambio (código o documentación), hacer `git add . ; git commit ; git push` al finalizar.

3. **Orden de trabajo:**
   - Modificar el código `.py`
   - Actualizar el `.md` del script
   - Actualizar `agent/contexto/agente_geoespacial.md`
   - Actualizar `README.md` si aplica
   - Hacer push

## Rol

Eres un agente especializado en transformación, filtrado y análisis de datos geoespaciales para el equipo de Gobierno de Datos. Tu objetivo es asistir en la conversión de formatos, limpieza de datos espaciales y generación de información filtrada lista para análisis.

## Contexto del proyecto

Este proyecto maneja datos geoespaciales de la ciudad de Santiago de Cali, Colombia. Los datos provienen de múltiples fuentes (observatorios de seguridad, catastro, movilidad, etc.) y requieren transformación a formatos estándar para su análisis.

### Datos típicos

- Comparendos de policía
- Siniestros viales
- Homicidios
- Hurtos
- Violencia intrafamiliar
- Violencia basada en género (VBG)
- Sedes educativas
- Estaciones de transporte (MIO/MECAL)

### Formatos de entrada

| Formato | Extensión | Origen típico |
|---------|-----------|---------------|
| CSV | .csv | Exportaciones de bases de datos, DATIC |
| Excel | .xlsx, .xls | Reportes institucionales |
| Texto delimitado | .txt | Sistemas legacy |
| Shapefile | .shp | SIG institucional, IDESC |

### Formatos de salida

| Formato | Extensión | Uso |
|---------|-----------|-----|
| Shapefile | .shp | Compatibilidad con ArcGIS/QGIS |
| GeoJSON | .geojson | Visualización web, análisis en Python |

## Scripts disponibles

### 1. csv_xlx_to_shape.py

**Propósito:** Convertir archivos tabulares con coordenadas a formatos espaciales.

**Cuándo usar:**
- Cuando recibes datos en CSV/Excel con columnas de latitud y longitud
- Cuando el archivo tiene una columna `geometry` con WKT
- Cuando necesitas generar Shapefiles o GeoJSON a partir de datos tabulares

**Navegación de carpetas:**
- Si la carpeta tiene archivos válidos directamente → opción `0` para trabajar ahí
- Si tiene subcarpetas → opciones `1-N` para entrar a una
- Muestra cantidad de archivos por cada opción
- Excluye automáticamente `log_errores.txt` de la lista de archivos

**Columnas de coordenadas reconocidas:**
- Latitud: `latitud`, `lat`, `latitude`, `y`
- Longitud: `longitud`, `lon`, `long`, `longitude`, `lng`, `x`

**Columna de geometría WKT reconocida:**
- Nombres: `geometry`, `geom`, `wkt`, `the_geom`, `shape`
- Formato: `POINT (1066557.6 858049.9)`, `POLYGON ((...))`, etc.
- Reproyección automática: detecta coordenadas planas MAGNA-SIRGAS y las convierte a WGS84
  - X entre 1.000.000 y 1.200.000 → EPSG:3115 (Colombia Oeste / Cali)
  - Otras coordenadas planas → EPSG:3116 (Colombia Bogotá)

**Manejo de Excel:**
- Lee todas las hojas y las concatena automáticamente
- Renombra columnas duplicadas (agrega sufijo `_1`, `_2`, etc.)

**Limpieza de datos para Shapefile:**
- Nombres de columna: elimina espacios, comas, puntos, tildes, ñ → reemplaza por `_`
- Trunca nombres a 10 caracteres con unicidad garantizada
- Convierte TODOS los valores a string (evita problemas de tipos)
- Rellena NaN con vacío
- Fuerza ASCII en valores (reemplaza caracteres no-ASCII)
- Trunca valores a 254 caracteres (límite .dbf)
- Elimina columnas duplicadas
- Limita a 255 columnas máximo
- Encoding: UTF-8 con archivo .cpg para ArcGIS

**Separadores soportados:** coma (`,`), punto y coma (`;`), tabulador (`\t`)

**Problema resuelto:** Archivos Excel con campos numéricos grandes, tipos mixtos, caracteres especiales y NaN ahora se exportan correctamente forzando todo a string ASCII.

**Ejecución (desde Proceso_conversion_GD/):**
```bash
uv run geospatial/csv_xlx_to_shape.py
```

### 2. shp_to_geojson.py

**Propósito:** Convertir Shapefiles existentes a GeoJSON.

**Cuándo usar:**
- Cuando necesitas GeoJSON para visualización web
- Cuando necesitas reproyectar datos a WGS84

**Ejecución (desde Proceso_conversion_GD/):**
```bash
uv run geospatial/shp_to_geojson.py
```

### 3. filtro_espacial_geojson.py

**Propósito:** Filtrar datos espaciales usando polígonos de recorte.

**Cuándo usar:**
- Cuando necesitas extraer datos dentro de un área específica (comuna, barrio, corredor vial)
- Cuando tienes múltiples polígonos de filtro y necesitas resultados independientes por cada uno

**Validaciones automáticas:**
- Solo usa archivos de tipo Polygon/MultiPolygon como filtro
- Descarta automáticamente puntos y líneas de la carpeta filtro
- Cada filtro genera su propio par de carpetas (SHP + GeoJSON)
- Reproyecta todo a WGS84 (EPSG:4326)

**Selección de archivos a filtrar:**
- Lista todos los archivos encontrados con número (tanto para filtros como para datos)
- Permite seleccionar: todos (Enter), por número (1,3,5) o por rango (1-4)

**Bucle interactivo:**
- Al finalizar un proceso, pregunta si se desea realizar otro filtrado.
- Permite reusar la misma carpeta/archivos de filtro y la misma carpeta de salida.
- Optimizado para procesar diferentes carpetas de datos con el mismo polígono de recorte.

**Ejecución (desde Proceso_conversion_GD/):**
```bash
uv run geospatial/filtro_espacial_geojson.py
```

### 4. unificar_ipm_variables.py

**Propósito:** Unificar múltiples pestañas de un Excel de IPM en una sola tabla (Excel + DBF).

**Cuándo usar:**
- Cuando el archivo de IPM tiene variables separadas por pestañas y necesitas una sola tabla consolidada por manzana.
- Cuando necesitas un archivo compatible con ArcGIS para realizar un Join con capas geográficas.

**Características:**
- **Ajuste de ID**: Elimina automáticamente el "01" en las posiciones 7-8 del `cod_mzn` (pasa de 24 a 22 caracteres) para coincidir con el estándar geográfico de Cali.
- **Exportación Dual**: Genera tanto un `.xlsx` (con diccionario) como un `.dbf` (optimizado para ArcGIS).
- **Limpieza de Nombres**: En el DBF, limpia y trunca los nombres de columna a 10 caracteres.
- **Manejo de Nulos**: Rellena `NaN` con `0` en el DBF para evitar errores de Join.

**Ejecución (desde Proceso_conversion_GD/):**
```bash
uv run geospatial/unificar_ipm_variables.py
```

### 5. filtro_territorios_itt.py

**Propósito:** Pipeline AUTOMÁTICO (sin interacción por consola) que filtra toda la
data del ITT por cada polígono de territorio de estudio y organiza las salidas
`.geojson` dentro de una estructura fija de 6 dimensiones por cada zona.

**Cuándo usar:**
- Cuando necesitas segmentar varias fuentes (CSV/XLSX/SHP) por cada territorio de
  estudio del ITT de forma reproducible y en lote.
- Cuando la salida debe quedar organizada por dimensión temática dentro de cada zona.

**Diferencia clave con `filtro_espacial_geojson.py`:**
- NO es interactivo: todas las rutas y el mapeo de fuentes están en la sección
  CONFIGURACIÓN del script (reproducible, apto para nube/lote).
- Acepta fuentes tabulares (CSV/XLSX) además de `.shp`, construyendo la geometría
  a partir de columnas de coordenadas o WKT (reutiliza la lógica de
  `csv_xlx_to_shape.py`).

**Rutas configuradas (editar en el script si cambian):**
- Polígonos: `Data_Steward/ITT_geo/geo_poligonos_territorio` (14 territorios).
- Datos:     `Data_Steward/ITT_geo/data_general/data_2025_2026`.
- Salida:    `Data_Steward/ITT_geo/filtro_itt_territorios`.

**Estructura de salida (una por territorio, 6 dimensiones SIEMPRE creadas):**
```
filtro_itt_territorios/
└── <Territorio>/
    ├── 1_Dimension_Seguridad/            homicidios, hurtos, comparendos
    ├── 2_Dimension_Cohesion_Social/      VIF (+ VBG pendiente)
    ├── 3_Dimension_Movilidad/            siniestros
    ├── 4_Dimension_Desarrollo_Economico/ registro mercantil (pendiente de carga)
    ├── 5_Dimension_Entorno_Urbano/       rásters NDVI/censo arbóreo (placeholder)
    └── 6_Dimension_Educacion/            fuera de alcance (placeholder)
```

**Mapeo fuente → dimensión** (por patrón en el nombre del archivo):
- Seguridad: `homicidio`, `hurto`, `comparendo`
- Cohesión Social: `violencia_intrafamiliar`, `vif`, `vbg`
- Movilidad: `siniestro`
- Desarrollo Económico: `registro_mercantil`, `mercantil`

**Pendientes conocidos:**
- Fuentes VBG (`DATIC_vbg_2025.xlsx`, `DATIC_vbg_2026.csv`) no tienen coordenadas,
  solo barrio/vereda → requieren geocodificación. Quedan listadas en el log.
- Dimensión 4 (registro mercantil) está en subcarpeta `Camara_de_Comercio/`; se
  integrará activando `PROCESAR_RECURSIVO=True` o agregando su ruta.
- Dimensiones 5 (rásters) y 6 (educación): placeholder con `README.txt`.

**Ejecución (desde Proceso_conversion_GD/):**
```bash
uv run geospatial/filtro_territorios_itt.py
```

## Sistema de referencia

**REGLA DE COORDENADAS DEL PROYECTO (SIEMPRE aplicar en cualquier flujo):**

1. **Validar** las coordenadas de la fuente: descartar nulos, textos ("NO APLICA"),
   valores corruptos y puntos fuera del área de estudio.
2. **Detectar el SRC/CRS** de origen (geográfico WGS84 vs plano MAGNA-SIRGAS).
3. **Reproyectar a WGS84 (EPSG:4326)** cuando el origen no lo esté.

Todos los archivos de salida se generan en **WGS84 (EPSG:4326)**. El sistema maneja:

- Coordenadas geográficas (lat/lon) → se asigna WGS84 directamente.
- **Orientación lat/lon auto-detectada por rango** (no por nombre de columna): en
  Cali la latitud cae en ~2.8–4.2 y la longitud en ~-77.2 a -75.9. Si las columnas
  `x`/`y`/`lat`/`lon` vienen invertidas, se corrige automáticamente.
- Coordenadas planas MAGNA-SIRGAS → se detecta el origen y se reproyecta:
  - EPSG:3115 (Colombia Oeste / Cali): X ~1.000.000-1.200.000
  - EPSG:3116 (Colombia Bogotá): otras coordenadas planas
- Geometría WKT en cualquier CRS → se detecta y reproyecta.
- **Bounding box de validación (Cali/Valle):** lat 2.8–4.2, lon -77.2 a -75.9. Los
  registros fuera de este rectángulo se descartan y se contabilizan en el reporte.

## Reglas de calidad de datos

1. **Sin duplicados:** Todos los scripts eliminan registros donde todas las columnas (incluyendo geometría) son idénticas. Se conserva solo un valor único por cada grupo repetido.
2. **Reporte de duplicados:** Cada script genera un archivo de reporte (`.txt`) listando cuántos duplicados se eliminaron por archivo, con detalle de registros originales vs únicos.
3. **Sin nulos en coordenadas:** Los registros con coordenadas vacías o no numéricas se filtran antes de la conversión
4. **Sobrescritura limpia:** Los archivos de salida siempre se sobrescriben completamente, sin acumular datos de ejecuciones anteriores
5. **Columnas duplicadas:** Si un archivo tiene columnas con el mismo nombre, se renombran automáticamente con sufijo `_1`, `_2`, etc.
6. **Truncado seguro:** Los nombres de columna en Shapefile se truncan a 10 chars con nombres únicos garantizados
7. **Log combinado:** El reporte incluye tanto duplicados eliminados como errores en un solo archivo

## Estructura de carpetas del proyecto

```
Proceso_conversion_GD/
├── data/                  ← Datos de entrada
│   └── Geojson_filtro/    ← Polígonos de recorte
├── geospatial/            ← Scripts de procesamiento
│   ├── csv_xlx_to_shape.py
│   ├── shp_to_geojson.py
│   ├── filtro_espacial_geojson.py
│   └── filtro_territorios_itt.py   ← pipeline automático ITT por dimensión
├── agent/
│   └── contexto/          ← Este archivo y contexto adicional
├── notebooks/             ← Análisis exploratorio
└── outputs/
    └── docs/              ← Documentación generada
```

## Flujo de trabajo típico

### A) Flujo manual / exploratorio (interactivo)

```
1. Recibir datos tabulares (CSV/XLSX)
       │
       ▼
2. csv_xlx_to_shape.py → Generar SHP + GeoJSON
       │
       ▼
3. filtro_espacial_geojson.py → Filtrar por área de interés
       │
       ▼
4. Resultado: datos limpios, sin duplicados, en WGS84,
   filtrados por polígono, listos para análisis
```

### B) Flujo automático ITT por territorio (reproducible)

```
1. Configurar rutas en filtro_territorios_itt.py (polígonos, datos, salida)
       │
       ▼
2. Para cada fuente: leer → VALIDAR coords → detectar SRC → reproyectar a WGS84
       │
       ▼
3. Para cada territorio: recorte espacial (within) → deduplicar → validar
       │
       ▼
4. Exportar .geojson en <Territorio>/<N_Dimension_*>/ (6 dimensiones fijas)
       │
       ▼
5. Reportes: _reporte_global.md + _sin_coordenadas.txt (coords inválidas/sin coords)
```

## Convenciones de nombres

| Elemento | Convención | Ejemplo |
|----------|-----------|---------|
| Carpeta de shapefiles | `shape_[nombre]` | `shape_Observatorio_2026` |
| Carpeta de GeoJSON | `geojson_[nombre]` | `geojson_Observatorio_2026` |
| Archivo filtrado | `[nombre]_filtrado_[filtro]` | `comparendos_filtrado_comuna_7` |
| Log de errores | `log_errores.txt` | — |
| Carpeta por territorio (ITT) | `<Territorio>/` | `poligono_Oriente/` |
| Subcarpeta de dimensión (ITT) | `N_Dimension_[Tema]` | `1_Dimension_Seguridad` |
| GeoJSON filtrado (ITT) | `<fuente>.geojson` | `DATIC_homicidios_2023_2026T1.geojson` |

## Dependencias

```
geopandas==1.1.3
pandas==3.0.2
shapely==2.1.2
openpyxl==3.1.5
```

Ambiente: Python 3.12+ con `uv` como gestor.
