from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "menurentable.sqlite3"
SCHEMA = """
CREATE TABLE IF NOT EXISTS ingredients (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    unit TEXT NOT NULL CHECK(unit IN ('kg','L','unidad')),
    stock TEXT NOT NULL, cost TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS recipes (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    yield INTEGER NOT NULL CHECK(yield > 0), price TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS recipe_items (
    recipe_id INTEGER NOT NULL REFERENCES recipes(id),
    ingredient_id INTEGER NOT NULL REFERENCES ingredients(id),
    quantity TEXT NOT NULL, PRIMARY KEY(recipe_id, ingredient_id)
);
CREATE TABLE IF NOT EXISTS daily (
    day TEXT NOT NULL, recipe_id INTEGER NOT NULL REFERENCES recipes(id),
    prepared INTEGER NOT NULL, sold INTEGER NOT NULL, leftover INTEGER NOT NULL,
    missed INTEGER NOT NULL, PRIMARY KEY(day, recipe_id)
);
CREATE TABLE IF NOT EXISTS plans (
    day TEXT NOT NULL, recipe_id INTEGER NOT NULL REFERENCES recipes(id),
    snapshot TEXT NOT NULL, PRIMARY KEY(day, recipe_id)
);
CREATE TABLE IF NOT EXISTS prices (
    id INTEGER PRIMARY KEY, product TEXT NOT NULL, unit TEXT NOT NULL,
    amount TEXT NOT NULL, source TEXT NOT NULL, location TEXT NOT NULL,
    observed TEXT NOT NULL
);
"""


def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db


def records(db, sql, params=()):
    return [dict(row) for row in db.execute(sql, params)]


def state(db):
    return {
        "ingredients": records(db, "SELECT * FROM ingredients ORDER BY name"),
        "recipes": records(db, "SELECT * FROM recipes ORDER BY name"),
        "prices": records(db, "SELECT * FROM prices ORDER BY observed DESC, id DESC"),
        "daily": records(db, """SELECT d.*, r.name FROM daily d
                              JOIN recipes r ON r.id=d.recipe_id ORDER BY day DESC"""),
        "plans": records(db, """SELECT p.*, r.name FROM plans p
                              JOIN recipes r ON r.id=p.recipe_id ORDER BY day DESC"""),
    }
