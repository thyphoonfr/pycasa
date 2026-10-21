"""
FR: Point d'entrée principal de PyCasa (portage Python fidèle et multi-OS de Picasa 3).
Lance l'application graphique Picasa 3 sur Windows, macOS et Linux.

EN: Main entry point for PyCasa (faithful cross-platform Python port of Picasa 3).
Launches the Picasa 3 graphical application on Windows, macOS, and Linux.

Usage :
    py main.py
    py main.py "chemin/vers/db3"

Ref: picasa3.exe @ 0x009838D0 (WinMain / Window initialization)
Ref: AGENTS.md §4 bis (Fidélité de l'interface / UI Fidelity)
"""

import sys
from picasa_py.ui.app import run_picasa


def main() -> int:
    """
    FR: Analyse les arguments de ligne de commande et démarre l'application PyCasa.
    EN: Parses command-line arguments and starts the PyCasa application.
    """
    db_path = sys.argv[1] if len(sys.argv) > 1 else None
    return run_picasa(db_path)


if __name__ == "__main__":
    sys.exit(main())

