import argparse
import os
import secrets
import sys
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from mcp.server.fastmcp import FastMCP

from src.agente.foundry_integration import ejecutar_calculo_reposicion

MCP_API_KEY = os.getenv("MCP_API_KEY")
if not MCP_API_KEY:
    raise RuntimeError("MCP_API_KEY no está configurado. Define la variable de entorno antes de iniciar el servidor MCP.")

mcp = FastMCP(
    "supply-chain-agent",
    instructions=(
        "Servidor MCP local para consultar y calcular la reposición de inventario "
        "usando la lógica existente de Azure Supply Chain Agent. "
        "No modifica datos ni expone credenciales."
    ),
    host="0.0.0.0",
    port=8000,
    stateless_http=True,
)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Endpoint liviano para comprobar que el servidor HTTP responde."""
    return JSONResponse(
        {
            "status": "ok",
            "service": "supply-chain-agent",
            "transport": "streamable-http",
            "stateless_http": True,
        }
    )


@mcp.tool(
    name="calcular_reposicion",
    description=(
        "Calcula la reposición para todas las tiendas usando las ventas de las últimas 4 semanas, "
        "el inventario actual y el inventario disponible en bodega. "
        "No modifica la base de datos."
    ),
    structured_output=True,
)
def calcular_reposicion() -> Dict[str, Any]:
    """Ejecuta el cálculo real de reposición definido en la lógica de negocio."""
    return ejecutar_calculo_reposicion()


class MCPBearerAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path == "/health" or path.startswith("/health"):
            return await call_next(request)

        if path == "/mcp" or path.startswith("/mcp"):
            auth_header = request.headers.get("authorization")
            if not auth_header:
                return JSONResponse({"detail": "Authorization header requerido"}, status_code=401)

            scheme, _, token = auth_header.partition(" ")
            if scheme.lower() != "bearer" or not token:
                return JSONResponse({"detail": "Authorization debe usar formato Bearer <token>"}, status_code=401)

            if not secrets.compare_digest(token, MCP_API_KEY):
                return JSONResponse({"detail": "Token inválido"}, status_code=401)

        return await call_next(request)


def build_app():
    app = mcp.streamable_http_app()
    app.add_middleware(MCPBearerAuthMiddleware)
    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Servidor MCP local para Azure Supply Chain Agent")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="streamable-http",
        help="Tipo de transporte para ejecutar el servidor MCP",
    )
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
        return

    import uvicorn

    app = build_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
