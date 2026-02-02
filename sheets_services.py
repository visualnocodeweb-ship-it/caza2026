from googleapiclient import discovery
from auth_services import get_google_credentials
from dotenv import load_dotenv
import os
import pandas as pd

load_dotenv(encoding='latin-1') # Cargar variables de entorno del archivo .env

GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME")

def get_sheets_service():
    """Obtiene y devuelve un objeto de servicio de Google Sheets."""
    credentials = get_google_credentials()
    service = discovery.build('sheets', 'v4', credentials=credentials)
    return service

def read_sheet_data(sheet_id, sheet_name):
    """
    Lee los datos de una hoja de cálculo específica de Google Sheets y los devuelve como un DataFrame de Pandas.

    Args:
        sheet_id (str): El ID de la hoja de cálculo de Google.
        sheet_name (str): El nombre de la pestaña dentro de la hoja de cálculo (ej. 'Hoja1').

    Returns:
        pd.DataFrame: Un DataFrame de Pandas con los datos de la hoja.
                      Retorna un DataFrame vacío si no se encuentran datos o hay un error.
    """
    service = get_sheets_service()
    range_name = f"'{sheet_name}'!A:ZZ" # Lee todas las columnas hasta ZZ

    if not sheet_id or not sheet_name:
        print("Error: GOOGLE_SHEET_ID o GOOGLE_SHEET_NAME no están configurados en .env")
        return pd.DataFrame()

    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=range_name
        ).execute()
        values = result.get('values', [])

        if not values or len(values) < 2:
            print("No se encontraron datos o solo se encontró la fila de encabezados.")
            return pd.DataFrame()

        headers = values[0]
        data_rows = values[1:]

        # Encuentra la primera fila con datos reales, ignorando las filas vacías
        first_real_row = next((row for row in data_rows if row), None)
        if not first_real_row:
            print("No se encontraron filas con datos después de los encabezados.")
            return pd.DataFrame(columns=headers)

        # Usa el número de columnas de la primera fila con datos como la fuente de verdad
        num_data_cols = len(first_real_row)
        trimmed_headers = headers[:num_data_cols]

        # Filtra los datos para que todas las filas tengan ese mismo número de columnas
        valid_data = [row for row in data_rows if len(row) == num_data_cols]

        if not valid_data:
            return pd.DataFrame(columns=trimmed_headers)

        df = pd.DataFrame(valid_data, columns=trimmed_headers)
        return df
    except Exception as e:
        print(f"Error al leer datos de la hoja {sheet_id}/{sheet_name}: {e}")
        raise # Re-raise the exception to be caught by the caller

def append_sheet_data(sheet_id, sheet_name, values):
    """
    Agrega filas de datos a una hoja de cálculo específica de Google Sheets.

    Args:
        sheet_id (str): El ID de la hoja de cálculo de Google.
        sheet_name (str): El nombre de la pestaña dentro de la hoja de cálculo (ej. 'Hoja1').
        values (list of list): Una lista de listas, donde cada sub-lista es una fila de datos a agregar.

    Returns:
        dict: El resultado de la operación de la API de Google Sheets.
    """
    service = get_sheets_service()
    range_name = f"'{sheet_name}'"

    body = {
        'values': values
    }
    result = service.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range=range_name,
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body=body
    ).execute()
    return result

if __name__ == '__main__':
    # Bloque de prueba para la función read_sheet_data
    print("Probando la función read_sheet_data...")
    if GOOGLE_SHEET_ID == "ID_DE_TU_HOJA_AQUI" or GOOGLE_SHEET_NAME == "NOMBRE_DE_TU_HOJA_AQUI":
        print("Por favor, configura GOOGLE_SHEET_ID y GOOGLE_SHEET_NAME en tu archivo .env antes de probar.")
    else:
        sheet_df = read_sheet_data(GOOGLE_SHEET_ID, GOOGLE_SHEET_NAME)
        if not sheet_df.empty:
            print(f"Se leyeron {len(sheet_df)} filas de la hoja '{GOOGLE_SHEET_NAME}':")
            print(sheet_df.head()) # Mostrar las primeras 5 filas
        else:
            print("No se pudo leer la hoja de cálculo.")

