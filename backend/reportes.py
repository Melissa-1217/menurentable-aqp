import csv
import io
import json

from .database import state


def report(db):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Fecha", "Plato", "Plan", "Demanda estimada", "Sobrantes previstos",
                     "Presupuesto de compra estimado", "Margen estimado", "Preparadas reales",
                     "Vendidas reales", "Sobrantes reales"])
    for plan in state(db)["plans"]:
        snapshot = json.loads(plan["snapshot"])
        chosen = snapshot["chosen"]
        actual = db.execute("SELECT * FROM daily WHERE day=? AND recipe_id=?",
                            (plan["day"], plan["recipe_id"])).fetchone()
        name = plan["name"]
        if name.lstrip().startswith(("=", "+", "-", "@")):
            name = "'" + name
        writer.writerow([plan["day"], name, chosen["portions"], snapshot["expected"],
                         chosen["leftover"], chosen["purchase"], chosen["margin"],
                         *([actual["prepared"], actual["sold"], actual["leftover"]] if actual else ["", "", ""])])
    return output.getvalue()
