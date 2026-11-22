# quackflow-F14

PDF-Extraktion mit On-Prem-LLM.

Weboberfläche zum Hochladen von PDFs. Der Text wird von einem FastAPI-Microservice extrahiert, an ein
On-Prem-LLM (OpenAI-kompatible API, z. B. vLLM, Ollama, LM Studio) geschickt, das die in der Oberfläche
definierten Variablen herausliest. Die Ergebnisse erscheinen als Tabelle und lassen sich als Excel exportieren.

```
Browser ──► app (FastAPI, :8765) ──► extractor (FastAPI, :8001)   PDF → Text
                     │
                     └────────────► On-Prem-LLM  /v1/chat/completions   Text → JSON mit Variablen
                     └── Excel-Export (openpyxl)
```

## Start

```bash
cp .env.example .env        # LLM_BASE_URL und LLM_MODEL anpassen
docker compose up -d --build
```

Dann http://localhost:8765 öffnen. Oben rechts zeigt die Seite, ob Extractor und LLM erreichbar sind.

## Bedienung

1. **Variablen definieren**: Name, Beschreibung (Anweisung ans LLM) und Typ (Text, Zahl, Datum, Ja/Nein).
   Die Definition wird in `data/variables.json` gespeichert.
2. **PDFs hochladen**: per Drag & Drop, auch mehrere. Sie werden nacheinander verarbeitet.
3. **Excel exportieren**: Blatt „Ergebnisse“ (eine Zeile pro PDF) und Blatt „Variablen“ (die verwendete Definition).

## API

| Dienst    | Endpunkt               | Zweck                                  |
|-----------|------------------------|----------------------------------------|
| extractor | `POST /extract`        | PDF (multipart `file`) → Text je Seite |
| app       | `GET/PUT /api/variables` | Variablendefinition lesen/speichern  |
| app       | `POST /api/process`    | PDF → Extractor → LLM → Werte          |
| app       | `POST /api/export`     | Ergebnisse → `.xlsx`                   |
| app       | `GET /api/health`      | Erreichbarkeit von Extractor und LLM   |

Swagger-Doku: http://localhost:8765/docs

## Hinweise

- Eingescannte PDFs ohne Textebene liefern keinen Text (keine OCR enthalten); sie werden als Fehler markiert.
- Lange Dokumente werden nach `LLM_MAX_CHARS` Zeichen abgeschnitten. Den Wert an das Kontextfenster des Modells anpassen.
- Unterstützt der LLM-Server `response_format` nicht, `LLM_JSON_MODE=false` setzen.

## Lokale Entwicklung ohne Docker

```bash
pip install -r extractor/requirements.txt -r app/requirements.txt
(cd extractor && uvicorn main:app --port 8001) &
(cd app && DATA_DIR=../data LLM_BASE_URL=http://localhost:11434/v1 uvicorn main:app --port 8000 --reload)
```

## Lizenz

MIT, siehe [LICENSE](LICENSE).
