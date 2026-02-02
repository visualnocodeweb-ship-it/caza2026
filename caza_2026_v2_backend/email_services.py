import os
from dotenv import load_dotenv
import resend

# Carga las variables de entorno desde el archivo .env
load_dotenv()

RESEND_API_KEY = os.getenv("RESEND_API_KEY")

if not RESEND_API_KEY:
    raise ValueError("RESEND_API_KEY environment variable not set.")

# Configura la API key directamente en el módulo resend
resend.api_key = RESEND_API_KEY

def send_simple_email(to_email: str, subject: str, html_content: str, sender_email: str = "onboarding@resend.dev") -> bool:
    """
    Envía un correo electrónico simple usando Resend.

    Args:
        to_email (str): La dirección de correo electrónico del destinatario.
        subject (str): El asunto del correo electrónico.
        html_content (str): El contenido HTML del cuerpo del correo electrónico.
        sender_email (str): La dirección de correo electrónico del remitente.
                            Por defecto "onboarding@resend.dev" para pruebas.
                            ¡Cámbiala a un dominio verificado en Resend!

    Returns:
        bool: True si el correo se envió con éxito, False en caso contrario.
    """
    try:
        # Asegúrate de que el sender_email esté verificado en Resend o usa el predeterminado.
        params = {
            "from": sender_email,
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        }
        
        email = resend.Emails.send(params) # Usar resend.Emails.send() directamente
        print(f"Correo enviado con Resend. ID: {email['id']}")
        return True
    except Exception as e:
        print(f"Error al enviar correo con Resend: {e}")
        return False

# --- Ejemplo de Uso (solo para pruebas directas de este módulo) ---
if __name__ == "__main__":
    # Asegúrate de tener RESEND_API_KEY en tu .env y un dominio verificado
    # o usa "onboarding@resend.dev" como remitente.
    test_recipient = "tu_email_de_prueba@ejemplo.com" # CAMBIA ESTO A UN EMAIL REAL PARA PROBAR
    test_subject = "Prueba de correo con Resend desde Python"
    test_html_content = "<h1>¡Hola desde Resend!</h1><p>Este es un correo de prueba enviado desde tu aplicación Python.</p>"
    
    # Intenta usar un remitente del .env si está configurado, de lo contrario usa el predeterminado.
    configured_sender = os.getenv("SENDER_EMAIL_RESEND", "onboarding@resend.dev") # Asumo una variable para el remitente de Resend
    
    if send_simple_email(test_recipient, test_subject, test_html_content, configured_sender):
        print("Envío de correo de prueba exitoso.")
    else:
        print("Fallo en el envío del correo de prueba.")