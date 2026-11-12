from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from .validacion import money, number, whole


def calculate(db, data):
    day = date.fromisoformat(data["day"])
    recipe_id = whole(data["recipe_id"], "Receta", True)
    budget = number(data["budget"], "Presupuesto")
    recipe = db.execute("SELECT * FROM recipes WHERE id=?", (recipe_id,)).fetchone()
    if not recipe:
        raise ValueError("Selecciona una receta registrada.")
    history = db.execute(
        """SELECT day, sold, missed FROM daily WHERE recipe_id=? AND day<?
           AND strftime('%w', day)=strftime('%w', ?) ORDER BY day DESC LIMIT 8""",
        (recipe_id, day.isoformat(), day.isoformat()),
    ).fetchall()
    if history:
        demand = Decimal(sum(row["sold"] + row["missed"] for row in history)) / len(history)
        expected = int(demand.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    else:
        expected = whole(data.get("manual_demand", ""), "Demanda inicial")
    items = db.execute(
        """SELECT i.*, ri.quantity FROM recipe_items ri JOIN ingredients i
           ON i.id=ri.ingredient_id WHERE ri.recipe_id=? ORDER BY i.name""", (recipe_id,),
    ).fetchall()

    scenarios = []
    for portions in sorted({expected * 4 // 5, expected, (expected * 6 + 4) // 5}):
        purchases = production = Decimal(0)
        supplies = []
        for item in items:
            quantity = Decimal(item["quantity"]) * portions / recipe["yield"]
            shortage = max(Decimal(0), quantity - Decimal(item["stock"]))
            price = Decimal(item["cost"])
            selected = data.get("price_id")
            quote = None
            if selected:
                quote = db.execute("SELECT * FROM prices WHERE id=?", (selected,)).fetchone()
            matches = quote and quote["unit"] == item["unit"] and quote["product"].casefold() == item["name"].casefold()
            purchase_price = Decimal(quote["amount"]) if matches else price
            purchases += shortage * purchase_price
            production += (quantity - shortage) * price + shortage * purchase_price
            supplies.append({
                "ingredient": item["name"], "unit": item["unit"],
                "required": str(quantity.quantize(Decimal(".001"))),
                "missing": str(shortage.quantize(Decimal(".001"))),
                "source": f"{quote['source']} ({quote['observed']})" if matches else "Costo de inventario",
            })
        sales = min(expected, portions)
        scenarios.append({
            "portions": portions, "sales": sales, "leftover": portions - sales,
            "unmet": expected - sales, "purchase": money(purchases),
            "margin": money(sales * Decimal(recipe["price"]) - production),
            "within_budget": purchases <= budget, "supplies": supplies,
        })
    feasible = [row for row in scenarios if row["within_budget"]]
    best = max(feasible, key=lambda row: (Decimal(row["margin"]), -row["leftover"])) if feasible else None
    return {
        "day": day.isoformat(), "recipe_id": recipe_id, "recipe": recipe["name"],
        "expected": expected, "samples": len(history), "scenarios": scenarios,
        "recommended": best["portions"] if best else None,
    }
