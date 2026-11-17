"""Startet das Makropad-Tool:  python start.py  [pfad\\zur\\config.json]"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from makropad.app import main  # noqa: E402

main()
