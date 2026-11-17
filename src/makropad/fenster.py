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


def fokus(prozess: str, starten_befehl: str | None = None, titel=None) -> str:
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

    if starten_befehl:
        starten(starten_befehl)
        for _ in range(15):          # bis zu 1,5 s auf das Fenster warten
            time.sleep(0.1)
            hwnd = _sichtbares(prozess, titel)
            if hwnd:
                _nach_vorne(hwnd)
                return "über Startbefehl geöffnet"

    versteckt = _hauptfenster([h for h, s in _fenster_von(prozess, titel) if not s])
    if versteckt:
        _einblenden(versteckt)
        return f"verstecktes Fenster „{_titel(versteckt)}“ eingeblendet"

    if not psutil.pids() or not any((p.info["name"] or "").lower() == prozess.lower()
                                    for p in psutil.process_iter(["name"])):
        return "Programm läuft nicht"
    namen = [f"„{_titel(h)}“ {_groesse(h)}" for h, _ in _fenster_von(prozess)]
    return "kein passendes Fenster gefunden. Fenster des Programms: " + (", ".join(namen) or "keine")
