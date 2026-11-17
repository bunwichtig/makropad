"""Symbole (Icons) von Programmen auf dem PC auslesen – als PNG."""

from __future__ import annotations

import ctypes
import io
from ctypes import wintypes

import psutil
from PIL import Image

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

GROESSE = 128
DI_NORMAL = 3


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD),
                ("biCompression", wintypes.DWORD), ("biSizeImage", wintypes.DWORD),
                ("biXPelsPerMeter", wintypes.LONG), ("biYPelsPerMeter", wintypes.LONG),
                ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]


user32.PrivateExtractIconsW.argtypes = [wintypes.LPCWSTR, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                        ctypes.POINTER(wintypes.HICON), ctypes.POINTER(wintypes.UINT),
                                        wintypes.UINT, wintypes.UINT]
user32.DrawIconEx.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.HICON, ctypes.c_int,
                              ctypes.c_int, wintypes.UINT, wintypes.HBRUSH, wintypes.UINT]
gdi32.CreateDIBSection.restype = wintypes.HBITMAP
gdi32.CreateDIBSection.argtypes = [wintypes.HDC, ctypes.c_void_p, wintypes.UINT,
                                   ctypes.POINTER(ctypes.c_void_p), wintypes.HANDLE, wintypes.DWORD]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.DeleteDC.argtypes = [wintypes.HDC]
user32.DestroyIcon.argtypes = [wintypes.HICON]


def symbol_aus_datei(pfad: str, groesse: int = GROESSE) -> Image.Image | None:
    """Liest das Symbol einer .exe (oder .ico/.dll) in der gewünschten Größe."""
    hicon = wintypes.HICON()
    anzahl = user32.PrivateExtractIconsW(pfad, 0, groesse, groesse, ctypes.byref(hicon), None, 1, 0)
    if anzahl < 1 or not hicon:
        return None
    hdc = gdi32.CreateCompatibleDC(None)
    kopf = BITMAPINFOHEADER(biSize=ctypes.sizeof(BITMAPINFOHEADER), biWidth=groesse,
                            biHeight=-groesse, biPlanes=1, biBitCount=32, biCompression=0)
    bits = ctypes.c_void_p()
    hbmp = gdi32.CreateDIBSection(hdc, ctypes.byref(kopf), 0, ctypes.byref(bits), None, 0)
    try:
        alt = gdi32.SelectObject(hdc, hbmp)
        ctypes.memset(bits, 0, groesse * groesse * 4)
        user32.DrawIconEx(hdc, 0, 0, hicon, groesse, groesse, 0, None, DI_NORMAL)
        roh = ctypes.string_at(bits, groesse * groesse * 4)
        gdi32.SelectObject(hdc, alt)
    finally:
        gdi32.DeleteObject(hbmp)
        gdi32.DeleteDC(hdc)
        user32.DestroyIcon(hicon)
    bild = Image.frombuffer("RGBA", (groesse, groesse), roh, "raw", "BGRA", 0, 1)
    # Alte Symbole ohne Transparenz-Kanal: Alpha ist überall 0 → voll deckend setzen
    if bild.getchannel("A").getextrema()[1] == 0:
        bild.putalpha(255)
    return bild


def als_png(bild: Image.Image) -> bytes:
    puffer = io.BytesIO()
    bild.save(puffer, format="PNG")
    return puffer.getvalue()


def laufende_programme() -> list[dict]:
    """Laufende Programme mit eigener .exe (ohne Windows-Systemprogramme), je einmal."""
    gesehen, liste = set(), []
    for p in psutil.process_iter(["name", "exe"]):
        exe = p.info.get("exe") or ""
        name = p.info.get("name") or ""
        if not exe or exe.lower() in gesehen:
            continue
        if exe.lower().startswith(r"c:\windows"):
            continue
        gesehen.add(exe.lower())
        liste.append({"name": name, "exe": exe})
    liste.sort(key=lambda e: e["name"].lower())
    return liste
