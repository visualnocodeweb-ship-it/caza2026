import os # Changed from 'from os import getenv'
from typing import List, Optional
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import mercadopago
import json
from datetime import datetime
from reportlab.lib.pagesizes import letter # Reverted to reportlab
from reportlab.pdfgen import canvas # Reverted to reportlab
from reportlab.lib.utils import ImageReader
from database import Establishment, create_db_and_tables, get_db
from airtable_service import get_current_price

# Initialize Mercado Pago SDK
# IMPORTANT: Replace with your actual Mercado Pago Access Token
# It's highly recommended to use environment variables for sensitive data
MERCADOPAGO_ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN", "YOUR_MERCADOPAGO_ACCESS_TOKEN") # Changed to os.getenv
mp = mercadopago.SDK(MERCADOPAGO_ACCESS_TOKEN)

# Pydantic models
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
    webhook_data: Optional[str] = None
    created_at: Optional[str] = None

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

def generate_establishment_pdf(establishment_data: EstablishmentSchema, webhook_data: dict, created_at: datetime) -> Optional[str]:
    """
    Generates a PDF certificate for the given establishment with complete webhook data.
    """
    try:
        file_name = f"pdfs/registro_{establishment_data.id}.pdf"
        c = canvas.Canvas(file_name, pagesize=letter)
        width, height = letter

        # Add logo at the top
        try:
            logo_path = "static/logo.png"
            if os.path.exists(logo_path):
                logo = ImageReader(logo_path)
                # Logo dimensions - adjust as needed
                logo_width = 300
                logo_height = 50
                c.drawImage(logo, 50, height - 80, width=logo_width, height=logo_height, preserveAspectRatio=True, mask='auto')
            else:
                print(f"WARNING: Logo not found at {logo_path}")
        except Exception as logo_error:
            print(f"ERROR: Could not add logo: {logo_error}")

        y_position = height - 120

        # Title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, y_position, "Inscripción de establecimiento para actividad de caza 2026")
        y_position -= 30

        # Registration ID and Date
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y_position, f"ID de Registro: {establishment_data.id}")
        y_position -= 20
        c.drawString(50, y_position, f"Fecha de Registro: {created_at.strftime('%d/%m/%Y %H:%M:%S')}")
        y_position -= 30

        # Main fields
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y_position, "DATOS PRINCIPALES")
        y_position -= 20

        c.setFont("Helvetica", 10)
        main_fields = [
            ("Nombre del Establecimiento", establishment_data.name),
            ("Email del Propietario", establishment_data.owner_email),
            ("CUIT", establishment_data.cuit),
            ("Dirección/Ubicación", establishment_data.address)
        ]

        for label, value in main_fields:
            if value:
                c.drawString(50, y_position, f"{label}: {value}")
                y_position -= 18

        y_position -= 10

        # Additional webhook data
        if webhook_data:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(50, y_position, "INFORMACIÓN ADICIONAL DEL FORMULARIO")
            y_position -= 20
            c.setFont("Helvetica", 9)

            # Filter out the main fields we already displayed
            excluded_keys = {'name', 'owner_email', 'cuit', 'address'}

            for key, value in webhook_data.items():
                if key not in excluded_keys and value:
                    # Format field name (replace underscores with spaces, capitalize)
                    field_name = key.replace('_', ' ').title()

                    # Handle long values
                    value_str = str(value)
                    if len(value_str) > 80:
                        # Split long text into multiple lines
                        words = value_str.split()
                        current_line = ""
                        for word in words:
                            if len(current_line + word) < 80:
                                current_line += word + " "
                            else:
                                if current_line:
                                    c.drawString(50, y_position, f"{field_name}: {current_line.strip()}")
                                    y_position -= 15
                                    field_name = ""  # Only show field name once
                                current_line = "  " + word + " "
                        if current_line.strip():
                            c.drawString(50, y_position, f"{field_name}: {current_line.strip()}" if field_name else f"  {current_line.strip()}")
                            y_position -= 15
                    else:
                        c.drawString(50, y_position, f"{field_name}: {value_str}")
                        y_position -= 15

                    # Check if we need a new page
                    if y_position < 50:
                        c.showPage()
                        y_position = height - 50
                        c.setFont("Helvetica", 9)

        # Footer
        y_position -= 20
        c.setFont("Helvetica-Italic", 8)
        c.drawString(50, 30, "Dirección Provincial de Fauna de Neuquén")
        c.drawString(50, 20, f"Documento generado automáticamente - {datetime.now().strftime('%d/%m/%Y')}")

        c.save()
        print(f"PDF generated: {file_name}")
        return file_name
    except Exception as e:
        print(f"Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        return None

@app.post("/webhook", response_model=EstablishmentResponse)
async def handle_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        # Parse incoming data - Fluent Form Pro can send JSON or form-data
        content_type = request.headers.get("content-type", "")
        print(f"DEBUG: Content-Type: {content_type}")

        if "application/json" in content_type:
            data = await request.json()
            print(f"DEBUG: Received JSON data: {data}")
        else:
            # Handle form-data
            form = await request.form()
            data = dict(form)
            print(f"DEBUG: Received form-data: {data}")

        # Extract data directly from Fluent Form webhook
        # Fields: name, owner_email, cuit, address (as configured in Fluent Form)
        establishment_data = {
            "name": data.get("name"),
            "owner_email": data.get("owner_email"),
            "cuit": data.get("cuit"),
            "address": data.get("address")
        }

        print(f"DEBUG: Mapped establishment data: {establishment_data}")

        # Validate that we received all required fields
        missing_fields = [field for field, value in establishment_data.items() if not value]
        if missing_fields:
            print(f"WARNING: Missing fields from webhook: {missing_fields}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required fields: {', '.join(missing_fields)}"
            )

        # Create database record with all webhook data
        db_establishment = Establishment(
            **establishment_data,
            webhook_data=json.dumps(data, ensure_ascii=False)  # Store complete webhook data as JSON
        )
        db.add(db_establishment)
        db.commit()
        db.refresh(db_establishment)

        print(f"DEBUG: Created establishment with ID: {db_establishment.id}")
        print(f"DEBUG: Establishment details - Name: {db_establishment.name}, Email: {db_establishment.owner_email}, CUIT: {db_establishment.cuit}, Address: {db_establishment.address}")
        print(f"DEBUG: Complete webhook data saved: {db_establishment.webhook_data}")

        # Generate PDF automatically with complete webhook data
        try:
            pdf_path = generate_establishment_pdf(
                EstablishmentSchema.model_validate(db_establishment),
                webhook_data=data,
                created_at=db_establishment.created_at
            )
            if pdf_path:
                db_establishment.pdf_path = pdf_path
                db.commit()
                db.refresh(db_establishment)
                print(f"DEBUG: PDF generated successfully: {pdf_path}")
                print(f"DEBUG: PDF accessible at: https://caza2026.onrender.com/{pdf_path}")
            else:
                print(f"ERROR: PDF generation returned None")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to generate PDF certificate"
                )
        except Exception as pdf_error:
            print(f"ERROR: Failed to generate PDF: {pdf_error}")
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate PDF: {str(pdf_error)}"
            )

        return EstablishmentResponse(
            id=db_establishment.id,
            name=db_establishment.name,
            owner_email=db_establishment.owner_email,
            cuit=db_establishment.cuit,
            address=db_establishment.address,
            pdf_path=pdf_path
        )
    except IntegrityError as e:
        db.rollback()
        print(f"ERROR: IntegrityError: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Establishment with this CUIT or owner email already exists."
        )
    except Exception as e:
        db.rollback()
        print(f"ERROR: Unexpected error in webhook: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process webhook: {str(e)}"
        )

@app.post("/establishments/{establishment_id}/generate-payment", response_model=EstablishmentPaymentLink)
async def generate_payment_link_for_establishment(
    establishment_id: int,
    db: Session = Depends(get_db)
):
    db_establishment = db.query(Establishment).filter(Establishment.id == establishment_id).first()
    if not db_establishment:
        raise HTTPException(status_code=404, detail="Establishment not found")

    payment_link = create_mercadopago_preference(EstablishmentSchema.model_validate(db_establishment))
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