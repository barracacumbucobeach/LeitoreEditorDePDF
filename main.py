#!/usr/bin/env python3
"""Ponto de entrada do Fólio Studio — Leitor & Editor de PDF Profissional."""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from folio_studio import __app_name__, __organization__
from folio_studio.main_window import FolioMainWindow


def main() -> int:
    QApplication.setOrganizationName(__organization__)
    QApplication.setApplicationName(__app_name__)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = FolioMainWindow()
    window.show()

    for arg in sys.argv[1:]:
        if arg.lower().endswith(".pdf") and Path(arg).exists():
            window.open_document(arg)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
