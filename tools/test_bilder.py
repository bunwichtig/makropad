"""
Phase 3 – Bilder auf die 6 Display-Tasten

Zeigt farbige Kacheln mit den Zahlen 1–6. Beim Drücken einer Display-Taste
wird die Kachel kurz weiß. Regler links dreht die Helligkeit. Beenden mit Strg+C.

Optionen:
  --bild PFAD       dieses Bild zusätzlich auf Taste 1 legen
  --drehen 90       falls die Zahlen verdreht erscheinen (90, 180 oder 270)
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

try:
    from PIL import Image, ImageDraw, ImageFont
    from makropad import Makropad
except ImportError:
    sys.exit("Bitte zuerst installieren:  pip install -r requirements.txt")

FARBEN = ["#e63946", "#f4a261", "#e9c46a", "#2a9d8f", "#457b9d", "#8e5bd9"]


def schrift(groesse: int):
    for name in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, groesse)
        except OSError:
            pass
    return ImageFont.load_default()


def kachel(text: str, hintergrund: str, vordergrund: str = "white") -> Image.Image:
    bild = Image.new("RGB", (60, 60), hintergrund)
    zeichnen = ImageDraw.Draw(bild)
    zeichnen.text((30, 30), text, fill=vordergrund, font=schrift(36), anchor="mm")
    # kleine Markierung oben links, um die Ausrichtung zu prüfen
    zeichnen.rectangle((2, 2, 9, 9), fill=vordergrund)
    return bild


def main() -> None:
    pad = Makropad()
    if "--drehen" in sys.argv:
        pad.drehung = int(sys.argv[sys.argv.index("--drehen") + 1])

    try:
        pad.verbinden(helligkeit=60)
    except Exception as e:
        sys.exit(f"Verbindung fehlgeschlagen: {e}\n"
                 "Tipp: Hersteller-Software vorher komplett beenden.")

    normal = [kachel(str(i + 1), FARBEN[i]) for i in range(6)]
    if "--bild" in sys.argv:
        normal[0] = Image.open(sys.argv[sys.argv.index("--bild") + 1])
    gedrueckt = [kachel(str(i + 1), "white", FARBEN[i]) for i in range(6)]

    for i, b in enumerate(normal, start=1):
        pad.bild_setzen(i, b, sofort=False)
    pad.anzeigen()
    print("Bilder gesendet. Drück die Display-Tasten, Regler links = Helligkeit. (Strg+C beendet)")

    helligkeit = 60
    zuruecksetzen = {}  # taste -> Zeitpunkt
    try:
        while True:
            e = pad.lesen(100)
            if e and e.art == "taste":
                print(f"Taste {e.nummer}")
                pad.bild_setzen(e.nummer, gedrueckt[e.nummer - 1])
                zuruecksetzen[e.nummer] = time.monotonic() + 0.3
            elif e and e.art == "regler" and e.nummer == 1:
                helligkeit = max(0, min(100, helligkeit + 10 * e.richtung))
                pad.helligkeit(helligkeit)
                print(f"Helligkeit {helligkeit} %")
            elif e:
                print(f"{e.art} {e.nummer} {e.richtung or ''}")

            jetzt = time.monotonic()
            for taste, zeit in list(zuruecksetzen.items()):
                if jetzt >= zeit:
                    pad.bild_setzen(taste, normal[taste - 1])
                    del zuruecksetzen[taste]
    except KeyboardInterrupt:
        print("\nBeendet.")
    finally:
        pad.trennen()


if __name__ == "__main__":
    main()
