"""
=============================================================================
SCRIPT: filtro_espacial_geojson.py
=============================================================================
Descripción:
    Filtra archivos espaciales (.shp) usando polígonos de recorte.
    Solo conserva los registros que están DENTRO del polígono filtro.
    Elimina duplicados y genera archivos en formato Shapefile y GeoJSON,
    ambos en WGS84 (EPSG:4326).

Flujo:
    1. Solicita la ruta del archivo(s) de polígono filtro (.shp)
    2. Solicita la carpeta con los .shp de puntos/líneas a filtrar
    3. Reproyecta todo a WGS84 (EPSG:4326)
    4. Realiza intersección espacial (spatial join)
    5. Elimina registros duplicados
    6. Exporta en dos formatos:
       - Shapefile (*_filtrado.shp) en carpeta shape_filtrado/
       - GeoJSON (*_filtrado.geojson) en carpeta geojson_filtrado/

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


def cargar_poligono_filtro(ruta: Path) -> gpd.GeoDataFrame:
    """
    Carga el polígono de filtro desde un archivo .shp.
    Reproyecta a WGS84 y disuelve todos los polígonos en uno solo.
    """
    gdf = gpd.read_file(ruta)

    if gdf.empty:
        raise ValueError("El archivo de polígono filtro está vacío")

    # Reproyectar a WGS84
    if gdf.crs is None:
        print("    ⚠️  Sin CRS definido, se asume WGS84")
        gdf = gdf.set_crs(epsg=4326)
    elif gdf.crs.to_epsg() != 4326:
        print(f"    Reproyectando filtro de {gdf.crs.to_epsg()} a EPSG:4326...")
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


def main():
    print("=" * 70)
    print("  FILTRO ESPACIAL POR POLÍGONO")
    print("  (SHP → SHP filtrado + GeoJSON filtrado)")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # 1. Solicitar archivo(s) de polígono filtro
    # -------------------------------------------------------------------------
    print("\n📐 Ingresa la ruta de la carpeta o archivo .shp del polígono filtro")
    print("   (puede ser una carpeta con varios .shp o un archivo .shp directo)")
    entrada_filtro = input("   > ").strip().strip('"').strip("'")

    if not entrada_filtro:
        print("\n❌ No ingresaste ninguna ruta.")
        return

    ruta_filtro = Path(entrada_filtro)

    if not ruta_filtro.exists():
        print(f"\n❌ No se encontró: {ruta_filtro.resolve()}")
        return

    # Determinar si es archivo o carpeta
    if ruta_filtro.is_file() and ruta_filtro.suffix.lower() == ".shp":
        archivos_filtro = [ruta_filtro]
    elif ruta_filtro.is_dir():
        archivos_filtro = buscar_shapefiles(ruta_filtro)
        if not archivos_filtro:
            print(f"\n❌ No se encontraron archivos .shp en: {ruta_filtro.resolve()}")
            return
    else:
        print(f"\n❌ La ruta no es un archivo .shp ni una carpeta válida.")
        return

    print(f"\n   Archivos de polígono filtro encontrados:")
    for f in archivos_filtro:
        print(f"   - {f.name}")

    # Cargar y combinar todos los polígonos filtro
    print(f"\n   Cargando polígono(s) filtro...")
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
        print(f"   ✅ Polígono filtro cargado ({len(gdfs_filtro)} archivo(s), geometría disuelta)")
    except Exception as e:
        print(f"\n❌ Error al cargar polígono filtro: {e}")
        return

    # -------------------------------------------------------------------------
    # 2. Solicitar carpeta con los .shp a filtrar
    # -------------------------------------------------------------------------
    print("\n📂 Ingresa la ruta de la carpeta con los archivos .shp a filtrar")
    print("   (puede ser ruta absoluta o relativa)")
    entrada_datos = input("   > ").strip().strip('"').strip("'")

    if not entrada_datos:
        print("\n❌ No ingresaste ninguna ruta.")
        return

    carpeta_datos = Path(entrada_datos)

    if not carpeta_datos.exists() or not carpeta_datos.is_dir():
        print(f"\n❌ La carpeta no existe: {carpeta_datos.resolve()}")
        return

    archivos_shp = buscar_shapefiles(carpeta_datos)

    if not archivos_shp:
        print(f"\n❌ No se encontraron archivos .shp en: {carpeta_datos.resolve()}")
        return

    print(f"\n📄 Se encontraron {len(archivos_shp)} archivos .shp para filtrar:")
    for archivo in archivos_shp:
        print(f"   - {archivo.name}")

    # -------------------------------------------------------------------------
    # 3. Solicitar carpeta de salida
    # -------------------------------------------------------------------------
    print("\n📂 Ingresa la ruta de la carpeta donde guardar los archivos filtrados")
    print("   (se crearán subcarpetas shape_filtrado/ y geojson_filtrado/)")
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

    print(f"\n📁 Carpetas de salida:")
    print(f"   SHP     → {carpeta_shape_out.resolve()}")
    print(f"   GeoJSON → {carpeta_geojson_out.resolve()}")

    # -------------------------------------------------------------------------
    # 4. Confirmar
    # -------------------------------------------------------------------------
    print("\n¿Deseas continuar con el filtrado espacial? (s/n)")
    confirm = input("   > ").strip().lower()
    if confirm not in ("s", "si", "sí", "y", "yes"):
        print("\n⚠️  Filtrado cancelado.")
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
        print(f"  📄 Procesando: {archivo.name}")

        try:
            # Leer shapefile
            gdf_datos = gpd.read_file(archivo)

            if gdf_datos.empty:
                msg = f"Archivo vacío: {archivo.name}"
                print(f"    ⚠️  {msg}")
                log_errores.append(msg)
                errores += 1
                continue

            # Reproyectar a WGS84
            if gdf_datos.crs is None:
                print(f"    ⚠️  Sin CRS definido, se asume WGS84")
                gdf_datos = gdf_datos.set_crs(epsg=4326)
            elif gdf_datos.crs.to_epsg() != 4326:
                print(f"    Reproyectando de EPSG:{gdf_datos.crs.to_epsg()} a EPSG:4326...")
                gdf_datos = gdf_datos.to_crs(epsg=4326)

            registros_entrada = len(gdf_datos)
            total_registros_entrada += registros_entrada
            print(f"    Registros de entrada: {registros_entrada}")

            # Filtrar por polígono
            gdf_filtrado = filtrar_por_poligono(gdf_datos, gdf_poligono)

            if gdf_filtrado.empty:
                msg = f"Sin registros dentro del polígono: {archivo.name}"
                print(f"    ⚠️  {msg}")
                log_errores.append(msg)
                errores += 1
                continue

            # Eliminar duplicados (mismos atributos + misma geometría)
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
                print(f"    📊 Dentro del polígono: {antes_dedup} | Únicos: {despues_dedup} | Duplicados eliminados: {duplicados}")
            else:
                print(f"    📊 Dentro del polígono: {despues_dedup} (sin duplicados)")

            # Exportar a Shapefile
            nombre_salida = f"{archivo.stem}_filtrado"
            ruta_shp_out = carpeta_shape_out / f"{nombre_salida}.shp"
            # Limpiar archivos previos
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

            print(f"    ✓ Guardado: {nombre_salida} ({despues_dedup} registros)")
            exitosos += 1

        except Exception as e:
            msg = f"Error en {archivo.name}: {str(e)}"
            print(f"    ✗ {msg}")
            log_errores.append(msg)
            errores += 1

    # -------------------------------------------------------------------------
    # 6. Log de errores
    # -------------------------------------------------------------------------
    if log_errores:
        ruta_log = carpeta_salida / "log_errores_filtro.txt"
        with open(ruta_log, "w", encoding="utf-8") as f:
            f.write(f"LOG DE ERRORES - Filtro espacial\n")
            f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Polígono filtro: {ruta_filtro.resolve()}\n")
            f.write(f"Carpeta de datos: {carpeta_datos.resolve()}\n")
            f.write("=" * 70 + "\n\n")
            for i, error in enumerate(log_errores, 1):
                f.write(f"{i}. {error}\n")
        print(f"\n📝 Log de errores guardado en: {ruta_log.name}")

    # -------------------------------------------------------------------------
    # 7. Resumen final
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("  RESUMEN DE FILTRADO ESPACIAL")
    print("=" * 70)
    print(f"  📊 Archivos procesados:             {len(archivos_shp)}")
    print(f"  ✅ Filtrados exitosamente:           {exitosos}")
    print(f"  ❌ Con errores:                      {errores}")
    print(f"  📍 Total registros de entrada:       {total_registros_entrada}")
    print(f"  📍 Total registros filtrados:        {total_registros_filtrados}")
    print(f"  🔄 Total duplicados eliminados:      {total_duplicados}")
    print(f"  📁 Shapefiles en:  {carpeta_shape_out.resolve()}")
    print(f"  📁 GeoJSON en:     {carpeta_geojson_out.resolve()}")
    print(f"  🌐 CRS de salida:  EPSG:4326 (WGS84)")
    print("=" * 70)


if __name__ == "__main__":
    main()
