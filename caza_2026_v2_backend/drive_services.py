from googleapiclient import discovery
from auth_services import get_google_credentials
from dotenv import load_dotenv
import os

load_dotenv(encoding='latin-1') # Cargar variables de entorno del archivo .env

GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

def get_drive_service():
    """Obtiene y devuelve un objeto de servicio de Google Drive."""
    credentials = get_google_credentials()
    service = discovery.build('drive', 'v3', credentials=credentials)
    return service

def list_pdfs_in_folder(folder_id):
    """
    Lista todos los archivos PDF en una carpeta específica de Google Drive.

    Args:
        folder_id (str): El ID de la carpeta de Google Drive.

    Returns:
        list: Una lista de diccionarios, cada uno con 'name' y 'id' del archivo PDF.
              Retorna una lista vacía si no se encuentran PDFs o la carpeta no existe/es inaccesible.
    """
    service = get_drive_service()
    pdfs = []
    page_token = None

    if not folder_id:
        print("Error: GOOGLE_DRIVE_FOLDER_ID no está configurado en .env")
        return []

    while True:
        try:
            # Consulta para buscar archivos PDF dentro de la carpeta especificada
            # mimeType='application/pdf' para PDFs
            # 'trashed = false' para no incluir archivos de la papelera
            query = f"mimeType='application/pdf' and '{folder_id}' in parents and trashed = false"
            response = service.files().list(
                q=query,
                spaces='drive',
                fields='nextPageToken, files(id, name, webViewLink)',
                pageToken=page_token
            ).execute()

            for file in response.get('files', []):
                pdfs.append({'id': file.get('id'), 'name': file.get('name'), 'link': file.get('webViewLink')})

            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
        except Exception as e:
            print(f"Error al listar PDFs en la carpeta {folder_id}: {e}")
            break
    return pdfs

if __name__ == '__main__':
    # Bloque de prueba para la función list_pdfs_in_folder
    print("Probando la función list_pdfs_in_folder...")
    if GOOGLE_DRIVE_FOLDER_ID == "ID_DE_TU_CARPETA_AQUI":
        print("Por favor, configura GOOGLE_DRIVE_FOLDER_ID en tu archivo .env antes de probar.")
    else:
        pdf_list = list_pdfs_in_folder(GOOGLE_DRIVE_FOLDER_ID)
        if pdf_list:
            print(f"Se encontraron {len(pdf_list)} PDFs:")
            for pdf in pdf_list:
                print(f"  - Nombre: {pdf['name']}, ID: {pdf['id']}")
        else:
            print("No se encontraron PDFs en la carpeta especificada o hubo un error.")