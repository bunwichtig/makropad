"""Programme in den Vordergrund holen – auch aus dem Infobereich (Tray)."""

from __future__ import annotations

import ctypes
import os
import shlex
import subprocess
import time
from ctypes import wintypes

import psutil

user32 = ctypes.WinDLL("user32", use_last_error=True)

SW_SHOW = 5
SW_RESTORE = 9
GW_OWNER = 4
VK_MENU = 0x12
KEYEVENTF_KEYUP = 0x0002

EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def _titel(hwnd) -> str:
    laenge = user32.GetWindowTextLengthW(hwnd)
    puffer = ctypes.create_unicode_buffer(laenge + 1)
    user32.GetWindowTextW(hwnd, puffer, laenge + 1)
    return puffer.value


def _klasse(hwnd) -> str:
    puffer = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, puffer, 256)
    return puffer.value


# Unsichtbare Hilfsfenster, die nie als Hauptfenster gelten
HILFSFENSTER = ("TrayIconMessage", "PowerDummyWindow", "ClipboardView", "QEventDispatcher")


def _pids(prozessname: str) -> set[int]:
    return {p.pid for p in psutil.process_iter(["name"])
            if (p.info["name"] or "").lower() == prozessname.lower()}


def _alle_fenster(pids: set[int]) -> list[int]:
    gefunden: list[int] = []

    @EnumWindowsProc
    def rueckruf(hwnd, _):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in pids:
            gefunden.append(hwnd)
        return True

    user32.EnumWindows(rueckruf, 0)
    return gefunden


def _fenster_von(prozessname: str, titel=None) -> list[tuple[int, bool]]:
    """Alle Hauptfenster (mit Titel, ohne Besitzer) des Prozesses: [(hwnd, sichtbar)].
    titel: optionaler Text (oder Liste), der im Fenstertitel vorkommen muss."""
    if isinstance(titel, str):
        titel = [titel]
    titel = [t.lower() for t in (titel or [])]
    pids = {p.pid for p in psutil.process_iter(["name"])
            if (p.info["name"] or "").lower() == prozessname.lower()}
    gefunden: list[tuple[int, bool]] = []

    @EnumWindowsProc
    def rueckruf(hwnd, _):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in pids and not user32.GetWindow(hwnd, GW_OWNER):
            if any(h in _klasse(hwnd) for h in HILFSFENSTER):
                return True
            name = _titel(hwnd)
            if name and (not titel or any(t in name.lower() for t in titel)):
                gefunden.append((hwnd, bool(user32.IsWindowVisible(hwnd))))
        return True

    user32.EnumWindows(rueckruf, 0)
    return gefunden


def _nach_vorne(hwnd: int) -> None:
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
    else:
        user32.ShowWindow(hwnd, SW_SHOW)
    # Windows lässt Hintergrund-Programme normalerweise kein Fenster nach vorne holen.
    # Ein kurzer Alt-Tastendruck hebt diese Sperre auf.
    user32.keybd_event(VK_MENU, 0, 0, 0)
    user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
    user32.SetForegroundWindow(hwnd)


def starten(befehl: str) -> None:
    befehl = os.path.expandvars(befehl).strip()
    # Gestartetes Programm darf sich selbst nach vorne holen
    user32.AllowSetForegroundWindow(-1)  # ASFW_ANY
    if "://" in befehl and not os.path.exists(befehl):
        os.startfile(befehl)                  # z. B. steam://open/friends
        return
    if os.path.isfile(befehl.strip('"')):
        teile = [befehl.strip('"')]            # reiner Pfad, auch mit Leerzeichen
    else:
        teile = [t.strip('"') for t in shlex.split(befehl, posix=False)]
    subprocess.Popen(teile, close_fds=True,
                     creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))


def _groesse(hwnd) -> tuple[int, int]:
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return r.right - r.left, r.bottom - r.top


def _hauptfenster(kandidaten: list[int]) -> int | None:
    """Das größte Fenster – kleine Hilfsfenster (Tray-Symbol, Meldungen) fallen raus."""
    gross = [(w * h, hwnd) for hwnd in kandidaten for w, h in [_groesse(hwnd)] if w >= 200 and h >= 150]
    return max(gross)[1] if gross else None


def _sichtbares(prozess, titel) -> int | None:
    return _hauptfenster([h for h, s in _fenster_von(prozess, titel) if s])


def _einblenden(hwnd: int) -> None:
    user32.ShowWindow(hwnd, SW_SHOW)
    user32.ShowWindow(hwnd, SW_RESTORE)
    _nach_vorne(hwnd)


WM_APP = 0x8000
QT_TRAY_NACHRICHT = WM_APP + 101      # MYWM_NOTIFYICON in Qt
NIN_SELECT = 0x0400
WM_LBUTTONDBLCLK = 0x0203


def _tray_klick(prozess: str) -> bool:
    """Simuliert einen Klick auf das Tray-Symbol eines Qt-Programms (z. B. EA App).
    Qt empfängt Tray-Klicks über ein unsichtbares Fenster „QTrayIconMessageWindow“ –
    dorthin schicken wir dieselbe Nachricht, die Windows bei einem echten Klick sendet."""
    tray = [h for h in _alle_fenster(_pids(prozess)) if "TrayIconMessage" in _klasse(h)]
    if not tray:
        return False
    for hwnd in tray:
        user32.ShowWindow(hwnd, 0)  # SW_HIDE – falls es versehentlich sichtbar wurde
    user32.AllowSetForegroundWindow(-1)
    for nachricht in (NIN_SELECT, WM_LBUTTONDBLCLK):
        for hwnd in tray:
            user32.PostMessageW(hwnd, QT_TRAY_NACHRICHT, 0, nachricht)
        for _ in range(10):
            time.sleep(0.1)
            if _hauptfenster([h for h, s in _fenster_von(prozess) if s]):
                return True
    return True


def fokus(prozess: str, starten_befehl: str | None = None, titel=None, tray_klick: bool = False) -> str:
    """Holt das Programm nach vorne. Gibt zurück, was passiert ist (fürs Protokoll).
    1. Sichtbares Fenster vorhanden → nach vorne holen.
    2. Startbefehl vorhanden (z. B. steam://…, Discord-Updater) → ausführen;
       laufende Programme holen sich dann meist selbst nach vorne.
    3. Sonst bzw. wenn das nicht hilft (z. B. EA App im Tray): verstecktes
       Hauptfenster direkt einblenden."""
    hwnd = _sichtbares(prozess, titel)
    if hwnd:
        _nach_vorne(hwnd)
        return "sichtbares Fenster nach vorne geholt"

    if tray_klick and _tray_klick(prozess):
        hwnd = _sichtbares(prozess, titel)
        if hwnd:
            _nach_vorne(hwnd)
            return "per Tray-Klick geöffnet"

    if starten_befehl:
        starten(starten_befehl)
        for _ in range(15):          # bis zu 1,5 s auf das Fenster warten
            time.sleep(0.1)
            hwnd = _sichtbares(prozess, titel)
            if hwnd:
                _nach_vorne(hwnd)
                return "über Startbefehl geöffnet"

    versteckt = None if tray_klick else _hauptfenster(
        [h for h, s in _fenster_von(prozess, titel) if not s])
    if versteckt:
        _einblenden(versteckt)
        return f"verstecktes Fenster „{_titel(versteckt)}“ eingeblendet"

    if not psutil.pids() or not any((p.info["name"] or "").lower() == prozess.lower()
                                    for p in psutil.process_iter(["name"])):
        return "Programm läuft nicht"
    namen = [f"„{_titel(h)}“ [{_klasse(h)}] {_groesse(h)}" for h in _alle_fenster(_pids(prozess))
             if _titel(h)]
    return "kein passendes Fenster gefunden. Fenster des Programms: " + (", ".join(namen) or "keine")


# ---------- Fenster nach Bildschirmposition ----------

class WINDOWPLACEMENT(ctypes.Structure):
    _fields_ = [("length", wintypes.UINT), ("flags", wintypes.UINT), ("showCmd", wintypes.UINT),
                ("ptMinPosition", wintypes.POINT), ("ptMaxPosition", wintypes.POINT),
                ("rcNormalPosition", wintypes.RECT)]


def _rechteck(hwnd) -> tuple[int, int, int, int]:
    """Position des Fensters – bei minimierten Fenstern die Position vor dem Minimieren."""
    if user32.IsIconic(hwnd):
        wp = WINDOWPLACEMENT(length=ctypes.sizeof(WINDOWPLACEMENT))
        user32.GetWindowPlacement(hwnd, ctypes.byref(wp))
        r = wp.rcNormalPosition
    else:
        r = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(r))
    return r.left, r.top, r.right, r.bottom


def fokus_position(prozess: str, bereich: str = "links") -> str:
    """Holt das Fenster des Programms nach vorne, das im gewünschten Bereich des Bildschirms liegt
    (links/rechts = linke/rechte Hälfte der gesamten Bildschirmfläche, bei zwei Monitoren also
    der linke bzw. rechte Monitor). Liegen dort mehrere, gewinnt das oberste (zuletzt benutzte)."""
    x0 = user32.GetSystemMetrics(76)       # SM_XVIRTUALSCREEN
    breite = user32.GetSystemMetrics(78)   # SM_CXVIRTUALSCREEN
    mitte = x0 + breite / 2

    # EnumWindows liefert die Fenster von oben nach unten (Z-Reihenfolge)
    kandidaten = []
    for hwnd, sichtbar in _fenster_von(prozess):
        if not sichtbar:
            continue
        links, oben, rechts, unten = _rechteck(hwnd)
        if rechts - links < 200 or unten - oben < 150:
            continue
        x = (links + rechts) / 2
        if (bereich == "links" and x < mitte) or (bereich == "rechts" and x >= mitte):
            kandidaten.append(hwnd)

    if not kandidaten:
        return f"kein Fenster im Bereich „{bereich}“ gefunden"
    _nach_vorne(kandidaten[0])
    return f"„{_titel(kandidaten[0])}“ nach vorne geholt"
