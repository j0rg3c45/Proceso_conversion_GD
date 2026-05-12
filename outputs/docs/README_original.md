# Conversión de Shapefiles a GeoJSON

## Resumen

Script en Python que convierte archivos `.shp` (ESRI Shapefile) a formato `.geojson`, reproyectando automáticamente a WGS84 (EPSG:4326) para garantizar compatibilidad con el estándar GeoJSON.

El script es interactivo y reutilizable: no tiene rutas fijas, por lo que sirve para cualquier carpeta de trabajo.

## Requisitos

- Python 3.12+
- `uv` como gestor de ambiente
- Librería: `geopandas`

```bash
uv pip install geopandas
```

## Ejecución

```bash
uv run CARPETA_CODIGOS_TRANSFORMACION/shp_to_geojson.py
```

## Flujo del proceso

```
┌─────────────────────────────────────┐
│  1. Solicitar ruta de entrada       │
│     (carpeta con archivos .shp)     │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│  2. Validar que la carpeta exista   │
│     y buscar archivos .shp          │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│  3. Listar archivos encontrados     │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│  4. Solicitar ruta de salida        │
│     (carpeta para los .geojson)     │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│  5. Confirmar conversión (s/n)      │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│  6. Por cada .shp:                  │
│     a. Leer con geopandas           │
│     b. Reproyectar a EPSG:4326      │
│        (si es necesario)            │
│     c. Guardar como .geojson        │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│  7. Mostrar resumen de resultados   │
│     (exitosos / errores)            │
└─────────────────────────────────────┘
```

## Ejemplo de uso

```
📂 Ingresa la ruta de la carpeta donde están los archivos .shp
   > Barrio_Obrero/info_obrero_shape

✅ Se encontraron 9 archivos .shp

📂 Ingresa la ruta de la carpeta donde guardar los archivos .geojson
   > Barrio_Obrero/Geojson_Barrio_Obrero

¿Deseas continuar con la conversión? (s/n)
   > s
```

## Notas

- El formato GeoJSON requiere coordenadas en WGS84 (EPSG:4326), por eso el script reproyecta automáticamente si el shapefile viene en otro sistema de referencia.
- Los archivos de salida conservan el mismo nombre del `.shp` original, solo cambia la extensión a `.geojson`.


## Librerías instaladas en el ambiente uv

Ambiente: Python 3.12.13 — `C:\Users\Jorge\.venv`

| Paquete | Versión |
|---------|---------|
| attrs | 26.1.0 |
| certifi | 2026.4.22 |
| cffi | 2.0.0 |
| charset-normalizer | 3.4.7 |
| colorama | 0.4.6 |
| et-xmlfile | 2.0.0 |
| geopandas | 1.1.3 |
| h11 | 0.16.0 |
| idna | 3.13 |
| numpy | 2.4.4 |
| openpyxl | 3.1.5 |
| outcome | 1.3.0.post0 |
| packaging | 26.2 |
| pandas | 3.0.2 |
| pillow | 12.2.0 |
| pycparser | 3.0 |
| pyogrio | 0.12.1 |
| pyproj | 3.7.2 |
| pysocks | 1.7.1 |
| python-dateutil | 2.9.0.post0 |
| python-dotenv | 1.2.2 |
| requests | 2.33.1 |
| selenium | 4.43.0 |
| shapely | 2.1.2 |
| six | 1.17.0 |
| sniffio | 1.3.1 |
| sortedcontainers | 2.4.0 |
| tqdm | 4.67.3 |
| trio | 0.33.0 |
| trio-websocket | 0.12.2 |
| typing-extensions | 4.15.0 |
| tzdata | 2026.2 |
| urllib3 | 2.6.3 |
| webdriver-manager | 4.0.2 |
| websocket-client | 1.9.0 |
| wsproto | 1.3.2 |
