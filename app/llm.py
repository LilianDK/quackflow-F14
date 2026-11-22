"""Anbindung an ein On-Prem-LLM über die OpenAI-kompatible Chat-Completions-API."""
import json
import re
from datetime import datetime

import httpx

import config

TYPE_HINTS = {
    "text": "Zeichenkette",
    "number": "Zahl (Punkt als Dezimaltrenner, ohne Tausendertrennzeichen und ohne Einheit)",
    "date": "Datum im Format JJJJ-MM-TT",
    "boolean": "true oder false",
}


def build_messages(text: str, variables: list[dict]) -> list[dict]:
    lines = []
    for v in variables:
        lines.append(f'- "{v["name"]}" ({TYPE_HINTS.get(v.get("type", "text"), "Zeichenkette")}): {v.get("description", "")}')
    keys = ", ".join(f'"{v["name"]}"' for v in variables)
    system = (
        "Du bist ein präzises System zur Informationsextraktion aus Dokumenten. "
        "Antworte ausschließlich mit einem einzigen JSON-Objekt, ohne Erklärungen und ohne Markdown. "
        "Wenn ein Wert im Dokument nicht vorkommt, setze null. Erfinde keine Werte."
    )
    user = (
        "Extrahiere die folgenden Variablen aus dem Dokument:\n"
        + "\n".join(lines)
        + f"\n\nDas JSON-Objekt muss genau diese Schlüssel enthalten: {keys}.\n\n"
        + "DOKUMENT:\n\"\"\"\n"
        + text[: config.LLM_MAX_CHARS]
        + "\n\"\"\""
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def parse_json(content: str) -> dict:
    content = content.strip()
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.S)
        if match:
            return json.loads(match.group(0))
        raise


def coerce(value, vtype: str):
    if value is None or value == "":
        return None
    try:
        if vtype == "number":
            if isinstance(value, (int, float)):
                return value
            s = str(value).strip().replace(" ", "")
            if "," in s and "." in s:  # 1.234,56 -> 1234.56
                s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
            else:
                s = s.replace(",", ".")
            s = re.sub(r"[^0-9.\-]", "", s)
            num = float(s)
            return int(num) if num.is_integer() else num
        if vtype == "boolean":
            if isinstance(value, bool):
                return value
            return str(value).strip().lower() in ("true", "ja", "yes", "1", "wahr")
        if vtype == "date":
            s = str(value).strip()
            for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y", "%d/%m/%Y"):
                try:
                    return datetime.strptime(s, fmt).date().isoformat()
                except ValueError:
                    pass
            return s
    except (ValueError, TypeError):
        return str(value)
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


async def extract_variables(text: str, variables: list[dict]) -> dict:
    payload = {
        "model": config.LLM_MODEL,
        "messages": build_messages(text, variables),
        "temperature": config.LLM_TEMPERATURE,
    }
    if config.LLM_JSON_MODE:
        payload["response_format"] = {"type": "json_object"}
    headers = {"Authorization": f"Bearer {config.LLM_API_KEY}"} if config.LLM_API_KEY else {}

    async with httpx.AsyncClient(timeout=config.LLM_TIMEOUT, verify=config.LLM_VERIFY_SSL) as client:
        resp = await client.post(f"{config.LLM_BASE_URL}/chat/completions", json=payload, headers=headers)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]

    raw = parse_json(content)
    return {v["name"]: coerce(raw.get(v["name"]), v.get("type", "text")) for v in variables}
