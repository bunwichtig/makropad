"""Konfigurationsprogramm: kleiner Webserver NUR auf diesem PC (127.0.0.1),
dessen Oberfläche in einem eigenen Edge-App-Fenster geöffnet wird.
Kein Zugriff aus dem Netzwerk, keine Verbindung ins Internet."""

from __future__ import annotations

import json
import os
import secrets
import shutil
import subprocess
import threading
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .app import log

UI_ORDNER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui")


class KonfigServer:
    def __init__(self, app) -> None:
        self.app = app
        self.token = secrets.token_urlsafe(24)
        self.server: ThreadingHTTPServer | None = None

    @property
    def config_ordner(self) -> str:
        return os.path.dirname(os.path.abspath(self.app.config_pfad))

    @property
    def bilder_ordner(self) -> str:
        pfad = os.path.join(self.config_ordner, "bilder")
        os.makedirs(pfad, exist_ok=True)
        return pfad

    # ---------- Start ----------

    def starten(self) -> str:
        if self.server is None:
            handler = _handler_fuer(self)
            self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
            threading.Thread(target=self.server.serve_forever, daemon=True).start()
            log(f"Konfiguration läuft auf Port {self.server.server_address[1]}")
        return f"http://127.0.0.1:{self.server.server_address[1]}/?t={self.token}"

    def fenster_oeffnen(self) -> None:
        url = self.starten()
        for edge in (r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
                     r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"):
            pfad = os.path.expandvars(edge)
            if os.path.exists(pfad):
                subprocess.Popen([pfad, f"--app={url}", "--window-size=1320,900"])
                return
        webbrowser.open(url)

    # ---------- Daten ----------

    def config_lesen(self) -> dict:
        with open(self.app.config_pfad, encoding="utf-8") as f:
            config = json.load(f)
        if "seiten" not in config:
            config["seiten"] = [{"name": "Start", "tasten": config.pop("tasten", {})}]
        config.setdefault("navigation", {"zurueck": 1, "vor": 2, "start": 3})
        config.setdefault("regler", {})
        return config

    def config_schreiben(self, config: dict) -> None:
        # Sicherung der alten Datei, dann schreiben
        if os.path.exists(self.app.config_pfad):
            shutil.copyfile(self.app.config_pfad, self.app.config_pfad + ".bak")
        tmp = self.app.config_pfad + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.app.config_pfad)
        self.app.neu_laden()
        log("Konfiguration gespeichert (Oberfläche).")

    def bild_speichern(self, daten: bytes) -> str:
        name = f"{uuid.uuid4().hex[:12]}.png"
        with open(os.path.join(self.bilder_ordner, name), "wb") as f:
            f.write(daten)
        return f"bilder/{name}"


def _handler_fuer(konfig: KonfigServer):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):  # keine Konsolenausgabe
            pass

        # ---------- Hilfen ----------
        def _erlaubt(self) -> bool:
            q = parse_qs(urlparse(self.path).query)
            token = self.headers.get("X-Token") or (q.get("t") or [""])[0]
            if not secrets.compare_digest(token, konfig.token):
                self._senden(403, b"Kein Zugriff", "text/plain; charset=utf-8")
                return False
            return True

        def _senden(self, code: int, daten: bytes, typ: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", typ)
            self.send_header("Content-Length", str(len(daten)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(daten)

        def _json(self, obj, code: int = 200) -> None:
            self._senden(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                         "application/json; charset=utf-8")

        def _datei(self, pfad: str, typ: str) -> None:
            try:
                with open(pfad, "rb") as f:
                    self._senden(200, f.read(), typ)
            except OSError:
                self._senden(404, b"", "text/plain")

        def _body(self) -> bytes:
            laenge = int(self.headers.get("Content-Length") or 0)
            return self.rfile.read(laenge) if laenge else b""

        # ---------- GET ----------
        def do_GET(self):
            url = urlparse(self.path)
            pfad = url.path
            if pfad == "/":
                if not self._erlaubt():
                    return
                return self._datei(os.path.join(UI_ORDNER, "index.html"), "text/html; charset=utf-8")
            if pfad == "/lucide.json":
                return self._datei(os.path.join(UI_ORDNER, "lucide.json"), "application/json")
            if not self._erlaubt():
                return
            if pfad.startswith("/bilder/"):
                name = os.path.basename(pfad)
                return self._datei(os.path.join(konfig.bilder_ordner, name), "image/png")
            if pfad == "/api/config":
                return self._json(konfig.config_lesen())
            if pfad == "/api/status":
                app = konfig.app
                return self._json({"verbunden": bool(app.pad._geraet), "seite": app.seite})
            if pfad == "/api/ausgaben":
                try:
                    return self._json(app_audio(konfig).ausgabe_namen())
                except Exception as e:
                    return self._json({"fehler": str(e)}, 500)
            if pfad == "/api/programme":
                from . import programmsymbole
                return self._json(programmsymbole.laufende_programme())
            if pfad == "/api/programmsymbol":
                from . import programmsymbole
                exe = (parse_qs(url.query).get("exe") or [""])[0]
                bild = programmsymbole.symbol_aus_datei(exe) if exe else None
                if bild is None:
                    return self._senden(404, b"", "text/plain")
                return self._senden(200, programmsymbole.als_png(bild), "image/png")
            self._senden(404, b"", "text/plain")

        # ---------- POST ----------
        def do_POST(self):
            if not self._erlaubt():
                return
            pfad = urlparse(self.path).path
            if pfad == "/api/config":
                try:
                    config = json.loads(self._body().decode("utf-8"))
                    konfig.config_schreiben(config)
                    return self._json({"ok": True})
                except Exception as e:
                    return self._json({"fehler": str(e)}, 400)
            if pfad == "/api/standard":
                # Standardbelegung (mitgeliefert) wiederherstellen; alte Datei bleibt als .bak
                with open(os.path.join(UI_ORDNER, "standard.json"), encoding="utf-8") as f:
                    standard = json.load(f)
                konfig.config_schreiben(standard)
                log("Standardbelegung wiederhergestellt.")
                return self._json(konfig.config_lesen())
            if pfad == "/api/bild":
                daten = self._body()
                if not daten.startswith(b"\x89PNG"):
                    return self._json({"fehler": "kein PNG"}, 400)
                return self._json({"pfad": konfig.bild_speichern(daten)})
            self._senden(404, b"", "text/plain")

    return Handler


def app_audio(konfig: KonfigServer):
    # COM muss im Server-Thread initialisiert sein
    try:
        import comtypes
        comtypes.CoInitialize()
    except Exception:
        pass
    return konfig.app.audio
