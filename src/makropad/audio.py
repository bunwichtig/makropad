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


def _mikrofone():
    """Standard-Mikrofon und Kommunikations-Mikrofon (oft dasselbe)."""
    return [
        _endpoint(EDataFlow.eCapture, ERole.eConsole),
        _endpoint(EDataFlow.eCapture, ERole.eCommunications),
    ]


# ---------- Mikrofon ----------

def mikro_ist_stumm() -> bool:
    return bool(_endpoint(EDataFlow.eCapture, ERole.eConsole).GetMute())


def mikro_umschalten() -> bool:
    """Schaltet das Mikrofon stumm bzw. wieder an. Gibt den neuen Zustand zurück (True = stumm)."""
    neu = not mikro_ist_stumm()
    for m in _mikrofone():
        m.SetMute(int(neu), None)
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
