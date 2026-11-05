import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.base_datos.conexion import get_connection


CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS tiendas (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    ciudad VARCHAR(100) NOT NULL,
    dias_operacion TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS productos (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(50) NOT NULL UNIQUE,
    nombre VARCHAR(150) NOT NULL,
    unidad VARCHAR(50) NOT NULL DEFAULT 'cajas'
);

CREATE TABLE IF NOT EXISTS inventarios_tienda (
    id SERIAL PRIMARY KEY,
    tienda_id INTEGER NOT NULL REFERENCES tiendas(id) ON DELETE RESTRICT,
    producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE RESTRICT,
    cantidad_cajas INTEGER NOT NULL CHECK (cantidad_cajas >= 0),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (tienda_id, producto_id)
);

CREATE TABLE IF NOT EXISTS inventario_bodega (
    id SERIAL PRIMARY KEY,
    producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE RESTRICT,
    cantidad_cajas INTEGER NOT NULL CHECK (cantidad_cajas >= 0),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (producto_id)
);

CREATE TABLE IF NOT EXISTS ventas (
    id SERIAL PRIMARY KEY,
    tienda_id INTEGER NOT NULL REFERENCES tiendas(id) ON DELETE RESTRICT,
    producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE RESTRICT,
    fecha DATE NOT NULL,
    cantidad_cajas INTEGER NOT NULL CHECK (cantidad_cajas >= 0),
    UNIQUE (tienda_id, producto_id, fecha)
);
"""


def crear_tablas():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLES_SQL)
            conn.commit()
        print("Tablas creadas o validadas correctamente.")


def cargar_datos_ficticios():
    with get_connection() as conn:
        with conn.cursor() as cur:
            tiendas = [
                ("Tienda Centro", "Ciudad de México", "Lunes a Domingo"),
                ("Tienda Norte", "Monterrey", "Lunes a Sábado"),
                ("Tienda Sur", "Guadalajara", "Lunes a Domingo"),
            ]

            for nombre, ciudad, dias_operacion in tiendas:
                cur.execute(
                    """
                    INSERT INTO tiendas (nombre, ciudad, dias_operacion)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (nombre) DO NOTHING
                    """,
                    (nombre, ciudad, dias_operacion),
                )

            productos = [
                ("P-1001", "Arroz 1kg", "cajas"),
                ("P-1002", "Frijol 1kg", "cajas"),
                ("P-1003", "Aceite 1L", "cajas"),
                ("P-1004", "Pasta 500g", "cajas"),
                ("P-1005", "Azúcar 1kg", "cajas"),
            ]

            for codigo, nombre, unidad in productos:
                cur.execute(
                    """
                    INSERT INTO productos (codigo, nombre, unidad)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (codigo) DO NOTHING
                    """,
                    (codigo, nombre, unidad),
                )

            tienda_map = {}
            for nombre, _, _ in tiendas:
                cur.execute("SELECT id FROM tiendas WHERE nombre = %s", (nombre,))
                row = cur.fetchone()
                tienda_map[nombre] = row[0]

            productos_ids = {}
            for codigo, _, _ in productos:
                cur.execute("SELECT id FROM productos WHERE codigo = %s", (codigo,))
                row = cur.fetchone()
                productos_ids[codigo] = row[0]

            inventario_bodega = {
                "P-1001": 180,
                "P-1002": 210,
                "P-1003": 150,
                "P-1004": 190,
                "P-1005": 160,
            }
            for codigo, cantidad in inventario_bodega.items():
                cur.execute(
                    """
                    INSERT INTO inventario_bodega (producto_id, cantidad_cajas, fecha_actualizacion)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (producto_id) DO UPDATE SET
                        cantidad_cajas = EXCLUDED.cantidad_cajas,
                        fecha_actualizacion = CURRENT_TIMESTAMP
                    """,
                    (productos_ids[codigo], cantidad),
                )

            inventarios_por_tienda = {
                "Tienda Centro": {"P-1001": 50, "P-1002": 40, "P-1003": 30, "P-1004": 45, "P-1005": 35},
                "Tienda Norte": {"P-1001": 42, "P-1002": 38, "P-1003": 28, "P-1004": 32, "P-1005": 30},
                "Tienda Sur": {"P-1001": 46, "P-1002": 44, "P-1003": 35, "P-1004": 40, "P-1005": 33},
            }

            for nombre, inventario in inventarios_por_tienda.items():
                tienda_id = tienda_map[nombre]
                for codigo, cantidad in inventario.items():
                    cur.execute(
                        """
                        INSERT INTO inventarios_tienda (tienda_id, producto_id, cantidad_cajas, fecha_actualizacion)
                        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (tienda_id, producto_id) DO UPDATE SET
                            cantidad_cajas = EXCLUDED.cantidad_cajas,
                            fecha_actualizacion = CURRENT_TIMESTAMP
                        """,
                        (tienda_id, productos_ids[codigo], cantidad),
                    )

            fecha_inicio = date.today() - timedelta(days=27)
            for nombre, _, _ in tiendas:
                tienda_id = tienda_map[nombre]
                for codigo, _, _ in productos:
                    producto_id = productos_ids[codigo]
                    for offset in range(28):
                        venta_fecha = fecha_inicio + timedelta(days=offset)
                        cantidad = (offset % 6) + 2 + (tienda_id % 3)
                        if codigo == "P-1003":
                            cantidad += 1
                        if codigo == "P-1005" and (venta_fecha.day % 4 == 0):
                            cantidad += 2
                        cur.execute(
                            """
                            INSERT INTO ventas (tienda_id, producto_id, fecha, cantidad_cajas)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (tienda_id, producto_id, fecha) DO NOTHING
                            """,
                            (tienda_id, producto_id, venta_fecha, cantidad),
                        )

            conn.commit()
        print("Datos ficticios cargados correctamente.")


def main():
    try:
        crear_tablas()
        cargar_datos_ficticios()
    except Exception as exc:  # pragma: no cover
        print(f"Error al preparar la base de datos: {exc}")
        raise


if __name__ == "__main__":
    main()
