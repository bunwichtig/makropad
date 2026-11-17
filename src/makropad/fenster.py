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


def _fenster_von(prozessname: str) -> list[tuple[int, bool]]:
    """Alle Hauptfenster (mit Titel, ohne Besitzer) des Prozesses: [(hwnd, sichtbar)]."""
    pids = {p.pid for p in psutil.process_iter(["name"])
            if (p.info["name"] or "").lower() == prozessname.lower()}
    gefunden: list[tuple[int, bool]] = []

    @EnumWindowsProc
    def rueckruf(hwnd, _):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in pids and not user32.GetWindow(hwnd, GW_OWNER):
            if user32.GetWindowTextLengthW(hwnd) > 0:
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
    if os.path.isfile(befehl.strip('"')):
        teile = [befehl.strip('"')]            # reiner Pfad, auch mit Leerzeichen
    else:
        teile = [t.strip('"') for t in shlex.split(befehl, posix=False)]
    subprocess.Popen(teile, close_fds=True,
                     creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))


def fokus(prozess: str, starten_befehl: str | None = None) -> None:
    """Holt das Programm nach vorne.
    1. Sichtbares Fenster vorhanden → nach vorne holen.
    2. Sonst (z. B. im Tray): Startbefehl ausführen – laufende Programme holen sich dann
       meist selbst nach vorne – und danach das Fenster suchen.
    3. Ohne Startbefehl: verstecktes Fenster direkt einblenden."""
    fenster = _fenster_von(prozess)
    sichtbar = [h for h, s in fenster if s]
    if sichtbar:
        _nach_vorne(sichtbar[0])
        return

    if starten_befehl:
        starten(starten_befehl)
        for _ in range(20):          # bis zu 2 s auf das Fenster warten
            time.sleep(0.1)
            sichtbar = [h for h, s in _fenster_von(prozess) if s]
            if sichtbar:
                _nach_vorne(sichtbar[0])
                return
        return

    if fenster:
        _nach_vorne(fenster[0][0])
