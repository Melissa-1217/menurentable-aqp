from datetime import date
import json

from .planificacion import calculate
from .validacion import number, required, whole


def change(db, action, data):
    if action == "ingredient":
        unit = data["unit"]
        if unit not in ("kg", "L", "unidad"):
            raise ValueError("Selecciona una unidad válida.")
        db.execute("""INSERT INTO ingredients(name, unit, stock, cost) VALUES(?,?,?,?)
                      ON CONFLICT(name) DO UPDATE SET stock=excluded.stock, cost=excluded.cost
                      WHERE ingredients.unit=excluded.unit""", (
            required(data["name"], "Ingrediente"), unit,
            str(number(data["stock"], "Existencia")), str(number(data["cost"], "Costo")),
        ))
        if db.execute("SELECT changes()").fetchone()[0] == 0:
            raise ValueError("El ingrediente ya existe con otra unidad.")
    elif action == "recipe":
        items = data["items"]
        if not items:
            raise ValueError("Agrega al menos un ingrediente.")
        recipe = db.execute("INSERT INTO recipes(name,yield,price) VALUES(?,?,?)", (
            required(data["name"], "Plato"), whole(data["yield"], "Rendimiento", True),
            str(number(data["price"], "Precio de venta", True)),
        )).lastrowid
        db.executemany("INSERT INTO recipe_items VALUES(?,?,?)", [
            (recipe, whole(item["ingredient_id"], "Ingrediente", True),
             str(number(item["quantity"], "Cantidad", True))) for item in items
        ])
    elif action == "daily":
        prepared = whole(data["prepared"], "Preparadas")
        sold = whole(data["sold"], "Vendidas")
        if sold > prepared:
            raise ValueError("Las ventas no pueden superar las porciones preparadas.")
        db.execute("""INSERT INTO daily VALUES(?,?,?,?,?,?)
                      ON CONFLICT(day, recipe_id) DO UPDATE SET prepared=excluded.prepared,
                      sold=excluded.sold, leftover=excluded.leftover, missed=excluded.missed""", (
            date.fromisoformat(data["day"]).isoformat(), whole(data["recipe_id"], "Receta", True),
            prepared, sold, prepared - sold, whole(data["missed"], "Pedidos no atendidos"),
        ))
    elif action == "price":
        if data["unit"] not in ("kg", "L", "unidad"):
            raise ValueError("Selecciona una unidad válida.")
        db.execute("INSERT INTO prices(product,unit,amount,source,location,observed) VALUES(?,?,?,?,?,?)", (
            required(data["product"], "Producto"), data["unit"],
            str(number(data["amount"], "Precio", True)), required(data["source"], "Fuente"),
            required(data["location"], "Ubicación"), date.fromisoformat(data["observed"]).isoformat(),
        ))
    elif action == "calculate":
        return calculate(db, data)
    elif action == "plan":
        result = calculate(db, data)
        chosen = whole(data["portions"], "Porciones")
        scenario = next((row for row in result["scenarios"] if row["portions"] == chosen), None)
        if not scenario or not scenario["within_budget"]:
            raise ValueError("Selecciona un escenario dentro del presupuesto.")
        result["chosen"] = scenario
        db.execute("""INSERT INTO plans VALUES(?,?,?) ON CONFLICT(day,recipe_id)
                      DO UPDATE SET snapshot=excluded.snapshot""",
                   (result["day"], result["recipe_id"], json.dumps(result, ensure_ascii=False)))
    else:
        raise ValueError("Operación desconocida.")
    return {"ok": True}
