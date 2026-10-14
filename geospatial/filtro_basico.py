"""
=============================================================================
SCRIPT: filtro_basico.py
=============================================================================
Descripcion:
    Filtro espacial BASICO por poligono. Recupera el comportamiento original
    de filtro_espacial_geojson.py (antes de su refactor).

    Filtra archivos espaciales (.shp) usando un poligono de recorte. Solo
    conserva los registros que estan DENTRO del poligono filtro (predicate
    'within'). Elimina duplicados y exporta en Shapefile y GeoJSON, ambos en
    WGS84 (EPSG:4326).

Flujo:
    1. Solicita la ruta del archivo o carpeta de poligono(s) filtro (.shp).
    2. Solicita la carpeta con los .shp de puntos/lineas a filtrar.
    3. Solicita la carpeta de salida (Enter = misma carpeta de datos).
    4. Reproyecta todo a WGS84 (EPSG:4326).
    5. Realiza interseccion espacial (spatial join 'within').
    6. Elimina registros duplicados.
    7. Exporta en dos formatos:
       - Shapefile  (*_filtrado.shp)     en carpeta shape_filtrado/
       - GeoJSON    (*_filtrado.geojson) en carpeta geojson_filtrado/

Dependencias:
    - geopandas
    - pandas
    - shapely

Ejecucion (desde Proceso_conversion_GD/):
    uv run Proceso_conversion_GD/geospatial/filtro_basico.py

=============================================================================
"""

import geopandas as gpd
import pandas as pd
from pathlib import Path
from datetime import datetime


# Extensiones espaciales aceptadas (filtro y datos).
EXTENSIONES_ESPACIALES = (".shp", ".geojson", ".json")


def buscar_espaciales(carpeta: Path, recursivo: bool = True) -> list:
    """
    Busca archivos espaciales (.shp, .geojson, .json) dentro de una carpeta.
    Por defecto busca de forma recursiva (incluye subcarpetas).
    """
    iterador = carpeta.rglob("*") if recursivo else carpeta.iterdir()
    archivos = []
    for item in sorted(iterador):
        if item.is_file() and item.suffix.lower() in EXTENSIONES_ESPACIALES:
            archivos.append(item)
    return archivos


def filtrar_por_poligono(gdf_datos: gpd.GeoDataFrame, gdf_poligono: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Filtra los registros que estan dentro del poligono (spatial join 'within')."""
    gdf_filtrado = gpd.sjoin(gdf_datos, gdf_poligono, how="inner", predicate="within")
    cols_eliminar = [col for col in gdf_filtrado.columns if col.startswith("index_")]
    return gdf_filtrado.drop(columns=cols_eliminar, errors="ignore")


def main():
    print("=" * 70)
    print("  FILTRO ESPACIAL BASICO POR POLIGONO")
    print("  (SHP -> SHP filtrado + GeoJSON filtrado)")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # 1. Solicitar archivo(s) de poligono filtro
    # -------------------------------------------------------------------------
    print("\n[FILTRO] Ingresa la ruta de la carpeta o archivo del poligono filtro")
    print("   (acepta .shp o .geojson; puede ser una carpeta o un archivo directo)")
    entrada_filtro = input("   > ").strip().strip('"').strip("'")

    if not entrada_filtro:
        print("\nERROR: No ingresaste ninguna ruta.")
        return

    ruta_filtro = Path(entrada_filtro)

    if not ruta_filtro.exists():
        print(f"\nERROR: No se encontro: {ruta_filtro.resolve()}")
        return

    # Determinar si es archivo o carpeta
    if ruta_filtro.is_file() and ruta_filtro.suffix.lower() in EXTENSIONES_ESPACIALES:
        archivos_filtro = [ruta_filtro]
    elif ruta_filtro.is_dir():
        archivos_filtro = buscar_espaciales(ruta_filtro)
        if not archivos_filtro:
            print(f"\nERROR: No se encontraron archivos .shp/.geojson en: {ruta_filtro.resolve()}")
            return
    else:
        print(f"\nERROR: La ruta no es un archivo .shp/.geojson ni una carpeta valida.")
        return

    print(f"\n   Archivos de poligono filtro encontrados:")
    for f in archivos_filtro:
        print(f"   - {f.name}")

    # Cargar y combinar todos los poligonos filtro
    print(f"\n   Cargando poligono(s) filtro...")
    try:
        gdfs_filtro = []
        for archivo_f in archivos_filtro:
            gdf_f = gpd.read_file(archivo_f)
            if gdf_f.crs is None:
                gdf_f = gdf_f.set_crs(epsg=4326)
            elif gdf_f.crs.to_epsg() != 4326:
                gdf_f = gdf_f.to_crs(epsg=4326)
            gdfs_filtro.append(gdf_f)

        gdf_poligono = pd.concat(gdfs_filtro, ignore_index=True)
        gdf_poligono = gpd.GeoDataFrame(gdf_poligono, geometry="geometry", crs="EPSG:4326")
        gdf_poligono = gdf_poligono.dissolve()
        print(f"   OK: Poligono filtro cargado ({len(gdfs_filtro)} archivo(s), geometria disuelta)")
    except Exception as e:
        print(f"\nERROR: Al cargar poligono filtro: {e}")
        return

    # -------------------------------------------------------------------------
    # 2. Solicitar carpeta con los .shp a filtrar
    # -------------------------------------------------------------------------
    print("\n[DATOS] Ingresa la ruta de la carpeta (o archivo) con los datos a filtrar")
    print("   (acepta .shp o .geojson; busca tambien en subcarpetas)")
    entrada_datos = input("   > ").strip().strip('"').strip("'")

    if not entrada_datos:
        print("\nERROR: No ingresaste ninguna ruta.")
        return

    ruta_datos = Path(entrada_datos)

    if not ruta_datos.exists():
        print(f"\nERROR: La ruta no existe: {ruta_datos.resolve()}")
        return

    # Permite archivo directo o carpeta
    if ruta_datos.is_file() and ruta_datos.suffix.lower() in EXTENSIONES_ESPACIALES:
        archivos_shp = [ruta_datos]
        carpeta_datos = ruta_datos.parent
    elif ruta_datos.is_dir():
        carpeta_datos = ruta_datos
        archivos_shp = buscar_espaciales(carpeta_datos)
    else:
        print(f"\nERROR: La ruta no es un archivo .shp/.geojson ni una carpeta valida.")
        return

    if not archivos_shp:
        print(f"\nERROR: No se encontraron archivos .shp/.geojson en: {carpeta_datos.resolve()}")
        return

    print(f"\n[INFO] Se encontraron {len(archivos_shp)} archivos para filtrar:")
    for archivo in archivos_shp:
        print(f"   - {archivo.name}")

    # -------------------------------------------------------------------------
    # 3. Solicitar carpeta de salida
    # -------------------------------------------------------------------------
    print("\n[SALIDA] Ingresa la ruta de la carpeta donde guardar los archivos filtrados")
    print("   (se crearan subcarpetas shape_filtrado/ y geojson_filtrado/)")
    print("   (presiona Enter para usar la misma carpeta de los datos)")
    entrada_salida = input("   > ").strip().strip('"').strip("'")

    if not entrada_salida:
        carpeta_salida = carpeta_datos
    else:
        carpeta_salida = Path(entrada_salida)

    carpeta_shape_out = carpeta_salida / "shape_filtrado"
    carpeta_geojson_out = carpeta_salida / "geojson_filtrado"

    carpeta_shape_out.mkdir(parents=True, exist_ok=True)
    carpeta_geojson_out.mkdir(parents=True, exist_ok=True)

    print(f"\n[INFO] Carpetas de salida:")
    print(f"   SHP     -> {carpeta_shape_out.resolve()}")
    print(f"   GeoJSON -> {carpeta_geojson_out.resolve()}")

    # -------------------------------------------------------------------------
    # 4. Confirmar
    # -------------------------------------------------------------------------
    print("\n¿Deseas continuar con el filtrado espacial? (s/n)")
    confirm = input("   > ").strip().lower()
    if confirm not in ("s", "si", "si", "y", "yes"):
        print("\nADVERTENCIA: Filtrado cancelado.")
        return

    # -------------------------------------------------------------------------
    # 5. Procesar cada archivo
    # -------------------------------------------------------------------------
    print("\n" + "-" * 70)
    print("Iniciando filtrado espacial...\n")

    exitosos = 0
    errores = 0
    log_errores = []
    total_registros_entrada = 0
    total_registros_filtrados = 0
    total_duplicados = 0

    for archivo in archivos_shp:
        print(f"  [INFO] Procesando: {archivo.name}")

        try:
            gdf_datos = gpd.read_file(archivo)

            if gdf_datos.empty:
                msg = f"Archivo vacio: {archivo.name}"
                print(f"    ADVERTENCIA: {msg}")
                log_errores.append(msg)
                errores += 1
                continue

            # Reproyectar a WGS84
            if gdf_datos.crs is None:
                print(f"    ADVERTENCIA: Sin CRS definido, se asume WGS84")
                gdf_datos = gdf_datos.set_crs(epsg=4326)
            elif gdf_datos.crs.to_epsg() != 4326:
                print(f"    INFO: Reproyectando de EPSG:{gdf_datos.crs.to_epsg()} a EPSG:4326...")
                gdf_datos = gdf_datos.to_crs(epsg=4326)

            registros_entrada = len(gdf_datos)
            total_registros_entrada += registros_entrada
            print(f"    Registros de entrada: {registros_entrada}")

            # Filtrar por poligono
            gdf_filtrado = filtrar_por_poligono(gdf_datos, gdf_poligono)

            if gdf_filtrado.empty:
                msg = f"Sin registros dentro del poligono: {archivo.name}"
                print(f"    ADVERTENCIA: {msg}")
                log_errores.append(msg)
                errores += 1
                continue

            # Eliminar duplicados (mismos atributos + misma geometria)
            antes_dedup = len(gdf_filtrado)
            gdf_filtrado["_geom_wkt"] = gdf_filtrado.geometry.apply(lambda g: g.wkt if g else None)
            cols_comparar = [col for col in gdf_filtrado.columns if col != "geometry"]
            gdf_filtrado = gdf_filtrado.drop_duplicates(subset=cols_comparar)
            gdf_filtrado = gdf_filtrado.drop(columns=["_geom_wkt"])
            despues_dedup = len(gdf_filtrado)
            duplicados = antes_dedup - despues_dedup
            total_duplicados += duplicados

            total_registros_filtrados += despues_dedup

            if duplicados > 0:
                print(f"    INFO: Dentro del poligono: {antes_dedup} | Unicos: {despues_dedup} | Duplicados eliminados: {duplicados}")
            else:
                print(f"    INFO: Dentro del poligono: {despues_dedup} (sin duplicados)")

            # Exportar a Shapefile
            nombre_salida = f"{archivo.stem}_filtrado"
            ruta_shp_out = carpeta_shape_out / f"{nombre_salida}.shp"
            for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg", ".fix"]:
                archivo_previo = carpeta_shape_out / f"{nombre_salida}{ext}"
                if archivo_previo.exists():
                    archivo_previo.unlink()
            gdf_filtrado.to_file(ruta_shp_out, driver="ESRI Shapefile", encoding="utf-8")

            # Exportar a GeoJSON
            ruta_geojson_out = carpeta_geojson_out / f"{nombre_salida}.geojson"
            if ruta_geojson_out.exists():
                ruta_geojson_out.unlink()
            gdf_filtrado.to_file(ruta_geojson_out, driver="GeoJSON")

            print(f"    OK: Guardado: {nombre_salida} ({despues_dedup} registros)")
            exitosos += 1

        except Exception as e:
            msg = f"Error en {archivo.name}: {str(e)}"
            print(f"    ERROR: {msg}")
            log_errores.append(msg)
            errores += 1

    # -------------------------------------------------------------------------
    # 6. Log de errores
    # -------------------------------------------------------------------------
    if log_errores:
        ruta_log = carpeta_salida / "log_errores_filtro.txt"
        with open(ruta_log, "w", encoding="utf-8") as f:
            f.write(f"LOG DE ERRORES - Filtro espacial basico\n")
            f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Poligono filtro: {ruta_filtro.resolve()}\n")
            f.write(f"Carpeta de datos: {carpeta_datos.resolve()}\n")
            f.write("=" * 70 + "\n\n")
            for i, error in enumerate(log_errores, 1):
                f.write(f"{i}. {error}\n")
        print(f"\n[INFO] Log de errores guardado en: {ruta_log.name}")

    # -------------------------------------------------------------------------
    # 7. Resumen final
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("  RESUMEN DE FILTRADO ESPACIAL")
    print("=" * 70)
    print(f"  INFO: Archivos procesados:          {len(archivos_shp)}")
    print(f"  OK: Filtrados exitosamente:         {exitosos}")
    print(f"  ERROR: Con errores:                 {errores}")
    print(f"  INFO: Total registros de entrada:   {total_registros_entrada}")
    print(f"  INFO: Total registros filtrados:    {total_registros_filtrados}")
    print(f"  INFO: Total duplicados eliminados:  {total_duplicados}")
    print(f"  INFO: Shapefiles en:  {carpeta_shape_out.resolve()}")
    print(f"  INFO: GeoJSON en:     {carpeta_geojson_out.resolve()}")
    print(f"  INFO: CRS de salida:  EPSG:4326 (WGS84)")
    print("=" * 70)


if __name__ == "__main__":
    main()
