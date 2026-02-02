import os
from google_auth_oauthlib.flow import InstalledAppFlow

# Asegúrate de que estos SCOPES coincidan con los que necesitas.
# Para enviar correos, solo necesitas el de gmail.send.
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send'
]

def main():
    """
    Ejecuta el flujo de autenticación para obtener y mostrar un refresh_token.
    """
    if not os.path.exists('credentials.json'):
        print("Error: No se encuentra el archivo 'credentials.json'.")
        print("Por favor, descárgalo desde Google Cloud Console y ponlo en esta carpeta.")
        return
        
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    
    # Esto abrirá una ventana en tu navegador para que inicies sesión
    # y autorices la aplicación.
    creds = flow.run_local_server(port=0)

    # Imprime el refresh_token para que lo copies.
    print("\n--- ¡Copia el siguiente REFRESH_TOKEN! ---\n")
    print(creds.refresh_token)
    print("\n--- ¡Copia el token de arriba y pégalo en tu archivo .env! ---\n")

if __name__ == '__main__':
    main()

