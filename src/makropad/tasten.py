"""Tastenkürzel senden, z. B. "strg+umschalt+m"."""

from __future__ import annotations

import ctypes
import time

user32 = ctypes.WinDLL("user32", use_last_error=True)

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002

TASTEN = {
    # Zusatztasten (deutsch und englisch)
    "strg": 0x11, "ctrl": 0x11, "control": 0x11,
    "umschalt": 0x10, "shift": 0x10,
    "alt": 0x12,
    "altgr": 0xA5,
    "win": 0x5B, "windows": 0x5B,
    # Sondertasten
    "enter": 0x0D, "eingabe": 0x0D, "esc": 0x1B, "tab": 0x09,
    "leer": 0x20, "leertaste": 0x20, "space": 0x20,
    "rück": 0x08, "rueck": 0x08, "backspace": 0x08,
    "entf": 0x2E, "delete": 0x2E, "einfg": 0x2D, "insert": 0x2D,
    "pos1": 0x24, "home": 0x24, "ende": 0x23, "end": 0x23,
    "bildauf": 0x21, "pageup": 0x21, "bildab": 0x22, "pagedown": 0x22,
    "links": 0x25, "left": 0x25, "hoch": 0x26, "up": 0x26,
    "rechts": 0x27, "right": 0x27, "runter": 0x28, "down": 0x28,
    "druck": 0x2C, "print": 0x2C,
    # Medientasten
    "play": 0xB3, "pause": 0xB3, "weiter": 0xB0, "next": 0xB0,
    "zurück": 0xB1, "zurueck": 0xB1, "prev": 0xB1, "stopp": 0xB2, "stop": 0xB2,
    "stumm": 0xAD, "mute": 0xAD, "lauter": 0xAF, "leiser": 0xAE,
}
TASTEN.update({f"f{i}": 0x6F + i for i in range(1, 25)})

ERWEITERT = {0xA5, 0x5B, 0x2E, 0x2D, 0x24, 0x23, 0x21, 0x22, 0x25, 0x26, 0x27, 0x28,
             0xB3, 0xB0, 0xB1, 0xB2, 0xAD, 0xAF, 0xAE}


def _code(name: str) -> int:
    name = name.strip().lower()
    if name in TASTEN:
        return TASTEN[name]
    if len(name) == 1 and (name.isalpha() or name.isdigit()):
        return ord(name.upper())
    raise ValueError(f"Unbekannte Taste: {name!r}")


def _taste(code: int, loslassen: bool) -> None:
    flags = (KEYEVENTF_KEYUP if loslassen else 0) | (KEYEVENTF_EXTENDEDKEY if code in ERWEITERT else 0)
    user32.keybd_event(code, 0, flags, 0)


def senden(kuerzel: str) -> None:
    """Drückt z. B. "strg+umschalt+m": alle Tasten nacheinander runter, dann rückwärts los."""
    codes = [_code(t) for t in kuerzel.split("+")]
    for c in codes:
        _taste(c, False)
        time.sleep(0.01)
    time.sleep(0.03)
    for c in reversed(codes):
        _taste(c, True)
        time.sleep(0.01)
