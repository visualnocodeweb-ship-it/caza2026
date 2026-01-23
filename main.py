import os # Changed from 'from os import getenv'
from typing import List, Optional
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import mercadopago
from reportlab.lib.pagesizes import letter # Reverted to reportlab
from reportlab.pdfgen import canvas # Reverted to reportlab
from database import Establishment, create_db_and_tables, get_db
from airtable_service import get_current_price

# Initialize Mercado Pago SDK
# IMPORTANT: Replace with your actual Mercado Pago Access Token
# It's highly recommended to use environment variables for sensitive data
MERCADOPAGO_ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN", "YOUR_MERCADOPAGO_ACCESS_TOKEN") # Changed to os.getenv
mp = mercadopago.SDK(MERCADOPAGO_ACCESS_TOKEN)

# Pydantic models
class EstablishmentBase(BaseModel):
    name: str
    owner_email: EmailStr
    cuit: str
    address: str

class EstablishmentCreate(BaseModel):
    pass

class EstablishmentSchema(EstablishmentBase):
    id: int
    payment_link: Optional[str] = None # Added payment_link to schema
    pdf_path: Optional[str] = None # Added pdf_path to schema

    class Config:
        from_attributes = True

class EstablishmentResponse(EstablishmentSchema):
    # payment_link is now part of EstablishmentSchema
    pdf_path: Optional[str] = None

class EstablishmentPaymentLink(BaseModel):
    payment_link: str

app = FastAPI()

# Ensure the 'pdfs' directory exists before mounting StaticFiles
if not os.path.exists("pdfs"):
    os.makedirs("pdfs")

# Serve static files (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve generated PDFs
app.mount("/pdfs", StaticFiles(directory="pdfs"), name="pdfs") # Re-added this mount

@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    # The 'pdfs' directory is now created before app.mount, so no need here
    # if not os.path.exists("pdfs"):
    #     os.makedirs("pdfs")

@app.get("/", response_class=HTMLResponse)
async def read_root_redirect():
    return """
    <!DOCTYPE html>
    <html>
        <head>
            <title>Redirecting...</title>
            <meta http-equiv="refresh" content="0; url=/dashboard" />
        </head>
        <body>
            Redirecting to <a href="/dashboard">Dashboard</a>
        </body>
    </html>
    """

@app.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard():
    with open("static/index.html", "r") as f:
        return HTMLResponse(content=f.read())

def create_mercadopago_preference(establishment_data: EstablishmentSchema) -> Optional[str]:
    """
    Creates a Mercado Pago preference (payment link) for the given establishment.
    """
    try:
        current_price = get_current_price() # Get price from Airtable
        preference_data = {
            "items": [
                {
                    "title": f"Registro Establecimiento {establishment_data.name}",
                    "quantity": 1,
                    "unit_price": current_price,  # Use price from Airtable
                    "currency_id": "ARS",  # Argentina Pesos
                }
            ],
            "payer": {
                "name": establishment_data.name,
                "email": establishment_data.owner_email,
            },
            "external_reference": str(establishment_data.id),
            "back_urls": {
                "success": "http://your-frontend.com/success", # Replace with actual success URL
                "failure": "http://your-frontend.com/failure", # Replace with actual failure URL
                "pending": "http://your-frontend.com/pending", # Replace with actual pending URL
            },
            "auto_return": "approved_only",
        }
        
        preference_response = mp.preference().create(preference_data)
        preference = preference_response["response"]
        return preference["init_point"]
    except Exception as e:
        print(f"Error creating Mercado Pago preference: {e}")
        return None

def generate_establishment_pdf(establishment_data: EstablishmentSchema) -> Optional[str]:
    """
    Generates a PDF certificate for the given establishment.
    """
    try:
        file_name = f"pdfs/registro_{establishment_data.id}.pdf"
        c = canvas.Canvas(file_name, pagesize=letter)
        y_position = 750
        c.drawString(100, y_position, "Inscripción de establecimiento para actividad de caza 2025.")
        y_position -= 20
        c.drawString(100, y_position, "Dirección Provincial de Fauna de Neuquén.")
        y_position -= 40
        c.drawString(100, y_position, f"ID de Registro: {establishment_data.id}")
        y_position -= 20
        c.drawString(100, y_position, f"Nombre del Establecimiento: {establishment_data.name}")
        y_position -= 20
        c.drawString(100, y_position, f"Email del Propietario: {establishment_data.owner_email}")
        y_position -= 20
        c.drawString(100, y_position, f"CUIT: {establishment_data.cuit}")
        y_position -= 20
        c.drawString(100, y_position, f"Dirección: {establishment_data.address}")
        c.save()
        print(f"PDF generated: {file_name}")
        return file_name # Return the full path
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return None

@app.post("/webhook", response_model=EstablishmentResponse)
async def handle_webhook(
    establishment: EstablishmentCreate,
    db: Session = Depends(get_db)
):
    try:
        print(f"DEBUG: Incoming Pydantic model from webhook: {establishment.model_dump_json()}") # Debug print 1
        
        db_establishment = Establishment(**establishment.model_dump()) # Use model_dump for Pydantic v2
        db.add(db_establishment)
        db.commit() # Commit here to get the ID for PDF generation
        db.refresh(db_establishment)
        print("DEBUG: db_establishment after initial commit:", db_establishment.id, db_establishment.name, db_establishment.owner_email, db_establishment.cuit, db_establishment.address) # Debug print 2

        # PDF is still generated automatically on webhook receipt
        pdf_path = generate_establishment_pdf(EstablishmentSchema.model_validate(db_establishment)) # Use model_validate for Pydantic v2
        db_establishment.pdf_path = pdf_path # Assign pdf_path to the database object
        db.commit() # Commit again to save pdf_path
        db.refresh(db_establishment)
        print("DEBUG: db_establishment after saving pdf_path:", db_establishment.id, db_establishment.name, db_establishment.owner_email, db_establishment.cuit, db_establishment.address, db_establishment.pdf_path) # Debug print 3

        return EstablishmentResponse(
            id=db_establishment.id,
            name=db_establishment.name,
            owner_email=db_establishment.owner_email,
            cuit=db_establishment.cuit,
            address=db_establishment.address,
            pdf_path=pdf_path # Ensure pdf_path is included in the response
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Establishment with this CUIT or owner email already exists."
        )

@app.post("/establishments/{establishment_id}/generate-payment", response_model=EstablishmentPaymentLink)
async def generate_payment_link_for_establishment(
    establishment_id: int,
    db: Session = Depends(get_db)
):
    db_establishment = db.query(Establishment).filter(Establishment.id == establishment_id).first()
    if not db_establishment:
        raise HTTPException(status_code=404, detail="Establishment not found")

    payment_link = create_mercadopago_preference(EstablishmentSchema.from_orm(db_establishment))
    if not payment_link:
        raise HTTPException(status_code=500, detail="Failed to generate payment link")

    db_establishment.payment_link = payment_link
    db.commit()
    db.refresh(db_establishment)
    
    return EstablishmentPaymentLink(payment_link=payment_link)


@app.get("/establishments", response_model=List[EstablishmentSchema])
async def get_establishments(db: Session = Depends(get_db)):
    establishments = db.query(Establishment).all()
    return establishments

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)