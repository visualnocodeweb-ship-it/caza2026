from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import datetime
import pandas as pd # Import pandas for DataFrame handling if needed
import json # Import json for json.dumps
import mercadopago # Import Mercado Pago SDK
from pydantic import BaseModel # Import BaseModel for Pydantic models

# Import your existing service files
from sheets_services import read_sheet_data, append_sheet_data, GOOGLE_SHEET_ID, GOOGLE_SHEET_NAME
from drive_services import list_pdfs_in_folder, GOOGLE_DRIVE_FOLDER_ID
from email_services import send_simple_email # Importa la función de envío de correos


# Load environment variables (important for GOOGLE_SHEET_ID, etc.)
load_dotenv(encoding='latin-1') # Ensure encoding is set as before

# Define API specific Sheet IDs and Names
# Assuming GOOGLE_SHEET_ID is the main sheet
MAIN_SHEET_ID = GOOGLE_SHEET_ID
MAIN_SHEET_NAME = GOOGLE_SHEET_NAME
PRICES_SHEET_ID = os.getenv("PRICES_SHEET_ID", GOOGLE_SHEET_ID) # Use main ID or specific
PRICES_SHEET_NAME = os.getenv("PRICES_SHEET_NAME", "precios") # Default to "precios"

# Mercado Pago configuration
MERCADOPAGO_ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
mp_sdk = None
mp_sdk_initialized = False

if MERCADOPAGO_ACCESS_TOKEN:
    try:
        mp_sdk = mercadopago.SDK(MERCADOPAGO_ACCESS_TOKEN)
        mp_sdk_initialized = True
        print("INFO: Mercado Pago SDK inicializado exitosamente.")
    except Exception as e:
        print(f"ERROR: Fallo al inicializar Mercado Pago SDK: {e}")
        # Considerar loguear esto en la hoja de errores si es apropiado
else:
    print("WARNING: MERCADOPAGO_ACCESS_TOKEN no configurado. La funcionalidad de Mercado Pago estará deshabilitada.")

# Payments Log Sheet Configuration
PAGOS_SHEET_ID = os.getenv("PAGOS_SHEET_ID")
PAGOS_SHEET_NAME = os.getenv("PAGOS_SHEET_NAME", "pagos")
if not PAGOS_SHEET_ID:
    raise ValueError("PAGOS_SHEET_ID environment variable not set for payments log.")

SENDER_EMAIL_RESEND = os.getenv("SENDER_EMAIL_RESEND")
if not SENDER_EMAIL_RESEND:
    raise ValueError("SENDER_EMAIL_RESEND environment variable not set.")

app = FastAPI()

class EmailRequest(BaseModel):
    to_email: str
    subject: str
    html_content: str
    
@app.post("/api/send-email")
async def send_email_endpoint(email_request: EmailRequest):
    try:
        success = send_simple_email(
            to_email=email_request.to_email,
            subject=email_request.subject,
            html_content=email_request.html_content,
            sender_email=SENDER_EMAIL_RESEND # Usar el remitente configurado globalmente
        )
        if success:
            return {"status": "success", "message": "Email enviado exitosamente."}
        else:
            raise HTTPException(status_code=500, detail="Fallo al enviar el email.")
    except Exception as e:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error_message = f"{timestamp} - API Error al enviar email: {str(e)}"
        print(f"ERROR: {error_message}") # Imprimir el error en consola
        raise HTTPException(status_code=500, detail=f"Error al enviar email: {str(e)}")


# --- Caching Mechanism for Google Sheet Data ---
_cached_sheet_data = None
_cache_timestamp = None
CACHE_DURATION_SECONDS = 300 # Cache expires after 5 minutes

def _get_sheet_data_cached():
    global _cached_sheet_data, _cache_timestamp
    current_time = datetime.datetime.now()

    if _cached_sheet_data and _cache_timestamp and (current_time - _cache_timestamp).total_seconds() < CACHE_DURATION_SECONDS:
        print("DEBUG: Returning data from cache.")
        return _cached_sheet_data
    
    print("DEBUG: Cache expired or empty, fetching fresh data from Google Sheets.")
    df = read_sheet_data(MAIN_SHEET_ID, MAIN_SHEET_NAME)
    
    if not df.empty and 'fecha_creacion' in df.columns:
        # Convert 'fecha_creacion' to datetime, coercing errors
        df['fecha_creacion'] = pd.to_datetime(df['fecha_creacion'], errors='coerce')
        # Sort by 'fecha_creacion' in descending order, putting NaT (invalid dates) at the end
        df = df.sort_values(by='fecha_creacion', ascending=False, na_position='last')
        
    _cached_sheet_data = df.to_dict(orient="records")
    _cache_timestamp = current_time
    return _cached_sheet_data
# --- End Caching Mechanism ---

# Configure CORS (Cross-Origin Resource Sharing)
# This allows your React frontend (running on a different port) to make requests to this API
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",  # React app new port
    "http://127.0.0.1:3001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Caza 2026 API"}

@app.get("/api/inscripciones")
async def get_inscripciones(page: int = 1, limit: int = 10):
    try:
        inscripciones_data = _get_sheet_data_cached() # Use cached data, now sorted
        
        # Calculate pagination
        total_records = len(inscripciones_data)
        start_index = (page - 1) * limit
        end_index = start_index + limit
        
        paginated_data = inscripciones_data[start_index:end_index]

        pdf_list = list_pdfs_in_folder(GOOGLE_DRIVE_FOLDER_ID)
        # print(f"DEBUG: PDF List from Drive: {pdf_list}") # DEBUG PRINT
        
        pdf_link_map = {}
        if pdf_list:
            for pdf in pdf_list:
                name_part, extension = os.path.splitext(pdf['name'])
                cleaned_name = name_part.strip()
                pdf_link_map[f"{name_part.strip()}{extension}"] = pdf['link']

        for inscripcion in paginated_data: # Iterate over paginated_data instead of all data
            # print(f"DEBUG: Processing inscripcion: {inscripcion}") # NUEVO DEBUG PRINT
            # Obtener el nombre del archivo PDF completo de la columna 'numero_inscripcion'
            # Asumimos que la columna 'numero_inscripcion' ya contiene el nombre completo del archivo PDF,
            # por ejemplo, 'fau_inscr6980a01326482.pdf'.
            expected_pdf_name = f"{str(inscripcion.get('numero_inscripcion', '')).strip()}.pdf"
            
            found_pdf_link = None
            if expected_pdf_name:
                found_pdf_link = pdf_link_map.get(expected_pdf_name, None)
            
            # print(f"DEBUG: Found PDF Link for '{expected_pdf_name}': {found_pdf_link}") # DEBUG PRINT
            
            inscripcion['pdf_link'] = found_pdf_link
            
        return {
            "data": paginated_data,
            "total_records": total_records,
            "page": page,
            "limit": limit,
            "total_pages": (total_records + limit - 1) // limit # Ceiling division
        }
    except Exception as e:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error_message = f"{timestamp} - API Error fetching inscripciones: {str(e)}"
        print(f"ERROR: {error_message}") # Imprimir el error en consola
        raise HTTPException(status_code=500, detail=f"Failed to fetch inscripciones: {str(e)}")

@app.get("/api/pdfs")
async def get_pdfs():
    try:
        pdfs = list_pdfs_in_folder(GOOGLE_DRIVE_FOLDER_ID)
        return pdfs
    except Exception as e:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error_message = f"{timestamp} - API Error fetching PDFs: {str(e)}"
        print(f"ERROR: {error_message}") # Imprimir el error en consola
        raise HTTPException(status_code=500, detail=f"Failed to fetch PDFs: {str(e)}")

class PaymentRequest(BaseModel):
    inscription_id: str
    email: str
    item_title: str
    nombre_establecimiento: str # Added to easily log to sheet

# --- Price Caching Mechanism for Google Sheet Data ---
_cached_price = None
_price_cache_timestamp = None
PRICE_CACHE_DURATION_SECONDS = 3600 # Cache expires after 1 hour for prices (less frequent changes)

def _get_fixed_price_cached():
    global _cached_price, _price_cache_timestamp
    current_time = datetime.datetime.now()

    if _cached_price and _price_cache_timestamp and (current_time - _price_cache_timestamp).total_seconds() < PRICE_CACHE_DURATION_SECONDS:
        print("DEBUG: Returning price from cache.")
        return _cached_price
    
    print("DEBUG: Price cache expired or empty, fetching fresh price from Google Sheets.")
    try:
        # Read a specific cell (B2) from the 'precios' sheet
        service = get_sheets_service()
        result = service.spreadsheets().values().get(
            spreadsheetId=PRICES_SHEET_ID,
            range=f"'{PRICES_SHEET_NAME}'!B2"
        ).execute()
        price_value = result.get('values', [['0']])[0][0] # Get B2 value, default to '0'
        price = float(price_value)
        _cached_price = price
        _price_cache_timestamp = current_time
        return price
    except Exception as e:
        print(f"Error al leer el precio de la hoja '{PRICES_SHEET_NAME}' celda B2: {e}")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error_message = f"{timestamp} - API Error fetching fixed price: {str(e)}"
        print(f"ERROR: {error_message}") # Imprimir el error en consola
        return 0.0 # Return 0 or handle as appropriate

# --- End Price Caching Mechanism ---
    
@app.post("/api/link-data")
async def link_data():
    global _cached_sheet_data, _cache_timestamp
    try:
        # Force cache invalidation so that the next read fetches fresh data
        _cached_sheet_data = None
        _cache_timestamp = None
        
        # Optionally, you can trigger a read here to proactively refresh the cache
        # For this specific implementation, get_inscripciones will trigger the refresh
        # so this endpoint just needs to clear the cache.
        return {"status": "success", "message": "Cache invalidado. Los datos se actualizarán en la próxima solicitud."}
    except Exception as e:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error_message = f"{timestamp} - API Error linking data: {str(e)}"
        print(f"ERROR: {error_message}") # Imprimir el error en consola
        raise HTTPException(status_code=500, detail=f"Failed to link data: {str(e)}")

@app.post("/api/create-payment-preference")
async def create_payment_preference(payment_request: PaymentRequest):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %M:%S")
    log_type = "fallido" # Default to failed, change to exitoso on success
    payment_link = "N/A"
    mp_preference_id = "N/A"

    if not mp_sdk_initialized:
        error_message = "La funcionalidad de Mercado Pago no está disponible debido a la falta de configuración del token."
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"ERROR: {error_message}") # Imprimir el error en consola
        raise HTTPException(status_code=503, detail=error_message)
    
    try:
        fixed_price = _get_fixed_price_cached()
        if fixed_price <= 0:
            raise ValueError("Precio de pago no válido o no configurado.")

        preference_data = {
            "items": [
                {
                    "title": payment_request.item_title,
                    "quantity": 1,
                    "unit_price": fixed_price,
                }
            ],
            "payer": {
                "email": payment_request.email,
            },
            # You might want to add back_urls for success, pending, failure
            # "back_urls": {
            #     "success": "http://localhost:3000/success",
            #     "pending": "http://localhost:3000/pending",
            #     "failure": "http://localhost:3000/failure",
            # },
            "external_reference": payment_request.inscription_id, # Use inscription ID to link payments
            "notification_url": "https://your-webhook-url.com/mercadopago-webhook", # IMPORTANT: Set up a real webhook
            "auto_return": "approved", # Automatically return to success URL on approved payments
        }

        preference_response = mp_sdk.preference().create(preference_data)
        preference = preference_response["response"]

        payment_link = preference["init_point"] if "init_point" in preference else preference["sandbox_init_point"]
        mp_preference_id = preference.get("id", "N/A")
        log_type = "exitoso" # Mark as successful

        return {"payment_link": payment_link}
    except Exception as e:
        error_message = f"{timestamp} - API Error creating Mercado Pago preference: {str(e)}"
        print(f"ERROR: {error_message}") # Imprimir el error en consola
        raise HTTPException(status_code=500, detail=f"Failed to create payment preference: {str(e)}")

@app.post("/api/simulate-payment")
async def simulate_payment(payment_request: PaymentRequest):
    if not mp_sdk_initialized: # Although simulate uses dummy link, good to indicate MP functionality might be down
        error_message = "La funcionalidad de Mercado Pago no está disponible. Simulación no operativa."
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"ERROR: {error_message}") # Imprimir el error en consola
        raise HTTPException(status_code=503, detail=error_message)

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    dummy_payment_link = "https://sandbox.mercadopago.com.ar/checkout/v1/redirect?pref_id=TEST_SIMULATED_PAYMENT_LINK" # Generic dummy link
    fixed_price = _get_fixed_price_cached() # Fetch price for logging

    log_entry = [
        timestamp,
        "SIMULATED",
        payment_request.inscription_id,
        payment_request.email,
        str(fixed_price), # Include fixed price
        payment_request.item_title,
        "SIMULATED_PREF_ID",
        dummy_payment_link,
        # Add any other relevant payment details
    ]
    print(f"DEBUG: Simulated payment log entry: {log_entry}") # Imprimir el log en consola
    # No se intenta append_sheet_data aquí

    return {"payment_link": dummy_payment_link}