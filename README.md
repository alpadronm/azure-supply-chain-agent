# Azure Supply Chain Agent

Azure Supply Chain Agent es un prototipo escolar para gestionar inventarios, ventas y reposición de productos en varias tiendas con apoyo de Azure AI Foundry, PostgreSQL y una interfaz web mínima. El objetivo es demostrar una solución fácil de entender y funcional, centrada en cálculos deterministas y en la integración con servicios de Azure.

## Objetivo del proyecto

- Consultar inventarios, productos, tiendas y ventas desde PostgreSQL.
- Calcular la reposición sugerida para la próxima semana.
- Mostrar resultados reales en un panel web simple.
- Permitir la consulta a un agente persistente de Azure AI Foundry.
- Exponer la lógica de negocio a través de un servidor MCP local.

## Tecnologías principales

- Python 3.11+
- PostgreSQL en Azure Database for PostgreSQL
- FastAPI para la API y el panel web
- Azure AI Foundry / Azure AI Projects
- Azure Identity
- psycopg para acceso a PostgreSQL
- MCP Python SDK para el servidor MCP

## Estructura del proyecto

- `src/agente/`: integración con Azure AI Foundry y servidor MCP.
- `src/base_datos/`: conexión y acceso a PostgreSQL.
- `src/logistica/`: cálculo de reposición y lógica de negocio.
- `src/api/`: endpoints de la API REST.
- `src/web/`: interfaz web estática servida por FastAPI.
- `scripts/`: utilidades para pruebas locales.
- `salida/`: exportaciones y archivos generados localmente.

## Requisitos

- Python 3.11 o superior
- PostgreSQL con acceso correcto en Azure
- Variables de entorno configuradas en un archivo `.env` local
- Credenciales de Azure autenticadas con `DefaultAzureCredential` o equivalente
- Dependencias listadas en `requirements.txt`

## Instalación local

1. Clona o descarga el proyecto.
2. Crea un entorno virtual:

   python -m venv .venv
   .\.venv\Scripts\activate

3. Instala dependencias:

   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt

4. Crea un archivo `.env` local basado en el ejemplo:

   Copy-Item .env.example .env

5. Ajusta los valores de tu entorno local en `.env`.

## Configuración de entorno

El proyecto usa variables de entorno para PostgreSQL, Azure AI Foundry y el servidor MCP. Consulta [.env.example](./.env.example) como referencia. No compartas ni publiques valores reales.

Variables principales:

- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `AZURE_PROJECT_ENDPOINT`
- `AZURE_AGENT_NAME`
- `AZURE_MODEL_NAME`
- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`
- `MCP_API_KEY`
- `CORS_ALLOWED_ORIGINS`
- `PORT`
- `LOG_LEVEL`

## Ejecución local

### API y panel web

Desde la raíz del proyecto:

   python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

Luego abre la siguiente URL en el navegador:

   http://localhost:8000/

### Servidor MCP

   python src\agente\mcp_server.py --transport streamable-http

El servidor expone la herramienta `calcular_reposicion` y requiere autenticación Bearer mediante `MCP_API_KEY`.

## Estado actual

Este repositorio contiene una primera versión funcional del prototipo con:

- conexión a PostgreSQL,
- cálculo determinista de reposición,
- API FastAPI,
- dashboard web básico,
- integración inicial con Azure AI Foundry,
- y un servidor MCP local para la herramienta de cálculo.

No se incluyen funcionalidades de transporte, GPS, optimización avanzada ni despliegue multi-servicio; este proyecto sigue siendo un prototipo pequeño y comprensible.

## Seguridad y buenas prácticas

- Los secretos nunca deben guardarse en el código fuente.
- El archivo `.env` local debe mantenerse fuera del control de versiones.
- `.env.example` sirve únicamente como plantilla y no debe contener valores reales.
- Los reportes generados y archivos temporales se manejan localmente y no deben compartirse sin revisar su contenido.

## Arquitectura general

La solución actual se compone de cuatro piezas principales:

1. PostgreSQL para almacenamiento de datos operativos.
2. Lógica de negocio en Python para cálculos de reposición y validación.
3. FastAPI para la API y la interfaz web mínima.
4. Azure AI Foundry para la integración del agente y la consulta del usuario.

Este diseño busca mantener la implementación simple, la lógica verificable y la operación accesible para un prototipo académico o de equipo pequeño.
