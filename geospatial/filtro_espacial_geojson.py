"""
=============================================================================
SCRIPT: filtro_espacial_geojson.py
=============================================================================
Descripción:
    Filtra archivos espaciales (.shp) usando polígonos de recorte.
    Cada archivo .shp en la carpeta de filtro se trata como un filtro
    INDEPENDIENTE. Por cada filtro se genera una subcarpeta con los
    resultados en formato Shapefile y GeoJSON, todo en WGS84 (EPSG:4326).

Flujo:
    1. Solicita la carpeta con los polígonos filtro (.shp)
    2. Solicita la carpeta con los .shp a filtrar
    3. Por cada polígono filtro:
       a. Crea subcarpetas de salida con el nombre del filtro
       b. Filtra todos los .shp de datos contra ese polígono
       c. Elimina duplicados
       d. Exporta en SHP y GeoJSON

Estructura de salida (ejemplo con 2 filtros):
    [salida]/
    ├── shape_filtrado_poligono_A/
    │   ├── datos1_filtrado_poligono_A.shp
    │   └── datos2_filtrado_poligono_A.shp
    ├── geojson_filtrado_poligono_A/
    │   ├── datos1_filtrado_poligono_A.geojson
    │   └── datos2_filtrado_poligono_A.geojson
    ├── shape_filtrado_poligono_B/
    │   ├── datos1_filtrado_poligono_B.shp
    │   └── datos2_filtrado_poligono_B.shp
    └── geojson_filtrado_poligono_B/
        ├── datos1_filtrado_poligono_B.geojson
        └── datos2_filtrado_poligono_B.geojson

Dependencias:
    - geopandas
    - pandas
    - shapely

Ejecución:
    uv run Proceso_conversion_GD/geospatial/filtro_espacial_geojson.py
=============================================================================
"""

import geopandas as gpd
import pandas as pd
from pathlib import Path
from datetime import datetime


def buscar_shapefiles(carpeta: Path) -> list:
    """
    Busca archivos .shp dentro de una carpeta (sin recursión).
    """
    archivos = []
    for item in sorted(carpeta.iterdir()):
        if item.is_file() and item.suffix.lower() == ".shp":
            archivos.append(item)
    return archivos


def buscar_shapefiles_poligonos(carpeta: Path) -> list:
    """
    Busca archivos .shp dentro de una carpeta y retorna solo los que
    contienen geometrías de tipo Polygon o MultiPolygon.
    Descarta automáticamente puntos, líneas y otros tipos.
    """
    archivos_poligono = []
    archivos_descartados = []

    for item in sorted(carpeta.iterdir()):
        if item.is_file() and item.suffix.lower() == ".shp":
            try:
                gdf = gpd.read_file(item, rows=1)  # Leer solo 1 fila para verificar tipo
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
    Carga un polígono desde un archivo .shp.
    Reproyecta a WGS84 y disuelve en una sola geometría.
    """
    gdf = gpd.read_file(ruta)

    if gdf.empty:
        raise ValueError(f"El archivo de polígono está vacío: {ruta.name}")

    # Reproyectar a WGS84
    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=4326)
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    # Disolver todos los polígonos en uno solo
    gdf_disuelto = gdf.dissolve()

    return gdf_disuelto


def filtrar_por_poligono(gdf_datos: gpd.GeoDataFrame, gdf_poligono: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Filtra los registros que están dentro del polígono usando spatial join.
    """
    gdf_filtrado = gpd.sjoin(
        gdf_datos,
        gdf_poligono,
        how="inner",
        predicate="within"
    )

    # Eliminar columnas agregadas por el sjoin
    cols_eliminar = [col for col in gdf_filtrado.columns if col.startswith("index_")]
    gdf_filtrado = gdf_filtrado.drop(columns=cols_eliminar, errors="ignore")

    return gdf_filtrado


def deduplicar(gdf: gpd.GeoDataFrame) -> tuple:
    """
    Elimina duplicados por atributos + geometría.
    Retorna (gdf_sin_duplicados, cantidad_duplicados_eliminados)
    """
    antes = len(gdf)
    gdf["_geom_wkt"] = gdf.geometry.apply(lambda g: g.wkt if g else None)
    cols_comparar = [col for col in gdf.columns if col != "geometry"]
    gdf = gdf.drop_duplicates(subset=cols_comparar)
    gdf = gdf.drop(columns=["_geom_wkt"])
    despues = len(gdf)
    return gdf, antes - despues


def main():
    print("=" * 70)
    print("  FILTRO ESPACIAL POR POLÍGONO (INDEPENDIENTE POR FILTRO)")
    print("  (SHP → SHP filtrado + GeoJSON filtrado)")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # 1. Solicitar carpeta con polígonos filtro
    # -------------------------------------------------------------------------
    print("\n📐 Ingresa la ruta de la carpeta con los polígonos filtro (.shp)")
    print("   (ruta absoluta o relativa, ej: C:\\Users\\...\\mi_carpeta)")
    print("   Cada .shp de tipo Polígono se usará como filtro INDEPENDIENTE")
    entrada_filtro = input("   > ").strip().strip('"').strip("'")

    if not entrada_filtro:
        print("\n❌ No ingresaste ninguna ruta.")
        return

    carpeta_filtro = Path(entrada_filtro)

    if not carpeta_filtro.exists():
        print(f"\n❌ La ruta no existe: {carpeta_filtro.resolve()}")
        print(f"   Directorio actual: {Path.cwd()}")
        return

    if not carpeta_filtro.is_dir():
        print(f"\n❌ La ruta no es una carpeta: {carpeta_filtro.resolve()}")
        return

    archivos_filtro, descartados = buscar_shapefiles_poligonos(carpeta_filtro)

    if not archivos_filtro:
        print(f"\n❌ No se encontraron archivos .shp de tipo Polígono en: {carpeta_filtro.resolve()}")
        return

    print(f"\n   ✅ Se encontraron {len(archivos_filtro)} polígono(s) filtro:")
    for f in archivos_filtro:
        print(f"   - {f.name} (Polygon)")

    if descartados:
        print(f"\n   ⚠️  Archivos descartados (no son polígonos):")
        for nombre, tipo in descartados:
            print(f"   - {nombre} ({tipo})")

    # -------------------------------------------------------------------------
    # 2. Solicitar carpeta con los .shp a filtrar
    # -------------------------------------------------------------------------
    print("\n📂 Ingresa la ruta de la carpeta con los archivos .shp a filtrar")
    print("   (ruta absoluta o relativa, ej: C:\\Users\\...\\mi_carpeta)")
    entrada_datos = input("   > ").strip().strip('"').strip("'")

    if not entrada_datos:
        print("\n❌ No ingresaste ninguna ruta.")
        return

    carpeta_datos = Path(entrada_datos)

    if not carpeta_datos.exists():
        print(f"\n❌ La ruta no existe: {carpeta_datos.resolve()}")
        print(f"   Directorio actual: {Path.cwd()}")
        return

    if not carpeta_datos.is_dir():
        print(f"\n❌ La ruta no es una carpeta: {carpeta_datos.resolve()}")
        return

    archivos_datos = buscar_shapefiles(carpeta_datos)

    if not archivos_datos:
        print(f"\n❌ No se encontraron archivos .shp en: {carpeta_datos.resolve()}")
        return

    print(f"\n   ✅ Se encontraron {len(archivos_datos)} archivos .shp para filtrar:")
    for archivo in archivos_datos:
        print(f"   - {archivo.name}")

    # -------------------------------------------------------------------------
    # 3. Solicitar carpeta de salida
    # -------------------------------------------------------------------------
    print("\n📂 Ingresa la ruta de la carpeta de salida")
    print("   (ruta absoluta o relativa, se crearán subcarpetas por cada filtro)")
    print("   (presiona Enter para usar la misma carpeta de los datos)")
    entrada_salida = input("   > ").strip().strip('"').strip("'")

    if not entrada_salida:
        carpeta_salida = carpeta_datos
        print(f"\n   Usando carpeta de datos como salida: {carpeta_salida.resolve()}")
    else:
        carpeta_salida = Path(entrada_salida)

    carpeta_salida.mkdir(parents=True, exist_ok=True)
    print(f"\n📁 Carpeta de salida: {carpeta_salida.resolve()}")

    # -------------------------------------------------------------------------
    # 4. Resumen y confirmación
    # -------------------------------------------------------------------------
    total_operaciones = len(archivos_filtro) * len(archivos_datos)
    print(f"\n" + "-" * 70)
    print(f"  RESUMEN DE OPERACIONES:")
    print(f"  • Polígonos filtro:  {len(archivos_filtro)}")
    print(f"  • Archivos a filtrar: {len(archivos_datos)}")
    print(f"  • Total operaciones:  {total_operaciones}")
    print(f"  • Carpeta salida:     {carpeta_salida.resolve()}")
    print(f"-" * 70)

    print("\n¿Deseas continuar con el filtrado espacial? (s/n)")
    confirm = input("   > ").strip().lower()
    if confirm not in ("s", "si", "sí", "y", "yes"):
        print("\n⚠️  Filtrado cancelado.")
        return

    # -------------------------------------------------------------------------
    # 5. Procesar: por cada polígono filtro, filtrar todos los datos
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("Iniciando filtrado espacial...\n")

    total_exitosos = 0
    total_errores = 0
    total_registros_entrada = 0
    total_registros_filtrados = 0
    total_duplicados = 0
    log_errores = []

    for i, archivo_filtro in enumerate(archivos_filtro, 1):
        nombre_filtro = archivo_filtro.stem
        print(f"\n{'─' * 70}")
        print(f"  🔷 FILTRO {i}/{len(archivos_filtro)}: {archivo_filtro.name}")
        print(f"{'─' * 70}")

        # Cargar polígono filtro
        try:
            gdf_poligono = cargar_poligono(archivo_filtro)
            print(f"    ✅ Polígono cargado y reproyectado a WGS84")
        except Exception as e:
            msg = f"Error al cargar filtro {archivo_filtro.name}: {e}"
            print(f"    ❌ {msg}")
            log_errores.append(msg)
            total_errores += len(archivos_datos)
            continue

        # Crear subcarpetas de salida con nombre del filtro
        carpeta_shp_out = carpeta_salida / f"shape_filtrado_{nombre_filtro}"
        carpeta_geojson_out = carpeta_salida / f"geojson_filtrado_{nombre_filtro}"
        carpeta_shp_out.mkdir(parents=True, exist_ok=True)
        carpeta_geojson_out.mkdir(parents=True, exist_ok=True)

        print(f"    📁 SHP     → .../{carpeta_shp_out.name}/")
        print(f"    📁 GeoJSON → .../{carpeta_geojson_out.name}/")
        print()

        # Filtrar cada archivo de datos contra este polígono
        for archivo_dato in archivos_datos:
            print(f"    📄 {archivo_dato.name}")

            try:
                # Leer datos
                gdf_datos = gpd.read_file(archivo_dato)

                if gdf_datos.empty:
                    msg = f"Archivo vacío: {archivo_dato.name} (filtro: {nombre_filtro})"
                    print(f"       ⚠️  {msg}")
                    log_errores.append(msg)
                    total_errores += 1
                    continue

                # Reproyectar a WGS84
                if gdf_datos.crs is None:
                    gdf_datos = gdf_datos.set_crs(epsg=4326)
                elif gdf_datos.crs.to_epsg() != 4326:
                    gdf_datos = gdf_datos.to_crs(epsg=4326)

                registros_entrada = len(gdf_datos)
                total_registros_entrada += registros_entrada

                # Filtrar por polígono
                gdf_filtrado = filtrar_por_poligono(gdf_datos, gdf_poligono)

                if gdf_filtrado.empty:
                    msg = f"Sin registros dentro del polígono: {archivo_dato.name} (filtro: {nombre_filtro})"
                    print(f"       ⚠️  {msg}")
                    log_errores.append(msg)
                    total_errores += 1
                    continue

                # Deduplicar
                gdf_filtrado, duplicados = deduplicar(gdf_filtrado)
                total_duplicados += duplicados
                total_registros_filtrados += len(gdf_filtrado)

                if duplicados > 0:
                    print(f"       📊 Entrada: {registros_entrada} | Filtrados: {len(gdf_filtrado)} | Duplicados eliminados: {duplicados}")
                else:
                    print(f"       📊 Entrada: {registros_entrada} | Filtrados: {len(gdf_filtrado)}")

                # Nombre de salida con referencia al filtro
                nombre_salida = f"{archivo_dato.stem}_filtrado_{nombre_filtro}"

                # Exportar Shapefile
                ruta_shp = carpeta_shp_out / f"{nombre_salida}.shp"
                for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg", ".fix"]:
                    previo = carpeta_shp_out / f"{nombre_salida}{ext}"
                    if previo.exists():
                        previo.unlink()
                gdf_filtrado.to_file(ruta_shp, driver="ESRI Shapefile", encoding="utf-8")

                # Exportar GeoJSON
                ruta_geojson = carpeta_geojson_out / f"{nombre_salida}.geojson"
                if ruta_geojson.exists():
                    ruta_geojson.unlink()
                gdf_filtrado.to_file(ruta_geojson, driver="GeoJSON")

                print(f"       ✓ Guardado: {nombre_salida}")
                total_exitosos += 1

            except Exception as e:
                msg = f"Error en {archivo_dato.name} (filtro: {nombre_filtro}): {str(e)}"
                print(f"       ✗ {msg}")
                log_errores.append(msg)
                total_errores += 1

    # -------------------------------------------------------------------------
    # 6. Log de errores
    # -------------------------------------------------------------------------
    if log_errores:
        ruta_log = carpeta_salida / "log_errores_filtro.txt"
        with open(ruta_log, "w", encoding="utf-8") as f:
            f.write(f"LOG DE ERRORES - Filtro espacial\n")
            f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Carpeta filtros: {carpeta_filtro.resolve()}\n")
            f.write(f"Carpeta datos: {carpeta_datos.resolve()}\n")
            f.write("=" * 70 + "\n\n")
            for i, error in enumerate(log_errores, 1):
                f.write(f"{i}. {error}\n")
        print(f"\n📝 Log de errores: {ruta_log.name}")

    # -------------------------------------------------------------------------
    # 7. Resumen final
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("  RESUMEN DE FILTRADO ESPACIAL")
    print("=" * 70)
    print(f"  🔷 Polígonos filtro usados:          {len(archivos_filtro)}")
    print(f"  📄 Archivos de datos procesados:     {len(archivos_datos)}")
    print(f"  📊 Total operaciones:                {total_operaciones}")
    print(f"  ✅ Exitosas:                          {total_exitosos}")
    print(f"  ❌ Con errores:                       {total_errores}")
    print(f"  📍 Total registros de entrada:        {total_registros_entrada}")
    print(f"  📍 Total registros filtrados:         {total_registros_filtrados}")
    print(f"  🔄 Total duplicados eliminados:       {total_duplicados}")
    print(f"  🌐 CRS de salida:                    EPSG:4326 (WGS84)")
    print(f"  📁 Carpeta de salida: {carpeta_salida.resolve()}")
    print("=" * 70)


if __name__ == "__main__":
    main()
