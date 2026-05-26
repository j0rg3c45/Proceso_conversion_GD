# unificar_ipm_variables.py — Unificación de variables IPM

Consolida múltiples pestañas de un archivo Excel de Índice de Pobreza Multidimensional (IPM) en una única tabla unificada.

## Propósito
Cuando los datos de IPM se encuentran distribuidos en diferentes pestañas (una por variable), este script permite unificarlos usando el código de manzana (`cod_mzn`) como llave de cruce.

## Características
- **Detección automática de pestañas**: Procesa todas las hojas del Excel excepto la pestaña "Diccionario".
- **Cruce de datos (Merge)**: Realiza un `outer join` por la columna `cod_mzn`, asegurando que no se pierdan registros si una manzana no aparece en todas las variables.
- **Limpieza de nombres**: Elimina espacios en blanco accidentales en los nombres de las columnas.
- **Salida directa**: Genera un nuevo archivo Excel unificado en la misma ruta de origen.

## Variables procesadas habitualmente
El script está diseñado para manejar variables como:
- `analf_`: Analfabetismo
- `bajo_`: Bajo logro educativo
- `infancia_`: Barreras para servicios de cuidado de primera infancia
- `inasis_`: Inasistencia escolar
- `rezago_`: Rezago escolar
- `trab_infan_`: Trabajo infantil
- `depen_`: Dependencia económica
- `infor_`: Informalidad
- `salud_`: Barreras de acceso a servicios de salud
- `asegu_`: Sin aseguramiento a salud
- `haci_`: Hacinamiento crítico
- `pared_`: Material inadecuado de las paredes exteriores
- `pisos_`: Material inadecuado de los pisos
- `agua_`: Sin acceso a fuentes de agua mejorada
- `excre_`: Eliminación inadecuada de excretas

## Uso

```bash
uv run geospatial/unificar_ipm_variables.py
```

## Requisitos
- Archivo Excel con columna `cod_mzn` en cada pestaña.
- Librerías: `pandas`, `openpyxl`.
