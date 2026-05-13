# Filtro Espacial por Polígono (Independiente por Filtro)

## Resumen

Script en Python que filtra archivos Shapefile (`.shp`) usando **múltiples polígonos de recorte independientes**. Cada archivo `.shp` en la carpeta de filtro se trata como un filtro separado, generando subcarpetas de salida con el nombre del filtro correspondiente.

Todos los archivos se reproyectan a **WGS84 (EPSG:4326)**, se eliminan duplicados y se exportan en dos formatos: Shapefile y GeoJSON.

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

## Validación automática de tipo de geometría

El script **solo usa archivos de tipo Polygon o MultiPolygon** como filtro. Al leer la carpeta de filtros:

- Verifica el tipo de geometría de cada `.shp`
- Usa solo los que son polígonos
- Descarta automáticamente puntos, líneas y otros tipos
- Muestra en consola cuáles se descartaron y por qué

```
   ✅ Se encontraron 2 polígono(s) filtro:
   - calle_5_area_Espejo_Bf100.shp (Polygon)
   - calle_7_area_Espejo_Bf100.shp (Polygon)

   ⚠️  Archivos descartados (no son polígonos):
   - calle_5_linea.shp (LineString)
```

## Lógica de filtrado independiente

Si la carpeta de filtro contiene N archivos `.shp`, el script ejecuta N procesos de filtrado completos. Cada filtro genera su propio par de carpetas de salida.

```
Carpeta filtro/
├── comuna_7.shp          → Filtro 1
├── comuna_13.shp         → Filtro 2
└── zona_centro.shp       → Filtro 3

Resultado: 3 pares de carpetas × M archivos de datos = 3×M archivos filtrados
```

## Flujo del proceso

```
┌─────────────────────────────────────────────┐
│  1. Solicitar carpeta con polígonos filtro  │
│     (cada .shp es un filtro independiente)  │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│  2. Solicitar carpeta con los .shp          │
│     a filtrar (datos de entrada)            │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│  3. Solicitar carpeta de salida             │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│  4. Confirmar filtrado (s/n)                │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│  5. POR CADA polígono filtro:               │
│     a. Cargar y reproyectar a WGS84        │
│     b. Crear subcarpetas:                   │
│        - shape_filtrado_[nombre_filtro]/    │
│        - geojson_filtrado_[nombre_filtro]/ │
│     c. POR CADA archivo de datos:           │
│        - Reproyectar a WGS84               │
│        - Spatial join (within)              │
│        - Eliminar duplicados               │
│        - Exportar *_filtrado_[filtro].shp  │
│        - Exportar *_filtrado_[filtro].geojson│
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│  6. Generar log_errores_filtro.txt          │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│  7. Mostrar resumen final en consola        │
└─────────────────────────────────────────────┘
```

## Nomenclatura de archivos de salida

Los archivos generados incluyen el nombre del filtro para identificar su origen:

```
[nombre_dato]_filtrado_[nombre_filtro].shp
[nombre_dato]_filtrado_[nombre_filtro].geojson
```

Ejemplo:
- Dato: `comparendos_2023.shp`
- Filtro: `comuna_7.shp`
- Salida: `comparendos_2023_filtrado_comuna_7.shp`

## Estructura de salida completa

Con 2 filtros (`comuna_7.shp`, `comuna_13.shp`) y 3 archivos de datos:

```
[carpeta_salida]/
├── shape_filtrado_comuna_7/
│   ├── comparendos_2023_filtrado_comuna_7.shp (+ .shx, .dbf, .prj, .cpg)
│   ├── accidentes_2024_filtrado_comuna_7.shp
│   └── puntos_control_filtrado_comuna_7.shp
├── geojson_filtrado_comuna_7/
│   ├── comparendos_2023_filtrado_comuna_7.geojson
│   ├── accidentes_2024_filtrado_comuna_7.geojson
│   └── puntos_control_filtrado_comuna_7.geojson
├── shape_filtrado_comuna_13/
│   ├── comparendos_2023_filtrado_comuna_13.shp
│   ├── accidentes_2024_filtrado_comuna_13.shp
│   └── puntos_control_filtrado_comuna_13.shp
├── geojson_filtrado_comuna_13/
│   ├── comparendos_2023_filtrado_comuna_13.geojson
│   ├── accidentes_2024_filtrado_comuna_13.geojson
│   └── puntos_control_filtrado_comuna_13.geojson
└── log_errores_filtro.txt (solo si hubo errores)
```

## Ejemplo de uso

```
======================================================================
  FILTRO ESPACIAL POR POLÍGONO (INDEPENDIENTE POR FILTRO)
  (SHP → SHP filtrado + GeoJSON filtrado)
======================================================================

📐 Ingresa la ruta de la carpeta con los polígonos filtro (.shp)
   Cada .shp en esta carpeta se usará como filtro INDEPENDIENTE
   > C:\...\Data_Steward\poligonos_filtro

   ✅ Se encontraron 2 polígono(s) filtro:
   - comuna_7.shp
   - comuna_13.shp

📂 Ingresa la ruta de la carpeta con los archivos .shp a filtrar
   > C:\...\Data_Steward\Observatorio_2026\shape_Observatorio_2026

   ✅ Se encontraron 3 archivos .shp para filtrar:
   - comparendos_2023.shp
   - accidentes_2024.shp
   - puntos_control.shp

📂 Ingresa la ruta de la carpeta de salida
   > C:\...\Data_Steward\resultados_filtro

----------------------------------------------------------------------
  RESUMEN DE OPERACIONES:
  • Polígonos filtro:  2
  • Archivos a filtrar: 3
  • Total operaciones:  6
----------------------------------------------------------------------

¿Deseas continuar con el filtrado espacial? (s/n)
   > s

══════════════════════════════════════════════════════════════════════════
Iniciando filtrado espacial...

──────────────────────────────────────────────────────────────────────────
  � FILTRO 1/2: comuna_7.shp
──────────────────────────────────────────────────────────────────────────
    ✅ Polígono cargado y reproyectado a WGS84
    📁 SHP     → .../shape_filtrado_comuna_7/
    📁 GeoJSON → .../geojson_filtrado_comuna_7/

    📄 comparendos_2023.shp
       📊 Entrada: 15420 | Filtrados: 4200
       ✓ Guardado: comparendos_2023_filtrado_comuna_7

    📄 accidentes_2024.shp
       📊 Entrada: 3200 | Filtrados: 890 | Duplicados eliminados: 10
       ✓ Guardado: accidentes_2024_filtrado_comuna_7

──────────────────────────────────────────────────────────────────────────
  🔷 FILTRO 2/2: comuna_13.shp
──────────────────────────────────────────────────────────────────────────
    ✅ Polígono cargado y reproyectado a WGS84
    📁 SHP     → .../shape_filtrado_comuna_13/
    📁 GeoJSON → .../geojson_filtrado_comuna_13/

    📄 comparendos_2023.shp
       📊 Entrada: 15420 | Filtrados: 5100
       ✓ Guardado: comparendos_2023_filtrado_comuna_13

======================================================================
  RESUMEN DE FILTRADO ESPACIAL
======================================================================
  🔷 Polígonos filtro usados:          2
  � Archivos de datos procesados:     3
  📊 Total operaciones:                6
  ✅ Exitosas:                          6
  ❌ Con errores:                       0
  📍 Total registros de entrada:        37240
  📍 Total registros filtrados:         15800
  🔄 Total duplicados eliminados:       10
  🌐 CRS de salida:                    EPSG:4326 (WGS84)
======================================================================
```

## Reproyección automática

No importa el CRS de los archivos de entrada. El script:
1. Detecta el CRS de cada archivo (filtro y datos)
2. Reproyecta automáticamente a WGS84 (EPSG:4326)
3. Los archivos de salida siempre quedan en EPSG:4326

## Deduplicación

Después del filtrado espacial, se eliminan registros donde todos los atributos y la geometría son idénticos.

## Manejo de errores

El script NO se detiene ante errores. Si un archivo:
- Está vacío
- No tiene geometría válida
- No tiene registros dentro del polígono

Se registra en `log_errores_filtro.txt` y continúa con el siguiente.

## Notas técnicas

- El filtrado usa `gpd.sjoin()` con predicado `within`
- Cada polígono filtro se disuelve en una sola geometría antes de filtrar
- Solo se usan archivos de tipo Polygon/MultiPolygon como filtro (puntos y líneas se descartan automáticamente)
- Todos los archivos se reproyectan a WGS84 (EPSG:4326) antes del filtrado
- Los archivos de salida siempre están en EPSG:4326
- Sobrescribe archivos existentes en las carpetas de salida
- Los nombres incluyen referencia al filtro para trazabilidad
