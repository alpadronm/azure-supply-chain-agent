# Instrucciones de Copilot - Azure Supply Chain Agent

## Objetivo

Crear un prototipo escolar funcional y pequeño de Azure Supply Chain Agent. El proyecto debe demostrar:
- agente de IA en Azure AI Foundry,
- PostgreSQL en Azure Database for PostgreSQL,
- Python para la lógica logística,
- almacenamiento de archivos Excel en Azure Storage,
- y una interfaz web sencilla.

## Principios

- Mantener el proyecto pequeño, claro y fácil de entender.
- Priorizar un prototipo funcional sobre una arquitectura avanzada.
- Usar Python determinista para cálculos logísticos.
- Reutilizar solo las dependencias necesarias.
- No introducir complejidad innecesaria, servicios adicionales ni abstracciones profundas.
- No inventar datos ni crear recursos Azure nuevos.
- No almacenar credenciales ni secretos en el repositorio.
- No tocar recursos Azure ya existentes ni archivos .env reales.

## Estructura esperada

Mantener una organización simple:
- README.md: descripción general del proyecto.
- requirements.txt: dependencias mínimas.
- .env.example: ejemplo de variables de entorno.
- src/: lógica principal.
  - src/agente/: integración con Azure AI Foundry.
  - src/base_datos/: conexión y acceso a PostgreSQL.
  - src/logistica/: cálculos logísticos y validaciones.
  - src/documentos/: generación de archivos Excel y reportes.
  - src/api/: endpoints o servicios simples.
- pruebas/: pruebas básicas.
- salida/: archivos temporales o exportaciones del prototipo.

## Reglas para cambios

- Mantener la lógica de negocio simple y verificable.
- Preferir nombres claros en español cuando sea viable.
- No crear una arquitectura de microservicios ni múltiples capas complejas.
- No proponer Azure Functions, OR-Tools, modelos predictivos complejos ni diseño de base de datos enorme si no es necesario para el prototipo.
- No crear más carpetas ni módulos de los estrictamente necesarios.
- Cuando exista una opción simple y una compleja, elegir la simple.
- Documentar cambios breves y útiles.

## Validación

- Mantener pruebas pequeñas y enfocadas.
- Verificar que el proyecto siga siendo comprensible para un estudiante o un equipo pequeño.
- Si una funcionalidad requiere demasiada complejidad, reducir el alcance en lugar de ampliarlo.

## Restricciones

- No se deben incluir credenciales reales.
- No se deben subir archivos .env ni secretos.
- No se deben modificar ni eliminar recursos de Azure existentes.
- El objetivo es un prototipo escolar funcional, no una plataforma enterprise.
