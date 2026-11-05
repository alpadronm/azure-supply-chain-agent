import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.agente.foundry_integration import ejecutar_calculo_reposicion
from src.base_datos.conexion import get_connection

BASE_DIR = Path(__file__).resolve().parents[2]
STATIC_DIR = BASE_DIR / "src" / "web"

app = FastAPI(
    title="Azure Supply Chain Agent API",
    version="0.1.0",
    description=(
        "API mínima para consultar inventarios, estimar reposición y exponer resultados "
        "de la lógica de negocio actual sin modificar la base de datos."
    ),
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

if not allowed_origins:
    allowed_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

CONVERSATIONS: Dict[str, Dict[str, Any]] = {}


@app.get("/")
def serve_index() -> FileResponse:
    """Sirve la interfaz web del panel logístico."""
    return FileResponse(STATIC_DIR / "index.html")


def _consulta_resumen_postgres() -> Dict[str, Any]:
    """Consulta SQL ligera para resumir inventarios y disponibilidad operativa."""
    query = """
        SELECT
            (SELECT COUNT(*) FROM tiendas) AS tiendas,
            (SELECT COUNT(*) FROM productos) AS productos,
            COALESCE((SELECT SUM(cantidad_cajas) FROM inventarios_tienda), 0) AS inventario_tiendas,
            COALESCE((SELECT SUM(cantidad_cajas) FROM inventario_bodega), 0) AS inventario_bodega;
    """

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                row = cur.fetchone()
    except Exception as exc:  # pragma: no cover - manejado en el endpoint
        raise RuntimeError(f"No se pudo consultar PostgreSQL: {exc}") from exc

    if not row:
        return {
            "tiendas": 0,
            "productos": 0,
            "inventario_tiendas": 0,
            "inventario_bodega": 0,
        }

    return {
        "tiendas": int(row[0] or 0),
        "productos": int(row[1] or 0),
        "inventario_tiendas": int(row[2] or 0),
        "inventario_bodega": int(row[3] or 0),
    }


@app.get("/health")
def health() -> Dict[str, Any]:
    """Estado de salud de la API."""
    return {
        "status": "ok",
        "service": "azure-supply-chain-agent-api",
        "database": "postgresql",
    }


@app.get("/api/dashboard")
def dashboard() -> Dict[str, Any]:
    """Devuelve un resumen del inventario y reposición disponible para un panel."""
    try:
        resumen_db = _consulta_resumen_postgres()
        reposicion = ejecutar_calculo_reposicion()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"No se pudo obtener el dashboard: {exc}",
        ) from exc

    detalle_por_tienda = reposicion.get("detalle_por_tienda", [])
    resumen_por_producto = reposicion.get("resumen_por_producto", [])

    return {
        "resumen": resumen_db,
        "reposicion": {
            "detalle_por_tienda": detalle_por_tienda,
            "resumen_por_producto": resumen_por_producto,
        },
        "totales": {
            "detalle_registros": len(detalle_por_tienda),
            "resumen_productos": len(resumen_por_producto),
        },
    }


@app.get("/api/reposicion")
def reposicion() -> Dict[str, Any]:
    """Ejecuta la lógica real de reposición y devuelve el resultado serializable."""
    try:
        resultado = ejecutar_calculo_reposicion()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"No se pudo ejecutar la reposición: {exc}",
        ) from exc

    return resultado


def _get_foundry_project_client() -> AIProjectClient:
    """Crea un cliente del proyecto Foundry con credenciales Azure Identity."""
    endpoint = os.getenv("AZURE_PROJECT_ENDPOINT")
    if not endpoint:
        raise ValueError("Falta AZURE_PROJECT_ENDPOINT en .env para Foundry.")

    credential = DefaultAzureCredential(exclude_interactive_browser_credential=False)
    return AIProjectClient(endpoint=endpoint, credential=credential, allow_preview=True)


def _response_text_from_foundry(response: Any) -> str:
    """Extrae el texto legible de una respuesta del agente usando la API Responses."""
    output_text = getattr(response, "output_text", None)
    if output_text:
        return str(output_text)

    output_items = getattr(response, "output", []) or []
    for item in output_items:
        item_type = getattr(item, "type", None)
        if item_type == "message":
            for content in getattr(item, "content", []) or []:
                if getattr(content, "type", None) == "output_text":
                    return str(getattr(content, "text", ""))

    return str(response)


@app.post("/api/chat")
def chat(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Invoca al agente persistente de Azure AI Foundry con contexto opcional por conversación."""
    message = str(payload.get("message", "")).strip()
    if not message:
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")

    conversation_id = str(payload.get("conversation_id") or uuid.uuid4())
    session = CONVERSATIONS.setdefault(
        conversation_id,
        {"last_response_id": None},
    )

    agent_reference = {
        "name": "supply-chain-planner",
        "type": "agent_reference",
    }

    try:
        with _get_foundry_project_client() as project_client:
            openai_client = project_client.get_openai_client()
            request_kwargs: Dict[str, Any] = {
                "input": message,
                "extra_body": {
                    "agent_reference": agent_reference,
                },
            }
            if session.get("last_response_id"):
                request_kwargs["previous_response_id"] = session["last_response_id"]

            response = openai_client.responses.create(**request_kwargs)
            response_text = _response_text_from_foundry(response)
            session["last_response_id"] = getattr(response, "id", None)

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"No se pudo contactar al agente persistente de Foundry: {exc}",
        ) from exc

    return {
        "conversation_id": conversation_id,
        "response": response_text,
        "agent": "supply-chain-planner",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=False,
    )
