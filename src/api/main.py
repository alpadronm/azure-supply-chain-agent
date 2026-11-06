import os
import uuid
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from src.agente.foundry_integration import (
    ejecutar_calculo_reposicion,
    invoke_agent_with_inventory_tools,
)
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


def _producto_codigo_y_nombre(product_label: Any) -> Dict[str, str]:
    """Separa la etiqueta Producto en código y nombre para exportar al Excel."""
    text = str(product_label or "").strip()
    if " - " in text:
        codigo, nombre = text.split(" - ", 1)
        return {"codigo": codigo.strip(), "nombre": nombre.strip()}
    return {"codigo": text, "nombre": text}


def _aplicar_estilo_hoja(worksheet, headers: List[str]) -> None:
    """Aplica estilos visuales de la identidad de Gelato a las filas de cabecera."""
    header_fill = PatternFill(fill_type="solid", fgColor="4B3028")
    header_font = Font(color="FFFFFF", bold=True)
    center_alignment = Alignment(horizontal="center", vertical="center")

    for cell in worksheet[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_alignment

    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = worksheet.dimensions
    for column_index, _ in enumerate(headers, start=1):
        width = max(12, min(28, len(_)))
        worksheet.column_dimensions[get_column_letter(column_index)].width = width

    for row in worksheet.iter_rows(min_row=2, max_row=worksheet.max_row, min_col=1, max_col=worksheet.max_column):
        for cell in row:
            if isinstance(cell.value, (int, float)):
                cell.number_format = "0"
            cell.alignment = Alignment(horizontal="left", vertical="center")


def _generar_libro_excel() -> bytes:
    """Genera el reporte en XLSX usando los datos actuales de reposición."""
    resultado = ejecutar_calculo_reposicion()
    detalle_por_tienda = resultado.get("detalle_por_tienda", [])
    resumen_por_producto = resultado.get("resumen_por_producto", [])

    wb = Workbook()

    hoja_resumen = wb.active
    hoja_resumen.title = "Resumen"
    cabeceras_resumen = [
        "Tienda",
        "Código del producto",
        "Sabor de gelato",
        "Inventario actual",
        "Demanda proyectada",
        "Pedido sugerido",
        "Cantidad que puede surtirse",
        "Faltante",
    ]
    hoja_resumen.append(cabeceras_resumen)

    for item in detalle_por_tienda:
        producto = _producto_codigo_y_nombre(item.get("Producto", ""))
        hoja_resumen.append(
            [
                item.get("Tienda", ""),
                producto["codigo"],
                producto["nombre"],
                int(item.get("Inventario actual", 0) or 0),
                int(item.get("Demanda proyectada a 7 días", 0) or 0),
                int(item.get("Pedido sugerido", 0) or 0),
                int(item.get("Cantidad que podría surtirse", 0) or 0),
                int(item.get("Cantidad faltante para esta tienda", 0) or 0),
            ]
        )

    _aplicar_estilo_hoja(hoja_resumen, cabeceras_resumen)

    hoja_sabor = wb.create_sheet("Resumen por sabor")
    cabeceras_sabor = [
        "Código del producto",
        "Sabor",
        "Inventario total en tiendas",
        "Inventario disponible en bodega",
        "Necesidad total",
        "Cantidad total que puede surtirse",
        "Faltante total",
    ]
    hoja_sabor.append(cabeceras_sabor)

    producto_totales: Dict[str, Dict[str, Any]] = {}
    for item in detalle_por_tienda:
        producto = _producto_codigo_y_nombre(item.get("Producto", ""))
        clave = producto["codigo"]
        if clave not in producto_totales:
            producto_totales[clave] = {
                "codigo": clave,
                "nombre": producto["nombre"],
                "inventario_total_tiendas": 0,
            }
        producto_totales[clave]["inventario_total_tiendas"] += int(item.get("Inventario actual", 0) or 0)

    resumen_por_codigo = {
        item.get("Producto", "").split(" - ", 1)[0]: item
        for item in resumen_por_producto
        if str(item.get("Producto", "")).strip()
    }

    for codigo in sorted(producto_totales.keys()):
        resumen_item = resumen_por_codigo.get(codigo, {})
        producto = _producto_codigo_y_nombre(resumen_item.get("Producto", producto_totales[codigo]["nombre"]))
        hoja_sabor.append(
            [
                codigo,
                producto["nombre"],
                int(producto_totales[codigo].get("inventario_total_tiendas", 0) or 0),
                int(resumen_item.get("Inventario disponible en bodega", 0) or 0),
                int(resumen_item.get("Necesidad total de las tiendas", 0) or 0),
                int(resumen_item.get("Cantidad que puede surtirse", 0) or 0),
                int(resumen_item.get("Cantidad faltante", 0) or 0),
            ]
        )

    _aplicar_estilo_hoja(hoja_sabor, cabeceras_sabor)

    output = BytesIO()
    wb.save(output)
    return output.getvalue()


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


@app.get("/api/reporte-excel")
def reporte_excel() -> StreamingResponse:
    """Descarga un archivo XLSX generado a partir de la reposición actual."""
    try:
        workbook_bytes = _generar_libro_excel()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo generar el reporte Excel: {exc}",
        ) from exc

    filename = f"Reporte_Gelato_Supply_Chain_{__import__('datetime').datetime.now().strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        BytesIO(workbook_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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

    try:
        response = invoke_agent_with_inventory_tools(
            prompt=message,
            previous_response_id=session.get("last_response_id"),
        )
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
