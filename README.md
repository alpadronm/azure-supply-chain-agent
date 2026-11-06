# Gelato Supply Chain

Azure Supply Chain Agent es una aplicación web que utiliza inteligencia artificial para facilitar la consulta y el análisis de inventarios dentro de una cadena de tiendas. Su objetivo es ayudar a los usuarios a obtener información sobre las existencias de productos en las tiendas y en bodega, así como apoyar la toma de decisiones relacionadas con el abastecimiento y la reposición de productos.

La aplicación cuenta con un asistente virtual con el que se puede interactuar mediante preguntas escritas en lenguaje natural, sin necesidad de utilizar consultas técnicas o acceder directamente a la base de datos.

## ¿Cómo funciona?

El usuario ingresa a la aplicación desde un navegador y escribe una pregunta al asistente, por ejemplo, solicitando conocer el inventario de un producto en todas las tiendas.

Cuando recibe la pregunta, el asistente utiliza inteligencia artificial para interpretar lo que necesita el usuario e identificar qué información debe consultar. Posteriormente, utiliza herramientas conectadas a una base de datos PostgreSQL para obtener los datos correspondientes, tanto de las tiendas como de la bodega.

Una vez que obtiene la información, el asistente procesa los resultados y genera una respuesta en lenguaje natural que se muestra directamente en la aplicación.

De esta manera, el usuario puede consultar información y obtener respuestas sin tener que revisar manualmente diferentes registros o tablas.

## Pruebas de uso

- Dashboard/Página principal
<img width="1894" height="721" alt="Captura de pantalla 2026-11-06 011248" src="https://github.com/user-attachments/assets/f9f0b674-8d2d-4ad2-98ce-a6c80324d9dd" />

- Tabla de recomendación para reposición de producto
<img width="1629" height="827" alt="Captura de pantalla 2026-11-06 011256" src="https://github.com/user-attachments/assets/2c6a9e61-5b61-40f4-b18c-bfddc365d290" />

- Tabla de inventario en bodega
<img width="1625" height="430" alt="Captura de pantalla 2026-11-06 011302" src="https://github.com/user-attachments/assets/6021df8a-ebea-4648-9731-07e7dd5675ad" />

- Cuadro de chat con el agente
<img width="1621" height="392" alt="Captura de pantalla 2026-11-06 011311" src="https://github.com/user-attachments/assets/6e6f0460-9cbc-4520-966f-143adc3841b4" />

- Consulta de stock por producto disponible en tienda
<img width="1594" height="393" alt="Captura de pantalla 2026-11-06 012515" src="https://github.com/user-attachments/assets/bf95b5ba-f380-4eac-86f1-2089e950158f" />

- Consulta de próximas reposiciones a realizarse
<img width="1593" height="588" alt="Captura de pantalla 2026-11-06 013211" src="https://github.com/user-attachments/assets/d84b7a74-2e59-42b9-9b6b-6e58160886c7" />
<img width="1601" height="593" alt="Captura de pantalla 2026-11-06 013218" src="https://github.com/user-attachments/assets/ab715870-5fc7-4785-bda3-0490e1fdf914" />

- Descarga de documento de Excel con el resumen de las tablas
<img width="1919" height="982" alt="Captura de pantalla 2026-11-06 013643" src="https://github.com/user-attachments/assets/abbd768d-1aca-4f7e-b231-eb72a61ca250" />
<img width="1915" height="1015" alt="Captura de pantalla 2026-11-06 013659" src="https://github.com/user-attachments/assets/646b5427-9438-45fb-b963-e17841f93991" />

Estos son algunos de los ejemplos con los que puede ayudar esta herramienta para la gestión logística.

## Tecnologías usadas
- Python: lenguaje utilizado para desarrollar la lógica de la aplicación.

- FastAPI: encargado de recibir las solicitudes y comunicar la interfaz con el agente.

- Azure AI Foundry: plataforma utilizada para crear e integrar el asistente de inteligencia artificial.

- GPT-4.1-mini: modelo de inteligencia artificial que interpreta las preguntas y genera las respuestas.

- PostgreSQL: base de datos donde se almacena la información de inventarios.

- Docker: utilizado para empaquetar la aplicación y facilitar su despliegue.

- Azure Container Apps: servicio de Microsoft Azure donde se encuentra alojada la aplicación.
