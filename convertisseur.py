from fastapi import FastAPI, File, UploadFile, HTTPException
from pdf2docx import Converter
import shutil
import os
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import asyncio

app = FastAPI()

# Chemin du dossier temporaire pour stocker les fichiers
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Pour servir les fichiers statiques depuis le dossier 'uploads'
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

def convert_pdf_to_docx(pdf_file_path: str, docx_file_path: str):
    """Convertit un fichier PDF en DOCX."""
    try:
        cv = Converter(pdf_file_path)
        cv.convert(docx_file_path, start=0, end=None)
        cv.close()

        # Vérification de la validité du fichier DOCX
        if not os.path.exists(docx_file_path) or os.path.getsize(docx_file_path) == 0:
            raise ValueError("Le fichier DOCX généré est vide ou corrompu.")
    except Exception as e:
        raise Exception(f"Erreur pendant la conversion : {e}")

async def delete_files_after_delay():
    """Supprime tous les fichiers dans 'uploads' après 40 secondes, sauf 'explanation.txt'."""
    await asyncio.sleep(40)  # Attendre 40 secondes

    for file in os.listdir(UPLOAD_DIR):
        file_path = UPLOAD_DIR / file
        if file != "explanation.txt" and file_path.is_file():
            os.remove(file_path)
            # print(f"Fichier supprimé : {file_path}")

@app.post("/convert")
async def convert_pdf_to_word(file: UploadFile = File(...)):
    # Enregistrer temporairement le fichier PDF
    pdf_path = UPLOAD_DIR / file.filename
    with open(pdf_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Vérifier si le fichier PDF est bien enregistré et lisible
    if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
        raise HTTPException(status_code=500, detail="Erreur lors de l'enregistrement du fichier PDF.")

    # Générer le nom du fichier DOCX
    docx_filename = pdf_path.stem + ".docx"
    docx_path = UPLOAD_DIR / docx_filename

    try:
        # Convertir le fichier PDF en DOCX
        convert_pdf_to_docx(str(pdf_path), str(docx_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de conversion : {e}")
    finally:
        # Supprimer le fichier PDF temporaire
        os.remove(pdf_path)

    # Lancer la suppression des fichiers après un délai de 40 secondes
    asyncio.create_task(delete_files_after_delay())

    # Vérification finale pour confirmer que le fichier est bien accessible
    if not os.path.exists(docx_path):
        raise HTTPException(status_code=500, detail="Le fichier DOCX n'a pas été généré correctement.")

    # Retourner le chemin du fichier DOCX sous forme de réponse
    return {"docx_file": f"/uploads/{docx_filename}"}
