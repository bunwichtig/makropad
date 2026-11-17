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
    return Image.open(os.path.expandvars(pfad)).convert("RGB")


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
