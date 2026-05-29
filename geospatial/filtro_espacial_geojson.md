# Filtro Espacial Geoespacial Experto

## Resumen

Script avanzado en Python para el filtrado de archivos Shapefile (`.shp`) utilizando polígonos de zona como máscara. El script está diseñado para el procesamiento masivo, con capacidades de búsqueda recursiva y organización automática de resultados.

Todos los archivos resultantes se normalizan a **WGS84 (EPSG:4326)** y se someten a un proceso de deduplicación geométrica y de atributos.

## Características Principales

1.  **Escaneo Recursivo:** Identifica automáticamente todos los archivos `.shp` en la carpeta raíz y sus subcarpetas.
2.  **Validación de Geometría:** Solo utiliza archivos de tipo `Polygon` o `MultiPolygon` como filtros de zona.
3.  **Selección Flexible:** Permite procesar un archivo específico, una lista personalizada o todos de forma masiva.
4.  **Deduplicación:** Elimina registros repetidos (geometría idéntica + atributos idénticos) para asegurar la integridad de los datos.
5.  **Estructura Organizada:** Separa los formatos GeoJSON y Shapefile, organizando estos últimos por subcarpetas de zona.

## Requisitos

- Python 3.12+
- `uv` como gestor de ambiente
- Librerías: `geopandas`, `pandas`, `shapely`, `fiona`

```bash
uv pip install -r requirements.txt
```

## Estructura de Salida (Nueva)

El script genera una estructura limpia para evitar la mezcla de archivos:

```
[carpeta_salida]/
├── geojson/
│   ├── datos1_Zona_A.geojson
│   ├── datos2_Zona_A.geojson
│   └── datos1_Zona_B.geojson
└── informacion_shape/
    ├── Zona_A/
    │   ├── datos1_Zona_A.shp (+ .shx, .dbf, .prj)
    │   └── datos2_Zona_A.shp
    └── Zona_B/
        └── datos1_Zona_B.shp
```

## Flujo de Trabajo

1.  **Configuración de Datos:** Se ingresa la ruta (local o red). El script informa si encontró uno o múltiples archivos.
2.  **Selección de Datos:** El usuario elige qué archivos filtrar (ej: `1`, `1,3`, `1-5` o `todos`).
3.  **Configuración de Filtros:** Se ingresa la ruta de las zonas. El script valida cuáles son polígonos útiles.
4.  **Selección de Zonas:** El usuario elige qué zonas aplicar como filtro.
5.  **Procesamiento:**
    - Reproyección automática a EPSG:4326.
    - Spatial Join (`within`).
    - Deduplicación.
    - Exportación organizada.

## Ejecución

```bash
uv run Proceso_conversion_GD/geospatial/filtro_espacial_geojson.py
```

## Ejemplo de Consola

```
--- SELECCIÓN DE ARCHIVOS DE DATOS ---
  1. comparendos.shp (en 2023)
  2. comparendos.shp (en 2024)
  3. incidentes.shp (en consolidado)

Opciones:
  • Escribe el número del archivo (ej: 1)
  • Escribe 'todos' para procesar masivamente
Selección > todos
✅ Se seleccionaron TODOS los archivos (3).
```

## Notas Técnicas

- **Deduplicación:** Se genera un WKT de la geometría temporalmente para comparar registros de forma exacta.
- **Normalización:** Si un archivo no tiene CRS definido, se asume EPSG:4326 por defecto, pero siempre se transforma a WGS84 antes de operar.
- **Log de Errores:** En caso de fallos en archivos específicos, se genera un archivo `log_ejecucion.txt` en la raíz de salida.
