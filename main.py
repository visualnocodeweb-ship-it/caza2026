import os
from typing import List, Optional
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
# import mercadopago
import json
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from database import Establishment, Price, create_db_and_tables, get_db

# # Initialize Mercado Pago SDK
# MERCADOPAGO_ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN", "YOUR_MERCADOPAGO_ACCESS_TOKEN")
# mp = mercadopago.SDK(MERCADOPAGO_ACCESS_TOKEN)

# --- Field Mapping Dictionary ---
FIELD_LABEL_MAP = {
    "input_text": "Nombre del establecimiento",
    "input_text_23": "Razón Social",
    "numeric_field_4": "Número CUIT",
    "phone": "WhatsApp",
    "input_text_24": "Ubicación del ACM",
    "email": "Email",
    "numeric_field_2": "Superficie del establecimiento en hectáreas",
    "input_text_2": "Departamento donde se ubica el establecimiento",
    "input_text_9": "Ubicación catastral (Sección - Fracción - Lote)",
    "input_text_10": "Coordenada Geográfica (Latitud y Longitud)",
    "dropdown_1": "Establecimiento inscripto como criadero de fauna silvestre",
    "multi_select": "Especies para caza mayor",
    "dropdown_3": "Presencia de ciervos en el campo",
    "dropdown_5": "Estimación numérica de ciervos",
    "input_text_11": "Valor estimado de ciervos",
    "input_text_13": "Margen de error en la estimación (+/- %)",
    "dropdown_4": "Evolución del número de ciervos (últimos 5 años)",
    "dropdown_6": "Porcentaje de superficie utilizada por ciervos",
    "checkbox": "Tipo de manejo o aprovechamiento de ciervos",
    "input_text_12": "Interés en mejorar prácticas de manejo",
    "input_text_15": "Proporción observada Machos/Hembras",
    "input_text_16": "Proporción en brama Machos/Hembras",
    "multi_select_2": "Ambientes preferenciales de ciervos",
    "numeric_field_3": "Estimación de ciervos extraídos por furtivos anualmente",
    "input_text_20": "Cantidad aproximada de jabalíes",
    "dropdown_8": "Evolución de la población de jabalí (últimos 3 años)",
    "input_text_19": "Cantidad aproximada de pumas",
    "dropdown_9": "Evolución de la población de pumas (últimos 3 años)",
    "input_text_21": "Daños cuantificados por pumas (último año)",
    "dropdown_10": "Presencia de poblaciones de guanacos",
    "dropdown_11": "Evolución de la población de guanacos (últimos 3 años)",
    "input_text_18": "Cantidad estimada de guanacos",
    "dropdown_14": "Solicitará evaluación para aprovechamiento de guanaco",
    "input_text_22": "Planilla completada por",
    "datetime": "Fecha del formulario"
}


# --- Pydantic Models ---
class EstablishmentBase(BaseModel):
    name: Optional[str] = None
    owner_email: Optional[str] = None
    cuit: Optional[str] = None
    address: Optional[str] = None

class EstablishmentCreate(EstablishmentBase):
    pass

class EstablishmentSchema(BaseModel):
    id: int
    name: Optional[str] = None
    owner_email: Optional[str] = None
    cuit: Optional[str] = None
    address: Optional[str] = None
    payment_link: Optional[str] = None
    pdf_path: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Schema for the full data view, including the raw webhook data
class EstablishmentFullSchema(EstablishmentSchema):
    webhook_data: Optional[str] = None

class EstablishmentResponse(EstablishmentSchema):
    pdf_path: Optional[str] = None

class EstablishmentPaymentLink(BaseModel):
    payment_link: str

class PriceBase(BaseModel):
    name: str
    value: int

class PriceCreate(PriceBase):
    pass

class PriceSchema(PriceBase):
    id: int
    updated_at: datetime

    class Config:
        from_attributes = True

app = FastAPI()

# --- Initial Setup ---
if not os.path.exists("pdfs"):
    os.makedirs("pdfs")

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/pdfs", StaticFiles(directory="pdfs"), name="pdfs")

def initialize_default_price():
    db: Session = next(get_db())
    try:
        price_name = "Inscripcion"
        default_price = 1000  # Default price in cents (e.g., 10.00 ARS)
        
        db_price = db.query(Price).filter(Price.name == price_name).first()
        if not db_price:
            new_price = Price(name=price_name, value=default_price)
            db.add(new_price)
            db.commit()
            print(f"Default price for '{price_name}' created with value: {default_price}")
        else:
            print(f"Price for '{price_name}' already exists.")
    finally:
        db.close()

@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    initialize_default_price()

# --- Price Management Functions ---
def get_current_price_from_db(db: Session, price_name: str = "Inscripcion") -> int:
    db_price = db.query(Price).filter(Price.name == price_name).first()
    if not db_price:
        raise HTTPException(status_code=404, detail=f"Price '{price_name}' not found.")
    return db_price.value

# --- Main Application Endpoints ---
@app.get("/", response_class=HTMLResponse)
async def read_root_redirect():
    return """
    <!DOCTYPE html>
    <html>
        <head><title>Redirecting...</title><meta http-equiv="refresh" content="0; url=/dashboard" /></head>
        <body>Redirecting to <a href="/dashboard">Dashboard</a></body>
    </html>
    """

@app.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard():
    with open("static/index.html", "r") as f:
        return HTMLResponse(content=f.read())

# --- Price Management Endpoints ---
@app.get("/prices", response_model=List[PriceSchema])
async def get_all_prices(db: Session = Depends(get_db)):
    prices = db.query(Price).all()
    return prices

@app.put("/prices/{name}", response_model=PriceSchema)
async def update_price(name: str, price_update: PriceCreate, db: Session = Depends(get_db)):
    db_price = db.query(Price).filter(Price.name == name).first()
    if not db_price:
        raise HTTPException(status_code=404, detail=f"Price '{name}' not found.")
    
    db_price.value = price_update.value
    db.commit()
    db.refresh(db_price)
    return db_price

# --- Mercado Pago and PDF Functions ---
# def create_mercadopago_preference(
#     establishment_data: EstablishmentSchema, db: Session
# ) -> Optional[str]:
#     try:
#         current_price = get_current_price_from_db(db) / 100  # Assuming price is stored in cents
#         preference_data = {
#             "items": [{"title": f"Registro Establecimiento {establishment_data.name}", "quantity": 1, "unit_price": current_price, "currency_id": "ARS"}],
#             "payer": {"name": establishment_data.name, "email": establishment_data.owner_email},
#             "external_reference": str(establishment_data.id),
#             "back_urls": {
#                 "success": "http://your-frontend.com/success",
#                 "failure": "http://your-frontend.com/failure",
#                 "pending": "http://your-frontend.com/pending",
#             },
#             "auto_return": "approved",
#         }
        
#         preference_response = mp.preference().create(preference_data)
#         preference = preference_response["response"]
#         return preference["init_point"]
#     except Exception as e:
#         print(f"Error creating Mercado Pago preference: {e}")
#         return None

def generate_establishment_pdf(establishment_data: EstablishmentSchema, webhook_data: dict, created_at: datetime) -> Optional[str]:
    file_name = f"pdfs/registro_{establishment_data.id}.pdf"
    c = canvas.Canvas(file_name, pagesize=letter)
    width, height = letter

    try:
        logo_path = "static/logo.png"
        if os.path.exists(logo_path):
            logo = ImageReader(logo_path)
            logo_width, logo_height = 300, 50
            c.drawImage(logo, 50, height - 80, width=logo_width, height=logo_height, preserveAspectRatio=True, mask='auto')
        else:
            print(f"WARNING: Logo not found at {logo_path}")
    except Exception as logo_error:
        print(f"ERROR: Could not add logo: {logo_error}")

    y_position = height - 120
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y_position, "Inscripción de establecimiento para actividad de caza 2026")
    y_position -= 30
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y_position, f"ID de Registro: {establishment_data.id}")
    y_position -= 20
    c.drawString(50, y_position, f"Fecha de Registro: {created_at.strftime('%d/%m/%Y %H:%M:%S')}")
    y_position -= 30
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y_position, "DATOS PRINCIPALES")
    y_position -= 20
    c.setFont("Helvetica", 10)
    main_fields = [("Nombre del Establecimiento", establishment_data.name), ("Email del Propietario", establishment_data.owner_email), ("CUIT", establishment_data.cuit), ("Dirección/Ubicación", establishment_data.address)]
    for label, value in main_fields:
        if value:
            c.drawString(50, y_position, f"{label}: {value}")
            y_position -= 18
    y_position -= 10
    if webhook_data:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y_position, "INFORMACIÓN ADICIONAL DEL FORMULARIO")
        y_position -= 20
        c.setFont("Helvetica", 9)
        excluded_keys = {
            "input_text", "email", "numeric_field_4", "input_text_24",
            "_fluentform_9_fluentformnonce", "__submission", "datetime", "created_at"
        }
        for key, value in webhook_data.items():
            if key not in excluded_keys and value:
                field_name = FIELD_LABEL_MAP.get(key, key.replace('_', ' ').title())
                if isinstance(value, list):
                    value_str = ", ".join(value)
                else:
                    value_str = str(value)

                if len(value_str) > 80:
                    words = value_str.split()
                    current_line = ""
                    for word in words:
                        if len(current_line + word) < 80:
                            current_line += word + " "
                        else:
                            if current_line: c.drawString(50, y_position, f"{field_name}: {current_line.strip()}"); y_position -= 15; field_name = ""
                            current_line = "  " + word + " "
                    if current_line.strip(): c.drawString(50, y_position, f"{field_name}: {current_line.strip()}" if field_name else f"  {current_line.strip()}"); y_position -= 15
                else:
                    c.drawString(50, y_position, f"{field_name}: {value_str}"); y_position -= 15
                if y_position < 50: c.showPage(); y_position = height - 50; c.setFont("Helvetica", 9)
    y_position -= 20
    c.setFont("Helvetica", 8)
    c.drawString(50, 30, "Dirección Provincial de Fauna de Neuquén")
    c.drawString(50, 20, f"Documento generado automáticamente - {datetime.now().strftime('%d/%m/%Y')}")
    c.save()
    return file_name


# --- Establishment and Webhook Endpoints ---
@app.post("/webhook", response_model=EstablishmentResponse)
async def handle_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type: data = await request.json()
        else: data = dict(await request.form())

        establishment_data = {
            "name": data.get("input_text"),
            "owner_email": data.get("email"),
            "cuit": data.get("numeric_field_4"),
            "address": data.get("input_text_24")
        }
        
        missing_fields = [field for field, value in establishment_data.items() if not value]
        if missing_fields:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Missing required fields: {', '.join(missing_fields)}")

        db_establishment = Establishment(**establishment_data, webhook_data=json.dumps(data, ensure_ascii=False))
        db.add(db_establishment)
        db.commit()
        db.refresh(db_establishment)

        pdf_path = generate_establishment_pdf(EstablishmentSchema.model_validate(db_establishment), webhook_data=data, created_at=db_establishment.created_at)
        if pdf_path:
            db_establishment.pdf_path = pdf_path
            db.commit()
            db.refresh(db_establishment)
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate PDF certificate")

        return EstablishmentResponse.model_validate(db_establishment)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database integrity error: {str(e)}")
    except Exception as e:
        db.rollback()
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to process webhook: {str(e)}")

# @app.post("/establishments/{establishment_id}/generate-payment", response_model=EstablishmentPaymentLink)
# async def generate_payment_link_for_establishment(establishment_id: int, db: Session = Depends(get_db)):
#     db_establishment = db.query(Establishment).filter(Establishment.id == establishment_id).first()
#     if not db_establishment:
#         raise HTTPException(status_code=404, detail="Establishment not found")

#     payment_link = create_mercadopago_preference(EstablishmentSchema.model_validate(db_establishment), db)
#     if not payment_link:
#         raise HTTPException(status_code=500, detail="Failed to generate payment link")

#     db_establishment.payment_link = payment_link
#     db.commit()
#     db.refresh(db_establishment)
    
#     return EstablishmentPaymentLink(payment_link=payment_link)

@app.get("/establishments", response_model=List[EstablishmentSchema])
async def get_establishments(db: Session = Depends(get_db)):
    establishments = db.query(Establishment).all()
    return establishments


# Endpoint to get the full data for the spreadsheet view
@app.get("/establishments/full", response_model=List[EstablishmentFullSchema])
async def get_full_establishments(db: Session = Depends(get_db)):
    establishments = db.query(Establishment).all()
    return establishments


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)