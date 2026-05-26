# Proceso de Conversión - Gobierno de Datos

Conjunto de scripts Python para transformación y análisis de datos geoespaciales. Convierte archivos tabulares a formatos espaciales, realiza filtrado por polígonos y elimina duplicados automáticamente.

## Estructura del proyecto

```
Proceso_conversion_GD/
├── README.md
├── requirements.txt
├── environment.yml
├── .gitignore
│
├── data/                  ← Datos de entrada (CSV, XLSX, SHP, etc.)
│   └── Geojson_filtro/    ← Polígonos de recorte
├── notebooks/             ← Notebooks Jupyter (.ipynb)
├── notebooks_py/          ← Notebooks exportados a Python (.py)
├── agent/
│   └── contexto/          ← Archivos de contexto para el agente
├── geospatial/            ← Scripts de procesamiento geoespacial
│   ├── csv_xlx_to_shape.py
│   ├── csv_xlx_to_shape.md
│   ├── shp_to_geojson.py
│   ├── filtro_espacial_geojson.py
│   └── filtro_espacial_geojson.md
└── outputs/
    └── docs/              ← Documentación generada
```

## Scripts disponibles

### 1. `csv_xlx_to_shape.py` — Conversión tabular a espacial

Convierte archivos `.csv`, `.txt`, `.xlsx`, `.xls` con coordenadas a Shapefile y GeoJSON.

**Características:**
- Detección automática de separador (`,` `;` `\t`) ignorando contenido entre comillas
- Detección automática de columnas de coordenadas (lat/lon) o geometría WKT
- Reproyección automática de MAGNA-SIRGAS a WGS84
- Deduplicación: elimina registros repetidos y genera reporte con detalle
- Manejo de Excel multi-hojas con columnas duplicadas
- Limpieza de nombres y tipos para compatibilidad con ArcGIS
- Bucle interactivo: procesa múltiples carpetas sin reiniciar
- CRS de salida: WGS84 (EPSG:4326)

```bash
uv run Proceso_conversion_GD/geospatial/csv_xlx_to_shape.py
```

### 2. `shp_to_geojson.py` — Conversión Shapefile a GeoJSON

Convierte archivos `.shp` a formato GeoJSON con reproyección a WGS84.

**Características:**
- Reproyección automática a EPSG:4326
- Deduplicación por atributos + geometría
- Sobrescritura de archivos existentes

```bash
uv run Proceso_conversion_GD/geospatial/shp_to_geojson.py
```

### 3. `filtro_espacial_geojson.py` — Filtro espacial por polígono

Filtra archivos `.shp` usando polígonos de recorte. Cada polígono filtro se aplica de forma **independiente**, generando carpetas separadas por filtro.

**Características:**
- Validación automática: solo usa archivos de tipo Polygon/MultiPolygon como filtro
- Selección de archivos: todos, por número (1,3,5) o por rango (1-4)
- Cada filtro genera su propio par de carpetas (SHP + GeoJSON)
- Reproyección automática a WGS84 sin importar el CRS de entrada
- Deduplicación por atributos + geometría con reporte detallado
- Nombres de salida incluyen referencia al filtro usado

```bash
uv run Proceso_conversion_GD/geospatial/filtro_espacial_geojson.py
```

### 4. `unificar_ipm_variables.py` — Unificación de variables IPM

Consolida múltiples pestañas de un archivo Excel de IPM en una única tabla unificada usando el código de manzana.

**Características:**
- Merge automático de todas las pestañas (excepto Diccionario)
- Uso de `outer join` por `cod_mzn` para evitar pérdida de datos
- Genera archivo Excel consolidado

```bash
uv run Proceso_conversion_GD/geospatial/unificar_ipm_variables.py
```

**Estructura de salida:**
```
[salida]/
├── shape_filtrado_[nombre_filtro]/
│   └── datos_filtrado_[nombre_filtro].shp
└── geojson_filtrado_[nombre_filtro]/
    └── datos_filtrado_[nombre_filtro].geojson
```

## Requisitos

- Python 3.12+
- `uv` como gestor de ambiente

### Instalación de dependencias

```bash
uv pip install -r requirements.txt
```

### Librerías principales

| Paquete | Función |
|---------|---------|
| geopandas | Lectura/escritura de formatos geoespaciales |
| pandas | Lectura de archivos tabulares |
| shapely | Creación de geometrías |
| openpyxl | Lectura de archivos Excel (.xlsx) |

## Documentación detallada

Cada script tiene su archivo `.md` con documentación completa:
- [`geospatial/csv_xlx_to_shape.md`](geospatial/csv_xlx_to_shape.md)
- [`geospatial/filtro_espacial_geojson.md`](geospatial/filtro_espacial_geojson.md)
