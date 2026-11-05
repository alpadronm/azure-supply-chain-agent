import math
from typing import Dict, List

from src.base_datos.conexion import get_connection


def _consultar_ventas_ultimas_4_semanas():
    """Devuelve las ventas acumuladas de las últimas 4 semanas por tienda y producto."""
    query = """
        SELECT
            t.id AS tienda_id,
            t.nombre AS tienda,
            p.id AS producto_id,
            p.codigo AS codigo_producto,
            p.nombre AS nombre_producto,
            COALESCE(SUM(v.cantidad_cajas), 0) AS ventas_4_semanas
        FROM tiendas t
        CROSS JOIN productos p
        LEFT JOIN ventas v
            ON v.tienda_id = t.id
           AND v.producto_id = p.id
           AND v.fecha >= CURRENT_DATE - INTERVAL '27 days'
        GROUP BY t.id, t.nombre, p.id, p.codigo, p.nombre
        ORDER BY t.id, p.id;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchall()


def _consultar_inventario_tienda():
    """Devuelve el inventario actual registrado por tienda y producto."""
    query = """
        SELECT
            t.id AS tienda_id,
            t.nombre AS tienda,
            p.id AS producto_id,
            p.codigo AS codigo_producto,
            p.nombre AS nombre_producto,
            COALESCE(it.cantidad_cajas, 0) AS inventario_actual
        FROM tiendas t
        CROSS JOIN productos p
        LEFT JOIN inventarios_tienda it
            ON it.tienda_id = t.id
           AND it.producto_id = p.id
        ORDER BY t.id, p.id;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchall()


def _consultar_inventario_bodega():
    """Devuelve el inventario disponible en bodega por producto."""
    query = """
        SELECT
            p.id AS producto_id,
            p.codigo AS codigo_producto,
            p.nombre AS nombre_producto,
            COALESCE(ib.cantidad_cajas, 0) AS inventario_bodega
        FROM productos p
        LEFT JOIN inventario_bodega ib
            ON ib.producto_id = p.id
        ORDER BY p.id;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchall()


def generar_resultados_reposicion() -> List[Dict[str, object]]:
    """Genera la propuesta de reposición por tienda y producto.

    Se conserva el pedido sugerido original de cada tienda. La cantidad que puede surtirse
    se calcula de forma determinista y nunca excede el inventario disponible real en bodega.
    """
    ventas = _consultar_ventas_ultimas_4_semanas()
    inventarios = _consultar_inventario_tienda()
    inventario_bodega = _consultar_inventario_bodega()

    ventas_por_tienda_producto: Dict[tuple[int, int], int] = {}
    for fila in ventas:
        tienda_id, _, producto_id, _, _, ventas_4 = fila
        ventas_por_tienda_producto[(int(tienda_id), int(producto_id))] = int(ventas_4)

    inventario_bodega_por_producto: Dict[int, int] = {}
    for fila in inventario_bodega:
        producto_id, _, _, cantidad = fila
        inventario_bodega_por_producto[int(producto_id)] = int(cantidad)

    pedidos_sugeridos_por_producto: Dict[int, int] = {}
    for fila in inventarios:
        tienda_id, _, producto_id, _, _, inventario_actual = fila
        tienda_key = (int(tienda_id), int(producto_id))
        ventas_4_semanas = int(ventas_por_tienda_producto.get(tienda_key, 0))
        promedio_diario = ventas_4_semanas / 28 if ventas_4_semanas > 0 else 0.0
        demanda_proyectada = math.ceil(promedio_diario * 7) if promedio_diario > 0 else 0
        pedido_sugerido = max(0, demanda_proyectada - int(inventario_actual))
        pedidos_sugeridos_por_producto[int(producto_id)] = (
            pedidos_sugeridos_por_producto.get(int(producto_id), 0) + pedido_sugerido
        )

    stock_disponible_restante = dict(inventario_bodega_por_producto)
    resultados: List[Dict[str, object]] = []

    for fila in inventarios:
        tienda_id, tienda, producto_id, codigo_producto, nombre_producto, inventario_actual = fila
        tienda_key = (int(tienda_id), int(producto_id))
        ventas_4_semanas = int(ventas_por_tienda_producto.get(tienda_key, 0))
        promedio_diario = ventas_4_semanas / 28 if ventas_4_semanas > 0 else 0.0
        demanda_proyectada = math.ceil(promedio_diario * 7) if promedio_diario > 0 else 0
        pedido_sugerido = max(0, demanda_proyectada - int(inventario_actual))
        producto_id_int = int(producto_id)
        inventario_disponible = inventario_bodega_por_producto.get(producto_id_int, 0)
        cantidad_que_podria_surtirse = min(
            pedido_sugerido,
            stock_disponible_restante.get(producto_id_int, 0),
        )
        stock_disponible_restante[producto_id_int] = (
            stock_disponible_restante.get(producto_id_int, 0) - cantidad_que_podria_surtirse
        )
        falta_por_cubrir = max(0, pedido_sugerido - cantidad_que_podria_surtirse)
        hay_inventario_suficiente = inventario_disponible >= pedido_sugerido

        resultados.append(
            {
                "Tienda": tienda,
                "Producto": f"{codigo_producto} - {nombre_producto}",
                "Producto id": producto_id_int,
                "Inventario actual": int(inventario_actual),
                "Ventas últimas 4 semanas": ventas_4_semanas,
                "Promedio diario de ventas": round(promedio_diario, 2),
                "Demanda proyectada a 7 días": demanda_proyectada,
                "Pedido sugerido": pedido_sugerido,
                "Inventario disponible en bodega": inventario_disponible,
                "Cantidad que podría surtirse": cantidad_que_podria_surtirse,
                "Cantidad faltante para esta tienda": falta_por_cubrir,
                "Hay suficiente inventario en bodega": hay_inventario_suficiente,
            }
        )

    return resultados


def generar_resumen_por_producto() -> List[Dict[str, object]]:
    """Resume la necesidad total por producto frente a la disponibilidad global de bodega."""
    ventas = _consultar_ventas_ultimas_4_semanas()
    inventarios = _consultar_inventario_tienda()
    inventario_bodega = _consultar_inventario_bodega()

    ventas_por_tienda_producto: Dict[tuple[int, int], int] = {}
    for fila in ventas:
        tienda_id, _, producto_id, _, _, ventas_4 = fila
        ventas_por_tienda_producto[(int(tienda_id), int(producto_id))] = int(ventas_4)

    inventario_bodega_por_producto: Dict[int, int] = {}
    for fila in inventario_bodega:
        producto_id, _, _, cantidad = fila
        inventario_bodega_por_producto[int(producto_id)] = int(cantidad)

    resumen: Dict[int, Dict[str, object]] = {}
    for fila in inventarios:
        tienda_id, tienda, producto_id, codigo_producto, nombre_producto, inventario_actual = fila
        tienda_key = (int(tienda_id), int(producto_id))
        ventas_4_semanas = int(ventas_por_tienda_producto.get(tienda_key, 0))
        promedio_diario = ventas_4_semanas / 28 if ventas_4_semanas > 0 else 0.0
        demanda_proyectada = math.ceil(promedio_diario * 7) if promedio_diario > 0 else 0
        pedido_sugerido = max(0, demanda_proyectada - int(inventario_actual))
        producto_id_int = int(producto_id)

        if producto_id_int not in resumen:
            resumen[producto_id_int] = {
                "Producto": f"{codigo_producto} - {nombre_producto}",
                "Inventario disponible en bodega": inventario_bodega_por_producto.get(producto_id_int, 0),
                "Necesidad total de las tiendas": 0,
                "Cantidad que puede surtirse": 0,
                "Cantidad faltante": 0,
                "Existe inventario suficiente": False,
            }

        resumen[producto_id_int]["Necesidad total de las tiendas"] = (
            int(resumen[producto_id_int]["Necesidad total de las tiendas"]) + pedido_sugerido
        )

    resultado_final: List[Dict[str, object]] = []
    for producto_id, datos in sorted(resumen.items()):
        inventario_disponible = int(datos["Inventario disponible en bodega"])
        necesidad_total = int(datos["Necesidad total de las tiendas"])
        cantidad_que_puede_surtirse = min(inventario_disponible, necesidad_total)
        cantidad_faltante = max(0, necesidad_total - inventario_disponible)
        inventario_suficiente = inventario_disponible >= necesidad_total
        datos["Cantidad que puede surtirse"] = cantidad_que_puede_surtirse
        datos["Cantidad faltante"] = cantidad_faltante
        datos["Existe inventario suficiente"] = inventario_suficiente
        resultado_final.append(datos)

    return resultado_final


def main():
    """Ejecuta el cálculo de reposición y muestra el detalle por tienda y por producto."""
    resultados = generar_resultados_reposicion()
    resumen_por_producto = generar_resumen_por_producto()

    print("Detalle por tienda y producto")
    print("=" * 180)
    encabezado = (
        "Tienda | Producto | Inventario actual | Ventas 4 semanas | "
        "Promedio diario | Demanda 7 días | Pedido sugerido | Bodega disponible | "
        "Surtible | Faltante | Hay stock"
    )
    print(encabezado)
    print("-" * len(encabezado))

    for item in resultados:
        print(
            f"{item['Tienda']:<15} | {item['Producto']:<25} | {item['Inventario actual']:^16} | "
            f"{item['Ventas últimas 4 semanas']:^15} | {item['Promedio diario de ventas']:^16.2f} | "
            f"{item['Demanda proyectada a 7 días']:^15} | {item['Pedido sugerido']:^15} | "
            f"{item['Inventario disponible en bodega']:^18} | {item['Cantidad que podría surtirse']:^10} | "
            f"{item['Cantidad faltante para esta tienda']:^10} | {str(item['Hay suficiente inventario en bodega']):^13}"
        )

    print("\nResumen por producto")
    print("=" * 150)
    resumen_encabezado = (
        "Producto | Inventario bodega | Necesidad total | Cantidad surtible | Faltante | Inventario suficiente"
    )
    print(resumen_encabezado)
    print("-" * len(resumen_encabezado))
    for item in resumen_por_producto:
        print(
            f"{item['Producto']:<25} | {item['Inventario disponible en bodega']:^17} | "
            f"{item['Necesidad total de las tiendas']:^15} | {item['Cantidad que puede surtirse']:^16} | "
            f"{item['Cantidad faltante']:^9} | {str(item['Existe inventario suficiente']):^22}"
        )


if __name__ == "__main__":
    main()
