import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.base_datos.conexion import get_connection


TABLAS = [
    ("tiendas", "SELECT * FROM tiendas ORDER BY id;"),
    ("productos", "SELECT * FROM productos ORDER BY id;"),
    ("inventarios_tienda", "SELECT * FROM inventarios_tienda ORDER BY id;"),
    ("inventario_bodega", "SELECT * FROM inventario_bodega ORDER BY id;"),
    ("ventas", "SELECT * FROM ventas ORDER BY fecha, tienda_id, producto_id;"),
]


def main():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                for nombre_tabla, query in TABLAS:
                    cur.execute(query)
                    filas = cur.fetchall()
                    print(f"\n--- {nombre_tabla} ({len(filas)} registros) ---")
                    if not filas:
                        print("Sin registros.")
                        continue
                    for fila in filas:
                        print(fila)
    except Exception as exc:  # pragma: no cover
        print("No fue posible consultar la base de datos.")
        print(f"Detalle: {exc}")
        print("Revisa que el servidor Azure PostgreSQL esté disponible y que la configuración de .env sea correcta.")


if __name__ == "__main__":
    main()
