"""Lautstärke und Mikrofon unter Windows (Core Audio über pycaw)."""

from __future__ import annotations

from ctypes import POINTER, cast

import comtypes
from comtypes import CLSCTX_ALL
from pycaw.api.endpointvolume import IAudioEndpointVolume
from pycaw.api.mmdeviceapi import IMMDeviceEnumerator
from pycaw.constants import CLSID_MMDeviceEnumerator, EDataFlow, ERole
from pycaw.pycaw import AudioUtilities


def _endpoint(fluss: EDataFlow, rolle: ERole):
    enum = comtypes.CoCreateInstance(
        CLSID_MMDeviceEnumerator, IMMDeviceEnumerator, comtypes.CLSCTX_INPROC_SERVER
    )
    geraet = enum.GetDefaultAudioEndpoint(fluss.value, rolle.value)
    schnittstelle = geraet.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(schnittstelle, POINTER(IAudioEndpointVolume))


def _alle_mikrofone():
    """Alle aktiven Aufnahmegeräte: [(Name, Lautstärke-Schnittstelle)]."""
    enum = comtypes.CoCreateInstance(
        CLSID_MMDeviceEnumerator, IMMDeviceEnumerator, comtypes.CLSCTX_INPROC_SERVER
    )
    sammlung = enum.EnumAudioEndpoints(EDataFlow.eCapture.value, 1)  # 1 = DEVICE_STATE_ACTIVE
    ergebnis = []
    for i in range(sammlung.GetCount()):
        geraet = sammlung.Item(i)
        try:
            name = AudioUtilities.CreateDevice(geraet).FriendlyName
        except Exception:
            name = f"Gerät {i + 1}"
        schnittstelle = geraet.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        ergebnis.append((name, cast(schnittstelle, POINTER(IAudioEndpointVolume))))
    return ergebnis


def mikrofon_namen() -> list[str]:
    return [name for name, _ in _alle_mikrofone()]


# ---------- Mikrofon ----------

def mikro_ist_stumm() -> bool:
    return bool(_endpoint(EDataFlow.eCapture, ERole.eConsole).GetMute())


def mikro_umschalten(protokoll=None) -> bool:
    """Schaltet ALLE aktiven Mikrofone stumm bzw. wieder an – so ist egal,
    welches Gerät ein Programm gerade benutzt. Gibt den neuen Zustand zurück (True = stumm)."""
    neu = not mikro_ist_stumm()
    for name, m in _alle_mikrofone():
        try:
            m.SetMute(int(neu), None)
            ok = bool(m.GetMute()) == neu
            if protokoll:
                protokoll(f"  {name}: " + ("stumm" if neu else "an") + ("" if ok else " – FEHLGESCHLAGEN"))
        except Exception as e:
            if protokoll:
                protokoll(f"  {name}: Fehler {e}")
    return neu


# ---------- Gesamtlautstärke ----------

def system_lautstaerke_aendern(schritt: float) -> float:
    """schritt z. B. +0.02 / -0.02. Gibt die neue Lautstärke (0–1) zurück."""
    v = _endpoint(EDataFlow.eRender, ERole.eConsole)
    neu = max(0.0, min(1.0, v.GetMasterVolumeLevelScalar() + schritt))
    v.SetMasterVolumeLevelScalar(neu, None)
    return neu


def system_stumm_umschalten() -> bool:
    v = _endpoint(EDataFlow.eRender, ERole.eConsole)
    neu = not v.GetMute()
    v.SetMute(int(neu), None)
    return neu


# ---------- Lautstärke einzelner Programme ----------

def app_lautstaerke_aendern(prozesse: list[str], schritt: float) -> float | None:
    """Ändert die Lautstärke aller Audio-Sitzungen der genannten Prozesse (z. B. Discord.exe).
    Gibt die neue Lautstärke zurück oder None, wenn das Programm gerade keinen Ton hat."""
    namen = {p.lower() for p in prozesse}
    neu = None
    for sitzung in AudioUtilities.GetAllSessions():
        if sitzung.Process is None:
            continue
        try:
            name = sitzung.Process.name().lower()
        except Exception:
            continue
        if name in namen:
            vol = sitzung.SimpleAudioVolume
            neu = max(0.0, min(1.0, vol.GetMasterVolume() + schritt))
            vol.SetMasterVolume(neu, None)
    return neu


def app_stumm_umschalten(prozesse: list[str]) -> bool | None:
    """Schaltet die genannten Programme stumm bzw. wieder an.
    Gibt den neuen Zustand zurück (True = stumm) oder None, wenn das Programm gerade keinen Ton hat."""
    namen = {p.lower() for p in prozesse}
    sitzungen = []
    for sitzung in AudioUtilities.GetAllSessions():
        if sitzung.Process is None:
            continue
        try:
            if sitzung.Process.name().lower() in namen:
                sitzungen.append(sitzung.SimpleAudioVolume)
        except Exception:
            continue
    if not sitzungen:
        return None
    neu = not bool(sitzungen[0].GetMute())
    for vol in sitzungen:
        vol.SetMute(int(neu), None)
    return neu


# ---------- Ausgabegerät wechseln ----------

def _alle_ausgaben():
    """Alle aktiven Wiedergabegeräte: [(id, Name)]."""
    enum = comtypes.CoCreateInstance(
        CLSID_MMDeviceEnumerator, IMMDeviceEnumerator, comtypes.CLSCTX_INPROC_SERVER
    )
    sammlung = enum.EnumAudioEndpoints(EDataFlow.eRender.value, 1)
    ergebnis = []
    for i in range(sammlung.GetCount()):
        geraet = sammlung.Item(i)
        try:
            name = AudioUtilities.CreateDevice(geraet).FriendlyName or ""
        except Exception:
            name = ""
        ergebnis.append((geraet.GetId(), name))
    return ergebnis


def ausgabe_namen() -> list[str]:
    return [name for _, name in _alle_ausgaben()]


def aktuelle_ausgabe() -> str:
    """Name des aktuellen Standard-Wiedergabegeräts."""
    enum = comtypes.CoCreateInstance(
        CLSID_MMDeviceEnumerator, IMMDeviceEnumerator, comtypes.CLSCTX_INPROC_SERVER
    )
    standard_id = enum.GetDefaultAudioEndpoint(EDataFlow.eRender.value, ERole.eConsole.value).GetId()
    for geraet_id, name in _alle_ausgaben():
        if geraet_id == standard_id:
            return name
    return ""


def ausgabe_setzen(suchtext: str) -> str | None:
    """Macht das Wiedergabegerät, dessen Name suchtext enthält, zum Standard
    (für normale Wiedergabe UND Kommunikation). Gibt den vollen Namen zurück oder None."""
    for geraet_id, name in _alle_ausgaben():
        if suchtext.lower() in name.lower():
            AudioUtilities.SetDefaultDevice(
                geraet_id, roles=[ERole.eConsole, ERole.eMultimedia, ERole.eCommunications])
            return name
    return None
