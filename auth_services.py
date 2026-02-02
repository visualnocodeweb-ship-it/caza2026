import os
from google.oauth2 import service_account
from googleapiclient import discovery

# Define los 'scopes' o permisos que nuestra aplicación solicitará.
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly"
]

# Nombre del archivo JSON de la clave de la cuenta de servicio
SERVICE_ACCOUNT_FILE = "service_account.json"

def get_google_credentials():
    """
    Carga las credenciales de la cuenta de servicio desde el archivo JSON.
    """
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        raise FileNotFoundError(
            f"El archivo de clave de la cuenta de servicio '{SERVICE_ACCOUNT_FILE}' no se encontró. "
            "Asegúrate de haberlo descargado desde Google Cloud Console."
        )

    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return creds

if __name__ == '__main__':
    # Este bloque de código es para probar que la autenticación funciona.
    try:
        credentials = get_google_credentials()
        print("¡Autenticación con Cuenta de Servicio exitosa!")

        # Opcional: Probar la conexión creando un servicio de Drive
        drive_service = discovery.build('drive', 'v3', credentials=credentials)
        print("Servicio de Google Drive creado exitosamente.")

        # Opcional: Probar la conexión creando un servicio de Sheets
        sheets_service = discovery.build('sheets', 'v4', credentials=credentials)
        print("Servicio de Google Sheets creado exitosamente.")

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Ocurrió un error inesperado durante la autenticación: {e}")
