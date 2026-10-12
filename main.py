"""
Point d'entrée principal de PyCasa.
Lance la reproduction Python de Picasa 3.

Usage :
    py main.py
    py main.py "chemin/vers/db3"

Ref: AGENTS.md §4 bis (Fidélité de l'interface)
"""

import sys
from picasa_py.ui.app import run_picasa

if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(run_picasa(db_path))
