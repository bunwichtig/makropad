"""Tray-Modus: Symbol im Infobereich, Menü, Autostart."""

from __future__ import annotations

import os
import shutil
import sys
import threading

import pystray
from PIL import Image, ImageDraw

from . import app as app_modul
from .app import App, log, nur_einmal_starten

NAME = "Makropad"
AUTOSTART_SCHLUESSEL = r"Software\Microsoft\Windows\CurrentVersion\Run"


# ---------- Pfade ----------

def ist_exe() -> bool:
    return getattr(sys, "frozen", False)


def programm_ordner() -> str:
    if ist_exe():
        return os.path.dirname(sys.executable)
    return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def config_pfad() -> str:
    """Als .exe: config.json liegt neben der .exe. Fehlt sie, wird die Standard-Belegung angelegt."""
    pfad = os.path.join(programm_ordner(), "config.json")
    if not os.path.exists(pfad) and ist_exe():
        vorlage = os.path.join(sys._MEIPASS, "config.json")  # type: ignore[attr-defined]
        shutil.copyfile(vorlage, pfad)
    return pfad


def startbefehl() -> str:
    if ist_exe():
        return f'"{sys.executable}"'
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    start = os.path.join(programm_ordner(), "start.py")
    return f'"{pythonw}" "{start}"'


# ---------- Autostart (Registry, nur aktueller Benutzer) ----------

def autostart_an() -> bool:
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_SCHLUESSEL) as k:
            winreg.QueryValueEx(k, NAME)
            return True
    except OSError:
        return False


def autostart_setzen(an: bool) -> None:
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_SCHLUESSEL, 0,
                        winreg.KEY_SET_VALUE) as k:
        if an:
            winreg.SetValueEx(k, NAME, 0, winreg.REG_SZ, startbefehl())
        else:
            try:
                winreg.DeleteValue(k, NAME)
            except OSError:
                pass


# ---------- Tray-Symbol ----------

def symbol(verbunden: bool) -> Image.Image:
    s = 64
    bild = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    z = ImageDraw.Draw(bild)
    z.rounded_rectangle((2, 10, 62, 54), radius=8, fill=(40, 40, 46, 255))
    farbe = (42, 157, 85, 255) if verbunden else (120, 120, 120, 255)
    for reihe in range(2):
        for spalte in range(3):
            x = 9 + spalte * 17
            y = 16 + reihe * 17
            z.rounded_rectangle((x, y, x + 12, y + 12), radius=2, fill=farbe)
    return bild


def diagnose_einrichten(ordner: str) -> None:
    """Fehler und Abstürze protokollieren:
    - Python-Fehler in allen Threads → makropad.log
    - harte Abstürze (z. B. in Windows-Bibliotheken) → absturz.log mit dem Stand ALLER Threads"""
    import faulthandler
    import traceback

    global _ABSTURZ_DATEI
    _ABSTURZ_DATEI = open(os.path.join(ordner, "absturz.log"), "a", encoding="utf-8")
    _ABSTURZ_DATEI.write(f"\n===== Start {__import__('time').strftime('%Y-%m-%d %H:%M:%S')} =====\n")
    _ABSTURZ_DATEI.flush()
    faulthandler.enable(file=_ABSTURZ_DATEI, all_threads=True)

    def unbehandelt(art, wert, tb):
        log("UNBEHANDELTER FEHLER:\n" + "".join(traceback.format_exception(art, wert, tb)))

    def thread_fehler(args):
        log(f"FEHLER im Thread {args.thread.name if args.thread else '?'}:\n"
            + "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback)))

    sys.excepthook = unbehandelt
    threading.excepthook = thread_fehler


_ABSTURZ_DATEI = None


def version() -> str:
    for basis in (getattr(sys, "_MEIPASS", ""), programm_ordner()):
        pfad = os.path.join(basis, "version.txt")
        if basis and os.path.exists(pfad):
            return open(pfad, encoding="utf-8").read().strip()
    return "Entwicklung"


def main() -> None:
    if not nur_einmal_starten():
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            None, "Makropad läuft bereits – siehe Symbol im Infobereich.", NAME, 0x40)
        return
    log_pfad = os.path.join(programm_ordner(), "makropad.log")
    app_modul.LOG_DATEI = log_pfad
    diagnose_einrichten(programm_ordner())
    pfad = config_pfad()
    import platform
    log(f"Start (Tray), Version {version()}, Windows {platform.version()}, Python {platform.python_version()}")
    log(f"Konfiguration: {pfad}")

    icon = pystray.Icon(NAME, symbol(False), f"{NAME} – warte auf Pad")

    def status(verbunden: bool) -> None:
        icon.icon = symbol(verbunden)
        icon.title = f"{NAME} – " + ("verbunden" if verbunden else "nicht verbunden")

    app = App(pfad, status=status)

    konfig = None

    def config_oeffnen(*_):
        nonlocal konfig
        from .konfig import KonfigServer
        try:
            log("Menü: Konfiguration öffnen")
            if konfig is None:
                konfig = KonfigServer(app)
            konfig.fenster_oeffnen()
        except Exception as e:
            import traceback
            log(f"Konfiguration konnte nicht geöffnet werden: {e}\n{traceback.format_exc()}")

    def json_oeffnen(*_):
        os.startfile(pfad)  # config.json im Standard-Editor

    def log_oeffnen(*_):
        if os.path.exists(log_pfad):
            os.startfile(log_pfad)

    def autostart_umschalten(*_):
        autostart_setzen(not autostart_an())

    def beenden(*_):
        app.beenden()
        icon.stop()

    icon.menu = pystray.Menu(
        pystray.MenuItem("Konfiguration öffnen", config_oeffnen, default=True),
        pystray.MenuItem("Konfiguration neu laden", lambda *_: app.neu_laden()),
        pystray.MenuItem("config.json im Editor", json_oeffnen),
        pystray.MenuItem("Protokoll anzeigen", log_oeffnen),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Mit Windows starten", autostart_umschalten,
                         checked=lambda _: autostart_an()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Beenden", beenden),
    )

    arbeiter = threading.Thread(target=app.laufen, daemon=True)
    arbeiter.start()
    icon.run()
    arbeiter.join(timeout=3)
    log("Beendet.")
