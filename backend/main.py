# main.py - Fixed OpenAI API calls
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

def process_company_questions(entry, api_key):
    """Generate personalized questions for a company"""
    # Set the API key directly
    openai.api_key = api_key
    
    company_name = entry.get("Business Name (pas de caractères spéciaux)", "Unnamed Company")
    company_description = "\n".join([f"{key}: {value}" for key, value in entry.items() if pd.notna(value)])

    prompt = f"""
Vous êtes analyste stratégique en France, spécialisé dans le diagnostic des PME. Votre mission consiste à générer un questionnaire personnalisé de 50 à 100 questions diagnostiques pour un dirigeant d'entreprise, à partir de ses réponses à un questionnaire de profilage général.

Given the following company details:

{company_description}

**exactement cinquante (50)**. L'objectif est de préparer une analyse SWOT (Forces, Faiblesses, Opportunités, Menaces) complète et structurée. Vos questions doivent explorer les axes stratégiques clés de l'entreprise avec précision et pertinence, en fonction de sa taille, de son secteur d'activité, de son chiffre d'affaires, de son modèle opérationnel, de sa structure clientèle et des défis déclarés.

Voici la marche à suivre :
1. Lire attentivement les 20 réponses du questionnaire de profilage. 
2. Identifiez les caractéristiques clés de l'entreprise : modèle économique, stade de croissance, dynamique sectorielle, maturité numérique, exposition internationale, etc.
3. Sur cette base, élaborez 50 à 100 questions **personnalisées** sur les axes suivants et les questions devraient augmenter en complexité:
    - Stratégie commerciale (par exemple, performance commerciale, taux de désabonnement, pouvoir de fixation des prix)
    - Opérations et chaîne d'approvisionnement
    - Structure financière et marges
    - Positionnement sur le marché et concurrence
    - Ressources humaines et management
    - Outils numériques et transformation
    - Risques réglementaires et externes
    - Vision stratégique et projets d'avenir
4. Variez le type de questions (QCM, échelles de notation, texte court) mais n'incluez pas le type de question
5. Assurez-vous que chaque question contribue à révéler un élément concret pour l'analyse SWOT
6. ne regroupez pas les questions par axes

Soyez attentif au contexte : si l'entreprise externalise sa production, ne posez pas de questions sur les indicateurs clés de performance de la production interne ; s'il s'agit d'une activité B2B dans un secteur de niche, ne posez pas de questions sur l'image de marque grand public.
Ne posez pas de questions directes sur les forces, les faiblesses, les opportunités, les menaces ou autres choses de ce genre.

"""

    try:
        # Use the older API format (more reliable for deployment)
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=4000
        )
        
        content = response['choices'][0]['message']['content']
        questions = [line.strip("1234567890. \t") for line in content.strip().split("\n") if line.strip()]
        
        return {
            "business_name": company_name,
            "questions": questions[:90]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(e)}")

def extract_qa_from_pdf(pdf_file):
    """Extract text from PDF file"""
    qa_text = ""
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    qa_text += text + "\n"
        return qa_text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF extraction error: {str(e)}")

def generate_swot_analysis(form_data, detailed_qa, api_key):
    """Generate SWOT analysis"""
    openai.api_key = api_key
    
    business_info = "\n".join([f"{k}: {v}" for k, v in form_data.items() if pd.notna(v)])

    prompt = f"""Réalise une analyse SWOT stratégique de l'entreprise en adoptant une approche consultante experte. 

## CONSIGNES STRATÉGIQUES PRIORITAIRES

**Perspective d'analyse :** Adopte le point de vue d'un consultant senior qui comprend les enjeux spécifiques aux PME et les dynamiques sectorielles.

**Focus qualité > quantité :** Limite-toi aux 3-4 éléments les plus critiques par catégorie, mais développe-les avec profondeur stratégique.

## STRUCTURE D'ANALYSE

### ATOUTS (Forces)
Focus sur les **avantages concurrentiels réels** :
- Positionnement différenciant vs concurrents majeurs
- Modèle économique ou approche unique 
- Relations client et satisfaction (taille humaine, proximité)
- Expertise technique ou savoir-faire spécialisé
- Stabilité contractuelle ou récurrence business

### FAIBLESSES (Faiblesses internes)
**Identifier les risques opérationnels critiques** :
- Dépendances organisationnelles (leadership, personne-clé)
- Contraintes de structuration interne (processus, communication)
- Limitations financières impactant la croissance
- Vulnérabilités contractuelles ou commerciales majeures

### OPPORTUNITÉS
**Axes de développement réalistes** :
- Évolutions réglementaires/marché favorables au positionnement
- Opportunités de conquête commerciale identifiées
- Leviers de transformation digitale/innovation
- Possibilités d'expansion géographique ou diversification

### MENACES
**Risques business majeurs** :
- Concurrence spécifique (nommer les acteurs dominants)
- Complexité croissante du marché (appels d'offres, etc.)
- Risques financiers et de stabilité
- Évolutions défavorables de l'environnement d'affaires

## DONNÉES À UTILISER

Informations entreprise : {business_info}

Réponses détaillées : {detailed_qa}

**Analyse les interdépendances** entre les éléments et explique les mécanismes sous-jacents (pourquoi/comment) pour chaque point identifié."""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=4000,
        )
        return response['choices'][0]['message']['content']
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
@app.get("/")
async def root():
    return {"message": "AI Business Analysis API", "status": "running", "version": "1.0.0"}

@app.get("/api/routes")
async def list_routes():
    """Debug endpoint to list all available routes"""
    routes = []
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            routes.append({
                "path": route.path,
                "methods": list(route.methods)
            })
    return {"routes": routes}

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

@app.post("/api/generate-swot")
async def generate_swot_endpoint(
    csv_file: UploadFile = File(...),
    pdf_file: UploadFile = File(...),
    business_name: str = Form(...),
    api_key: str = Form(...)
):
    """Generate SWOT analysis from company data and Q&A"""
    try:
        # Validate file types
        if not csv_file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Please upload a CSV file")
        
        if not pdf_file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Please upload a PDF file")
        
        # Read CSV
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
        
        # Extract PDF content
        pdf_content = await pdf_file.read()
        
        # Save PDF temporarily for processing
        temp_pdf_path = os.path.join(TEMP_DIR, f"temp_{uuid.uuid4()}.pdf")
        with open(temp_pdf_path, 'wb') as f:
            f.write(pdf_content)
        
        try:
            detailed_qa = extract_qa_from_pdf(temp_pdf_path)
        finally:
            # Clean up temp file
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)
        
        # Generate SWOT analysis
        form_data = matches.iloc[0].to_dict()
        swot_analysis = generate_swot_analysis(form_data, detailed_qa, api_key)
        
        # Create PDF
        pdf = create_pdf(swot_analysis, f"Analyse SWOT - {business_name}")
        
        # Save PDF temporarily
        pdf_id = str(uuid.uuid4())
        pdf_path = os.path.join(TEMP_DIR, f"{pdf_id}.pdf")
        pdf.output(pdf_path)
        
        return {
            "success": True,
            "business_name": business_name,
            "swot_analysis": swot_analysis,
            "pdf_id": pdf_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.post("/api/generate-swot")
async def generate_swot_endpoint(
    csv_file: UploadFile = File(...),
    pdf_file: UploadFile = File(...),
    business_name: str = Form(...),
    api_key: str = Form(...)
):
    """Generate SWOT analysis from company data and Q&A"""
    try:
        # Validate file types
        if not csv_file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Please upload a CSV file")
        
        if not pdf_file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Please upload a PDF file")
        
        # Read CSV
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
        
        # Extract PDF content
        pdf_content = await pdf_file.read()
        
        # Save PDF temporarily for processing
        temp_pdf_path = os.path.join(TEMP_DIR, f"temp_{uuid.uuid4()}.pdf")
        with open(temp_pdf_path, 'wb') as f:
            f.write(pdf_content)
        
        try:
            detailed_qa = extract_qa_from_pdf(temp_pdf_path)
        finally:
            # Clean up temp file
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)
        
        # Generate SWOT analysis
        form_data = matches.iloc[0].to_dict()
        swot_analysis = generate_swot_analysis(form_data, detailed_qa, api_key)
        
        # Create PDF
        pdf = create_pdf(swot_analysis, f"Analyse SWOT - {business_name}")
        
        # Save PDF temporarily
        pdf_id = str(uuid.uuid4())
        pdf_path = os.path.join(TEMP_DIR, f"{pdf_id}.pdf")
        pdf.output(pdf_path)
        
        return {
            "success": True,
            "business_name": business_name,
            "swot_analysis": swot_analysis,
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