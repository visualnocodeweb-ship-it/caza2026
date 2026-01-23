import os # Changed from 'from os import getenv'
from typing import List, Optional
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import mercadopago
from weasyprint import HTML, CSS # New PDF library
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

class EstablishmentCreate(EstablishmentBase):
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
    Generates a PDF certificate for the given establishment using WeasyPrint.
    """
    try:
        file_name_only = f"registro_{establishment_data.id}.pdf"
        file_path_with_dir = os.path.join("pdfs", file_name_only) # Full path for saving

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Certificado de Registro</title>
            <style>
                body {{ font-family: sans-serif; margin: 2cm; }}
                h1 {{ color: #333; }}
                p {{ margin-bottom: 0.5cm; }}
                .highlight {{ background-color: #f0f0f0; padding: 5px; }}
            </style>
        </head>
        <body>
            <h1>Inscripción de establecimiento para actividad de caza 2025.</h1>
            <p>Dirección Provincial de Fauna de Neuquén.</p>
            <p class="highlight"><strong>ID de Registro:</strong> {establishment_data.id}</p>
            <p><strong>Nombre del Establecimiento:</strong> {establishment_data.name}</p>
            <p><strong>Email del Propietario:</strong> {establishment_data.owner_email}</p>
            <p><strong>CUIT:</strong> {establishment_data.cuit}</p>
            <p><strong>Dirección:</strong> {establishment_data.address}</p>
            <p>Este certificado confirma el registro exitoso en el Sistema Caza 2025.</p>
        </body>
        </html>
        """
        
        HTML(string=html_content).write_pdf(file_path_with_dir)
        print(f"PDF generated: {file_path_with_dir}")
        return file_name_only # Return only the filename
    except Exception as e:
        print(f"Error generating PDF with WeasyPrint: {e}")
        return None

@app.post("/webhook", response_model=EstablishmentResponse)
async def handle_webhook(
    establishment: EstablishmentCreate,
    db: Session = Depends(get_db)
):
    try:
        db_establishment = Establishment(**establishment.dict())
        db.add(db_establishment)
        db.commit() # Commit here to get the ID for PDF generation
        db.refresh(db_establishment)
        print("Received webhook payload and saved to DB (initial):", db_establishment.name, db_establishment.id)

        # PDF is still generated automatically on webhook receipt
        pdf_path = generate_establishment_pdf(EstablishmentSchema.from_orm(db_establishment))
        db_establishment.pdf_path = pdf_path # Assign pdf_path to the database object
        db.commit() # Commit again to save pdf_path
        db.refresh(db_establishment)
        print("Received webhook payload and saved to DB (final):", db_establishment.name, db_establishment.id, db_establishment.pdf_path)

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