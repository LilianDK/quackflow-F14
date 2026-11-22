"""Kleiner Fake-LLM-Server zum Testen ohne echtes Modell (gibt fixe Werte zurück)."""
import json
from fastapi import FastAPI, Request
app = FastAPI()

@app.get("/v1/models")
def models():
    return {"data": [{"id": "mock"}]}

@app.post("/v1/chat/completions")
async def chat(req: Request):
    body = await req.json()
    prompt = body["messages"][-1]["content"]
    keys = json.loads("[" + prompt.split("genau diese Schlüssel enthalten: ")[1].split(".\n")[0] + "]")
    vals = {k: None for k in keys}
    vals.update({"Dokumenttyp": "Rechnung", "Datum": "15.03.2026", "Absender": "Muster GmbH", "Betrag": "1.234,56 €", "Bezahlt": "ja"})
    return {"choices": [{"message": {"content": "```json\n" + json.dumps({k: vals[k] for k in keys}) + "\n```"}}]}
