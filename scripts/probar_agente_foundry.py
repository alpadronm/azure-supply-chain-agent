import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


BASE_DIR = ROOT
load_dotenv(BASE_DIR / ".env")


def get_project_endpoint() -> str:
    endpoint = os.getenv("AZURE_PROJECT_ENDPOINT")
    if not endpoint:
        raise ValueError("Falta AZURE_PROJECT_ENDPOINT en .env.")
    return endpoint


def main() -> None:
    endpoint = get_project_endpoint()
    prompt = "Describe brevemente tu función y las tareas logísticas que puedes realizar."
    agent_name = "supply-chain-planner"

    try:
        credential = DefaultAzureCredential(exclude_interactive_browser_credential=False)
        with AIProjectClient(endpoint=endpoint, credential=credential, allow_preview=True) as project_client:
            openai_client = project_client.get_openai_client()
            response = openai_client.responses.create(
                input=prompt,
                extra_body={
                    "agent_reference": {
                        "name": agent_name,
                        "type": "agent_reference",
                    }
                },
            )

            output_text = getattr(response, "output_text", None)
            if output_text:
                print(output_text)
                return

            output = getattr(response, "output", None)
            if output is not None:
                print(output)
                return

            print(response)

    except Exception as exc:  # pragma: no cover
        print("Error al invocar el agente persistente de Azure AI Foundry.")
        print(f"Detalle completo: {exc}")
        print("No se revelan credenciales ni tokens.")


if __name__ == "__main__":
    main()
