"""
=============================================================================
SCRIPT: filtro_territorios_itt.py
=============================================================================
Descripcion:
    Pipeline AUTOMATICO (sin interaccion) que filtra la data del ITT por cada
    poligono de territorio de estudio y organiza las salidas .geojson dentro
    de una estructura fija de 6 dimensiones por cada zona.

    Combina dos logicas ya existentes en el repo:
      - Deteccion de coordenadas / lectura robusta  (csv_xlx_to_shape.py)
      - Recorte espacial por poligono 'within'       (filtro_espacial_geojson.py)

    A diferencia de los scripts previos, este NO pide datos por consola:
    todas las rutas y el mapeo de fuentes estan parametrizados en la seccion
    CONFIGURACION. Esto garantiza reproducibilidad y permite ejecutarlo en
    lote o en la nube.

Flujo:
    1. Carga todos los poligonos de territorio (.shp) de la carpeta de filtros.
    2. Para cada fuente de datos (CSV/XLSX/XLS/SHP) detecta su geometria y la
       reproyecta a WGS84 (EPSG:4326).
    3. Para cada territorio recorta la fuente (sjoin 'within'), deduplica,
       valida y exporta un .geojson en la subcarpeta de dimension que le
       corresponde.
    4. Genera un reporte global y un log de fuentes sin coordenadas.

Estructura de salida (una por territorio):
    filtro_itt_territorios/
    +-- <Territorio>/
    |   +-- 1_Dimension_Seguridad/            homicidios, hurtos, comparendos
    |   +-- 2_Dimension_Cohesion_Social/      VIF + VBG
    |   +-- 3_Dimension_Movilidad/            siniestros
    |   +-- 4_Dimension_Desarrollo_Economico/ registro mercantil
    |   +-- 5_Dimension_Entorno_Urbano/       rasters (pendiente)
    |   +-- 6_Dimension_Educacion/            fuera de alcance
    +-- _reporte_global.md
    +-- _sin_coordenadas.txt

Dependencias:
    - geopandas
    - pandas
    - shapely

Ejecucion (desde Proceso_conversion_GD/):
    uv run geospatial/filtro_territorios_itt.py
=============================================================================
"""

import re
import warnings
from pathlib import Path
from datetime import datetime

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from shapely import wkt

warnings.filterwarnings("ignore", category=UserWarning)


# =============================================================================
# CONFIGURACION
# =============================================================================

# Carpeta con los poligonos de territorio (.shp). Cada .shp = una zona.
RUTA_POLIGONOS = Path(
    r"C:\Users\Jorge\Documents\GOBIERNO_DE_DATOS\Data_Steward\ITT_geo\geo_poligonos_territorio"
)

# Carpeta raiz con la data a filtrar.
RUTA_DATOS = Path(
    r"C:\Users\Jorge\Documents\GOBIERNO_DE_DATOS\Data_Steward\ITT_geo\data_general\data_2025_2026"
)

# Carpeta de salida (provisional).
RUTA_SALIDA = Path(
    r"C:\Users\Jorge\Documents\GOBIERNO_DE_DATOS\Data_Steward\ITT_geo\filtro_itt_territorios"
)

# Estructura fija de dimensiones (se crea COMPLETA en cada territorio).
DIMENSIONES = [
    "1_Dimension_Seguridad",
    "2_Dimension_Cohesion_Social",
    "3_Dimension_Movilidad",
    "4_Dimension_Desarrollo_Economico",
    "5_Dimension_Entorno_Urbano",
    "6_Dimension_Educacion",
]

# Dimensiones sin fuentes vectoriales definidas -> se dejan como placeholder.
# (Entorno Urbano y Educacion ya tienen fuentes; ver REGLAS_DIMENSION y
#  FUENTES_EXPLICITAS. Solo queda vacio lo que no tenga datos filtrables.)
DIMENSIONES_PENDIENTES = {}

# Mapeo de fuentes de datos a su dimension.
# Cada entrada: patron de nombre de archivo (regex, en minusculas) -> dimension.
# Se aplica a los archivos SUELTOS de la raiz de RUTA_DATOS.
# El primer patron que coincida define la dimension del archivo.
REGLAS_DIMENSION = [
    (r"homicidio",                 "1_Dimension_Seguridad"),
    (r"hurto",                     "1_Dimension_Seguridad"),
    (r"comparendo",                "1_Dimension_Seguridad"),
    (r"violencia_intrafamiliar",   "2_Dimension_Cohesion_Social"),
    (r"\bvif\b",                   "2_Dimension_Cohesion_Social"),
    (r"vbg",                       "2_Dimension_Cohesion_Social"),
    (r"siniestro",                 "3_Dimension_Movilidad"),
    (r"registro_mercantil",        "4_Dimension_Desarrollo_Economico"),
    (r"mercantil",                 "4_Dimension_Desarrollo_Economico"),
]

# Fuentes EXPLICITAS que viven en subcarpetas (ruta relativa a RUTA_DATOS).
# Se declaran una por una para evitar barrer archivos sin coordenadas.
# Formato: (ruta_relativa, dimension)
FUENTES_EXPLICITAS = [
    # Dimension 4 - Desarrollo Economico (registro mercantil geocodificado)
    (r"Camara_de_Comercio\camara_comercio_geocodificado_13102026.csv", "4_Dimension_Desarrollo_Economico"),
    # Dimension 5 - Entorno Urbano (obras de infraestructura, geometria LineString)
    (r"Observatorio_de_Infraestructura\2025_Consolidado.shp",             "5_Dimension_Entorno_Urbano"),
    (r"Observatorio_de_Infraestructura\2026_Consolidado_proyect.shp",     "5_Dimension_Entorno_Urbano"),
    (r"Observatorio_de_Infraestructura\2024\Infraestructura_2024.shp",    "5_Dimension_Entorno_Urbano"),
    # Dimension 6 - Educacion (sedes educativas, geometria Point)
    (r"Educacion\info_geografica\shape_info_geografica\Información geográfica sedes.shp", "6_Dimension_Educacion"),
]

# Solo se procesan los archivos SUELTOS de la raiz via REGLAS_DIMENSION.
# Las fuentes en subcarpetas se declaran en FUENTES_EXPLICITAS (no barrido ciego).
PROCESAR_RECURSIVO = False

# Extensiones de datos tabulares/espaciales soportadas como fuente.
EXTENSIONES_DATOS = {".csv", ".txt", ".xlsx", ".xls", ".shp"}

# Nombres posibles de columnas de coordenadas.
NOMBRES_LATITUD = ["latitud", "lat", "latitude", "y_geo", "coord_y"]
NOMBRES_LONGITUD = ["longitud", "lon", "long", "longitude", "lng", "x_geo", "coord_x"]
NOMBRES_X_PLANA = ["x", "este", "easting", "coord_x_plana"]
NOMBRES_Y_PLANA = ["y", "norte", "northing", "coord_y_plana"]
NOMBRES_GEOMETRY = ["geometry", "geom", "wkt", "the_geom", "shape"]

# Valores que se tratan como coordenada invalida/nula.
VALORES_NULOS = {"", "nan", "none", "null", "no aplica", "na", "n/a", "sin dato", "0", "0.0"}

CODIFICACIONES = ["utf-8", "latin-1", "cp1252"]

# -----------------------------------------------------------------------------
# REGLA DE COORDENADAS DEL PROYECTO (siempre aplicar):
#   1. Validar las coordenadas (nulos, rango, orientacion lat/lon, basura).
#   2. Detectar el SRC/CRS de origen (geografico WGS84 o plano MAGNA-SIRGAS).
#   3. Reproyectar a WGS84 (EPSG:4326) cuando no lo este.
# Bounding box geografico de Santiago de Cali / Valle del Cauca usado para
# validar coordenadas geograficas y auto-corregir orientacion lat/lon.
# -----------------------------------------------------------------------------
CALI_LAT_MIN, CALI_LAT_MAX = 2.8, 4.2
CALI_LON_MIN, CALI_LON_MAX = -77.2, -75.9


# =============================================================================
# LECTURA DE ARCHIVOS (reutiliza logica de csv_xlx_to_shape.py)
# =============================================================================

def detectar_separador(ruta: Path, codificacion: str) -> str:
    """Detecta el separador de un archivo de texto analizando el header."""
    with open(ruta, "r", encoding=codificacion) as f:
        header = f.readline()
    if not header:
        return ","
    en_comillas = False
    limpio = []
    for char in header:
        if char == '"':
            en_comillas = not en_comillas
        elif not en_comillas:
            limpio.append(char)
    header_sin_comillas = "".join(limpio)
    conteo = {";": header_sin_comillas.count(";"),
              ",": header_sin_comillas.count(","),
              "\t": header_sin_comillas.count("\t")}
    mejor = max(conteo, key=conteo.get)
    return mejor if conteo[mejor] > 0 else ","


def leer_tabular(ruta: Path) -> pd.DataFrame:
    """Lee CSV/TXT/XLSX/XLS a DataFrame con deteccion de encoding y separador."""
    ext = ruta.suffix.lower()
    if ext in (".xlsx", ".xls"):
        engine = "openpyxl" if ext == ".xlsx" else "xlrd"
        xls = pd.ExcelFile(ruta, engine=engine)
        hojas = xls.sheet_names
        if len(hojas) == 1:
            return pd.read_excel(xls, sheet_name=hojas[0])
        dfs = [pd.read_excel(xls, sheet_name=h) for h in hojas]
        dfs = [d for d in dfs if not d.empty]
        return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    for codificacion in CODIFICACIONES:
        try:
            sep = detectar_separador(ruta, codificacion)
            return pd.read_csv(ruta, encoding=codificacion, sep=sep,
                               quotechar='"', doublequote=True,
                               on_bad_lines="skip", low_memory=False)
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ValueError(f"No se pudo leer el archivo con ninguna codificacion: {ruta.name}")


# =============================================================================
# DETECCION Y CONSTRUCCION DE GEOMETRIA
# =============================================================================

def _buscar(columnas_lower: dict, candidatos: list):
    for nombre in candidatos:
        if nombre in columnas_lower:
            return columnas_lower[nombre]
    return None


def detectar_geometria(df: pd.DataFrame) -> tuple:
    """
    Determina como construir la geometria.
    Retorna (modo, info) donde modo es uno de:
      'wkt'      -> info = nombre de columna WKT
      'latlon'   -> info = (col_lat, col_lon)   coordenadas geograficas
      'xy_plana' -> info = (col_x, col_y)        coordenadas planas (MAGNA-SIRGAS)
      None       -> no hay coordenadas
    """
    columnas_lower = {str(c).lower().strip(): c for c in df.columns}

    # 1) WKT
    col_geom = _buscar(columnas_lower, NOMBRES_GEOMETRY)
    if col_geom is not None:
        muestra = df[col_geom].dropna().head(10).astype(str)
        if muestra.str.contains(r"POINT|POLYGON|LINESTRING|MULTIPOINT", case=False, regex=True).any():
            return "wkt", col_geom

    # 2) lat/lon geograficas (prioridad sobre x/y planas)
    col_lat = _buscar(columnas_lower, NOMBRES_LATITUD)
    col_lon = _buscar(columnas_lower, NOMBRES_LONGITUD)
    if col_lat and col_lon:
        return "latlon", (col_lat, col_lon)

    # 3) x/y planas
    col_x = _buscar(columnas_lower, NOMBRES_X_PLANA)
    col_y = _buscar(columnas_lower, NOMBRES_Y_PLANA)
    if col_x and col_y:
        return "xy_plana", (col_x, col_y)

    return None, None


def _a_numerico(serie: pd.Series) -> pd.Series:
    """Convierte a numerico tratando textos nulos ('NO APLICA', etc.) como NaN."""
    s = serie.astype(str).str.strip().str.lower()
    s = s.where(~s.isin(VALORES_NULOS), other=None)
    # normalizar coma decimal
    s = s.str.replace(",", ".", regex=False)
    return pd.to_numeric(s, errors="coerce")


def _crs_desde_x(x_coord: float) -> str:
    """Decide el CRS de origen para coordenadas planas segun rango X (Cali)."""
    if 1000000 < abs(x_coord) < 1200000:
        return "EPSG:3115"  # Colombia Oeste (Cali)
    return "EPSG:3116"      # Colombia Bogota (fallback)


def _parece_latitud(serie: pd.Series) -> bool:
    """Heuristica: la mediana cae dentro del rango de latitud de Cali."""
    m = serie.median()
    return CALI_LAT_MIN <= m <= CALI_LAT_MAX


def _parece_longitud(serie: pd.Series) -> bool:
    """Heuristica: la mediana cae dentro del rango de longitud de Cali."""
    m = serie.median()
    return CALI_LON_MIN <= m <= CALI_LON_MAX


def _construir_geografico_validado(df, serie_a, serie_b):
    """
    Recibe dos series numericas que se asume son coordenadas geograficas
    (en cualquier orden). Auto-detecta cual es latitud y cual longitud por
    rango de Cali, descarta registros fuera del bounding box (basura /
    corruptos) y devuelve (GeoDataFrame WGS84, n_descartados).

    Implementa la regla del proyecto: validar -> detectar -> (ya en WGS84).
    """
    a = _a_numerico(serie_a)
    b = _a_numerico(serie_b)
    base = df.copy()
    base["_a"], base["_b"] = a, b
    base = base.dropna(subset=["_a", "_b"])
    if base.empty:
        raise ValueError("Sin coordenadas numericas validas")

    # Decidir orientacion: lat vs lon por rango (no por nombre de columna)
    if _parece_latitud(base["_a"]) and _parece_longitud(base["_b"]):
        lat_col, lon_col = "_a", "_b"
    elif _parece_latitud(base["_b"]) and _parece_longitud(base["_a"]):
        lat_col, lon_col = "_b", "_a"
    else:
        # Fallback: la de valores negativos grandes es longitud
        if base["_a"].median() < 0 and base["_b"].median() > 0:
            lat_col, lon_col = "_b", "_a"
        else:
            lat_col, lon_col = "_a", "_b"

    antes = len(base)
    # Validacion dura: solo registros dentro del bounding box de Cali/Valle
    dentro = base[
        base[lat_col].between(CALI_LAT_MIN, CALI_LAT_MAX)
        & base[lon_col].between(CALI_LON_MIN, CALI_LON_MAX)
    ].copy()
    descartados = antes - len(dentro)
    if dentro.empty:
        raise ValueError("Sin coordenadas dentro del area de Cali/Valle")

    geom = [Point(lon, lat) for lon, lat in zip(dentro[lon_col], dentro[lat_col])]
    dentro = dentro.drop(columns=["_a", "_b"])
    gdf = gpd.GeoDataFrame(dentro, geometry=geom, crs="EPSG:4326")
    return gdf, descartados


def construir_gdf(df: pd.DataFrame, modo: str, info) -> tuple:
    """
    Construye un GeoDataFrame en WGS84 segun el modo detectado.
    Aplica la regla del proyecto: validar coordenadas, detectar SRC y
    reproyectar a WGS84 cuando el origen sea plano (MAGNA-SIRGAS).
    Retorna (GeoDataFrame, n_descartados).
    """
    if modo == "wkt":
        col = info
        mask = df[col].notna() & (df[col].astype(str).str.strip() != "")
        dfv = df[mask].copy()
        if dfv.empty:
            raise ValueError("Sin geometrias WKT validas")
        geoms = dfv[col].apply(wkt.loads)
        dfv = dfv.drop(columns=[col])
        x0 = geoms.iloc[0].centroid.x
        if abs(x0) > 10000:
            # Coordenadas planas -> detectar SRC y reproyectar a WGS84
            crs = _crs_desde_x(x0)
            gdf = gpd.GeoDataFrame(dfv, geometry=list(geoms), crs=crs).to_crs(epsg=4326)
        else:
            gdf = gpd.GeoDataFrame(dfv, geometry=list(geoms), crs="EPSG:4326")
        # Validacion final contra bounding box de Cali
        antes = len(gdf)
        gdf = gdf[gdf.geometry.y.between(CALI_LAT_MIN, CALI_LAT_MAX)
                  & gdf.geometry.x.between(CALI_LON_MIN, CALI_LON_MAX)].copy()
        return gdf, antes - len(gdf)

    if modo in ("latlon", "xy_plana"):
        col_a, col_b = info
        serie_a, serie_b = df[col_a], df[col_b]

        # Deteccion de SRC: si los valores lucen como metros (planas), reproyectar.
        a_num = _a_numerico(serie_a).dropna()
        es_plana = len(a_num) > 0 and a_num.abs().median() > 1000
        if es_plana:
            base = df.copy()
            base["_x"], base["_y"] = _a_numerico(serie_a), _a_numerico(serie_b)
            base = base.dropna(subset=["_x", "_y"])
            base = base[(base["_x"] != 0) | (base["_y"] != 0)].copy()
            if base.empty:
                raise ValueError("Sin coordenadas planas validas")
            crs = _crs_desde_x(base["_x"].median())
            geom = [Point(x, y) for x, y in zip(base["_x"], base["_y"])]
            base = base.drop(columns=["_x", "_y"])
            gdf = gpd.GeoDataFrame(base, geometry=geom, crs=crs).to_crs(epsg=4326)
            antes = len(gdf)
            gdf = gdf[gdf.geometry.y.between(CALI_LAT_MIN, CALI_LAT_MAX)
                      & gdf.geometry.x.between(CALI_LON_MIN, CALI_LON_MAX)].copy()
            return gdf, antes - len(gdf)

        # Geograficas: validar, auto-detectar orientacion lat/lon y recortar basura
        return _construir_geografico_validado(df, serie_a, serie_b)

    raise ValueError("Modo de geometria desconocido")


def leer_fuente_como_gdf(ruta: Path) -> tuple:
    """
    Lee cualquier fuente soportada y devuelve (GeoDataFrame WGS84, n_descartados).
    Aplica la regla del proyecto: valida coordenadas, detecta SRC y reproyecta
    a WGS84 cuando corresponde.
    """
    ext = ruta.suffix.lower()
    if ext == ".shp":
        gdf = gpd.read_file(ruta)
        if gdf.crs is None:
            gdf = gdf.set_crs(epsg=4326)
        elif gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)  # detectar SRC -> reproyectar a WGS84
        return gdf, 0

    df = leer_tabular(ruta)
    if df.empty:
        raise ValueError("Archivo vacio")
    df = df.drop_duplicates()
    modo, info = detectar_geometria(df)
    if modo is None:
        raise ValueError("SIN_COORDENADAS")
    return construir_gdf(df, modo, info)


# =============================================================================
# FILTRADO ESPACIAL Y UTILIDADES (reutiliza filtro_espacial_geojson.py)
# =============================================================================

def cargar_poligono(ruta: Path) -> gpd.GeoDataFrame:
    """Carga un poligono, lo reproyecta a WGS84 y lo disuelve."""
    gdf = gpd.read_file(ruta)
    if gdf.empty:
        raise ValueError(f"Poligono vacio: {ruta.name}")
    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=4326)
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)
    return gdf.dissolve()


def _predicado_para(gdf_datos) -> str:
    """
    Elige el predicado espacial segun el tipo de geometria dominante:
      - Puntos            -> 'within'    (el punto debe caer dentro del poligono)
      - Lineas/Poligonos  -> 'intersects' (basta que toquen el area de estudio;
                             una via que cruza el borde debe incluirse)
    """
    tipos = set(gdf_datos.geom_type.dropna().unique())
    solo_puntos = tipos.issubset({"Point", "MultiPoint"})
    return "within" if solo_puntos else "intersects"


def filtrar_por_poligono(gdf_datos, gdf_poligono):
    """Filtra registros contra el poligono con el predicado adecuado al tipo."""
    predicado = _predicado_para(gdf_datos)
    res = gpd.sjoin(gdf_datos, gdf_poligono, how="inner", predicate=predicado)
    cols_idx = [c for c in res.columns if c.startswith("index_")]
    return res.drop(columns=cols_idx, errors="ignore")


def deduplicar(gdf):
    """Elimina duplicados por atributos + geometria (WKT)."""
    antes = len(gdf)
    gdf = gdf.copy()
    gdf["_geom_wkt"] = gdf.geometry.apply(lambda g: g.wkt if g is not None else None)
    cols = [c for c in gdf.columns if c != "geometry"]
    gdf = gdf.drop_duplicates(subset=cols).drop(columns=["_geom_wkt"])
    return gdf, antes - len(gdf)


def sanear_atributos(gdf):
    """
    Convierte a texto las columnas de tipo 'object' con tipos mixtos u objetos
    no serializables (p.ej. datetime.time, bytes). Evita cuelgues/crashes del
    driver GeoJSON al exportar atributos con tipos inconsistentes.
    Las columnas numericas y de fecha nativas se conservan tal cual.
    """
    gdf = gdf.copy()
    for col in gdf.columns:
        if col == "geometry":
            continue
        serie = gdf[col]
        if serie.dtype == object:
            # Normalizar a string; nulos -> cadena vacia
            gdf[col] = serie.apply(
                lambda v: "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v)
            )
    return gdf


def dimension_de(nombre_archivo: str) -> str:
    """Determina la dimension destino segun el nombre del archivo."""
    nombre = nombre_archivo.lower()
    for patron, dim in REGLAS_DIMENSION:
        if re.search(patron, nombre):
            return dim
    return None


def listar_fuentes() -> list:
    """
    Lista las fuentes a procesar como pares (ruta, dimension).
    Combina:
      - Archivos sueltos de la raiz que coinciden con REGLAS_DIMENSION.
      - Fuentes declaradas en FUENTES_EXPLICITAS (subcarpetas).
    """
    fuentes = []  # lista de (Path, dimension)
    vistos = set()

    # 1) Archivos de la raiz por patron de nombre
    if PROCESAR_RECURSIVO:
        candidatos = [p for p in RUTA_DATOS.rglob("*") if p.is_file()]
    else:
        candidatos = [p for p in RUTA_DATOS.iterdir() if p.is_file()]
    for p in sorted(candidatos):
        dim = dimension_de(p.name)
        if p.suffix.lower() in EXTENSIONES_DATOS and dim is not None:
            fuentes.append((p, dim))
            vistos.add(p.resolve())

    # 2) Fuentes explicitas en subcarpetas
    for rel, dim in FUENTES_EXPLICITAS:
        p = (RUTA_DATOS / rel)
        if not p.exists():
            print(f"   AVISO: fuente explicita no encontrada: {rel}")
            continue
        if p.resolve() in vistos:
            continue
        fuentes.append((p, dim))
        vistos.add(p.resolve())

    return fuentes


# =============================================================================
# PIPELINE PRINCIPAL
# =============================================================================

def main():
    print("=" * 78)
    print("  FILTRADO AUTOMATICO DE DATA ITT POR TERRITORIO (salida GeoJSON)")
    print("=" * 78)

    # Validacion de rutas de entrada
    if not RUTA_POLIGONOS.is_dir():
        print(f"ERROR: No existe la carpeta de poligonos: {RUTA_POLIGONOS}")
        return
    if not RUTA_DATOS.is_dir():
        print(f"ERROR: No existe la carpeta de datos: {RUTA_DATOS}")
        return

    RUTA_SALIDA.mkdir(parents=True, exist_ok=True)

    # 1) Cargar poligonos de territorio
    poligonos = sorted(RUTA_POLIGONOS.glob("*.shp"))
    if not poligonos:
        print(f"ERROR: No hay poligonos .shp en: {RUTA_POLIGONOS}")
        return
    print(f"\n[INFO] Territorios detectados: {len(poligonos)}")
    for p in poligonos:
        print(f"   - {p.stem}")

    # 2) Listar fuentes de datos (pares ruta -> dimension)
    fuentes = listar_fuentes()
    print(f"\n[INFO] Fuentes de datos a procesar: {len(fuentes)}")
    for f, dim in fuentes:
        print(f"   - {f.name}  ->  {dim}")

    # 3) Preparar territorios: cargar poligonos (pequenos) y crear estructura.
    #    No se precargan las fuentes para no agotar memoria (algunas tienen
    #    cientos de miles de registros). Se procesan de a una.
    print("\n" + "-" * 78)
    print("Preparando territorios (poligonos + estructura de dimensiones)...")
    territorios = []  # (nombre, carpeta_zona, gdf_poligono)
    for pol in poligonos:
        territorio = pol.stem
        carpeta_zona = RUTA_SALIDA / territorio
        for dim in DIMENSIONES:
            (carpeta_zona / dim).mkdir(parents=True, exist_ok=True)
        for dim, motivo in DIMENSIONES_PENDIENTES.items():
            readme = carpeta_zona / dim / "README.txt"
            if not readme.exists():
                readme.write_text(
                    f"Dimension: {dim}\nEstado: PENDIENTE / FUERA DE ALCANCE\nMotivo: {motivo}\n",
                    encoding="utf-8",
                )
        try:
            gdf_pol = cargar_poligono(pol)
            territorios.append((territorio, carpeta_zona, gdf_pol))
        except Exception as e:
            print(f"   ERROR cargando poligono {territorio}: {e}")

    # 4) Procesar FUENTE por FUENTE (cada una se lee una vez y se libera).
    print("\n" + "=" * 78)
    print("PROCESANDO FUENTES (una lectura por fuente, filtrado a 14 territorios)")
    print("=" * 78)

    reporte = []   # filas para el reporte global
    total_exportados = 0
    sin_coordenadas = []
    errores_lectura = []
    descartes_coords = {}  # nombre -> registros descartados por validacion

    for ruta, dim in fuentes:
        print(f"\n>>> FUENTE: {ruta.name}  ({dim})")
        try:
            gdf_src, descartados = leer_fuente_como_gdf(ruta)
        except ValueError as e:
            if str(e) == "SIN_COORDENADAS":
                sin_coordenadas.append(ruta.name)
                print(f"    SKIP (sin columnas de coordenadas)")
            else:
                errores_lectura.append(f"{ruta.name}: {e}")
                print(f"    ERR ({e})")
            continue
        except Exception as e:
            errores_lectura.append(f"{ruta.name}: {e}")
            print(f"    ERR ({e})")
            continue

        geom_tipo = ",".join(sorted(set(gdf_src.geom_type.dropna().unique())))
        if descartados:
            descartes_coords[ruta.name] = descartados
            print(f"    {len(gdf_src)} {geom_tipo} validos | "
                  f"{descartados} descartados por coords invalidas/fuera de Cali")
        else:
            print(f"    {len(gdf_src)} registros {geom_tipo}")

        # Filtrar contra cada territorio
        for territorio, carpeta_zona, gdf_pol in territorios:
            try:
                filtrado = filtrar_por_poligono(gdf_src, gdf_pol)
                if filtrado.empty:
                    reporte.append((territorio, dim, ruta.name, 0, 0, "vacio"))
                    continue
                filtrado, dups = deduplicar(filtrado)
                filtrado = sanear_atributos(filtrado)
                salida = carpeta_zona / dim / f"{ruta.stem}.geojson"
                if salida.exists():
                    salida.unlink()
                filtrado.to_file(salida, driver="GeoJSON")
                total_exportados += 1
                print(f"    -> {territorio}: {len(filtrado)} (dups: {dups})")
                reporte.append((territorio, dim, ruta.name, len(filtrado), dups, "ok"))
            except Exception as e:
                print(f"    ERROR {territorio}: {e}")
                reporte.append((territorio, dim, ruta.name, 0, 0, f"error: {e}"))

        # Liberar memoria de la fuente antes de la siguiente
        del gdf_src

    # 5) Reportes
    print("\n" + "=" * 78)
    print("GENERANDO REPORTES")
    print("=" * 78)

    _escribir_reporte_global(reporte, poligonos, fuentes, total_exportados)

    if sin_coordenadas or errores_lectura or descartes_coords:
        ruta_log = RUTA_SALIDA / "_sin_coordenadas.txt"
        with open(ruta_log, "w", encoding="utf-8") as f:
            f.write("REPORTE DE VALIDACION DE COORDENADAS\n")
            f.write(f"Fecha: {datetime.now():%Y-%m-%d %H:%M:%S}\n")
            f.write("=" * 60 + "\n\n")
            if sin_coordenadas:
                f.write("SIN COLUMNAS DE COORDENADAS (requieren geocodificacion):\n")
                for n in sin_coordenadas:
                    f.write(f"  - {n}\n")
                f.write("\n")
            if descartes_coords:
                f.write("REGISTROS DESCARTADOS POR COORDENADAS INVALIDAS\n")
                f.write("(nulas, corruptas o fuera del area de Cali/Valle):\n")
                for n, c in descartes_coords.items():
                    f.write(f"  - {n}: {c} registros descartados\n")
                f.write("\n")
            if errores_lectura:
                f.write("ERRORES DE LECTURA:\n")
                for n in errores_lectura:
                    f.write(f"  - {n}\n")
        print(f"   Log de validacion de coordenadas: {ruta_log.name}")

    print(f"\n[OK] GeoJSON exportados: {total_exportados}")
    print(f"[OK] Salida: {RUTA_SALIDA}")
    print("=" * 78)


def _escribir_reporte_global(reporte, poligonos, fuentes, total_exportados):
    ruta = RUTA_SALIDA / "_reporte_global.md"
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("# Reporte de filtrado ITT por territorio\n\n")
        f.write(f"- Fecha: {datetime.now():%Y-%m-%d %H:%M:%S}\n")
        f.write(f"- Territorios: {len(poligonos)}\n")
        f.write(f"- Fuentes procesadas: {len(fuentes)}\n")
        f.write(f"- GeoJSON exportados: {total_exportados}\n\n")
        f.write("| Territorio | Dimension | Fuente | Registros | Duplicados | Estado |\n")
        f.write("|---|---|---|---|---|---|\n")
        for terr, dim, fuente, n, dups, estado in reporte:
            f.write(f"| {terr} | {dim} | {fuente} | {n} | {dups} | {estado} |\n")
    print(f"   Reporte global: {ruta.name}")


if __name__ == "__main__":
    main()
