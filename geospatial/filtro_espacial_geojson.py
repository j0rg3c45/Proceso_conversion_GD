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


def seleccionar_archivos(lista_archivos: list, tipo_nombre: str) -> list:
    """
    Muestra una lista de archivos y permite al usuario seleccionar por número,
    rango o 'todos'.
    """
    if not lista_archivos:
        return []

    print(f"\n   Se encontraron {len(lista_archivos)} archivos {tipo_nombre}:\n")
    for i, archivo in enumerate(lista_archivos, 1):
        print(f"   {i}. {archivo.name}")

    print(f"\n   Selecciona cuáles deseas usar:")
    print(f"   • Escribe 'todos' o presiona Enter para usar todos")
    print(f"   • Escribe los números separados por coma (ej: 1,3,5)")
    print(f"   • Escribe un rango (ej: 1-4)")
    seleccion = input("   > ").strip().lower()

    if not seleccion or seleccion in ("todos", "all", "t"):
        print(f"\n   ✅ Se usarán todos los {len(lista_archivos)} archivos")
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

        # Validar rango
        indices_validos = [i for i in indices_seleccionados if 1 <= i <= len(lista_archivos)]
        if not indices_validos:
            print(f"\n⚠️  Selección no válida o fuera de rango. Se usarán TODOS.")
            return lista_archivos

        seleccionados = [lista_archivos[i - 1] for i in sorted(indices_validos)]
        print(f"\n   ✅ Archivos seleccionados ({len(seleccionados)}):")
        for archivo in seleccionados:
            print(f"   - {archivo.name}")
        return seleccionados

    except ValueError:
        print("\n⚠️  Formato no válido. Se usarán TODOS.")
        return lista_archivos


def main():
    print("=" * 70)
    print("  FILTRO ESPACIAL POR POLÍGONO (INDEPENDIENTE POR FILTRO)")
    print("  (SHP → SHP filtrado + GeoJSON filtrado)")
    print("=" * 70)

    # Variables para recordar rutas y selecciones
    ultima_carpeta_filtro = None
    ultimos_archivos_filtro = None
    ultima_carpeta_salida = None

    while True:
        # -------------------------------------------------------------------------
        # 1. Solicitar carpeta con polígonos filtro
        # -------------------------------------------------------------------------
        reusar_filtro = False
        if ultima_carpeta_filtro and ultimos_archivos_filtro:
            print(f"\n📐 Configuración de filtro actual:")
            print(f"   Carpeta: {ultima_carpeta_filtro.resolve()}")
            print(f"   Archivos: {', '.join([f.name for f in ultimos_archivos_filtro])}")
            confirm_filtro = input("\n   ¿Deseas usar el MISMO filtro? (s/n/salir): ").strip().lower()
            
            if confirm_filtro in ("salir", "exit", "q"):
                break
            if confirm_filtro in ("s", "si", "sí", "y", "yes"):
                carpeta_filtro = ultima_carpeta_filtro
                archivos_filtro = ultimos_archivos_filtro
                reusar_filtro = True
        
        if not reusar_filtro:
            print("\n📐 Ingresa la ruta de la carpeta con los polígonos filtro (.shp)")
            print("   (o escribe 'salir' para terminar)")
            entrada_filtro = input("   > ").strip().strip('"').strip("'")

            if not entrada_filtro or entrada_filtro.lower() in ("salir", "exit", "q"):
                break

            carpeta_filtro = Path(entrada_filtro)

            if not carpeta_filtro.exists() or not carpeta_filtro.is_dir():
                print(f"\n❌ Carpeta no válida: {carpeta_filtro.resolve()}")
                continue

            archivos_candidatos, descartados = buscar_shapefiles_poligonos(carpeta_filtro)

            if not archivos_candidatos:
                print(f"\n❌ No se encontraron polígonos en: {carpeta_filtro.resolve()}")
                continue

            if descartados:
                print(f"\n   ⚠️  Archivos descartados (no son polígonos):")
                for nombre, tipo in descartados:
                    print(f"   - {nombre} ({tipo})")

            # Permitir seleccionar qué filtros usar de la carpeta
            archivos_filtro = seleccionar_archivos(archivos_candidatos, "de polígono filtro")
            
            ultima_carpeta_filtro = carpeta_filtro
            ultimos_archivos_filtro = archivos_filtro

        # -------------------------------------------------------------------------
        # 2. Solicitar carpeta con los .shp a filtrar
        # -------------------------------------------------------------------------
        print("\n📂 Ingresa la ruta de la carpeta con los archivos .shp a filtrar")
        entrada_datos = input("   > ").strip().strip('"').strip("'")

        if not entrada_datos or entrada_datos.lower() in ("salir", "exit", "q"):
            break

        carpeta_datos = Path(entrada_datos)

        if not carpeta_datos.exists() or not carpeta_datos.is_dir():
            print(f"\n❌ Carpeta no válida: {carpeta_datos.resolve()}")
            continue

        archivos_candidatos_datos = buscar_shapefiles(carpeta_datos)

        if not archivos_candidatos_datos:
            print(f"\n❌ No se encontraron archivos .shp en: {carpeta_datos.resolve()}")
            continue

        archivos_datos = seleccionar_archivos(archivos_candidatos_datos, ".shp a filtrar")

        # -------------------------------------------------------------------------
        # 3. Solicitar carpeta de salida
        # -------------------------------------------------------------------------
        reusar_salida = False
        if ultima_carpeta_salida:
            print(f"\n📂 Carpeta de salida actual: {ultima_carpeta_salida.resolve()}")
            confirm_salida = input("   ¿Usar la MISMA carpeta de salida? (s/n): ").strip().lower()
            if confirm_salida in ("s", "si", "sí", "y", "yes"):
                carpeta_salida = ultima_carpeta_salida
                reusar_salida = True

        if not reusar_salida:
            print("\n📂 Ingresa la ruta de la carpeta de salida")
            print("   (presiona Enter para usar la misma carpeta de los datos)")
            entrada_salida = input("   > ").strip().strip('"').strip("'")

            if not entrada_salida:
                carpeta_salida = carpeta_datos
            else:
                carpeta_salida = Path(entrada_salida)

            carpeta_salida.mkdir(parents=True, exist_ok=True)
            ultima_carpeta_salida = carpeta_salida

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
            continue

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
        reporte_duplicados = []

        for i, archivo_filtro in enumerate(archivos_filtro, 1):
            nombre_filtro = archivo_filtro.stem
            print(f"\n{'─' * 70}")
            print(f"  🔷 FILTRO {i}/{len(archivos_filtro)}: {archivo_filtro.name}")
            print(f"{'─' * 70}")

            try:
                gdf_poligono = cargar_poligono(archivo_filtro)
                print(f"    ✅ Polígono cargado y reproyectado a WGS84")
            except Exception as e:
                msg = f"Error al cargar filtro {archivo_filtro.name}: {e}"
                print(f"    ❌ {msg}")
                log_errores.append(msg)
                total_errores += len(archivos_datos)
                continue

            carpeta_shp_out = carpeta_salida / f"shape_filtrado_{nombre_filtro}"
            carpeta_geojson_out = carpeta_salida / f"geojson_filtrado_{nombre_filtro}"
            carpeta_shp_out.mkdir(parents=True, exist_ok=True)
            carpeta_geojson_out.mkdir(parents=True, exist_ok=True)

            print(f"    📁 SHP     → .../{carpeta_shp_out.name}/")
            print(f"    📁 GeoJSON → .../{carpeta_geojson_out.name}/")
            print()

            for archivo_dato in archivos_datos:
                print(f"    📄 {archivo_dato.name}")
                try:
                    gdf_datos = gpd.read_file(archivo_dato)
                    if gdf_datos.empty:
                        msg = f"Archivo vacío: {archivo_dato.name} (filtro: {nombre_filtro})"
                        print(f"       ⚠️  {msg}"); log_errores.append(msg); total_errores += 1; continue

                    if gdf_datos.crs is None: gdf_datos = gdf_datos.set_crs(epsg=4326)
                    elif gdf_datos.crs.to_epsg() != 4326: gdf_datos = gdf_datos.to_crs(epsg=4326)

                    registros_entrada = len(gdf_datos)
                    total_registros_entrada += registros_entrada
                    gdf_filtrado = filtrar_por_poligono(gdf_datos, gdf_poligono)

                    if gdf_filtrado.empty:
                        msg = f"Sin registros dentro del polígono: {archivo_dato.name} (filtro: {nombre_filtro})"
                        print(f"       ⚠️  {msg}"); log_errores.append(msg); total_errores += 1; continue

                    gdf_filtrado, duplicados = deduplicar(gdf_filtrado)
                    total_duplicados += duplicados
                    total_registros_filtrados += len(gdf_filtrado)

                    if duplicados > 0:
                        print(f"       📊 Entrada: {registros_entrada} | Filtrados: {len(gdf_filtrado)} | Duplicados eliminados: {duplicados}")
                        reporte_duplicados.append(f"{archivo_dato.name} (filtro: {nombre_filtro}): {duplicados} duplicados eliminados")
                    else:
                        print(f"       📊 Entrada: {registros_entrada} | Filtrados: {len(gdf_filtrado)}")

                    nombre_salida = f"{archivo_dato.stem}_filtrado_{nombre_filtro}"
                    ruta_shp = carpeta_shp_out / f"{nombre_salida}.shp"
                    for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg", ".fix"]:
                        previo = carpeta_shp_out / f"{nombre_salida}{ext}"
                        if previo.exists(): previo.unlink()
                    gdf_filtrado.to_file(ruta_shp, driver="ESRI Shapefile", encoding="utf-8")

                    ruta_geojson = carpeta_geojson_out / f"{nombre_salida}.geojson"
                    if ruta_geojson.exists(): ruta_geojson.unlink()
                    gdf_filtrado.to_file(ruta_geojson, driver="GeoJSON")

                    print(f"       ✓ Guardado: {nombre_salida}")
                    total_exitosos += 1
                except Exception as e:
                    msg = f"Error en {archivo_dato.name} (filtro: {nombre_filtro}): {str(e)}"
                    print(f"       ✗ {msg}"); log_errores.append(msg); total_errores += 1

        # -------------------------------------------------------------------------
        # 6. Log de errores y Resumen final
        # -------------------------------------------------------------------------
        if log_errores or reporte_duplicados:
            ruta_log = carpeta_salida / "log_errores_filtro.txt"
            with open(ruta_log, "w", encoding="utf-8") as f:
                f.write(f"REPORTE DE FILTRADO ESPACIAL\nFecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Carpeta filtros: {carpeta_filtro.resolve()}\nCarpeta datos: {carpeta_datos.resolve()}\n" + "=" * 70 + "\n\n")
                if reporte_duplicados:
                    f.write("REGISTROS DUPLICADOS ELIMINADOS:\n" + "-" * 40 + "\n")
                    for item in reporte_duplicados: f.write(f"  {item}\n")
                    f.write("\n")
                if log_errores:
                    f.write("ERRORES:\n" + "-" * 40 + "\n")
                    for i, error in enumerate(log_errores, 1): f.write(f"  {i}. {error}\n")
            print(f"\n📝 Reporte: {ruta_log.name}")

        print("\n" + "=" * 70)
        print("  RESUMEN DE FILTRADO ESPACIAL")
        print("=" * 70)
        print(f"  ✅ Exitosas: {total_exitosos} | ❌ Errores: {total_errores}")
        print(f"  📍 Registros filtrados: {total_registros_filtrados} | 🔄 Duplicados: {total_duplicados}")
        print(f"  📁 Salida: {carpeta_salida.name}")
        print("=" * 70)

        print("\n----------------------------------------------------------------------")
        print("  ¿Qué deseas hacer ahora?")
        print("   1. Procesar otros datos (mismo filtro y misma salida)")
        print("   2. Cambiar todo")
        print("   3. Salir")
        opcion = input("   > ").strip()
        
        if opcion == "1":
            continue
        elif opcion == "2":
            ultima_carpeta_filtro = None
            ultimos_archivos_filtro = None
            ultima_carpeta_salida = None
            continue
        else:
            break


if __name__ == "__main__":
    main()
