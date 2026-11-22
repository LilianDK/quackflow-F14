import os

EXTRACTOR_URL = os.getenv("EXTRACTOR_URL", "http://localhost:8001")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1").rstrip("/")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.1:8b")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0"))
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "300"))
LLM_MAX_CHARS = int(os.getenv("LLM_MAX_CHARS", "60000"))
# "true": sendet response_format={"type":"json_object"} (vLLM, Ollama, LM Studio unterstützen das)
LLM_JSON_MODE = os.getenv("LLM_JSON_MODE", "true").lower() == "true"
LLM_VERIFY_SSL = os.getenv("LLM_VERIFY_SSL", "true").lower() == "true"
DATA_DIR = os.getenv("DATA_DIR", "./data")
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))
