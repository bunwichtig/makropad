# Makropad-Tool – eigene Software für AJAZZ AKP03E

Schlanke, quelloffene Windows-Software zur Steuerung des Makropads **AJAZZ AKP03E**, die ohne die Hersteller-Software auskommt und keine Verbindung ins Internet aufbaut.

---

## 1. Ziel

- Die Hersteller-Software („Stream Dock AJAZZ“) vollständig ersetzen
- **Keine Internetverbindung**: kein Telemetrie-Code, keine Updates von außen
- Nachvollziehbarer Code und eine einzelne `.exe` zum Starten

## 2. Hardware

| Merkmal | Wert |
|---|---|
| Gerät | AJAZZ AKP03E (Mirabox-N3-Familie) |
| Baugleich verkauft als | Mirabox N3, Treaslin N3, AJAZZ AKP03 / AKP03R u. a. |
| Bedienelemente | 6 Tasten mit Display, 3 Drehregler (drückbar), 3 Knöpfe |
| Anschluss | USB-C, USB-HID |
| **USB-ID des eigenen Geräts** | **`0B00:1001`** ✅ (am 17.11.2026 geprüft) |
| Meldet sich als | „CS06 for signing“ |
| Baugleiche ID bekannt als | Mars Gaming MSD-TWO, unterstützt von opendeck-akp03 seit v0.7.0 |
| USB-Schnittstellen | `MI_00` = herstellerdefiniertes HID-Gerät (Displays & Steuerung) · `MI_01` = HID-Tastatur |

**Weitere IDs der Familie:** AKP03 `0300:1001`, AKP03E `0300:1002` / rev. 2 `0300:3002`, AKP03R `0300:1003` / `0300:3003`, Mirabox N3 `6602:1002`, N3EN `6603:1003`, TreasLin N3 `5548:1001`.

**Bekannte Eigenheiten der N3-Familie:**
- Pakete mit 1024 Bytes, Protokollversion 2 oder 3 (mit v3 sind langes Drücken und GIFs möglich)
- Tastenbilder in 60 px (v2) bzw. 64 px (v3)
- Zum Leeren der Displays ist ein extra Befehl nötig
- Das Gerät trennt sich nach ca. 35 s Stille → **Keepalive** nötig
- Welche Protokollversion `0B00:1001` nutzt, wird in Phase 1 geklärt

## 3. Protokoll

Ein Reverse Engineering der Installationsdatei ist **nicht nötig**, weil das USB-Protokoll bereits in Open-Source-Projekten umgesetzt ist:

- **opendeck-akp03**: Plugin für OpenDeck, unterstützt die gesamte N3-Familie
  https://github.com/4ndv/opendeck-akp03
- **OpenDeck**: Open-Source-Alternative zur Stream-Deck-Software (GPL-3.0)
- **mirajazz**: Rust-Bibliothek mit dem Protokoll (v2/v3) für die ganze Familie
  https://github.com/4ndv/mirajazz
- **deck-commander**: C#-Treiber mit dokumentiertem Wire-Format und Keepalive
  https://github.com/tysongf/deck-commander
- **codexdeck**: Windows-Projekt für das AKP03E (MIT), eine weitere Referenz für die Ansteuerung unter Windows
  https://github.com/sepivip/codexdeck

Aufgabe in Phase 1: Aus diesen Quellen die Befehle für Bild senden, Helligkeit, Display leeren und Eingaben lesen (Taste, Regler, Knopf) herausarbeiten und dokumentieren. Lizenzen beachten: Den Code nicht 1:1 übernehmen, sondern das Protokoll nachimplementieren.

## 4. Funktionen

### Tasten (6 mit Display)
- [ ] Eigenes Bild oder Icon pro Taste, optional mit Text
- [ ] Tastenkürzel senden (z. B. Strg+C, Mikro stumm)
- [ ] Programm, Datei oder Ordner öffnen
- [ ] Webseite öffnen
- [ ] Text einfügen
- [ ] Mehrere Seiten / Profile umschalten

### Drehregler (3)
- [ ] Systemlautstärke
- [ ] Lautstärke einzelner Apps (Spotify, Discord …)
- [ ] Scrollen, Zoomen, Helligkeit
- [ ] Drücken des Reglers = eigene Aktion (z. B. stumm schalten)

### Knöpfe (3)
- [ ] Profil- oder Seitenwechsel
- [ ] Eigene Aktionen wie bei den Tasten

### Programm
- [ ] Läuft im Infobereich (Tray), Autostart mit Windows
- [ ] **Grafische Oberfläche**, damit sich alles einfach konfigurieren lässt (Design separat, 3 Varianten zur Auswahl)
- [ ] Konfiguration wird intern als `config.json` gespeichert
- [ ] Profil wechselt automatisch je nach aktivem Programm
- [ ] Keine Internetverbindung (im Code prüfbar)
- [ ] Helligkeit der Displays einstellen

## 5. Technik (Vorschlag)

| Bereich | Wahl |
|---|---|
| Sprache | Python 3 (gut lesbar, schnell anpassbar) |
| USB-Zugriff | `hidapi` |
| Bilder für die Tasten | `Pillow` |
| Tray-Icon | `pystray` |
| Tastenkürzel / Text | `pynput` oder `keyboard` |
| Lautstärke (System & pro App) | `pycaw` |
| Aktives Programm erkennen | `pywin32` / `psutil` |
| Konfiguration | `config.json` (oder YAML) |
| Oberfläche | wird separat festgelegt (3 Varianten) |
| .exe bauen | `PyInstaller` über **GitHub Actions** (Windows-Runner) |

Alternative: Rust mit eigenem HID-Code ergibt eine kleinere .exe, lässt sich aber schwerer selbst anpassen.

## 6. Projektstruktur (Entwurf)

```
makropad-tool/
├── src/
│   ├── main.py          # Start, Tray, Hauptschleife
│   ├── device.py        # USB-Kommunikation mit dem AKP03E
│   ├── actions.py       # Tastenkürzel, Programme, Text, Web
│   ├── audio.py         # Lautstärke (System / pro App)
│   ├── profiles.py      # Profile, Seiten, Auto-Wechsel
│   └── images.py        # Icons/Text auf Tastengröße rendern
├── icons/               # eigene Tastenbilder
├── config.json          # Belegung
├── .github/workflows/
│   └── build.yml        # baut die .exe
├── PROJEKT.md
└── README.md
```

## 7. Fahrplan

1. **Protokoll klären**: Befehle aus den Referenzprojekten dokumentieren und die USB-ID des eigenen Geräts prüfen
2. **Grundgerüst**: Gerät verbinden, Tastendrücke und Regler im Terminal ausgeben
3. **Displays**: Bilder auf die 6 Tasten senden, Helligkeit einstellen
4. **Aktionen**: Tastenkürzel, Programme, Webseiten, Text
5. **Audio**: System- und App-Lautstärke über die Regler
6. **Profile**: Seiten, Knöpfe zum Umschalten, automatischer Wechsel je nach Programm
7. **Tray & Autostart**
8. **.exe-Build** per GitHub Actions
9. **Oberfläche** zum Belegen (Variante wird separat ausgewählt)

## 8. Offene Fragen

- ~~Genaue USB-ID des eigenen Geräts?~~ → `0B00:1001`
- Protokollversion (v2 oder v3)?
- ~~Oberfläche?~~ → ja, wird eingeplant; Design in eigenem Thread (3 Varianten)
- ~~Repo-Name?~~ → https://github.com/bunwichtig/makropad
- Kommen weitere Funktionen dazu?
