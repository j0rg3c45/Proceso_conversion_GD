"""
Script para convertir archivos .shp a formato GeoJSON.
Permite seleccionar archivos específicos o procesar masivamente.

Uso:
    uv run Proceso_conversion_GD/geospatial/shp_to_geojson.py
"""

import geopandas as gpd
from pathlib import Path
import datetime


def seleccionar_archivos_interactivo(lista_archivos: list, titulo: str) -> list:
    """
    Permite al usuario seleccionar un archivo específico o todos.
    """
    if not lista_archivos:
        return []

    print(f"\n--- SELECCIÓN DE {titulo} ---")
    for i, archivo in enumerate(lista_archivos, 1):
        print(f"  {i}. {archivo.name}")

    print(f"\nOpciones:")
    print(f"  • Escribe 0 para procesar TODOS los archivos")
    print(f"  • Escribe el número del archivo (ej: 1)")
    print(f"  • Escribe varios números (ej: 1,3,5) o rango (1-4)")
    
    seleccion = input("Selección > ").strip().lower()

    if seleccion == "0" or not seleccion:
        print(f"INFO: Se seleccionaron TODOS los archivos ({len(lista_archivos)}).")
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
            print("ADVERTENCIA: Selección no válida. Se usarán todos por defecto.")
            return lista_archivos
        
        print(f"OK: Seleccionados: {len(validos)} archivo(s).")
        return validos
    except (ValueError, IndexError):
        print("ADVERTENCIA: Error en formato. Se usarán todos por defecto.")
        return lista_archivos


def main():
    print("=" * 60)
    print("  CONVERSIÓN DE SHAPEFILES (.shp) A GEOJSON")
    print("=" * 60)

    # 1. Solicitar carpeta de entrada
    print("\n[DIRECTORIO] Ingresa la ruta de la carpeta donde están los archivos .shp")
    input_dir = Path(input("   > ").strip().strip('"').strip("'"))

    if not input_dir.exists():
        print(f"\nERROR: La carpeta no existe: {input_dir.resolve()}")
        return

    # Buscar archivos .shp
    shp_files_candidatos = sorted(input_dir.glob("*.shp"))

    if not shp_files_candidatos:
        print(f"\nERROR: No se encontraron archivos .shp en: {input_dir.resolve()}")
        return

    # 2. Selección interactiva
    shp_files = seleccionar_archivos_interactivo(shp_files_candidatos, "ARCHIVOS SHAPEFILE")

    # 3. Solicitar carpeta de salida
    print("\n[DIRECTORIO] Ingresa la ruta de la carpeta donde guardar los archivos .geojson")
    output_dir = Path(input("   > ").strip().strip('"').strip("'"))

    # Crear carpeta de salida si no existe
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nINFO: Los GeoJSON se guardarán en: {output_dir.resolve()}")

    # Confirmar
    print("\n¿Deseas continuar con la conversión? (s/n)")
    confirm = input("   > ").strip().lower()
    if confirm not in ("s", "si", "sí", "y", "yes"):
        print("\nCANCELADO: Conversión cancelada.")
        return

    # 4. Convertir
    print("\n" + "-" * 60)
    print("Iniciando conversión...\n")

    exitosos = 0
    errores = 0
    reporte_duplicados = []

    for shp_path in shp_files:
        output_name = shp_path.stem + ".geojson"
        output_path = output_dir / output_name

        print(f"  Convirtiendo: {shp_path.name} -> {output_name}")

        try:
            gdf = gpd.read_file(shp_path)
            # Reproyectar a WGS84 (EPSG:4326) para compatibilidad GeoJSON
            if gdf.crs and (not gdf.crs.is_projected or gdf.crs.to_epsg() != 4326):
                gdf = gdf.to_crs(epsg=4326)

            # Detectar y eliminar duplicados
            total_leidos = len(gdf)
            gdf["_geom_wkt"] = gdf.geometry.apply(lambda g: g.wkt if g else None)
            cols_comparar = [col for col in gdf.columns if col != "geometry"]
            gdf = gdf.drop_duplicates(subset=cols_comparar)
            gdf = gdf.drop(columns=["_geom_wkt"])
            unicos = len(gdf)
            duplicados = total_leidos - unicos

            if duplicados > 0:
                print(f"    INFO: Registros leídos: {total_leidos} | Únicos: {unicos} | Duplicados eliminados: {duplicados}")
                reporte_duplicados.append(f"{shp_path.name}: {duplicados} duplicados eliminados (de {total_leidos} → {unicos} únicos)")
            else:
                print(f"    INFO: Registros leídos: {total_leidos} (sin duplicados)")

            # Exportar
            if output_path.exists():
                output_path.unlink()
            gdf.to_file(output_path, driver="GeoJSON")
            print(f"    OK: Guardado ({unicos} registros)")
            exitosos += 1
        except Exception as e:
            print(f"    ERROR: {e}")
            errores += 1

    # Resumen
    print("\n" + "=" * 60)
    print(f"  RESUMEN: {exitosos} convertidos | {errores} errores")
    if reporte_duplicados:
        print(f"  INFO: Archivos con duplicados: {len(reporte_duplicados)}")
    print(f"  Archivos en: {output_dir.resolve()}")
    print("=" * 60)

    # Generar reporte si hubo duplicados
    if reporte_duplicados:
        ruta_reporte = output_dir / "reporte_duplicados.txt"
        with open(ruta_reporte, "w", encoding="utf-8") as f:
            f.write(f"REPORTE DE DUPLICADOS - Conversión SHP a GeoJSON\n")
            f.write(f"Fecha: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            for item in reporte_duplicados:
                f.write(f"  {item}\n")
        print(f"  REPORTE: {ruta_reporte.name}")


if __name__ == "__main__":
    main()
