"""
USB-Kommunikation mit dem AJAZZ AKP03E (USB-ID 0B00:1001, Mirabox-N3-Familie, Protokoll v2).

Protokoll nachimplementiert nach der Beschreibung in mirajazz / opendeck-akp03.
"""

from __future__ import annotations

import io
import time
from dataclasses import dataclass

import hid
from PIL import Image

VID = 0x0B00
PID = 0x1001
USAGE_PAGE = 0xFFA0
PAKETGROESSE = 1024
BILDGROESSE = (60, 60)
KEEPALIVE_SEKUNDEN = 10

CRT = b"CRT\x00\x00"

# Eingabe-Code → (Art, Nummer, Richtung)
EINGABEN = {
    0x01: ("taste", 1, 0), 0x02: ("taste", 2, 0), 0x03: ("taste", 3, 0),
    0x04: ("taste", 4, 0), 0x05: ("taste", 5, 0), 0x06: ("taste", 6, 0),
    0x25: ("knopf", 1, 0), 0x30: ("knopf", 2, 0), 0x31: ("knopf", 3, 0),
    0x90: ("regler", 1, -1), 0x91: ("regler", 1, +1),
    0x50: ("regler", 2, -1), 0x51: ("regler", 2, +1),
    0x60: ("regler", 3, -1), 0x61: ("regler", 3, +1),
    0x33: ("regler_druck", 1, 0), 0x35: ("regler_druck", 2, 0),
    0x34: ("regler_druck", 3, 0),
}


@dataclass
class Ereignis:
    art: str        # "taste", "knopf", "regler", "regler_druck"
    nummer: int     # 1–6 bei Tasten, 1–3 sonst (Regler: 1 = links, 2 = mitte, 3 = rechts)
    richtung: int   # nur bei "regler": -1 = nach links, +1 = nach rechts
    code: int


class Makropad:
    def __init__(self) -> None:
        self._geraet = None
        self._letzter_keepalive = 0.0
        self.drehung = 0  # falls Bilder verdreht erscheinen: 90, 180 oder 270

    # ---------- Verbindung ----------

    @staticmethod
    def finden():
        kandidaten = hid.enumerate(VID, PID)
        for k in kandidaten:
            if k.get("usage_page") == USAGE_PAGE:
                return k
        for k in kandidaten:
            if k.get("interface_number") == 0:
                return k
        return kandidaten[0] if kandidaten else None

    def verbinden(self, helligkeit: int = 60) -> None:
        info = self.finden()
        if info is None:
            raise RuntimeError("Pad nicht gefunden. Ist es angeschlossen?")
        self._geraet = hid.device()
        self._geraet.open_path(info["path"])
        self._senden(CRT + b"DIS")
        self.helligkeit(helligkeit)
        self.alle_leeren()   # nötig, damit die Display-Tasten Ereignisse senden
        self._letzter_keepalive = time.monotonic()

    def trennen(self) -> None:
        if self._geraet:
            self._geraet.close()
            self._geraet = None

    def __enter__(self):
        self.verbinden()
        return self

    def __exit__(self, *_):
        self.trennen()

    # ---------- Befehle ----------

    def _senden(self, befehl: bytes) -> None:
        self._geraet.write(b"\x00" + befehl.ljust(PAKETGROESSE, b"\x00"))

    def helligkeit(self, prozent: int) -> None:
        prozent = max(0, min(100, int(prozent)))
        self._senden(CRT + b"LIG\x00\x00" + bytes([prozent]))

    def alle_leeren(self) -> None:
        self._senden(CRT + b"CLE\x00\x00\x00\xff")
        self._senden(CRT + b"STP")

    def taste_leeren(self, taste: int) -> None:
        self._senden(CRT + b"CLE\x00\x00\x00" + bytes([taste]))
        self._senden(CRT + b"STP")

    def bild_setzen(self, taste: int, bild: Image.Image, sofort: bool = True) -> None:
        """Bild auf Display-Taste 1–6 legen. Mit sofort=False erst bei anzeigen() sichtbar."""
        if not 1 <= taste <= 6:
            raise ValueError("Taste muss 1–6 sein")
        bild = bild.convert("RGB").resize(BILDGROESSE, Image.LANCZOS)
        if self.drehung:
            bild = bild.rotate(-self.drehung, expand=True)
        puffer = io.BytesIO()
        bild.save(puffer, format="JPEG", quality=90)
        daten = puffer.getvalue()

        laenge = len(daten)
        self._senden(CRT + b"BAT\x00\x00" + bytes([laenge >> 8, laenge & 0xFF, taste]))
        for start in range(0, laenge, PAKETGROESSE):
            self._senden(daten[start:start + PAKETGROESSE])
        if sofort:
            self.anzeigen()

    def anzeigen(self) -> None:
        self._senden(CRT + b"STP")

    def keepalive(self) -> None:
        self._senden(CRT + b"CONNECT")
        self._letzter_keepalive = time.monotonic()

    # ---------- Eingaben ----------

    def lesen(self, timeout_ms: int = 200) -> Ereignis | None:
        """Wartet bis zu timeout_ms auf eine Eingabe. Kümmert sich nebenbei um den Keepalive."""
        if time.monotonic() - self._letzter_keepalive > KEEPALIVE_SEKUNDEN:
            self.keepalive()
        daten = self._geraet.read(512, timeout_ms)
        if not daten:
            return None
        daten = bytes(daten)
        if not daten.startswith(b"ACK") or len(daten) < 10:
            return None
        code = daten[9]
        if code not in EINGABEN:
            return Ereignis("unbekannt", 0, 0, code)
        art, nummer, richtung = EINGABEN[code]
        return Ereignis(art, nummer, richtung, code)
