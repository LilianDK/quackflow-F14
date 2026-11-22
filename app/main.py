"""Haupt-API: Web-Oberfläche, Variablenverwaltung, Orchestrierung (Extractor -> LLM) und Excel-Export."""
import json
from datetime import datetime
from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

import config
from excel import build_workbook
from llm import extract_variables

app = FastAPI(title="quackflow-F14", version="1.0.0")
VARIABLES_FILE = Path(config.DATA_DIR) / "variables.json"

DEFAULT_VARIABLES = [
    {"name": "Dokumenttyp", "description": "Art des Dokuments, z. B. Rechnung, Vertrag, Angebot", "type": "text"},
    {"name": "Datum", "description": "Ausstellungsdatum des Dokuments", "type": "date"},
    {"name": "Absender", "description": "Name der Firma oder Person, die das Dokument erstellt hat", "type": "text"},
]


class Variable(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = ""
    type: Literal["text", "number", "date", "boolean"] = "text"

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


class ExportRequest(BaseModel):
    variables: list[Variable]
    results: list[dict]


def load_variables() -> list[dict]:
    if VARIABLES_FILE.exists():
        return json.loads(VARIABLES_FILE.read_text(encoding="utf-8"))
    return DEFAULT_VARIABLES


@app.get("/api/health")
async def health():
    status = {"app": "ok", "llm_base_url": config.LLM_BASE_URL, "llm_model": config.LLM_MODEL}
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            r = await client.get(f"{config.EXTRACTOR_URL}/health")
            status["extractor"] = "ok" if r.status_code == 200 else f"Fehler {r.status_code}"
        except httpx.HTTPError as exc:
            status["extractor"] = f"nicht erreichbar ({exc.__class__.__name__})"
    headers = {"Authorization": f"Bearer {config.LLM_API_KEY}"} if config.LLM_API_KEY else {}
    async with httpx.AsyncClient(timeout=5, verify=config.LLM_VERIFY_SSL) as client:
        try:
            r = await client.get(f"{config.LLM_BASE_URL}/models", headers=headers)
            status["llm"] = "ok" if r.status_code == 200 else f"Fehler {r.status_code}"
        except httpx.HTTPError as exc:
            status["llm"] = f"nicht erreichbar ({exc.__class__.__name__})"
    return status


@app.get("/api/variables")
def get_variables():
    return load_variables()


@app.put("/api/variables")
def put_variables(variables: list[Variable]):
    names = [v.name for v in variables]
    if len(names) != len(set(names)):
        raise HTTPException(400, "Variablennamen müssen eindeutig sein.")
    data = [v.model_dump() for v in variables]
    VARIABLES_FILE.parent.mkdir(parents=True, exist_ok=True)
    VARIABLES_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


@app.post("/api/process")
async def process(file: UploadFile = File(...)):
    """Ein PDF verarbeiten: an den Extractor senden, Text ans LLM geben, Variablen zurückgeben."""
    variables = load_variables()
    if not variables:
        raise HTTPException(400, "Bitte zuerst mindestens eine Variable definieren.")
    data = await file.read()
    if len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"Datei größer als {config.MAX_UPLOAD_MB} MB.")

    result = {"filename": file.filename, "values": None, "error": None, "page_count": None}

    # 1) PDF-Extraktion über den Microservice
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{config.EXTRACTOR_URL}/extract",
                files={"file": (file.filename, data, "application/pdf")},
            )
        if r.status_code != 200:
            result["error"] = f"Extraktion fehlgeschlagen: {r.json().get('detail', r.text)}"
            return result
        extracted = r.json()
    except httpx.HTTPError as exc:
        result["error"] = f"Extractor nicht erreichbar: {exc}"
        return result

    result["page_count"] = extracted["page_count"]
    if extracted["char_count"] == 0:
        result["error"] = "Kein Text im PDF gefunden (evtl. eingescanntes Dokument ohne Textebene)."
        return result

    # 2) Variablen per LLM extrahieren
    try:
        result["values"] = await extract_variables(extracted["text"], variables)
    except httpx.HTTPStatusError as exc:
        result["error"] = f"LLM-Fehler {exc.response.status_code}: {exc.response.text[:300]}"
    except httpx.HTTPError as exc:
        result["error"] = f"LLM nicht erreichbar: {exc}"
    except (ValueError, KeyError) as exc:
        result["error"] = f"LLM-Antwort war kein gültiges JSON: {exc}"
    return result


@app.post("/api/export")
def export(req: ExportRequest):
    content = build_workbook([v.model_dump() for v in req.variables], req.results)
    filename = f"extraktion_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
    return Response(
        content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="static")
