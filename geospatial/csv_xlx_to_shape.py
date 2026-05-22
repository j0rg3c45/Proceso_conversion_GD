"""
=============================================================================
SCRIPT: csv_xlx_to_shape.py
=============================================================================
Descripción:
    Convierte archivos tabulares (.csv, .txt, .xlsx, .xls) con columnas de
    coordenadas geográficas a formatos espaciales Shapefile (.shp) y
    GeoJSON (.geojson), reproyectando automáticamente a WGS84 (EPSG:4326).

Autor: Científico de datos geoespacial
Fecha: Mayo 2026

Ejemplo de uso:
    1. Ejecutar desde la raíz del proyecto:
       uv run CARPETA_CODIGOS_TRANSFORMACION/csv_xlx_to_shape.py

    2. O activando el ambiente virtual:
       python CARPETA_CODIGOS_TRANSFORMACION/csv_xlx_to_shape.py

    3. El script pedirá:
       - La ruta de la carpeta principal (ej: Data_Steward)
       - Seleccionar una subcarpeta de trabajo
       - Confirmar la conversión

Estructura de salida:
    data_stewart/
    ├── carpeta_seleccionada/
    │   ├── archivo1.csv
    │   ├── shape_carpeta_seleccionada/
    │   │   └── archivo1.shp
    │   └── geojson_carpeta_seleccionada/
    │       └── archivo1.geojson

Dependencias:
    - pandas
    - geopandas
    - shapely
    - openpyxl (para archivos .xlsx)
=============================================================================

uv run Proceso_conversion_GD/geospatial/csv_xlx_to_shape.py



"""

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from pathlib import Path
from datetime import datetime


# =============================================================================
# CONFIGURACIÓN: Nombres posibles de columnas de coordenadas
# =============================================================================
NOMBRES_LATITUD = ["latitud", "lat", "latitude", "y"]
NOMBRES_LONGITUD = ["longitud", "lon", "long", "longitude", "lng", "x"]

# Extensiones de archivos soportados
EXTENSIONES_VALIDAS = {".csv", ".txt", ".xlsx", ".xls"}

# Codificaciones a intentar para archivos de texto
CODIFICACIONES = ["utf-8", "latin-1", "cp1252"]


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def listar_subcarpetas(ruta_principal: Path) -> list:
    """
    Lista todas las subcarpetas dentro de la ruta principal.
    Excluye carpetas de salida creadas previamente por este script.
    """
    subcarpetas = []
    for item in sorted(ruta_principal.iterdir()):
        if item.is_dir() and not item.name.startswith(("shape_", "geojson_")):
            subcarpetas.append(item)
    return subcarpetas


def buscar_archivos(carpeta: Path) -> list:
    """
    Busca archivos con extensiones válidas (.csv, .txt, .xlsx, .xls)
    dentro de la carpeta indicada (sin recursión).
    """
    archivos = []
    for item in sorted(carpeta.iterdir()):
        if item.is_file() and item.suffix.lower() in EXTENSIONES_VALIDAS:
            archivos.append(item)
    return archivos


def detectar_columnas_coordenadas(df: pd.DataFrame) -> tuple:
    """
    Detecta automáticamente las columnas de latitud y longitud
    en un DataFrame, buscando coincidencias con nombres comunes.

    Retorna:
        (col_latitud, col_longitud) o (None, None) si no encuentra
    """
    columnas_lower = {col.lower().strip(): col for col in df.columns}

    col_lat = None
    col_lon = None

    # Buscar columna de latitud
    for nombre in NOMBRES_LATITUD:
        if nombre in columnas_lower:
            col_lat = columnas_lower[nombre]
            break

    # Buscar columna de longitud
    for nombre in NOMBRES_LONGITUD:
        if nombre in columnas_lower:
            col_lon = columnas_lower[nombre]
            break

    return col_lat, col_lon


def detectar_columna_geometry(df: pd.DataFrame) -> str:
    """
    Detecta si el DataFrame tiene una columna con geometría WKT
    (ej: 'POINT (1066557.6 858049.9)').

    Retorna:
        Nombre de la columna o None si no encuentra
    """
    nombres_geometry = ["geometry", "geom", "wkt", "the_geom", "shape"]
    columnas_lower = {col.lower().strip(): col for col in df.columns}

    for nombre in nombres_geometry:
        if nombre in columnas_lower:
            col = columnas_lower[nombre]
            # Verificar que al menos un valor parece WKT
            muestra = df[col].dropna().head(5).astype(str)
            if muestra.str.contains(r"POINT|POLYGON|LINESTRING|MULTIPOINT", case=False, regex=True).any():
                return col

    return None


def crear_geodataframe_desde_wkt(df: pd.DataFrame, col_geom: str) -> gpd.GeoDataFrame:
    """
    Crea un GeoDataFrame a partir de una columna con geometría WKT.
    Detecta si las coordenadas son planas (MAGNA-SIRGAS) o geográficas (WGS84)
    y reproyecta a WGS84 si es necesario.
    """
    from shapely import wkt

    # Filtrar filas con geometría nula o vacía
    df_valido = df[df[col_geom].notna() & (df[col_geom].astype(str).str.strip() != "")].copy()

    if df_valido.empty:
        raise ValueError("No hay registros con geometría válida")

    # Parsear WKT a geometría
    try:
        geometrias = df_valido[col_geom].apply(wkt.loads)
    except Exception as e:
        raise ValueError(f"Error al parsear geometría WKT: {e}")

    # Eliminar la columna de texto WKT del DataFrame
    df_valido = df_valido.drop(columns=[col_geom])

    # Detectar CRS basado en el rango de coordenadas
    # Coordenadas planas MAGNA-SIRGAS Colombia: X ~800.000-1.200.000, Y ~600.000-1.800.000
    # Coordenadas geográficas WGS84: lon ~-80 a -66, lat ~-5 a 13
    primera_geom = geometrias.iloc[0]
    x_coord = primera_geom.centroid.x

    if abs(x_coord) > 10000:
        # Coordenadas planas - probablemente MAGNA-SIRGAS
        # EPSG:3115 = Colombia Oeste (Cali)
        # EPSG:3116 = Colombia Bogotá
        # Para Cali usamos 3115
        if x_coord > 1000000 and x_coord < 1200000:
            crs_origen = "EPSG:3115"  # Colombia Oeste (Cali)
        else:
            crs_origen = "EPSG:3116"  # Colombia Bogotá (default)
        print(f"    🌐 Coordenadas planas detectadas → CRS origen: {crs_origen}")
        gdf = gpd.GeoDataFrame(df_valido, geometry=list(geometrias), crs=crs_origen)
        gdf = gdf.to_crs(epsg=4326)
        print(f"    🌐 Reproyectado a WGS84 (EPSG:4326)")
    else:
        # Coordenadas geográficas - ya es WGS84
        gdf = gpd.GeoDataFrame(df_valido, geometry=list(geometrias), crs="EPSG:4326")

    return gdf


def detectar_separador(ruta: Path, codificacion: str) -> str:
    """
    Detecta el separador de un archivo de texto analizando el header.
    Ignora contenido entre comillas para no confundir separadores con datos.
    Retorna el separador más probable: ';', ',' o '\t'
    """
    with open(ruta, "r", encoding=codificacion) as f:
        header = f.readline()

    if not header:
        return ","

    # Remover contenido entre comillas para contar separadores reales
    en_comillas = False
    header_limpio = []
    for char in header:
        if char == '"':
            en_comillas = not en_comillas
        elif not en_comillas:
            header_limpio.append(char)

    header_sin_comillas = "".join(header_limpio)

    # Contar ocurrencias de cada separador fuera de comillas
    conteo_sep = {
        ";": header_sin_comillas.count(";"),
        ",": header_sin_comillas.count(","),
        "\t": header_sin_comillas.count("\t"),
    }

    # El separador con más ocurrencias es el más probable
    mejor_sep = max(conteo_sep, key=conteo_sep.get)

    if conteo_sep[mejor_sep] == 0:
        return ","

    return mejor_sep


def leer_archivo(ruta: Path) -> pd.DataFrame:
    """
    Lee un archivo tabular según su extensión.
    Intenta múltiples codificaciones para archivos de texto.
    Detecta automáticamente el separador antes de leer.

    Retorna:
        DataFrame con los datos o lanza excepción si falla
    """
    extension = ruta.suffix.lower()

    if extension in (".xlsx", ".xls"):
        # Archivos Excel - leer todas las hojas y concatenar
        engine = "openpyxl" if extension == ".xlsx" else "xlrd"
        xls = pd.ExcelFile(ruta, engine=engine)
        hojas = xls.sheet_names

        if len(hojas) == 1:
            df = pd.read_excel(xls, sheet_name=hojas[0])
        else:
            # Múltiples hojas: concatenar todas
            dfs = []
            for hoja in hojas:
                df_hoja = pd.read_excel(xls, sheet_name=hoja)
                if not df_hoja.empty:
                    dfs.append(df_hoja)
            if not dfs:
                return pd.DataFrame()
            df = pd.concat(dfs, ignore_index=True)
            print(f"    📑 Excel con {len(hojas)} hojas, concatenadas ({len(df)} registros total)")

        return df

    # Archivos de texto (.csv, .txt)
    for codificacion in CODIFICACIONES:
        try:
            # Detectar el separador correcto antes de leer
            separador = detectar_separador(ruta, codificacion)

            # Leer con el separador detectado y manejo de comillas
            df = pd.read_csv(
                ruta,
                encoding=codificacion,
                sep=separador,
                quotechar='"',
                doublequote=True,
                on_bad_lines="skip"
            )
            return df

        except (UnicodeDecodeError, UnicodeError):
            continue
        except Exception as e:
            raise e

    raise ValueError(f"No se pudo leer el archivo con ninguna codificación: {ruta.name}")


def crear_geodataframe(df: pd.DataFrame, col_lat: str, col_lon: str) -> gpd.GeoDataFrame:
    """
    Crea un GeoDataFrame a partir de un DataFrame con columnas de coordenadas.
    Filtra filas con coordenadas nulas o no numéricas.
    """
    # Convertir columnas a numérico, forzando errores a NaN
    df[col_lat] = pd.to_numeric(df[col_lat], errors="coerce")
    df[col_lon] = pd.to_numeric(df[col_lon], errors="coerce")

    # Filtrar filas sin coordenadas válidas
    df_valido = df.dropna(subset=[col_lat, col_lon]).copy()

    if df_valido.empty:
        raise ValueError("No hay registros con coordenadas válidas después de filtrar nulos")

    # Crear geometría de puntos
    geometria = [Point(lon, lat) for lon, lat in zip(df_valido[col_lon], df_valido[col_lat])]

    # Crear GeoDataFrame con CRS WGS84
    gdf = gpd.GeoDataFrame(df_valido, geometry=geometria, crs="EPSG:4326")

    return gdf


# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def main():
    print("=" * 70)
    print("  CONVERSIÓN DE ARCHIVOS TABULARES A SHAPEFILE Y GEOJSON")
    print("  (CSV, TXT, XLSX, XLS → SHP + GeoJSON)")
    print("=" * 70)

    while True:
        # ---------------------------------------------------------------------
        # 1. Solicitar carpeta principal
        # ---------------------------------------------------------------------
        print("\n📂 Ingresa la ruta de la carpeta principal (o 'salir' para terminar)")
        print("   (puede ser ruta absoluta o relativa al directorio actual)")
        entrada = input("   > ").strip().strip('"').strip("'")

        if entrada.lower() in ("salir", "exit", "q"):
            print("\n👋 ¡Hasta luego!")
            return

        if not entrada:
            print("\n❌ No ingresaste ninguna ruta.")
            continue

        ruta_principal = Path(entrada)

        if not ruta_principal.exists():
            print(f"\n❌ La ruta no existe: {ruta_principal.resolve()}")
            print(f"   Directorio actual: {Path.cwd()}")
            continue

        if not ruta_principal.is_dir():
            print(f"\n❌ La ruta no es una carpeta: {ruta_principal.resolve()}")
            continue

        print(f"\n✅ Carpeta encontrada: {ruta_principal.resolve()}")

        # ---------------------------------------------------------------------
        # 2. Verificar archivos en carpeta principal o listar subcarpetas
        # ---------------------------------------------------------------------
        archivos_en_raiz = buscar_archivos(ruta_principal)
        subcarpetas = listar_subcarpetas(ruta_principal)

        if not subcarpetas and not archivos_en_raiz:
            print(f"\n❌ No se encontraron subcarpetas ni archivos válidos en: {ruta_principal.resolve()}")
            continue

        # Bucle para seleccionar carpeta de trabajo
        while True:
            # Refrescar
            archivos_en_raiz = buscar_archivos(ruta_principal)
            subcarpetas = listar_subcarpetas(ruta_principal)

            print(f"\n📁 Contenido de '{ruta_principal.name}':\n")

            opciones = []

            # Opción de trabajar directamente en la carpeta si tiene archivos
            if archivos_en_raiz:
                print(f"   0. [ESTA CARPETA] ({len(archivos_en_raiz)} archivos: {', '.join(a.suffix for a in archivos_en_raiz[:5])})")
                opciones.append(("raiz", ruta_principal))

            # Listar subcarpetas
            for i, carpeta in enumerate(subcarpetas, 1):
                archivos_sub = buscar_archivos(carpeta)
                print(f"   {i}. {carpeta.name}/ ({len(archivos_sub)} archivos)")
                opciones.append(("sub", carpeta))

            if not opciones:
                print(f"\n❌ No hay archivos ni subcarpetas disponibles.")
                break

            print(f"\n   Selecciona una opción (0={len(archivos_en_raiz)} archivos aquí, 1-{len(subcarpetas)} subcarpetas)")
            print(f"   o escribe 'cambiar' para otra carpeta principal, 'salir' para terminar:")
            entrada_sub = input("   > ").strip().lower()

            if entrada_sub in ("salir", "exit", "q"):
                print("\n👋 ¡Hasta luego!")
                return

            if entrada_sub in ("cambiar", "c"):
                break  # Vuelve al bucle externo para pedir nueva carpeta principal

            try:
                seleccion = int(entrada_sub)
                if seleccion == 0 and archivos_en_raiz:
                    carpeta_trabajo = ruta_principal
                elif seleccion < 1 or seleccion > len(subcarpetas):
                    print(f"\n❌ Selección fuera de rango (0-{len(subcarpetas)}).")
                    continue
                else:
                    carpeta_trabajo = subcarpetas[seleccion - 1]
            except ValueError:
                print("\n❌ Debes ingresar un número válido.")
                continue

            print(f"\n✅ Carpeta seleccionada: {carpeta_trabajo.name}")

            # -----------------------------------------------------------------
            # 3. Detectar archivos válidos
            # -----------------------------------------------------------------
            archivos = buscar_archivos(carpeta_trabajo)

            if not archivos:
                print(f"\n❌ No se encontraron archivos válidos (.csv, .txt, .xlsx, .xls)")
                print(f"   en: {carpeta_trabajo.resolve()}")
                continue

            print(f"\n📄 Se encontraron {len(archivos)} archivos para procesar:")
            for archivo in archivos:
                print(f"   - {archivo.name} ({archivo.suffix})")

            # -----------------------------------------------------------------
            # 4. Confirmar conversión
            # -----------------------------------------------------------------
            print("\n¿Deseas continuar con la conversión? (s/n)")
            confirm = input("   > ").strip().lower()
            if confirm not in ("s", "si", "sí", "y", "yes"):
                print("\n⚠️  Conversión cancelada.")
                continue

            # -----------------------------------------------------------------
            # 5. Crear carpetas de salida
            # -----------------------------------------------------------------
            nombre_carpeta = carpeta_trabajo.name
            carpeta_shape = carpeta_trabajo / f"shape_{nombre_carpeta}"
            carpeta_geojson = carpeta_trabajo / f"geojson_{nombre_carpeta}"

            carpeta_shape.mkdir(parents=True, exist_ok=True)
            carpeta_geojson.mkdir(parents=True, exist_ok=True)

            print(f"\n📁 Carpetas de salida creadas:")
            print(f"   SHP    → {carpeta_shape.resolve()}")
            print(f"   GeoJSON → {carpeta_geojson.resolve()}")

            # -----------------------------------------------------------------
            # 6. Procesar archivos
            # -----------------------------------------------------------------
            print("\n" + "-" * 70)
            print("Iniciando conversión...\n")

            exitosos = 0
            errores = 0
            log_errores = []
            total_registros = 0

            for archivo in archivos:
                print(f"  📄 Procesando: {archivo.name}")

                try:
                    # Leer archivo
                    df = leer_archivo(archivo)

                    if df.empty:
                        msg = f"Archivo vacío: {archivo.name}"
                        print(f"    ⚠️  {msg}")
                        log_errores.append(msg)
                        errores += 1
                        continue

                    # Eliminar registros duplicados (todas las columnas iguales)
                    total_leidos = len(df)

                    # Renombrar columnas duplicadas para evitar error en GeoDataFrame
                    cols = list(df.columns)
                    conteo_cols = {}
                    cols_nuevos = []
                    for col in cols:
                        if col in conteo_cols:
                            conteo_cols[col] += 1
                            cols_nuevos.append(f"{col}_{conteo_cols[col]}")
                        else:
                            conteo_cols[col] = 0
                            cols_nuevos.append(col)
                    if cols != cols_nuevos:
                        df.columns = cols_nuevos
                        renombradas = sum(1 for a, b in zip(cols, cols_nuevos) if a != b)
                        print(f"    ⚠️  {renombradas} columna(s) con nombre duplicado renombradas")

                    df = df.drop_duplicates()
                    unicos = len(df)
                    duplicados = total_leidos - unicos

                    if duplicados > 0:
                        print(f"    📊 Registros leídos: {total_leidos} | Únicos: {unicos} | Duplicados eliminados: {duplicados}")
                    else:
                        print(f"    📊 Registros leídos: {total_leidos} (sin duplicados)")

                    # Detectar tipo de coordenadas: WKT o columnas lat/lon
                    col_geom = detectar_columna_geometry(df)

                    if col_geom is not None:
                        # Ruta WKT: columna con geometría como texto
                        print(f"    Geometría WKT detectada en columna: '{col_geom}'")
                        gdf = crear_geodataframe_desde_wkt(df, col_geom)
                    else:
                        # Ruta lat/lon: columnas separadas de coordenadas
                        col_lat, col_lon = detectar_columnas_coordenadas(df)

                        if col_lat is None or col_lon is None:
                            msg = (f"No se detectaron coordenadas (ni WKT ni lat/lon): {archivo.name} "
                                   f"(columnas disponibles: {list(df.columns)})")
                            print(f"    ⚠️  {msg}")
                            log_errores.append(msg)
                            errores += 1
                            continue

                        print(f"    Coordenadas detectadas: lat='{col_lat}', lon='{col_lon}'")
                        gdf = crear_geodataframe(df, col_lat, col_lon)
                    registros = len(gdf)
                    total_registros += registros

                    # Resetear índice para evitar problemas en exportación
                    gdf = gdf.reset_index(drop=True)

                    print(f"    📋 Columnas en salida: {len(gdf.columns) - 1} atributos + geometry")

                    # Exportar a Shapefile (eliminar existentes primero)
                    nombre_salida = archivo.stem
                    ruta_shp = carpeta_shape / f"{nombre_salida}.shp"
                    # Limpiar archivos shapefile previos
                    for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg", ".fix"]:
                        archivo_previo = carpeta_shape / f"{nombre_salida}{ext}"
                        if archivo_previo.exists():
                            archivo_previo.unlink()

                    # Truncar nombres de columna para Shapefile (máx 10 chars)
                    gdf_shp = gdf.copy()
                    columnas_originales = [col for col in gdf_shp.columns if col != "geometry"]
                    columnas_truncadas = {}
                    nombres_usados = set()

                    for col in columnas_originales:
                        if len(col) > 10:
                            nombre_base = col[:10]
                            nombre_nuevo = nombre_base
                            contador = 1
                            # Asegurar que no se repita
                            while nombre_nuevo in nombres_usados:
                                sufijo = str(contador)
                                nombre_nuevo = col[:10 - len(sufijo)] + sufijo
                                contador += 1
                            columnas_truncadas[col] = nombre_nuevo
                            nombres_usados.add(nombre_nuevo)
                        else:
                            nombres_usados.add(col)

                    if columnas_truncadas:
                        gdf_shp = gdf_shp.rename(columns=columnas_truncadas)
                        print(f"    ⚠️  SHP: {len(columnas_truncadas)} columnas truncadas a 10 chars")

                    gdf_shp.to_file(ruta_shp, driver="ESRI Shapefile", encoding="utf-8")

                    # Exportar a GeoJSON (sin truncar, conserva nombres completos)
                    ruta_geojson = carpeta_geojson / f"{nombre_salida}.geojson"
                    if ruta_geojson.exists():
                        ruta_geojson.unlink()
                    gdf.to_file(ruta_geojson, driver="GeoJSON")

                    print(f"    ✓ Convertido exitosamente ({registros} registros)")
                    exitosos += 1

                except Exception as e:
                    msg = f"Error en {archivo.name}: {str(e)}"
                    print(f"    ✗ {msg}")
                    log_errores.append(msg)
                    errores += 1

            # -----------------------------------------------------------------
            # 7. Generar log de errores
            # -----------------------------------------------------------------
            if log_errores:
                ruta_log = carpeta_trabajo / "log_errores.txt"
                with open(ruta_log, "w", encoding="utf-8") as f:
                    f.write(f"LOG DE ERRORES - Conversión espacial\n")
                    f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Carpeta: {carpeta_trabajo.resolve()}\n")
                    f.write("=" * 70 + "\n\n")
                    for i, error in enumerate(log_errores, 1):
                        f.write(f"{i}. {error}\n")
                print(f"\n📝 Log de errores guardado en: {ruta_log.name}")

            # -----------------------------------------------------------------
            # 8. Resumen final
            # -----------------------------------------------------------------
            print("\n" + "=" * 70)
            print("  RESUMEN DE CONVERSIÓN")
            print("=" * 70)
            print(f"  📊 Total de archivos encontrados:  {len(archivos)}")
            print(f"  ✅ Convertidos exitosamente:        {exitosos}")
            print(f"  ❌ Archivos con errores:            {errores}")
            print(f"  📍 Total de registros procesados:   {total_registros}")
            print(f"  📁 Shapefiles en:  {carpeta_shape.resolve()}")
            print(f"  📁 GeoJSON en:     {carpeta_geojson.resolve()}")
            print("=" * 70)

            # Preguntar si desea continuar
            print("\n" + "-" * 70)
            print("  ¿Qué deseas hacer ahora?")
            print("   1. Procesar otra subcarpeta (misma carpeta principal)")
            print("   2. Cambiar carpeta principal")
            print("   3. Salir")
            opcion = input("   > ").strip()

            if opcion == "3" or opcion.lower() in ("salir", "exit", "q"):
                print("\n👋 ¡Hasta luego!")
                return
            elif opcion == "2" or opcion.lower() in ("cambiar", "c"):
                break  # Vuelve al bucle externo
            # Si es "1" o cualquier otra cosa, continúa en el bucle de subcarpetas


if __name__ == "__main__":
    main()
