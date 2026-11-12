from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import argparse
import json
import sqlite3

from backend.database import ROOT, SCHEMA, connect, state
from backend.operaciones import change
from backend.reportes import report


STATIC_FILES = {
    "/": ("frontend/index.html", "text/html"),
    "/static/styles.css": ("frontend/static/styles.css", "text/css"),
    "/static/app.js": ("frontend/static/app.js", "text/javascript"),
}


class Handler(BaseHTTPRequestHandler):
    def send(self, body, content_type, status=200, filename=None):
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(encoded)

    def json(self, value, status=200):
        self.send(json.dumps(value, ensure_ascii=False), "application/json", status)

    def do_GET(self):
        with closing(connect()) as db:
            if self.path == "/api/state":
                self.json(state(db))
            elif self.path == "/report.csv":
                self.send("\ufeff" + report(db), "text/csv", filename="planificacion.csv")
            elif self.path in STATIC_FILES:
                filename, content_type = STATIC_FILES[self.path]
                self.send((ROOT / filename).read_text(encoding="utf-8"), content_type)
            else:
                self.json({"error": "Ruta desconocida."}, 404)

    def do_POST(self):
        if not self.path.startswith("/api/"):
            self.json({"error": "Ruta desconocida."}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            if not 0 < length <= 65536:
                raise ValueError("Tamaño de solicitud inválido.")
            data = json.loads(self.rfile.read(length))
            with closing(connect()) as db, db:
                result = change(db, self.path.removeprefix("/api/"), data)
            self.json(result)
        except (ValueError, KeyError, TypeError) as error:
            self.json({"error": f"Revisa los datos: {error}"}, 400)
        except sqlite3.IntegrityError:
            self.json({"error": "El registro está duplicado o hace referencia a un dato inexistente."}, 400)


def main():
    parser = argparse.ArgumentParser(description="MenúRentable AQP")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    with closing(connect()) as db:
        db.executescript(SCHEMA)
    address = ("127.0.0.1", args.port)
    print(f"MenúRentable AQP: http://{address[0]}:{address[1]}", flush=True)
    with ThreadingHTTPServer(address, Handler) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()

