import json
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
ARCHIVO_DATOS = "inventario.json"


def datos_iniciales():
    """Retorna registros de prueba iniciales para visualizar el sistema."""
    return [
        {
            "id": "FER-001",
            "nombre": "Martillo de Uña 16 oz",
            "cantidad": 12,
            "precio": 28000.0,
            "iva_porcentaje": 19.0,
            "fecha_compra": "2026-11-01",
            "fecha_venta": "2026-11-10",
        },
        {
            "id": "FER-002",
            "nombre": "Taladro Percutor 1/2 Pulgada",
            "cantidad": 4,
            "precio": 185000.0,
            "iva_porcentaje": 19.0,
            "fecha_compra": "2026-11-05",
            "fecha_venta": "",
        },
        {
            "id": "FER-003",
            "nombre": "Bulto Cemento Gris 50 kg",
            "cantidad": 0,
            "precio": 32000.0,
            "iva_porcentaje": 19.0,
            "fecha_compra": "2026-10-25",
            "fecha_venta": "2026-11-14",
        },
    ]


def cargar_inventario():
    """Lee el inventario desde el archivo JSON o crea datos iniciales."""
    if not os.path.exists(ARCHIVO_DATOS):
        inventario = datos_iniciales()
        guardar_inventario(inventario)
        return inventario
    with open(ARCHIVO_DATOS, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


def guardar_inventario(inventario):
    """Guarda la lista actualizada de productos en disco."""
    with open(ARCHIVO_DATOS, "w", encoding="utf-8") as archivo:
        json.dump(inventario, archivo, indent=4, ensure_ascii=False)


def calcular_iva(precio, porcentaje_iva):
    """Calcula el valor del IVA y el precio final con impuesto incluido."""
    valor_iva = round(precio * (porcentaje_iva / 100.0), 2)
    precio_con_iva = round(precio + valor_iva, 2)
    return valor_iva, precio_con_iva


@app.route("/", methods=["GET", "POST"])
def index():
    inventario = cargar_inventario()

    if request.method == "POST":
        prod_id = request.form.get("id", "").strip().upper()
        nombre = request.form.get("nombre", "").strip()
        cantidad = int(request.form.get("cantidad", 0))
        precio = float(request.form.get("precio", 0))
        iva_porcentaje = float(request.form.get("iva_porcentaje", 19))
        fecha_compra = request.form.get("fecha_compra", "")
        fecha_venta = request.form.get("fecha_venta", "")

        nuevo_producto = {
            "id": prod_id,
            "nombre": nombre,
            "cantidad": max(0, cantidad),
            "precio": max(0.0, precio),
            "iva_porcentaje": max(0.0, iva_porcentaje),
            "fecha_compra": fecha_compra,
            "fecha_venta": fecha_venta,
        }

        # Si el ID ya existe se actualiza; de lo contrario, se agrega una fila nueva
        actualizado = False
        for i, item in enumerate(inventario):
            if item["id"] == prod_id:
                inventario[i] = nuevo_producto
                actualizado = True
                break

        if not actualizado:
            inventario.append(nuevo_producto)

        guardar_inventario(inventario)
        return redirect(url_for("index"))

    # Enriquecer cada fila con el cálculo del IVA y estado de agotado
    filas_inventario = []
    productos_agotados = []

    for prod in inventario:
        valor_iva, precio_total = calcular_iva(prod["precio"], prod["iva_porcentaje"])
        agotado = prod["cantidad"] == 0

        if agotado:
            productos_agotados.append(f"{prod['nombre']} ({prod['id']})")

        filas_inventario.append({
            **prod,
            "valor_iva": valor_iva,
            "precio_total": precio_total,
            "agotado": agotado,
        })

    return render_template(
        "index.html",
        inventario=filas_inventario,
        productos_agotados=productos_agotados,
    )


@app.route("/vender/<prod_id>", methods=["POST"])
def vender_producto(prod_id):
    """Descuenta 1 unidad del inventario y registra la fecha actual de venta."""
    inventario = cargar_inventario()
    for prod in inventario:
        if prod["id"] == prod_id and prod["cantidad"] > 0:
            prod["cantidad"] -= 1
            prod["fecha_venta"] = datetime.now().strftime("%Y-%m-%d")
            break
    guardar_inventario(inventario)
    return redirect(url_for("index"))


@app.route("/eliminar/<prod_id>", methods=["POST"])
def eliminar_producto(prod_id):
    """Elimina un registro del almacén por su ID."""
    inventario = cargar_inventario()
    inventario = [p for p in inventario if p["id"] != prod_id]
    guardar_inventario(inventario)
    return redirect(url_for("index"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)