# main.py - Combined FastAPI + React server
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import pandas as pd
import openai
import pdfplumber
from fpdf import FPDF
import tempfile
import os
import uuid
import io
from typing import Optional

app = FastAPI(title="AI Business Analysis API", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store temporary files
TEMP_DIR = tempfile.gettempdir()

# Your existing functions here (process_company_questions, etc.)
def process_company_questions(entry, api_key):
    """Generate personalized questions for a company"""
    openai.api_key = api_key
    
    company_name = entry.get("Business Name (pas de caractères spéciaux)", "Unnamed Company")
    company_description = "\n".join([f"{key}: {value}" for key, value in entry.items() if pd.notna(value)])

    prompt = f"""
Vous êtes analyste stratégique en France, spécialisé dans le diagnostic des PME. Votre mission consiste à générer un questionnaire personnalisé de 50 à 100 questions diagnostiques pour un dirigeant d'entreprise, à partir de ses réponses à un questionnaire de profilage général.

Given the following company details:

{company_description}

[Your full prompt here...]
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000
        )
        
        content = response['choices'][0]['message']['content']
        questions = [line.strip("1234567890. \t") for line in content.strip().split("\n") if line.strip()]
        
        return {
            "business_name": company_name,
            "questions": questions[:90]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(e)}")

def create_pdf(content, title="Document"):
    """Create PDF from content"""
    try:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        
        # Add title
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, title, ln=True, align='C')
        pdf.ln(10)
        
        # Add content
        pdf.set_font('Arial', '', 11)
        
        lines = content.split('\n')
        for line in lines:
            try:
                encoded_line = line.encode('latin-1', 'replace').decode('latin-1')
                pdf.multi_cell(0, 6, encoded_line)
            except:
                clean_line = ''.join(char for char in line if ord(char) < 256)
                pdf.multi_cell(0, 6, clean_line)
            pdf.ln(2)
        
        return pdf
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF creation error: {str(e)}")

# API Routes
@app.get("/api/health")
async def health():
    return {"status": "OK", "message": "AI Business Analysis API is running"}

@app.post("/api/generate-questions")
async def generate_questions_endpoint(
    csv_file: UploadFile = File(...),
    business_name: str = Form(...),
    api_key: str = Form(...)
):
    """Generate personalized questions from company profile"""
    try:
        # Validate file type
        if not csv_file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Please upload a CSV file")
        
        # Read and process CSV
        csv_content = await csv_file.read()
        df = pd.read_csv(io.BytesIO(csv_content))
        
        # Check if required column exists
        if 'Business Name (pas de caractères spéciaux)' not in df.columns:
            raise HTTPException(
                status_code=400, 
                detail="Column 'Business Name (pas de caractères spéciaux)' not found in CSV"
            )
        
        # Find matching business
        matches = df[df['Business Name (pas de caractères spéciaux)'].str.lower() == business_name.lower()]
        
        if matches.empty:
            available_businesses = df['Business Name (pas de caractères spéciaux)'].dropna().unique()[:10]
            raise HTTPException(
                status_code=404, 
                detail={
                    "message": f"No responses found for business '{business_name}'",
                    "available_businesses": available_businesses.tolist()
                }
            )
        
        # Process company
        company_entry = matches.iloc[0].to_dict()
        result = process_company_questions(company_entry, api_key)
        
        # Create PDF
        questions_text = f"QUESTIONNAIRE DIAGNOSTIC - {result['business_name']}\n\n"
        questions_text += "\n".join([f"{i+1}. {q}" for i, q in enumerate(result['questions'])])
        
        pdf = create_pdf(questions_text, f"Questionnaire Diagnostic - {result['business_name']}")
        
        # Save PDF temporarily
        pdf_id = str(uuid.uuid4())
        pdf_path = os.path.join(TEMP_DIR, f"{pdf_id}.pdf")
        pdf.output(pdf_path)
        
        return {
            "success": True,
            "business_name": result['business_name'],
            "questions_count": len(result['questions']),
            "questions_preview": result['questions'][:5],
            "pdf_id": pdf_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.get("/api/download-pdf/{pdf_id}")
async def download_pdf(pdf_id: str):
    """Download generated PDF"""
    pdf_path = os.path.join(TEMP_DIR, f"{pdf_id}.pdf")
    
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF not found or expired")
    
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"analysis_{pdf_id}.pdf"
    )

# Serve React app (add this after you build React)
# Mount static files
if os.path.exists("build"):
    app.mount("/static", StaticFiles(directory="build/static"), name="static")
    
    @app.get("/")
    async def serve_react_app():
        return FileResponse("build/index.html")
    
    @app.get("/{full_path:path}")
    async def serve_react_routes(full_path: str):
        # Handle React Router routes
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="API route not found")
        return FileResponse("build/index.html")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)