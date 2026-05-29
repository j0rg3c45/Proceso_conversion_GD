"""
=============================================================================
SCRIPT: filtro_espacial_geojson.py
=============================================================================
Descripción:
    Filtra archivos espaciales (.shp) usando polígonos de recorte.
    Permite seleccionar archivos específicos o procesar masivamente.
    Organiza la salida en carpetas GeoJSON y Shapefile por zonas.

Flujo:
    1. Escanea recursivamente carpetas de datos y filtros.
    2. Permite seleccionar uno o todos los archivos a filtrar.
    3. Aplica filtro espacial, elimina duplicados y organiza la salida.

Estructura de salida:
    [salida]/
    ├── geojson/
    │   ├── datos1_ZonaA.geojson
    │   └── datos2_ZonaA.geojson
    └── informacion_shape/
        ├── ZonaA/
        │   ├── datos1_ZonaA.shp
        │   └── datos2_ZonaA.shp
        └── ZonaB/
            └── ...

Dependencias:
    - geopandas
    - pandas
    - shapely


    uv run Proceso_conversion_GD/geospatial/filtro_espacial_geojson.py
=============================================================================
"""

import geopandas as gpd
import pandas as pd
from pathlib import Path
from datetime import datetime
import os


def buscar_shapefiles_recursivo(carpeta: Path) -> list:
    """
    Busca archivos .shp dentro de una carpeta y todas sus subcarpetas.
    """
    return sorted(list(carpeta.rglob("*.shp")))


def buscar_shapefiles_poligonos(carpeta: Path) -> tuple:
    """
    Busca archivos .shp recursivamente y retorna solo los que
    contienen geometrías de tipo Polygon o MultiPolygon.
    """
    archivos_poligono = []
    archivos_descartados = []

    candidatos = buscar_shapefiles_recursivo(carpeta)

    for item in candidatos:
        try:
            # Leer solo la primera fila para validar tipo de geometría rápidamente
            gdf = gpd.read_file(item, rows=1)
            tipos = gdf.geom_type.unique()
            es_poligono = any(t in ("Polygon", "MultiPolygon") for t in tipos)
            if es_poligono:
                archivos_poligono.append(item)
            else:
                archivos_descartados.append((item.name, tipos[0] if len(tipos) > 0 else "desconocido"))
        except Exception:
            archivos_descartados.append((item.name, "error al leer"))

    return archivos_poligono, archivos_descartados


def cargar_poligono(ruta: Path) -> gpd.GeoDataFrame:
    """
    Carga un polígono, lo reproyecta a WGS84 y lo disuelve.
    """
    gdf = gpd.read_file(ruta)
    if gdf.empty:
        raise ValueError(f"El archivo de polígono está vacío: {ruta.name}")

    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=4326)
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    return gdf.dissolve()


def filtrar_por_poligono(gdf_datos: gpd.GeoDataFrame, gdf_poligono: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Filtra registros dentro del polígono (spatial join predicate 'within').
    """
    gdf_filtrado = gpd.sjoin(gdf_datos, gdf_poligono, how="inner", predicate="within")
    cols_eliminar = [col for col in gdf_filtrado.columns if col.startswith("index_")]
    return gdf_filtrado.drop(columns=cols_eliminar, errors="ignore")


def deduplicar(gdf: gpd.GeoDataFrame) -> tuple:
    """
    Elimina duplicados por atributos + geometría (WKT).
    """
    antes = len(gdf)
    gdf["_geom_wkt"] = gdf.geometry.apply(lambda g: g.wkt if g else None)
    cols_comparar = [col for col in gdf.columns if col != "geometry"]
    gdf = gdf.drop_duplicates(subset=cols_comparar)
    gdf = gdf.drop(columns=["_geom_wkt"])
    despues = len(gdf)
    return gdf, antes - despues


def seleccionar_archivos_interactivo(lista_archivos: list, titulo: str) -> list:
    """
    Permite al usuario seleccionar un archivo específico o todos.
    """
    if not lista_archivos:
        return []

    print(f"\n--- SELECCIÓN DE {titulo} ---")
    for i, archivo in enumerate(lista_archivos, 1):
        # Mostrar ruta relativa para mejor contexto en escaneo recursivo
        print(f"  {i}. {archivo.name} (en {archivo.parent.name})")

    print(f"\nOpciones:")
    print(f"  • Escribe el número del archivo (ej: 1)")
    print(f"  • Escribe 'todos' para procesar masivamente")
    print(f"  • Escribe varios números (ej: 1,3,5) o rango (1-4)")
    
    seleccion = input("Selección > ").strip().lower()

    if seleccion in ("todos", "t", "all") or not seleccion:
        print(f"✅ Se seleccionaron TODOS los archivos ({len(lista_archivos)}).")
        return lista_archivos

    indices_seleccionados = set()
    try:
        for parte in seleccion.split(","):
            parte = parte.strip()
            if "-" in parte:
                inicio, fin = parte.split("-")
                for idx in range(int(inicio), int(fin) + 1):
                    indices_seleccionados.add(idx)
            else:
                indices_seleccionados.add(int(parte))

        validos = [lista_archivos[i - 1] for i in indices_seleccionados if 1 <= i <= len(lista_archivos)]
        if not validos:
            print("⚠️ Selección no válida. Se usarán todos por defecto.")
            return lista_archivos
        
        print(f"✅ Seleccionados: {len(validos)} archivo(s).")
        return validos
    except (ValueError, IndexError):
        print("⚠️ Error en formato. Se usarán todos por defecto.")
        return lista_archivos


def main():
    print("=" * 80)
    print("  ASISTENTE DE FILTRADO ESPACIAL GEOESPACIAL EXPERTO")
    print("=" * 80)

    # 1. Identificación y Validación de Shapefiles de DATOS
    print("\n1. CONFIGURACIÓN DE DATOS DE ENTRADA")
    print("Ingrese la ruta de la carpeta (local o red) que contiene los .shp a filtrar:")
    ruta_input = input("> ").strip().strip('"').strip("'")
    
    path_datos = Path(ruta_input)
    if not path_datos.exists() or not path_datos.is_dir():
        print(f"❌ Error: La ruta no existe o no es un directorio: {ruta_input}")
        return

    print(f"\n🔍 Escaneando archivos en: {path_datos.resolve()} ...")
    archivos_datos_candidatos = buscar_shapefiles_recursivo(path_datos)

    if not archivos_datos_candidatos:
        print("❌ No se encontraron archivos Shapefile (.shp) en la ruta proporcionada.")
        return

    if len(archivos_datos_candidatos) == 1:
        print(f"INFO: Se encontró UN SOLO shapefile:")
    else:
        print(f"INFO: Se encontraron MULTIPLES shapefiles ({len(archivos_datos_candidatos)}):")
    
    for a in archivos_datos_candidatos:
        print(f"   - {a.name}")

    # 2. Selección de datos (Interactivo)
    archivos_datos = seleccionar_archivos_interactivo(archivos_datos_candidatos, "ARCHIVOS DE DATOS")

    # 3. Selección de FILTROS (Polígonos de zona)
    print("\n2. CONFIGURACIÓN DE POLÍGONOS DE FILTRO (ZONAS)")
    print("Ingrese la ruta de la carpeta con los polígonos de zona (.shp):")
    ruta_filtro = input("> ").strip().strip('"').strip("'")
    
    path_filtros = Path(ruta_filtro)
    if not path_filtros.exists() or not path_filtros.is_dir():
        print(f"ERROR en ruta de filtros.")
        return

    filtros_candidatos, descartados = buscar_shapefiles_poligonos(path_filtros)
    if not filtros_candidatos:
        print("ERROR: No se encontraron polígonos válidos para filtrar.")
        return

    if descartados:
        print(f"ADVERTENCIA: Se descartaron {len(descartados)} archivos por no ser polígonos.")

    archivos_filtros = seleccionar_archivos_interactivo(filtros_candidatos, "POLÍGONOS DE FILTRO")

    # 4. Ruta de SALIDA y Estructura
    print("\n3. CONFIGURACIÓN DE SALIDA")
    print("Ingrese la ruta donde se guardarán los resultados:")
    ruta_out = input("> ").strip().strip('"').strip("'")
    path_salida = Path(ruta_out)
    path_salida.mkdir(parents=True, exist_ok=True)

    # Crear estructura base
    path_geojson_root = path_salida / "geojson"
    path_shape_root = path_salida / "informacion_shape"
    path_geojson_root.mkdir(exist_ok=True)
    path_shape_root.mkdir(exist_ok=True)

    # 5. Ejecución del Filtrado
    print("\n" + "=" * 80)
    print("INICIANDO PROCESAMIENTO...")
    print("=" * 80)

    total_exitos = 0
    total_errores = 0
    log_reporte = []

    for f_path in archivos_filtros:
        nombre_zona = f_path.stem
        print(f"\nPROCESANDO ZONA: {nombre_zona}")
        
        try:
            gdf_filtro = cargar_poligono(f_path)
            
            # Crear subcarpeta para la zona en informacion_shape
            path_zona_shp = path_shape_root / nombre_zona
            path_zona_shp.mkdir(exist_ok=True)

            for d_path in archivos_datos:
                print(f"  Archivo: {d_path.name} ...", end="", flush=True)
                try:
                    gdf_data = gpd.read_file(d_path)
                    
                    # Normalizar CRS a WGS84
                    if gdf_data.crs is None:
                        gdf_data = gdf_data.set_crs(epsg=4326)
                    elif gdf_data.crs.to_epsg() != 4326:
                        gdf_data = gdf_data.to_crs(epsg=4326)

                    # Aplicar Filtro Espacial
                    gdf_filtrado = filtrar_por_poligono(gdf_data, gdf_filtro)
                    
                    if gdf_filtrado.empty:
                        print(" (Vacio)")
                        continue

                    # Deduplicación (Regla de negocio crucial)
                    gdf_filtrado, num_dups = deduplicar(gdf_filtrado)
                    
                    # Nombres de salida
                    nombre_base = f"{d_path.stem}_{nombre_zona}"
                    
                    # Guardar GeoJSON (Carpeta raíz geojson/)
                    ruta_geojson = path_geojson_root / f"{nombre_base}.geojson"
                    gdf_filtrado.to_file(ruta_geojson, driver="GeoJSON")

                    # Guardar Shapefile (Subcarpeta por zona)
                    ruta_shp = path_zona_shp / f"{nombre_base}.shp"
                    gdf_filtrado.to_file(ruta_shp, driver="ESRI Shapefile", encoding="utf-8")

                    print(f" OK! (Filtrados: {len(gdf_filtrado)}, Duplicados: {num_dups})")
                    total_exitos += 1
                    
                except Exception as e:
                    print(f" ERROR: {e}")
                    log_reporte.append(f"Error en {d_path.name} con zona {nombre_zona}: {e}")
                    total_errores += 1

        except Exception as e:
            print(f"ERROR critico cargando zona {nombre_zona}: {e}")
            total_errores += len(archivos_datos)

    # Resumen Final
    print("\n" + "=" * 80)
    print("RESUMEN DE EJECUCIÓN")
    print("-" * 80)
    print(f"  ✅ Procesos exitosos: {total_exitos}")
    print(f"  ❌ Procesos con error: {total_errores}")
    print(f"  📂 Salida principal:  {path_salida.resolve()}")
    print(f"  📂 GeoJSONs:          {path_geojson_root.name}/")
    print(f"  📂 Shapefiles:        {path_shape_root.name}/[Zona]/")
    print("=" * 80)

    if log_reporte:
        with open(path_salida / "log_ejecucion.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(log_reporte))
        print(f"⚠️ Se generó un log de errores en: log_ejecucion.txt")


if __name__ == "__main__":
    main()
