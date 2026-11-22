"""PDF-Extraktions-Microservice: nimmt ein PDF entgegen und liefert den Text zurück."""
import io

import pdfplumber
from fastapi import FastAPI, File, HTTPException, UploadFile

app = FastAPI(title="PDF Extractor", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/extract")
async def extract(file: UploadFile = File(...)):
    data = await file.read()
    if not data.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Die Datei ist kein gültiges PDF.")
    try:
        pages = []
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                pages.append(page.extract_text() or "")
    except Exception as exc:  # beschädigte oder verschlüsselte PDFs
        raise HTTPException(status_code=422, detail=f"PDF konnte nicht gelesen werden: {exc}")

    text = "\n\n".join(f"--- Seite {i + 1} ---\n{t}" for i, t in enumerate(pages))
    return {
        "filename": file.filename,
        "page_count": len(pages),
        "char_count": sum(len(t) for t in pages),
        "text": text,
    }
