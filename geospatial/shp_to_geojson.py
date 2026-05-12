"""
Script para convertir archivos .shp a formato GeoJSON.
Solicita al usuario las rutas de entrada y salida.



uv run shp_to_geojson.py
"""

import geopandas as gpd
from pathlib import Path


def main():
    print("=" * 60)
    print("  CONVERSIÓN DE SHAPEFILES (.shp) A GEOJSON")
    print("=" * 60)

    # Solicitar carpeta de entrada (donde están los .shp)
    print("\n📂 Ingresa la ruta de la carpeta donde están los archivos .shp")
    print("   (puede ser ruta absoluta o relativa al directorio actual)")
    input_dir = Path(input("   > ").strip().strip('"').strip("'"))

    if not input_dir.exists():
        print(f"\n❌ La carpeta no existe: {input_dir.resolve()}")
        return

    # Buscar archivos .shp
    shp_files = sorted(input_dir.glob("*.shp"))

    if not shp_files:
        print(f"\n❌ No se encontraron archivos .shp en: {input_dir.resolve()}")
        return

    print(f"\n✅ Se encontraron {len(shp_files)} archivos .shp en:")
    print(f"   {input_dir.resolve()}")
    print("\n   Archivos encontrados:")
    for shp in shp_files:
        print(f"   - {shp.name}")

    # Solicitar carpeta de salida (donde se guardarán los .geojson)
    print("\n📂 Ingresa la ruta de la carpeta donde guardar los archivos .geojson")
    print("   (se creará si no existe)")
    output_dir = Path(input("   > ").strip().strip('"').strip("'"))

    # Crear carpeta de salida si no existe
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n📁 Los GeoJSON se guardarán en: {output_dir.resolve()}")

    # Confirmar
    print("\n¿Deseas continuar con la conversión? (s/n)")
    confirm = input("   > ").strip().lower()
    if confirm not in ("s", "si", "sí", "y", "yes"):
        print("\n⚠️  Conversión cancelada.")
        return

    # Convertir
    print("\n" + "-" * 60)
    print("Iniciando conversión...\n")

    exitosos = 0
    errores = 0

    for shp_path in shp_files:
        output_name = shp_path.stem + ".geojson"
        output_path = output_dir / output_name

        print(f"  Convirtiendo: {shp_path.name} -> {output_name}")

        try:
            gdf = gpd.read_file(shp_path)
            # Reproyectar a WGS84 (EPSG:4326) para compatibilidad GeoJSON
            if gdf.crs and gdf.crs.to_epsg() != 4326:
                gdf = gdf.to_crs(epsg=4326)

            # Detectar y eliminar duplicados (mismos atributos + misma geometría)
            total_leidos = len(gdf)
            # Comparar por todas las columnas incluyendo geometría como WKT
            gdf["_geom_wkt"] = gdf.geometry.apply(lambda g: g.wkt if g else None)
            cols_comparar = [col for col in gdf.columns if col != "geometry"]
            gdf = gdf.drop_duplicates(subset=cols_comparar)
            gdf = gdf.drop(columns=["_geom_wkt"])
            unicos = len(gdf)
            duplicados = total_leidos - unicos

            if duplicados > 0:
                print(f"    📊 Registros leídos: {total_leidos} | Únicos: {unicos} | Duplicados eliminados: {duplicados}")
            else:
                print(f"    📊 Registros leídos: {total_leidos} (sin duplicados)")

            # Exportar (sobrescribir si existe)
            if output_path.exists():
                output_path.unlink()
            gdf.to_file(output_path, driver="GeoJSON")
            print(f"    ✓ Guardado ({unicos} registros)")
            exitosos += 1
        except Exception as e:
            print(f"    ✗ Error: {e}")
            errores += 1

    # Resumen
    print("\n" + "=" * 60)
    print(f"  RESUMEN: {exitosos} convertidos | {errores} errores")
    print(f"  Archivos en: {output_dir.resolve()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
