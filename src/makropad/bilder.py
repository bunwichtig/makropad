"""Erzeugt die 60×60-Bilder für die Display-Tasten."""

from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFont

GROESSE = 60
ROT = "#d62828"
GRUEN = "#2a9d55"


def _schrift(groesse: int):
    for name in ("segoeuib.ttf", "arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, groesse)
        except OSError:
            pass
    return ImageFont.load_default()


def text_kachel(text: str, farbe: str = "#333333", schriftfarbe: str = "white") -> Image.Image:
    bild = Image.new("RGB", (GROESSE, GROESSE), farbe)
    z = ImageDraw.Draw(bild)
    groesse = 30 if len(text) <= 2 else 22 if len(text) <= 4 else 14
    z.text((GROESSE / 2, GROESSE / 2), text, fill=schriftfarbe, font=_schrift(groesse), anchor="mm")
    return bild


def bild_kachel(pfad: str) -> Image.Image:
    bild = Image.open(os.path.expandvars(pfad))
    if bild.mode in ("RGBA", "LA", "P"):
        bild = bild.convert("RGBA")
        grund = Image.new("RGB", bild.size, "black")
        grund.paste(bild, mask=bild.getchannel("A"))
        return grund
    return bild.convert("RGB")


def leer() -> Image.Image:
    return Image.new("RGB", (GROESSE, GROESSE), "black")


def mikro(stumm: bool) -> Image.Image:
    """Mikrofon-Symbol: grün = an, rot mit Querstrich = stumm."""
    s = 4  # in 4-facher Größe zeichnen, dann verkleinern → glatte Kanten
    g = GROESSE * s
    bild = Image.new("RGB", (g, g), ROT if stumm else GRUEN)
    z = ImageDraw.Draw(bild)
    w = "white"
    # Kapsel
    z.rounded_rectangle((22 * s, 8 * s, 38 * s, 36 * s), radius=8 * s, fill=w)
    # Bügel
    z.arc((15 * s, 18 * s, 45 * s, 44 * s), start=0, end=180, fill=w, width=3 * s)
    # Stiel und Fuß
    z.line((30 * s, 44 * s, 30 * s, 51 * s), fill=w, width=3 * s)
    z.line((22 * s, 51 * s, 38 * s, 51 * s), fill=w, width=3 * s)
    if stumm:
        z.line((12 * s, 10 * s, 48 * s, 52 * s), fill=ROT, width=8 * s)
        z.line((12 * s, 10 * s, 48 * s, 52 * s), fill=w, width=4 * s)
    return bild.resize((GROESSE, GROESSE), Image.LANCZOS)


def _gross(farbe: str):
    s = 4
    bild = Image.new("RGB", (GROESSE * s, GROESSE * s), farbe)
    return bild, ImageDraw.Draw(bild), s


def lautsprecher(farbe: str = "#1e6fd9") -> Image.Image:
    """Zwei Lautsprecherboxen."""
    bild, z, s = _gross(farbe)
    w = "white"
    for x0 in (7, 33):
        z.rounded_rectangle((x0 * s, 10 * s, (x0 + 20) * s, 50 * s), radius=3 * s, fill=w)
        z.ellipse(((x0 + 6) * s, 15 * s, (x0 + 14) * s, 23 * s), fill=farbe)      # Hochtöner
        z.ellipse(((x0 + 3) * s, 27 * s, (x0 + 17) * s, 45 * s), fill=farbe)      # Tieftöner
        z.ellipse(((x0 + 8) * s, 34 * s, (x0 + 12) * s, 38 * s), fill=w)
    return bild.resize((GROESSE, GROESSE), Image.LANCZOS)


def headset(farbe: str = "#e76f00") -> Image.Image:
    """Headset mit Bügel, Ohrmuscheln und Mikrofon."""
    bild, z, s = _gross(farbe)
    w = "white"
    z.arc((10 * s, 8 * s, 50 * s, 48 * s), start=180, end=360, fill=w, width=5 * s)   # Bügel
    z.line((10 * s, 28 * s, 10 * s, 34 * s), fill=w, width=5 * s)
    z.line((50 * s, 28 * s, 50 * s, 34 * s), fill=w, width=5 * s)
    z.rounded_rectangle((5 * s, 30 * s, 17 * s, 48 * s), radius=4 * s, fill=w)       # Ohrmuscheln
    z.rounded_rectangle((43 * s, 30 * s, 55 * s, 48 * s), radius=4 * s, fill=w)
    z.arc((9 * s, 30 * s, 37 * s, 56 * s), start=90, end=170, fill=w, width=3 * s)   # Mikro-Arm
    z.ellipse((20 * s, 51 * s, 28 * s, 57 * s), fill=w)
    return bild.resize((GROESSE, GROESSE), Image.LANCZOS)


def freunde(farbe: str = "#1b2838") -> Image.Image:
    """Zwei Personen (z. B. Steam-Freundesliste)."""
    bild, z, s = _gross(farbe)
    hinten, vorne = "#66c0f4", "white"
    z.ellipse((31 * s, 10 * s, 45 * s, 24 * s), fill=hinten)
    z.pieslice((24 * s, 27 * s, 52 * s, 55 * s), start=180, end=360, fill=hinten)
    z.ellipse((14 * s, 14 * s, 30 * s, 30 * s), fill=farbe)          # Rand um vordere Person
    z.ellipse((16 * s, 16 * s, 28 * s, 28 * s), fill=vorne)
    z.pieslice((6 * s, 32 * s, 38 * s, 64 * s), start=180, end=360, fill=vorne)
    return bild.resize((GROESSE, GROESSE), Image.LANCZOS)


def browser_links(farbe: str = "#3c4043") -> Image.Image:
    """Globus mit Pfeil nach links – Browserfenster auf der linken Seite."""
    bild, z, s = _gross(farbe)
    w, blau = "white", "#8ab4f8"
    # Bildschirm-Umriss, linke Hälfte gefüllt
    z.rounded_rectangle((5 * s, 9 * s, 55 * s, 45 * s), radius=3 * s, outline=w, width=2 * s)
    z.rectangle((8 * s, 12 * s, 29 * s, 42 * s), fill=blau)
    z.line((30 * s, 12 * s, 30 * s, 42 * s), fill=w, width=1 * s)
    # Globus in der linken Hälfte
    z.ellipse((11 * s, 19 * s, 26 * s, 34 * s), outline=farbe, width=2 * s)
    z.ellipse((15 * s, 19 * s, 22 * s, 34 * s), outline=farbe, width=1 * s)
    z.line((11 * s, 26.5 * s, 26 * s, 26.5 * s), fill=farbe, width=1 * s)
    # Standfuß
    z.line((30 * s, 45 * s, 30 * s, 50 * s), fill=w, width=2 * s)
    z.line((22 * s, 51 * s, 38 * s, 51 * s), fill=w, width=2 * s)
    return bild.resize((GROESSE, GROESSE), Image.LANCZOS)


SYMBOLE = {"browser_links": browser_links, "lautsprecher": lautsprecher, "headset": headset, "freunde": freunde}


def ausgabe_symbol(symbol: str, farbe: str | None = None, text: str = "") -> Image.Image:
    if symbol in SYMBOLE:
        return SYMBOLE[symbol](farbe) if farbe else SYMBOLE[symbol]()
    return text_kachel(text or "?", farbe or "#333333")
