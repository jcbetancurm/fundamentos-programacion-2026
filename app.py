import csv
import io
import json
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
ARCHIVO_DATOS = "inventario.json"
ARCHIVO_CSV_BASE = "base_datos_ferreteria.csv"


def datos_iniciales():
    """Carga la mini base de datos desde CSV si existe o usa respaldo en memoria."""
    if os.path.exists(ARCHIVO_CSV_BASE):
        with open(ARCHIVO_CSV_BASE, "r", encoding="utf-8-sig") as f:
            return parsear_csv(f.read())

    return [
        {
            "id": "FER-001",
            "nombre": "Martillo de Una 16 oz Mango Fibra",
            "cantidad": 15,
            "precio": 28500.0,
            "iva_porcentaje": 19.0,
            "fecha_compra": "2026-10-15",
            "fecha_venta": "2026-11-10",
        },
        {
            "id": "FER-002",
            "nombre": "Taladro Percutor Inalambrico 1/2 Pulgada",
            "cantidad": 4,
            "precio": 215000.0,
            "iva_porcentaje": 19.0,
            "fecha_compra": "2026-10-18",
            "fecha_venta": "2026-11-12",
        },
        {
            "id": "FER-003",
            "nombre": "Bulto Cemento Gris Uso General 50 kg",
            "cantidad": 0,
            "precio": 32500.0,
            "iva_porcentaje": 19.0,
            "fecha_compra": "2026-10-20",
            "fecha_venta": "2026-11-14",
        },
    ]


def parsear_csv(contenido_texto):
    """Convierte texto CSV (delimitado por coma o punto y coma) a lista de productos."""
    primera_linea = contenido_texto.splitlines()[0] if contenido_texto.strip() else ""
    delimitador = ";" if ";" in primera_linea else ","
    lector = csv.DictReader(io.StringIO(contenido_texto), delimiter=delimitador)

    productos = []
    for idx, fila in enumerate(lector, start=1):
        # Normalizar llaves a minúsculas y sin espacios
        fila_limpia = {
            (k.strip().lower() if k else ""): (v.strip() if v else "")
            for k, v in fila.items()
        }
        prod_id = (fila_limpia.get("id") or f"IMP-{idx:03d}").upper()
        nombre = fila_limpia.get("nombre") or fila_limpia.get("producto") or f"Producto {idx}"
        cantidad = int(float(fila_limpia.get("cantidad") or fila_limpia.get("stock") or 0))
        precio = float(fila_limpia.get("precio") or fila_limpia.get("price") or 0)
        iva = float(fila_limpia.get("iva_porcentaje") or fila_limpia.get("iva") or 19)
        fecha_compra = fila_limpia.get("fecha_compra") or datetime.now().strftime("%Y-%m-%d")
        fecha_venta = fila_limpia.get("fecha_venta") or ""

        productos.append({
            "id": prod_id,
            "nombre": nombre,
            "cantidad": max(0, cantidad),
            "precio": max(0.0, precio),
            "iva_porcentaje": max(0.0, iva),
            "fecha_compra": fecha_compra,
            "fecha_venta": fecha_venta,
        })
    return productos


def cargar_inventario():
    if not os.path.exists(ARCHIVO_DATOS):
        inventario = datos_iniciales()
        guardar_inventario(inventario)
        return inventario
    with open(ARCHIVO_DATOS, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


def guardar_inventario(inventario):
    with open(ARCHIVO_DATOS, "w", encoding="utf-8") as archivo:
        json.dump(inventario, archivo, indent=4, ensure_ascii=False)


def calcular_iva(precio, porcentaje_iva):
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


@app.route("/importar", methods=["POST"])
def importar_bd():
    """Carga una mini base de datos externa en formato CSV o JSON."""
    archivo = request.files.get("archivo_bd")
    modo = request.form.get("modo_carga", "reemplazar")

    if not archivo or archivo.filename == "":
        return redirect(url_for("index"))

    contenido = archivo.read().decode("utf-8-sig", errors="replace")
    nombre_archivo = archivo.filename.lower()

    nuevos_registros = []
    if nombre_archivo.endswith(".json"):
        data = json.loads(contenido)
        for idx, item in enumerate(data, start=1):
            nuevos_registros.append({
                "id": str(item.get("id", f"IMP-{idx:03d}")).upper(),
                "nombre": str(item.get("nombre", f"Producto {idx}")),
                "cantidad": max(0, int(item.get("cantidad", 0))),
                "precio": max(0.0, float(item.get("precio", 0))),
                "iva_porcentaje": max(0.0, float(item.get("iva_porcentaje", 19))),
                "fecha_compra": str(item.get("fecha_compra", datetime.now().strftime("%Y-%m-%d"))),
                "fecha_venta": str(item.get("fecha_venta", "")),
            })
    else:
        nuevos_registros = parsear_csv(contenido)

    if nuevos_registros:
        if modo == "reemplazar":
            inventario = nuevos_registros
        else:
            inventario = cargar_inventario()
            mapa = {p["id"]: p for p in inventario}
            for reg in nuevos_registros:
                mapa[reg["id"]] = reg
            inventario = list(mapa.values())

        guardar_inventario(inventario)

    return redirect(url_for("index"))


@app.route("/restaurar", methods=["POST"])
def restaurar_bd():
    """Restaura la mini base de datos inicial de 15 productos de ferretería."""
    inventario = datos_iniciales()
    guardar_inventario(inventario)
    return redirect(url_for("index"))


@app.route("/vender/<prod_id>", methods=["POST"])
def vender_producto(prod_id):
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
    inventario = cargar_inventario()
    inventario = [p for p in inventario if p["id"] != prod_id]
    guardar_inventario(inventario)
    return redirect(url_for("index"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
            
