import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import FunctionTool, PromptAgentDefinition
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from src.base_datos.conexion import get_connection
from src.logistica.calculo_reposicion import (
    generar_resumen_por_producto,
    generar_resultados_reposicion,
)

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


def get_azure_project_endpoint() -> str:
    endpoint = os.getenv("AZURE_PROJECT_ENDPOINT")
    if not endpoint:
        raise ValueError(
            "Falta AZURE_PROJECT_ENDPOINT en .env. Debe apuntar al proyecto de Azure AI Foundry."
        )
    return endpoint


def get_agent_name() -> str:
    agent_name = os.getenv("AZURE_AGENT_NAME", "supply-chain-planner")
    if not agent_name:
        raise ValueError("Falta AZURE_AGENT_NAME en .env.")
    return agent_name


def get_model_name() -> str:
    model_name = os.getenv("AZURE_MODEL_NAME", "gpt-4.1-mini")
    if not model_name:
        raise ValueError("Falta AZURE_MODEL_NAME en .env.")
    return model_name


def get_project_client() -> AIProjectClient:
    """Crea el cliente del proyecto usando Azure Identity y el endpoint oficial del proyecto."""
    credential = DefaultAzureCredential(exclude_interactive_browser_credential=False)
    endpoint = get_azure_project_endpoint()
    return AIProjectClient(endpoint=endpoint, credential=credential, allow_preview=True)


def ejecutar_calculo_reposicion() -> Dict[str, Any]:
    """Ejecuta el cálculo existente de reposición sin modificar la base de datos."""
    detalle = generar_resultados_reposicion()
    resumen = generar_resumen_por_producto()
    return {
        "detalle_por_tienda": detalle,
        "resumen_por_producto": resumen,
    }


def _parse_int(value: Any, field_name: str) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"El parámetro '{field_name}' debe ser un número entero válido.") from exc


def consultar_inventario_db(
    tienda: Optional[str] = None,
    producto: Optional[str] = None,
    tienda_id: Optional[int] = None,
    producto_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Consulta inventario real de PostgreSQL y devuelve resultados legibles para el agente."""
    filters: List[str] = []
    params: List[Any] = []
    index = 1

    if tienda_id is not None:
        filters.append(f"t.id = %s")
        params.append(int(tienda_id))
        index += 1
    elif tienda:
        filters.append(f"LOWER(t.nombre) LIKE LOWER(%s)")
        params.append(f"%{str(tienda).strip()}%")
        index += 1

    if producto_id is not None:
        filters.append(f"p.id = %s")
        params.append(int(producto_id))
        index += 1
    elif producto:
        filters.append(f"LOWER(p.nombre) LIKE LOWER(%s)")
        params.append(f"%{str(producto).strip()}%")
        index += 1

    if not filters:
        raise ValueError(
            "Debe indicar al menos un filtro válido: tienda, producto, tienda_id o producto_id."
        )

    query = """
        SELECT
            t.id AS tienda_id,
            t.nombre AS tienda,
            p.id AS producto_id,
            p.codigo AS codigo_producto,
            p.nombre AS nombre_producto,
            COALESCE(it.cantidad_cajas, 0) AS inventario_tienda,
            COALESCE(ib.cantidad_cajas, 0) AS inventario_bodega
        FROM tiendas t
        CROSS JOIN productos p
        LEFT JOIN inventarios_tienda it
            ON it.tienda_id = t.id
           AND it.producto_id = p.id
        LEFT JOIN inventario_bodega ib
            ON ib.producto_id = p.id
    """

    query += " WHERE " + " AND ".join(filters)
    query += " ORDER BY t.id, p.id;"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

    resultados = []
    for row in rows:
        resultados.append(
            {
                "tienda_id": int(row[0]),
                "tienda": row[1],
                "producto_id": int(row[2]),
                "codigo_producto": row[3],
                "nombre_producto": row[4],
                "inventario_tienda": int(row[5]),
                "inventario_bodega": int(row[6]),
            }
        )

    return {
        "filtros": {
            "tienda": tienda,
            "producto": producto,
            "tienda_id": tienda_id,
            "producto_id": producto_id,
        },
        "total_registros": len(resultados),
        "resultados": resultados,
    }


def build_inventario_tool() -> Dict[str, Any]:
    """Define la herramienta que consulta inventario real desde PostgreSQL."""
    return {
        "type": "function",
        "name": "consultar_inventario",
        "description": (
            "Consulta inventarios reales de tiendas y bodega usando PostgreSQL. "
            "Permite filtrar por tienda y/o producto. Devuelve cantidades reales de inventario y "
            "nunca inventa cantidades. Solo usar esta herramienta para consultas de inventario."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "tienda": {
                    "type": ["string", "null"],
                    "description": "Nombre de la tienda para filtrar. Opcional.",
                },
                "producto": {
                    "type": ["string", "null"],
                    "description": "Nombre del producto o sabor para filtrar. Opcional.",
                },
                "tienda_id": {
                    "type": ["integer", "null"],
                    "description": "ID de la tienda. Opcional.",
                },
                "producto_id": {
                    "type": ["integer", "null"],
                    "description": "ID del producto. Opcional.",
                },
            },
            "required": [],
        },
    }


def build_reposicion_tool() -> Dict[str, Any]:
    """Define la herramienta para Function Calling del cliente OpenAI Responses."""
    return {
        "type": "function",
        "name": "consultar_reposicion",
        "description": (
            "Calcula la reposición de inventario usando la lógica existente en Python. "
            "Devuelve resultados reales de reposición de PostgreSQL sin duplicar la lógica de negocio."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    }


def _parse_tool_arguments(raw_arguments: Any) -> Dict[str, Any]:
    """Convierte argumentos JSON a diccionario y valida el tipo de entrada."""
    if raw_arguments is None:
        return {}
    if isinstance(raw_arguments, str):
        try:
            parsed = json.loads(raw_arguments)
        except json.JSONDecodeError as exc:
            raise ValueError("Los argumentos de la herramienta no son JSON válido.") from exc
    else:
        parsed = raw_arguments

    if not isinstance(parsed, dict):
        raise ValueError("Los argumentos de la herramienta deben ser un objeto JSON.")

    return parsed


def ejecutar_tool_inventario(arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Ejecuta la consulta de inventario con validación de parámetros."""
    payload = arguments or {}
    if not isinstance(payload, dict):
        raise ValueError("Los argumentos de la herramienta deben ser un objeto JSON con filtros.")

    tienda = payload.get("tienda")
    producto = payload.get("producto")

    if tienda is not None and not isinstance(tienda, str):
        raise ValueError("El parámetro 'tienda' debe ser una cadena de texto.")
    if producto is not None and not isinstance(producto, str):
        raise ValueError("El parámetro 'producto' debe ser una cadena de texto.")

    if not any(value is not None for value in [tienda, producto, payload.get("tienda_id"), payload.get("producto_id")]):
        raise ValueError("Debe indicar al menos un filtro válido: tienda, producto, tienda_id o producto_id.")

    tienda_id = _parse_int(payload.get("tienda_id"), "tienda_id")
    producto_id = _parse_int(payload.get("producto_id"), "producto_id")

    return consultar_inventario_db(
        tienda=tienda,
        producto=producto,
        tienda_id=tienda_id,
        producto_id=producto_id,
    )


def ejecutar_tool_reposicion() -> Dict[str, Any]:
    """Compatibilidad para que el agente pueda invocar la función Python de reposición."""
    return ejecutar_calculo_reposicion()


def build_agent_instruction_prompt(prompt: str) -> str:
    """Da contexto a la respuesta para que el agente sebase solo responder con datos de inventario y reposición."""
    return (
        "Eres el agente de inventario de Gelato Supply Chain. "
        "Responde solo en español. "
        "Si el usuario pregunta por inventario o reposición, usa únicamente los datos devueltos por las herramientas. "
        "Nunca inventes cantidades, tiendas, productos o fechas. "
        "Si la herramienta no devuelve resultados, indica que no hay información disponible y no afirmes haber consultado la base de datos. "
        "Mantén el alcance a inventarios y reposición. No planifiques transporte ni asignación de vehículos. "
        f"\n\nPregunta del usuario: {prompt}"
    )


def build_prompt_agent_definition() -> PromptAgentDefinition:
    """Crea la definición del agente persistente con herramientas de inventario y reposición."""
    return PromptAgentDefinition(
        kind="prompt",
        model=get_model_name(),
        instructions=(
            "Eres el agente de inventario de Gelato Supply Chain. "
            "Responde siempre en español. "
            "Consulta la información de inventario y reposición únicamente a través de las herramientas disponibles. "
            "No inventes cantidades, tiendas, productos, fechas ni resultados. "
            "Si no hay datos disponibles, indica que no hay información disponible. "
            "Mantén el alcance dentro de inventarios y reposición. "
            "No propongas rutas de transporte ni asignación de vehículos."
        ),
        tools=[
            FunctionTool(
                type="function",
                name="consultar_inventario",
                description=(
                    "Consulta inventarios reales de tiendas y bodega usando PostgreSQL. "
                    "Permite filtrar por tienda y/o producto. Devuelve cantidades reales de inventario y "
                    "nunca inventa cantidades. Solo usar esta herramienta para consultas de inventario."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "tienda": {
                            "type": ["string", "null"],
                            "description": "Nombre de la tienda para filtrar. Opcional.",
                        },
                        "producto": {
                            "type": ["string", "null"],
                            "description": "Nombre del producto o sabor para filtrar. Opcional.",
                        },
                        "tienda_id": {
                            "type": ["integer", "null"],
                            "description": "ID de la tienda. Opcional.",
                        },
                        "producto_id": {
                            "type": ["integer", "null"],
                            "description": "ID del producto. Opcional.",
                        },
                    },
                    "required": [],
                },
                strict=False,
            ),
            FunctionTool(
                type="function",
                name="consultar_reposicion",
                description=(
                    "Calcula la reposición de inventario usando la lógica existente en Python. "
                    "Devuelve resultados reales de reposición de PostgreSQL sin duplicar la lógica de negocio."
                ),
                parameters={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
                strict=False,
            ),
        ],
        tool_choice="auto",
    )


def publicar_nueva_version_agente() -> Any:
    """Publica explícitamente una nueva versión del agente persistente con las herramientas definidas."""
    with get_project_client() as project_client:
        definition = build_prompt_agent_definition()
        return project_client.agents.create_version(
            agent_name=get_agent_name(),
            definition=definition,
            description="Versión con herramientas de inventario y reposición para Gelato Supply Chain.",
        )


def invoke_agent_with_inventory_tools(
    prompt: str,
    previous_response_id: Optional[str] = None,
) -> Any:
    """Invoca el agente persistente con herramientas de inventario y reposición."""
    with get_project_client() as project_client:
        openai_client = project_client.get_openai_client(agent_name=get_agent_name())
        max_rounds = 5

        request_kwargs: Dict[str, Any] = {
            "input": prompt,
        }
        if previous_response_id:
            request_kwargs["previous_response_id"] = previous_response_id

        response = openai_client.responses.create(**request_kwargs)

        for round_index in range(1, max_rounds + 1):
            function_calls = [
                item
                for item in getattr(response, "output", []) or []
                if getattr(item, "type", None) == "function_call"
            ]

            if not function_calls:
                return response

            function_outputs = []
            for item in function_calls:
                function_name = getattr(item, "name", None)
                call_id = getattr(item, "call_id", None)
                raw_arguments = getattr(item, "arguments", None)

                try:
                    arguments = _parse_tool_arguments(raw_arguments)
                except ValueError as exc:
                    result = {"error": str(exc)}
                else:
                    try:
                        if function_name == "consultar_inventario":
                            result = ejecutar_tool_inventario(arguments)
                        elif function_name == "consultar_reposicion":
                            result = ejecutar_tool_reposicion()
                        else:
                            result = {"error": f"Función no soportada: {function_name}"}
                    except ValueError as exc:
                        result = {"error": str(exc)}
                    except Exception as exc:
                        result = {"error": f"Error al ejecutar la herramienta: {exc}"}

                function_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": json.dumps(result, ensure_ascii=False, default=str),
                    }
                )

            response = openai_client.responses.create(
                previous_response_id=response.id,
                input=function_outputs,
            )

            if not any(
                getattr(item, "type", None) == "function_call"
                for item in getattr(response, "output", []) or []
            ):
                return response

            if round_index >= max_rounds:
                raise RuntimeError(
                    "Se alcanzó el límite máximo de 5 rondas de Function Calling. "
                    "El agente sigue solicitando herramientas y no se obtuvo una respuesta final."
                )
