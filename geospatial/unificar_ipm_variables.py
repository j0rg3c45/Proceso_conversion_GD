import pandas as pd
import os
from functools import reduce
import dbf

def limpiar_nombre_columna(col):
    """Limpia nombres de columna para compatibilidad con ArcGIS (DBF)"""
    # Eliminar espacios y caracteres especiales, limitar a 10 caracteres
    clean = col.replace(' ', '_').replace('.', '').replace('(', '').replace(')', '').replace('%', '')
    return clean[:10]

def unificar_ipm(input_path, output_path_xlsx, output_path_dbf):
    """
    Lee todas las pestañas de un archivo Excel de IPM y las unifica en una sola tabla
    basada en la columna 'cod_mzn'. Exporta a Excel y DBF.
    """
    print(f"Leyendo archivo: {input_path}")
    xl = pd.ExcelFile(input_path)
    
    # Lista de pestañas a procesar (excluyendo 'Diccionario')
    sheets = [s for s in xl.sheet_names if s.lower() != 'diccionario']
    
    dataframes = []
    
    for sheet in sheets:
        print(f"  Procesando pestaña: {sheet}")
        # Leer la pestaña. Forzamos cod_mzn a string para evitar pérdida de precisión
        df = pd.read_excel(input_path, sheet_name=sheet, dtype={'cod_mzn': str})
        
        df.columns = [c.strip() for c in df.columns]
        
        if 'cod_mzn' not in df.columns:
            print(f"  ¡ADVERTENCIA! 'cod_mzn' no encontrada en {sheet}. Saltando...")
            continue
        
        # Ajustar estructura de cod_mzn: eliminar '01' en posiciones 7-8 (índice 6 y 7)
        # Ejemplo: 760011010000000001010101 -> 7600110000000001010101
        df['cod_mzn'] = df['cod_mzn'].apply(lambda x: x[:6] + x[8:] if isinstance(x, str) and len(x) >= 8 else x)
            
        dataframes.append(df)
    
    if not dataframes:
        print("No se encontraron datos para unificar.")
        return

    print("Unificando pestañas...")
    df_unificado = reduce(lambda left, right: pd.merge(left, right, on='cod_mzn', how='outer'), dataframes)
    
    # Crear diccionario de variables
    diccionario_data = {
        'Variable': [
            'analf_', 'bajo_', 'infancia_', 'inasis_', 'rezago_', 'trab_infan_',
            'depen_', 'infor_', 'salud_', 'asegu_', 'haci_', 'pared_',
            'pisos_', 'agua_', 'excre_'
        ],
        'Descripción': [
            'Analfabetismo (%)', 'Bajo logro educativo (%)', 
            'Barreras para servicios de cuidado de primera infancia (%)',
            'Inasistencia escolar (%)', 'Rezago escolar (%)', 'Trabajo infantil (%)',
            'Dependencia económica (%)', 'Informalidad (%)', 
            'Barreras de acceso a servicios de salud (%)', 'Sin aseguramiento a salud (%)',
            'Hacinamiento crítico (%)', 'Material inadecuado de las paredes exteriores (%)',
            'Material inadecuado de los pisos (%)', 'Sin acceso a fuentes de agua mejorada (%)',
            'Eliminación inadecuada de excretas (%)'
        ]
    }
    df_diccionario = pd.DataFrame(diccionario_data)

    # Guardar Excel
    print(f"Guardando Excel en: {output_path_xlsx}")
    with pd.ExcelWriter(output_path_xlsx) as writer:
        df_unificado.to_excel(writer, sheet_name='Datos_Unificados', index=False)
        df_diccionario.to_excel(writer, sheet_name='Diccionario', index=False)
    
    # Guardar DBF para ArcGIS
    print(f"Generando archivo DBF en: {output_path_dbf}")
    df_dbf = df_unificado.copy()
    df_dbf.columns = [limpiar_nombre_columna(c) for c in df_dbf.columns]
    
    # Definir campos para el DBF
    # cod_mzn C(24), los demás N(12, 4)
    specs = "cod_mzn C(50)" # 50 por si acaso son largos
    for col in df_dbf.columns:
        if col != 'cod_mzn':
            specs += f"; {col} N(12, 4)"
            df_dbf[col] = df_dbf[col].fillna(0)
    
    # Crear tabla DBF
    if os.path.exists(output_path_dbf):
        os.remove(output_path_dbf)
        
    table = dbf.Table(output_path_dbf, specs, codepage='utf8')
    table.open(mode=dbf.READ_WRITE)
    
    for _, row in df_dbf.iterrows():
        # Crear un diccionario para los datos de la fila
        record_data = row.to_dict()
        # Asegurarse de que cod_mzn sea string y no tenga espacios raros
        record_data['cod_mzn'] = str(record_data['cod_mzn']).strip()
        table.append(record_data)
    
    table.close()

    print("¡Proceso completado exitosamente!")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    data_path = os.path.join(project_root, "data")
    
    input_file = os.path.join(data_path, "IPM - Variables (incidencias).xlsx")
    output_xlsx = os.path.join(data_path, "IPM_Unificado_Variables.xlsx")
    output_dbf = os.path.join(data_path, "IPM_Unificado_Variables.dbf")
    
    if not os.path.exists(input_file):
        base_path_ext = r"C:\Users\Jorge\Documents\GOBIERNO_DE_DATOS\Data_Steward\Pobreza_multidimensional_y_condicion_social"
        input_file = os.path.join(base_path_ext, "IPM - Variables (incidencias).xlsx")
        output_xlsx = os.path.join(base_path_ext, "IPM_Unificado_Variables.xlsx")
        output_dbf = os.path.join(base_path_ext, "IPM_Unificado_Variables.dbf")
    
    if os.path.exists(input_file):
        unificar_ipm(input_file, output_xlsx, output_dbf)
    else:
        print(f"Error: No se encontró el archivo de entrada.")
