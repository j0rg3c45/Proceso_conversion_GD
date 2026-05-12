# Proceso de Conversión - Gobierno de Datos

## Estructura del proyecto

```
Proceso_conversion_GD/
├── README.md
├── requirements.txt
├── environment.yml
├── .gitignore
│
├── data/                  ← Datos de entrada (CSV, XLSX, SHP, etc.)
│   └── Geojson_filtro/    ← Polígono de recorte (.zip)
├── notebooks/             ← Notebooks Jupyter (.ipynb)
├── notebooks_py/          ← Notebooks exportados a Python (.py)
├── agent/
│   └── contexto/          ← Archivos de contexto para el agente
├── geospatial/            ← Scripts de procesamiento geoespacial
│   ├── csv_xlx_to_shape.py
│   ├── csv_xlx_to_shape.md
│   ├── shp_to_geojson.py
│   ├── filtro_espacial_geojson.py
│   └── filtro_espacial_geojson.md
└── outputs/
    └── docs/              ← Documentación generada
```
