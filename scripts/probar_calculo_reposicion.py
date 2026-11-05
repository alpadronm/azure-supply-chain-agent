import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.logistica.calculo_reposicion import (
    generar_resumen_por_producto,
    generar_resultados_reposicion,
)


def main():
    resultados = generar_resultados_reposicion()
    resumen = generar_resumen_por_producto()

    if not resultados:
        print("No hay datos para calcular reposición.")
        return

    print("Resultados de reposición por tienda y producto")
    print("=" * 180)
    for item in resultados:
        print(
            f"Tienda: {item['Tienda']} | "
            f"Producto: {item['Producto']} | "
            f"Inventario actual: {item['Inventario actual']} cajas | "
            f"Ventas últimas 4 semanas: {item['Ventas últimas 4 semanas']} cajas | "
            f"Promedio diario: {item['Promedio diario de ventas']} cajas | "
            f"Demanda proyectada a 7 días: {item['Demanda proyectada a 7 días']} cajas | "
            f"Pedido sugerido: {item['Pedido sugerido']} cajas | "
            f"Inventario disponible en bodega: {item['Inventario disponible en bodega']} cajas | "
            f"Cantidad que podría surtirse: {item['Cantidad que podría surtirse']} cajas | "
            f"Cantidad faltante para esta tienda: {item['Cantidad faltante para esta tienda']} cajas | "
            f"Hay suficiente inventario en bodega: {item['Hay suficiente inventario en bodega']}"
        )

    print("\nResumen por producto")
    print("=" * 150)
    for item in resumen:
        print(
            f"Producto: {item['Producto']} | "
            f"Inventario disponible en bodega: {item['Inventario disponible en bodega']} cajas | "
            f"Necesidad total de las tiendas: {item['Necesidad total de las tiendas']} cajas | "
            f"Cantidad que puede surtirse: {item['Cantidad que puede surtirse']} cajas | "
            f"Cantidad faltante: {item['Cantidad faltante']} cajas | "
            f"Existe inventario suficiente: {item['Existe inventario suficiente']}"
        )


if __name__ == "__main__":
    main()
