import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.base_datos.conexion import get_connection


def main():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                version = cur.fetchone()[0]
        print("Conexión exitosa a PostgreSQL.")
        print(version)
    except ValueError as error:
        print(f"No se pudo iniciar la conexión: {error}")
        print("Verifica que el archivo .env exista y contenga las variables requeridas.")
    except Exception as error:  # pragma: no cover
        print("Error de conexión a PostgreSQL.")
        print(f"Detalle: {error}")
        print("Revisa el host, puerto, usuario, contraseña y que el servidor permita SSL.")


if __name__ == "__main__":
    main()
