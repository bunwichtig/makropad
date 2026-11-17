"""
Hauptprogramm: liest config.json, zeigt die Tastenbilder an und führt die Aktionen aus.

Start:  python start.py            (aus dem Repo-Ordner)
"""

from __future__ import annotations

import json
import os
import sys
import time
import webbrowser

from . import bilder
from .device import Ereignis, Makropad

REGLER_NAMEN = {1: "links", 2: "mitte", 3: "rechts"}
MIKRO_PRUEFEN_SEKUNDEN = 1.0


def log(text: str) -> None:
    print(time.strftime("%H:%M:%S"), text, flush=True)


class App:
    def __init__(self, config_pfad: str) -> None:
        self.config_pfad = config_pfad
        self.config: dict = {}
        self.pad = Makropad()
        self.mikro_stumm: bool | None = None
        self._audio = None
        self._fenster = None

    # ---------- Module erst bei Bedarf laden (Windows-spezifisch) ----------

    @property
    def audio(self):
        if self._audio is None:
            from . import audio
            self._audio = audio
        return self._audio

    @property
    def fenster(self):
        if self._fenster is None:
            from . import fenster
            self._fenster = fenster
        return self._fenster

    # ---------- Konfiguration & Anzeige ----------

    def config_laden(self) -> None:
        with open(self.config_pfad, encoding="utf-8") as f:
            self.config = json.load(f)

    def _taste(self, nummer: int) -> dict:
        return self.config.get("tasten", {}).get(str(nummer), {})

    def _bild_fuer(self, nummer: int):
        taste = self._taste(nummer)
        aktion = taste.get("aktion", {})
        if aktion.get("typ") == "mikro":
            return bilder.mikro(bool(self.mikro_stumm))
        anzeige = taste.get("anzeige")
        if not anzeige:
            return bilder.leer()
        if "bild" in anzeige:
            try:
                return bilder.bild_kachel(anzeige["bild"])
            except OSError:
                log(f"Bild für Taste {nummer} nicht gefunden: {anzeige['bild']}")
        return bilder.text_kachel(anzeige.get("text", ""), anzeige.get("farbe", "#333333"),
                                  anzeige.get("schriftfarbe", "white"))

    def alle_bilder_senden(self) -> None:
        for nummer in range(1, 7):
            self.pad.bild_setzen(nummer, self._bild_fuer(nummer), sofort=False)
        self.pad.anzeigen()

    def _mikro_tasten(self) -> list[int]:
        return [n for n in range(1, 7) if self._taste(n).get("aktion", {}).get("typ") == "mikro"]

    def mikro_pruefen(self) -> None:
        """Mikrofon-Zustand abgleichen – falls er woanders umgeschaltet wurde."""
        tasten = self._mikro_tasten()
        if not tasten:
            return
        try:
            stumm = self.audio.mikro_ist_stumm()
        except Exception as e:
            log(f"Mikrofon nicht lesbar: {e}")
            return
        if stumm != self.mikro_stumm:
            self.mikro_stumm = stumm
            for n in tasten:
                self.pad.bild_setzen(n, bilder.mikro(stumm))

    # ---------- Aktionen ----------

    def ausfuehren(self, aktion: dict, richtung: int = 0) -> None:
        typ = aktion.get("typ")
        try:
            if typ == "mikro":
                self.mikro_stumm = self.audio.mikro_umschalten()
                log("Mikrofon " + ("STUMM" if self.mikro_stumm else "AN"))
                for n in self._mikro_tasten():
                    self.pad.bild_setzen(n, bilder.mikro(self.mikro_stumm))

            elif typ == "fokus":
                log(f"Nach vorne: {aktion['prozess']}")
                self.fenster.fokus(aktion["prozess"], aktion.get("starten"))

            elif typ == "starten":
                log(f"Starte: {aktion['befehl']}")
                self.fenster.starten(aktion["befehl"])

            elif typ == "webseite":
                log(f"Öffne: {aktion['url']}")
                webbrowser.open(aktion["url"])

            elif typ == "system_lautstaerke":
                neu = self.audio.system_lautstaerke_aendern(richtung * aktion.get("schritt", 0.02))
                log(f"Gesamtlautstärke {round(neu * 100)} %")

            elif typ == "system_stumm":
                stumm = self.audio.system_stumm_umschalten()
                log("Ton " + ("STUMM" if stumm else "AN"))

            elif typ == "app_lautstaerke":
                neu = self.audio.app_lautstaerke_aendern(
                    aktion["prozesse"], richtung * aktion.get("schritt", 0.02))
                if neu is None:
                    log(f"{', '.join(aktion['prozesse'])}: gerade kein Ton aktiv")
                else:
                    log(f"{aktion['prozesse'][0]}: {round(neu * 100)} %")

            elif typ:
                log(f"Unbekannte Aktion: {typ}")
        except Exception as e:
            log(f"Fehler bei Aktion {typ}: {e}")

    def ereignis(self, e: Ereignis) -> None:
        if e.art == "taste":
            aktion = self._taste(e.nummer).get("aktion")
        elif e.art == "knopf":
            aktion = self.config.get("knoepfe", {}).get(str(e.nummer), {}).get("aktion")
        elif e.art == "regler":
            aktion = self.config.get("regler", {}).get(REGLER_NAMEN[e.nummer], {}).get("drehen")
        elif e.art == "regler_druck":
            aktion = self.config.get("regler", {}).get(REGLER_NAMEN[e.nummer], {}).get("druecken")
        else:
            aktion = None
        if aktion:
            self.ausfuehren(aktion, e.richtung)

    # ---------- Hauptschleife ----------

    def verbinden(self) -> None:
        while True:
            try:
                self.pad.verbinden(self.config.get("helligkeit", 60))
                log("Pad verbunden.")
                if self._mikro_tasten():
                    self.mikro_stumm = self.audio.mikro_ist_stumm()
                self.alle_bilder_senden()
                return
            except Exception as e:
                self.pad.trennen()
                log(f"Warte auf Pad … ({e})")
                time.sleep(3)

    def laufen(self) -> None:
        self.config_laden()
        self.verbinden()
        naechste_pruefung = 0.0
        while True:
            try:
                e = self.pad.lesen(100)
                if e:
                    self.ereignis(e)
                if time.monotonic() >= naechste_pruefung:
                    self.mikro_pruefen()
                    naechste_pruefung = time.monotonic() + MIKRO_PRUEFEN_SEKUNDEN
            except OSError:
                log("Verbindung zum Pad verloren.")
                self.pad.trennen()
                time.sleep(1)
                self.verbinden()


def main() -> None:
    standard = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "config.json")
    pfad = sys.argv[1] if len(sys.argv) > 1 else os.path.normpath(standard)
    log(f"Konfiguration: {pfad}")
    try:
        App(pfad).laufen()
    except KeyboardInterrupt:
        log("Beendet.")
