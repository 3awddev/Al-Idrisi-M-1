from __future__ import annotations

import sys

import qdarkstyle
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from src.ui_layout import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("CFC - CanSat Flight Control")
    app.setOrganizationName("CFC")

    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt6())

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
