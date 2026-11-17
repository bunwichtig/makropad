# makropad

Eigene, quelloffene Windows-Software für das Makropad **AJAZZ AKP03E** (USB-ID `0B00:1001`, Mirabox-N3-Familie). Sie ersetzt die Hersteller-Software und baut keine Internetverbindung auf.

Projektplan, Funktionen und Fahrplan: [PROJEKT.md](PROJEKT.md)

> Status: in Entwicklung – Grundfunktionen laufen

## Herunterladen

Unter **Releases → „Neueste Version“** liegt `makropad-windows.zip`. Entpacken und im Ordner `makropad` die `makropad.exe` starten: Das Programm erscheint im Infobereich, die `config.json` wird beim ersten Start neben der .exe angelegt.

Rechtsklick auf das Tray-Symbol:
- **Konfiguration öffnen**: Oberfläche zum Belegen aller Seiten, Tasten und Regler (auch per Doppelklick aufs Symbol)
- **config.json im Editor**: für Feinheiten von Hand
- **Konfiguration neu laden**: nach Änderungen von Hand
- **Protokoll anzeigen**
- **Mit Windows starten**
- **Beenden**

Die Hersteller-Software vorher beenden.

## Entwicklung

```powershell
pip install -r requirements.txt
python start.py             # Tray
python start.py --konsole   # mit Ausgabe im Terminal
```


## Lizenzen

Symbole: [Lucide](https://lucide.dev) (ISC-Lizenz, siehe `src/makropad/ui/LUCIDE_LICENSE.txt`).
