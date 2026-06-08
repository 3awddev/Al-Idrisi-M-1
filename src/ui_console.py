from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QPlainTextEdit, QWidget, QHBoxLayout, QLabel, QVBoxLayout


class MessageConsole(QPlainTextEdit):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(500)
        self.setPlaceholderText("Messages appear here...")
        self._daylight = False

    def log(self, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S.%f")[:12]
        self.appendPlainText(f"[{ts}] {message}")

    def set_daylight(self, enabled: bool) -> None:
        self._daylight = enabled
        if enabled:
            self.setStyleSheet(
                "QPlainTextEdit { background: #ffffff; color: #000000; "
                "font: 11pt 'Segoe UI'; font-weight: bold; }"
            )
        else:
            self.setStyleSheet(
                "QPlainTextEdit { background: #1a1a1a; color: #c8c8c8; "
                "font: 10pt 'Consolas'; }"
            )


class PacketMonitor(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        title = QLabel("Packet Monitor")
        title.setStyleSheet("font-weight: bold; font-size: 10pt;")
        layout.addWidget(title)

        stats_layout = QHBoxLayout()
        self._rcvd_label = QLabel("Rcvd: 0")
        self._lost_label = QLabel("Lost: 0")
        self._pct_label = QLabel("Success: 100%")

        for lbl in [self._rcvd_label, self._lost_label, self._pct_label]:
            lbl.setStyleSheet("font-size: 12pt; font-weight: bold; padding: 4px;")
            stats_layout.addWidget(lbl)

        layout.addLayout(stats_layout)
        layout.addStretch()

    def update_counts(self, received: int, lost: int) -> None:
        self._rcvd_label.setText(f"Rcvd: {received}")
        self._lost_label.setText(f"Lost: {lost}")
        total = received + lost
        pct = 100.0 if total == 0 else (received / total) * 100.0
        self._pct_label.setText(f"Success: {pct:.1f}%")

        if total > 0 and (lost / total) > 0.05:
            self._lost_label.setStyleSheet(
                "font-size: 12pt; font-weight: bold; padding: 4px; color: red;"
            )
        else:
            self._lost_label.setStyleSheet(
                "font-size: 12pt; font-weight: bold; padding: 4px; color: #888;"
            )

    def set_daylight(self, enabled: bool) -> None:
        color = "#000" if enabled else "#c8c8c8"
        for lbl in [self._rcvd_label, self._lost_label, self._pct_label]:
            lbl.setStyleSheet(f"font-size: 12pt; font-weight: bold; padding: 4px; color: {color};")
