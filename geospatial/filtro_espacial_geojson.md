# Filtro Espacial por Polígono

## Resumen

Script en Python que filtra archivos Shapefile (`.shp`) usando polígonos de recorte. Solo conserva los registros que están **dentro** del polígono filtro, elimina duplicados, reproyecta todo a **WGS84 (EPSG:4326)** y genera archivos en dos formatos: Shapefile y GeoJSON.

## Requisitos

- Python 3.12+
- `uv` como gestor de ambiente
- Librerías: `geopandas`, `pandas`, `shapely`

```bash
uv pip install -r requirements.txt
```

## Ejecución

```bash
uv run Proceso_conversion_GD/geospatial/filtro_espacial_geojson.py
```

## Flujo del proceso

```
┌─────────────────────────────────────────────┐
│  1. Solicitar ruta del polígono filtro      │
│     (archivo .shp o carpeta con .shp)       │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│  2. Cargar polígono(s), reproyectar a       │
│     WGS84 y disolver en uno solo            │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│  3. Solicitar carpeta con los .shp          │
│     a filtrar                               │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│  4. Solicitar carpeta de salida             │
│     (crea shape_filtrado/ y                 │
│      geojson_filtrado/)                     │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│  5. Confirmar filtrado (s/n)                │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│  6. Por cada archivo .shp:                  │
│     a. Leer datos                           │
│     b. Reproyectar a WGS84 (EPSG:4326)     │
│     c. Spatial join (within) con polígono   │
│     d. Eliminar duplicados                  │
│     e. Exportar *_filtrado.shp              │
│     f. Exportar *_filtrado.geojson          │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│  7. Generar log_errores_filtro.txt          │
│     (si aplica)                             │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│  8. Mostrar resumen final en consola        │
└─────────────────────────────────────────────┘
```

## Reproyección automática

No importa el sistema de referencia que tengan los archivos de entrada. El script:

1. Detecta el CRS de cada archivo
2. Reproyecta automáticamente a **WGS84 (EPSG:4326)**
3. Los archivos de salida siempre quedan en EPSG:4326

Si un archivo no tiene CRS definido, se asume WGS84.

## Deduplicación

Después del filtrado espacial, se eliminan registros donde **todos los atributos y la geometría** son idénticos (comparando geometría como WKT).

```
  📄 Procesando: comparendos_2023.shp
    Reproyectando de EPSG:3116 a EPSG:4326...
    Registros de entrada: 15420
    📊 Dentro del polígono: 8200 | Únicos: 8150 | Duplicados eliminados: 50
    ✓ Guardado: comparendos_2023_filtrado (8150 registros)
```

## Estructura de salida

```
[carpeta_salida]/
├── shape_filtrado/                    ← Shapefiles filtrados
│   ├── archivo1_filtrado.shp (+ .shx, .dbf, .prj, .cpg)
│   ├── archivo2_filtrado.shp
│   └── archivo3_filtrado.shp
├── geojson_filtrado/                  ← GeoJSON filtrados
│   ├── archivo1_filtrado.geojson
│   ├── archivo2_filtrado.geojson
│   └── archivo3_filtrado.geojson
└── log_errores_filtro.txt             ← Solo si hubo errores
```

## Ejemplo de uso

```
======================================================================
  FILTRO ESPACIAL POR POLÍGONO
  (SHP → SHP filtrado + GeoJSON filtrado)
======================================================================

📐 Ingresa la ruta de la carpeta o archivo .shp del polígono filtro
   (puede ser una carpeta con varios .shp o un archivo .shp directo)
   > C:\Users\Jorge\Documents\GOBIERNO_DE_DATOS\Data_Steward\poligono_cali.shp

   Archivos de polígono filtro encontrados:
   - poligono_cali.shp

   Cargando polígono(s) filtro...
   ✅ Polígono filtro cargado (1 archivo(s), geometría disuelta)

📂 Ingresa la ruta de la carpeta con los archivos .shp a filtrar
   (puede ser ruta absoluta o relativa)
   > C:\Users\Jorge\Documents\GOBIERNO_DE_DATOS\Data_Steward\Observatorio_Seguridad_2026\shape_Observatorio_Seguridad_2026

📄 Se encontraron 5 archivos .shp para filtrar:
   - comparendos_2023.shp
   - accidentes_2024.shp
   - puntos_control.shp

📂 Ingresa la ruta de la carpeta donde guardar los archivos filtrados
   (se crearán subcarpetas shape_filtrado/ y geojson_filtrado/)
   (presiona Enter para usar la misma carpeta de los datos)
   > C:\Users\Jorge\Documents\GOBIERNO_DE_DATOS\Data_Steward\filtrado_cali

📁 Carpetas de salida:
   SHP     → C:\...\filtrado_cali\shape_filtrado
   GeoJSON → C:\...\filtrado_cali\geojson_filtrado

¿Deseas continuar con el filtrado espacial? (s/n)
   > s

----------------------------------------------------------------------
Iniciando filtrado espacial...

  📄 Procesando: comparendos_2023.shp
    Reproyectando de EPSG:3116 a EPSG:4326...
    Registros de entrada: 15420
    📊 Dentro del polígono: 12300 | Únicos: 12250 | Duplicados eliminados: 50
    ✓ Guardado: comparendos_2023_filtrado (12250 registros)

  📄 Procesando: accidentes_2024.shp
    Registros de entrada: 3200
    📊 Dentro del polígono: 2800 (sin duplicados)
    ✓ Guardado: accidentes_2024_filtrado (2800 registros)

======================================================================
  RESUMEN DE FILTRADO ESPACIAL
======================================================================
  📊 Archivos procesados:             5
  ✅ Filtrados exitosamente:           4
  ❌ Con errores:                      1
  📍 Total registros de entrada:       22150
  📍 Total registros filtrados:        18200
  🔄 Total duplicados eliminados:      120
  📁 Shapefiles en:  C:\...\filtrado_cali\shape_filtrado
  📁 GeoJSON en:     C:\...\filtrado_cali\geojson_filtrado
  🌐 CRS de salida:  EPSG:4326 (WGS84)
======================================================================
```

## Polígono filtro

El polígono filtro puede ser:
- Un archivo `.shp` directo (ej: `poligono_cali.shp`)
- Una carpeta con varios `.shp` de polígonos (se combinan y disuelven en uno solo)

Si hay múltiples polígonos, se disuelven en una sola geometría para hacer el filtro.

## Manejo de errores

El script NO se detiene ante errores. Si un archivo:
- Está vacío
- No tiene geometría válida
- No tiene registros dentro del polígono

Se registra en `log_errores_filtro.txt` y continúa con el siguiente archivo.

## Notas técnicas

- El filtrado usa `gpd.sjoin()` con predicado `within` (registros dentro del polígono).
- Todos los archivos se reproyectan a WGS84 (EPSG:4326) antes del filtrado.
- Los archivos de salida siempre están en EPSG:4326.
- Los Shapefiles generados incluyen archivos auxiliares (.shx, .dbf, .prj, .cpg).
- Sobrescribe archivos existentes en las carpetas de salida.
- Los archivos filtrados llevan el sufijo `_filtrado` para distinguirlos de los originales.
