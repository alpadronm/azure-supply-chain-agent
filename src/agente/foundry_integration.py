import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

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


def get_agent_reference_model() -> Dict[str, str]:
    """Compatibilidad con el agente del proyecto.

    El objeto ``agent_reference`` no es compatible con el cliente OpenAI Responses estándar
    de ``project_client.get_openai_client()`` en azure-ai-projects 2.10.0. La invocación
    oficial de proyecto usa el nombre del modelo desplegado (por ejemplo, ``gpt-4.1-mini``)
    y no un objeto de tipo ``agent_reference``. El nombre del agente existente sigue
    disponible para uso en la API de ``project_client.agents`` cuando se requiere invocar
    el agente por nombre, no como ``model`` del cliente OpenAI.
    """
    return {"type": "agent_reference", "name": get_agent_name()}


def ejecutar_calculo_reposicion() -> Dict[str, Any]:
    """Ejecuta el cálculo existente de reposición sin modificar la base de datos."""
    detalle = generar_resultados_reposicion()
    resumen = generar_resumen_por_producto()
    return {
        "detalle_por_tienda": detalle,
        "resumen_por_producto": resumen,
    }


def build_reposicion_tool() -> Dict[str, Any]:
    """Define la herramienta para Function Calling del cliente OpenAI Responses."""
    return {
        "type": "function",
        "name": "calcular_reposicion",
        "description": (
            "Calcula la reposición de inventario para cada tienda y producto usando "
            "las ventas de las últimas 4 semanas, el inventario actual y el inventario disponible "
            "en bodega. No modifica la base de datos ni crea nuevos registros."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    }


def ejecutar_tool_reposicion() -> Dict[str, Any]:
    """Compatibilidad simple para que el agente pueda invocar la función Python."""
    return ejecutar_calculo_reposicion()


def invoke_agent_reposicion(prompt: str) -> Any:
    """Invoca el modelo de Foundry mediante Responses API usando el deployment del proyecto.

    El nombre del agente existente (`supply-chain-planner`) no debe pasarse como ``model`` del
    cliente OpenAI de project_client.get_openai_client() en azure-ai-projects 2.10.0; la API
    oficial del cliente OpenAI responde con un ``model`` de despliegue (por ejemplo,
    ``gpt-4.1-mini``). Si se requiere invocar un agente registrado del proyecto, la API
    compatible es la de ``project_client.agents`` y no el payload ``model={...}`` del cliente
    OpenAI.
    """
    with get_project_client() as project_client:
        openai_client = project_client.get_openai_client()
        tool_definition = build_reposicion_tool()
        model_name = get_model_name()

        response = openai_client.responses.create(
            model=model_name,
            input=prompt,
            tools=[tool_definition],
            tool_choice="auto",
        )

        output_items = getattr(response, "output", []) or []
        for item in output_items:
            if getattr(item, "type", None) == "function_call":
                result = ejecutar_tool_reposicion()
                follow_up = openai_client.responses.create(
                    model=model_name,
                    previous_response_id=response.id,
                    input=[
                        {
                            "type": "function_call_output",
                            "call_id": item.call_id,
                            "output": json.dumps(result),
                        }
                    ],
                )
                return follow_up

        return response
