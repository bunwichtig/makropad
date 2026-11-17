"""Startet das Makropad-Tool.

  python start.py             → läuft im Infobereich (Tray)
  python start.py --konsole   → läuft im Terminal mit Ausgabe (zum Testen)
"""

import os
import sys

if not getattr(sys, "frozen", False):
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

if "--konsole" in sys.argv:
    from makropad.app import main
else:
    from makropad.tray import main

main()
