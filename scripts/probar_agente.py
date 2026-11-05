import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agente.foundry_integration import invoke_agent_reposicion


def main():
    try:
        prompt = (
            "Calcula la reposición de inventario para todas las tiendas y muestra el resumen "
            "por producto. Usa la lógica disponible en Python y no modifiques PostgreSQL."
        )

        response = invoke_agent_reposicion(prompt)
        output_text = getattr(response, "output_text", None)
        if output_text:
            print(output_text)
            return

        if hasattr(response, "output"):
            print(json.dumps(response.output, default=str, ensure_ascii=False, indent=2))
            return

        print(response)
    except ValueError as exc:
        print(f"Falta configuración para Azure AI Foundry: {exc}")
        print("Completa AZURE_PROJECT_ENDPOINT y AZURE_AGENT_NAME en .env.")
    except Exception as exc:  # pragma: no cover
        print("No fue posible conectar con Azure AI Foundry.")
        print(f"Detalle: {exc}")
        print("Verifica el proyecto, el agente existente y que el usuario tenga permisos correctos.")


if __name__ == "__main__":
    main()
