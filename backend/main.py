# main.py - Updated to support multiple PDFs
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
import markdown
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
from typing import Optional, List

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

**entre cinquante (50) et cent (100)**. L'objectif est de préparer une analyse SWOT (Forces, Faiblesses, Opportunités, Menaces) complète et structurée. Vos questions doivent explorer les axes stratégiques clés de l'entreprise avec précision et pertinence, en fonction de sa taille, de son secteur d'activité, de son chiffre d'affaires, de son modèle opérationnel, de sa structure clientèle et des défis déclarés.

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

def extract_qa_from_multiple_pdfs(pdf_files):
    """Extract text from multiple PDF files and combine them"""
    combined_qa_text = ""
    processed_files = []
    
    for i, pdf_file in enumerate(pdf_files):
        try:
            # Save PDF temporarily for processing
            temp_pdf_path = os.path.join(TEMP_DIR, f"temp_pdf_{i}_{uuid.uuid4()}.pdf")
            
            # Read the uploaded file content
            pdf_content = pdf_file.file.read()
            pdf_file.file.seek(0)  # Reset file pointer for potential reuse
            
            # Write to temporary file
            with open(temp_pdf_path, 'wb') as f:
                f.write(pdf_content)
            
            # Extract text from this PDF
            pdf_text = ""
            with pdfplumber.open(temp_pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        pdf_text += text + "\n"
            
            if pdf_text.strip():
                combined_qa_text += f"\n=== DOCUMENT {i+1}: {pdf_file.filename} ===\n"
                combined_qa_text += pdf_text + "\n"
                processed_files.append(pdf_file.filename)
            
            # Clean up temporary file
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)
                
        except Exception as e:
            # Log error but continue with other files
            print(f"Error processing PDF {pdf_file.filename}: {str(e)}")
            continue
    
    if not combined_qa_text.strip():
        raise HTTPException(status_code=400, detail="No readable content found in any PDF files")
    
    return combined_qa_text, processed_files

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

Réponses détaillées (analysées à partir de plusieurs documents) : {detailed_qa}

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

def generate_action_plan(form_data, detailed_qa, swot_analysis, api_key):
    """Generate strategic action plan based on SWOT analysis and company data"""
    openai.api_key = api_key
    
    business_info = "\n".join([f"{k}: {v}" for k, v in form_data.items() if pd.notna(v)])

    prompt = f"""
Tu es un consultant en stratégie senior en cabinet de conseil. Génère un **Plan d’Actions Structuré** au format texte destiné à une PME/ETI, dans un style clair, directement opérationnel et prêt à être mis en œuvre.

## OBJECTIF
Convertir les éléments concrets de l’analyse SWOT en actions **priorisées, activables immédiatement**, adaptées **spécifiquement au contexte réel de l’entreprise** (taille, secteur, maturité…).

## STRUCTURE À PRODUIRE POUR CHAQUE DOMAINE CI-DESSOUS :
1. **RECOMMANDATIONS D’ACTIONS** :  
   - 2 à 3 actions maximum par domaine  
   - Toujours commencer par un **verbe d’action fort** (Ex : Définir, Mettre en place, Structurer, Optimiser, Digitaliser…)  
   -  Donnez des exemples tels que les services existants qu'ils pourraient utiliser et nommez les concurrents réels sur leur marché.
   - Chaque action doit être :
     - **Spécifique** : faire référence à un problème ou un levier identifié dans {swot_analysis}  
     - **Opérationnelle** : directement mise en œuvre par une PME/ETI sans dépendre d’acteurs externes ou d’approches trop générales  
     - **Structurée** en deux puces (problème ciblé + réponse/action)

2. **ÉCHÉANCE** : Trimestre et année (ex. T3 2025)

3. **RESPONSABLE** : Toujours écrire : “À remplir par le client”

4. **PRIORITÉ** : 
   - Priorité 1 = action urgente / structurante
   - Priorité 2 = action utile / court-moyen terme
   - Priorité 3 = action de fond / moins critique

## DOMAINES À TRAITER :
- Marché et stratégie  
- Systèmes d’information et digital  
- Organisation et management  
- Finance et juridique  
- Commercial et marketing  
- Opérations  
- RSE et climat  
- Ressources humaines  

## CONTEXTE À UTILISER :
- *Profil de l’entreprise* : {business_info}
- *Analyse complète* : {detailed_qa}

## STANDARDS À RESPECTER :
- Suivre **le format des exemples suivants** :
  - Exemple :  
    - Déployer un outil d’évaluation des AO basé sur un scoring structuré  
    - Optimiser la sélection des opportunités et maximiser le taux de conversion  
    - Échéance : T4 2025 | Responsable : À remplir par le client | Priorité : 1

- Pas de généralités : chaque action doit **résoudre un problème concret** ou **exploiter un levier clair**
- Chaque ligne doit pouvoir être **assignée immédiatement à un responsable opérationnel**
"""

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
    """Create beautifully formatted PDF from markdown using HTML/CSS"""
    try:
        # Convert markdown to HTML
        md = markdown.Markdown(extensions=['tables', 'toc', 'codehilite'])
        html_content = md.convert(content)
        
        # Create styled HTML document
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                @page {{
                    margin: 2cm;
                    @top-center {{
                        content: "{title}";
                        font-family: Arial, sans-serif;
                        font-size: 10pt;
                        color: #666;
                    }}
                    @bottom-center {{
                        content: "Page " counter(page) " of " counter(pages);
                        font-family: Arial, sans-serif;
                        font-size: 10pt;
                        color: #666;
                    }}
                }}
                
                body {{
                    font-family: Arial, sans-serif;
                    font-size: 11pt;
                    line-height: 1.5;
                    color: #333;
                }}
                
                h1 {{
                    color: #2c3e50;
                    font-size: 18pt;
                    margin-top: 0;
                    margin-bottom: 16pt;
                    text-align: center;
                    border-bottom: 2px solid #3498db;
                    padding-bottom: 8pt;
                }}
                
                h2 {{
                    color: #34495e;
                    font-size: 14pt;
                    margin-top: 20pt;
                    margin-bottom: 10pt;
                    border-left: 4px solid #3498db;
                    padding-left: 10pt;
                    background-color: #f8f9fa;
                    padding: 8pt;
                    border-radius: 4pt;
                }}
                
                h3 {{
                    color: #34495e;
                    font-size: 12pt;
                    margin-top: 16pt;
                    margin-bottom: 8pt;
                    border-left: 2px solid #95a5a6;
                    padding-left: 8pt;
                }}
                
                h4 {{
                    color: #34495e;
                    font-size: 11pt;
                    margin-top: 12pt;
                    margin-bottom: 6pt;
                }}
                
                p {{
                    margin-bottom: 8pt;
                    text-align: justify;
                }}
                
                strong {{
                    color: #2c3e50;
                    font-weight: bold;
                }}
                
                em {{
                    color: #7f8c8d;
                    font-style: italic;
                }}
                
                ul, ol {{
                    margin-bottom: 12pt;
                    padding-left: 20pt;
                }}
                
                li {{
                    margin-bottom: 4pt;
                    line-height: 1.4;
                }}
                
                .priority-high {{
                    background-color: #ffebee;
                    border-left: 4px solid #e74c3c;
                    padding: 8pt;
                    margin: 8pt 0;
                    border-radius: 4pt;
                }}
                
                .priority-medium {{
                    background-color: #fff8e1;
                    border-left: 4px solid #f39c12;
                    padding: 8pt;
                    margin: 8pt 0;
                    border-radius: 4pt;
                }}
                
                .priority-low {{
                    background-color: #e8f5e8;
                    border-left: 4px solid #27ae60;
                    padding: 8pt;
                    margin: 8pt 0;
                    border-radius: 4pt;
                }}
                
                .separator {{
                    border-top: 1px solid #bdc3c7;
                    margin: 16pt 0;
                }}
                
                .action-item {{
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 4pt;
                    padding: 10pt;
                    margin: 8pt 0;
                }}
                
                .highlight {{
                    background-color: #fff3cd;
                    padding: 2pt 4pt;
                    border-radius: 2pt;
                }}
                
                code {{
                    background-color: #f1f2f6;
                    padding: 2pt 4pt;
                    border-radius: 2pt;
                    font-family: "Courier New", monospace;
                    font-size: 10pt;
                }}
                
                blockquote {{
                    border-left: 3px solid #3498db;
                    margin: 12pt 0;
                    padding-left: 12pt;
                    font-style: italic;
                    background-color: #f8f9fa;
                    padding: 8pt 8pt 8pt 20pt;
                }}
            </style>
        </head>
        <body>
            <h1>{title}</h1>
            {html_content}
        </body>
        </html>
        """
        
        # Generate PDF from HTML
        font_config = FontConfiguration()
        html_doc = HTML(string=html_template)
        
        # Create temporary file for PDF
        temp_pdf_path = os.path.join(TEMP_DIR, f"temp_advanced_{uuid.uuid4()}.pdf")
        html_doc.write_pdf(temp_pdf_path, font_config=font_config)
        
        # Return a custom PDF object that works with your existing code
        class AdvancedPDF:
            def __init__(self, pdf_path):
                self.pdf_path = pdf_path
                
            def output(self, output_path):
                """Copy the generated PDF to the output path"""
                import shutil
                shutil.copy2(self.pdf_path, output_path)
                # Clean up temp file
                if os.path.exists(self.pdf_path):
                    os.remove(self.pdf_path)
        
        return AdvancedPDF(temp_pdf_path)
        
    except Exception as e:
        print(f"Advanced PDF creation failed: {e}")
        # Fallback to basic PDF creation
        return create_basic_pdf(content, title)

def create_basic_pdf(content, title="Document"):
    """Fallback basic PDF creation"""
    try:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        
        # Add title
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, encode_text(title), ln=True, align='C')
        pdf.ln(10)
        
        # Add content
        pdf.set_font('Arial', '', 11)
        
        lines = content.split('\n')
        for line in lines:
            encoded_line = encode_text(line)
            pdf.multi_cell(0, 6, encoded_line)
            pdf.ln(2)
        
        return pdf
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF creation error: {str(e)}")

def encode_text(text):
    """Safely encode text for PDF"""
    try:
        return text.encode('latin-1', 'replace').decode('latin-1')
    except:
        return ''.join(char for char in text if ord(char) < 256)

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
    pdf_files: List[UploadFile] = File(...),
    business_name: str = Form(...),
    api_key: str = Form(...)
):
    """Generate SWOT analysis from company data and multiple Q&A PDFs"""
    try:
        # Validate file types
        if not csv_file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Please upload a CSV file")
        
        # Validate PDF files
        for pdf_file in pdf_files:
            if not pdf_file.filename.endswith('.pdf'):
                raise HTTPException(status_code=400, detail=f"File {pdf_file.filename} is not a PDF file")
        
        if len(pdf_files) == 0:
            raise HTTPException(status_code=400, detail="At least one PDF file is required")
        
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
        
        # Extract content from all PDF files
        detailed_qa, processed_files = extract_qa_from_multiple_pdfs(pdf_files)
        
        # Generate SWOT analysis
        form_data = matches.iloc[0].to_dict()
        swot_analysis = generate_swot_analysis(form_data, detailed_qa, api_key)
        
        # Create PDF with analysis info
        analysis_header = f"ANALYSE SWOT - {business_name}\n\n"
        analysis_header += f"Documents analysés: {', '.join(processed_files)}\n"
        analysis_header += f"Nombre de documents PDF traités: {len(processed_files)}\n\n"
        analysis_header += "=" * 50 + "\n\n"
        
        full_content = analysis_header + swot_analysis
        
        pdf = create_pdf(full_content, f"Analyse SWOT - {business_name}")
        
        # Save PDF temporarily
        pdf_id = str(uuid.uuid4())
        pdf_path = os.path.join(TEMP_DIR, f"{pdf_id}.pdf")
        pdf.output(pdf_path)
        
        return {
            "success": True,
            "business_name": business_name,
            "swot_analysis": swot_analysis,
            "processed_files": processed_files,
            "files_count": len(processed_files),
            "pdf_id": pdf_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.post("/api/generate-action-plan")
async def generate_action_plan_endpoint(
    csv_file: UploadFile = File(...),
    pdf_files: List[UploadFile] = File(...),
    business_name: str = Form(...),
    swot_analysis: str = Form(...),
    api_key: str = Form(...)
):
    """Generate strategic action plan from SWOT analysis and company data"""
    try:
        # Validate file types
        if not csv_file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Please upload a CSV file")
        
        # Validate PDF files
        for pdf_file in pdf_files:
            if not pdf_file.filename.endswith('.pdf'):
                raise HTTPException(status_code=400, detail=f"File {pdf_file.filename} is not a PDF file")
        
        if len(pdf_files) == 0:
            raise HTTPException(status_code=400, detail="At least one PDF file is required")
        
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
        
        # Extract content from all PDF files
        detailed_qa, processed_files = extract_qa_from_multiple_pdfs(pdf_files)
        
        # Generate action plan
        form_data = matches.iloc[0].to_dict()
        action_plan = generate_action_plan(form_data, detailed_qa, swot_analysis, api_key)
        
        action_plan_header = f"PLAN D'ACTION - {business_name}\n\n"
        action_plan_header += f"Documents analysés: {', '.join(processed_files)}\n"
        action_plan_header += f"Nombre de documents PDF traités: {len(processed_files)}\n\n"
        action_plan_header += "=" * 50 + "\n\n"

        action_plan_content = action_plan_header + action_plan
        action_pdf = create_pdf(action_plan_content, f"Plan d'action - {business_name}")

        # Save Action Plan PDF
        action_pdf_id = str(uuid.uuid4())
        action_pdf_path = os.path.join(TEMP_DIR, f"{action_pdf_id}.pdf")
        action_pdf.output(action_pdf_path)
        
        # Create comprehensive PDF with SWOT + Action Plan
        comprehensive_header = f"ANALYSE STRATEGIQUE COMPLETE - {business_name}\n\n"
        comprehensive_header += f"Documents analysés: {', '.join(processed_files)}\n"
        comprehensive_header += f"Nombre de documents PDF traités: {len(processed_files)}\n\n"
        comprehensive_header += "=" * 60 + "\n"
        comprehensive_header += "PARTIE 1: ANALYSE SWOT\n"
        comprehensive_header += "=" * 60 + "\n\n"
        
        comprehensive_content = comprehensive_header + swot_analysis + "\n\n"
        comprehensive_content += "=" * 60 + "\n"
        comprehensive_content += "PARTIE 2: PLAN D'ACTION STRATEGIQUE\n"
        comprehensive_content += "=" * 60 + "\n\n"
        comprehensive_content += action_plan
        
        comprehensive_pdf = create_pdf(comprehensive_content, f"Strategie Complete - {business_name}")
        
        # Save comprehensive PDF
        comprehensive_pdf_id = str(uuid.uuid4())
        comprehensive_pdf_path = os.path.join(TEMP_DIR, f"{comprehensive_pdf_id}.pdf")
        comprehensive_pdf.output(comprehensive_pdf_path)
        
        return {
            "success": True,
            "business_name": business_name,
            "action_plan": action_plan,
            "processed_files": processed_files,
            "files_count": len(processed_files),
            "action_pdf_id": action_pdf_id,  # SWOT-only PDF ID
            "comprehensive_pdf_id": comprehensive_pdf_id  # Combined PDF ID
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