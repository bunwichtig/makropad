"""
Phase 1 – Verbindungstest für das AKP03E (USB-ID 0B00:1001)

Verbindet sich mit dem Pad, schaltet die Displays ein und zeigt an,
welche Taste, welcher Knopf oder welcher Drehregler bedient wird.
Beenden mit Strg+C.

Protokoll nachimplementiert nach der Beschreibung in mirajazz /
opendeck-akp03 (Mirabox-N3-Familie, Protokollversion 2).
"""

import sys
import time

try:
    import hid
except ImportError:
    sys.exit("Bitte zuerst installieren:  pip install hidapi")

VID = 0x0B00
PID = 0x1001
USAGE_PAGE = 0xFFA0          # herstellerdefinierte Schnittstelle (MI_00)
PAKETGROESSE = 1024          # Protokollversion 2
KEEPALIVE_SEKUNDEN = 10      # Gerät trennt sich nach ca. 35 s Stille

CRT = b"CRT\x00\x00"

NAMEN = {
    0x01: "Display-Taste 1", 0x02: "Display-Taste 2", 0x03: "Display-Taste 3",
    0x04: "Display-Taste 4", 0x05: "Display-Taste 5", 0x06: "Display-Taste 6",
    0x25: "Knopf 1 (ohne Display)", 0x30: "Knopf 2 (ohne Display)",
    0x31: "Knopf 3 (ohne Display)",
    0x90: "Regler links  ⟲ (links gedreht)", 0x91: "Regler links  ⟳ (rechts gedreht)",
    0x50: "Regler mitte  ⟲ (links gedreht)", 0x51: "Regler mitte  ⟳ (rechts gedreht)",
    0x60: "Regler rechts ⟲ (links gedreht)", 0x61: "Regler rechts ⟳ (rechts gedreht)",
    0x33: "Regler links gedrückt", 0x35: "Regler mitte gedrückt",
    0x34: "Regler rechts gedrückt",
}


def senden(geraet, befehl: bytes) -> None:
    """Befehl auf 1024 Bytes auffüllen, Report-ID 0 voranstellen und senden."""
    daten = befehl.ljust(PAKETGROESSE, b"\x00")
    geraet.write(b"\x00" + daten)


def finde_geraet():
    kandidaten = hid.enumerate(VID, PID)
    if not kandidaten:
        return None
    for k in kandidaten:
        if k.get("usage_page") == USAGE_PAGE:
            return k
    # Fallback: Schnittstelle 0
    for k in kandidaten:
        if k.get("interface_number") == 0:
            return k
    return kandidaten[0]


def main() -> None:
    info = finde_geraet()
    if info is None:
        sys.exit("Pad nicht gefunden. Ist es angeschlossen?")

    print(f"Gefunden: {info.get('product_string') or '?'}  "
          f"(Schnittstelle {info.get('interface_number')}, "
          f"Usage-Page 0x{info.get('usage_page', 0):04X})")

    geraet = hid.device()
    try:
        geraet.open_path(info["path"])
    except OSError as e:
        sys.exit(f"Konnte das Pad nicht öffnen: {e}\n"
                 "Tipp: Hersteller-Software (Stream Dock) vorher komplett beenden.")

    # Initialisieren: Displays aufwecken, Helligkeit setzen
    senden(geraet, CRT + b"DIS")
    senden(geraet, CRT + b"LIG\x00\x00" + bytes([60]))
    print("Verbunden. Drück Tasten, Knöpfe oder dreh an den Reglern … (Strg+C beendet)\n")

    letzter_keepalive = time.monotonic()
    try:
        while True:
            daten = geraet.read(512, 200)   # 200 ms Timeout
            if time.monotonic() - letzter_keepalive > KEEPALIVE_SEKUNDEN:
                senden(geraet, CRT + b"CONNECT")
                letzter_keepalive = time.monotonic()
            if not daten:
                continue

            daten = bytes(daten)
            roh = daten[:16].hex(" ")
            if not daten.startswith(b"ACK"):
                print(f"  (anderes Paket)            roh: {roh}")
                continue

            code, zustand = daten[9], daten[10]
            name = NAMEN.get(code, f"UNBEKANNT 0x{code:02X}")
            print(f"{name:<34} Zustand {zustand}   roh: {roh}")
    except KeyboardInterrupt:
        print("\nBeendet.")
    finally:
        geraet.close()


if __name__ == "__main__":
    main()
