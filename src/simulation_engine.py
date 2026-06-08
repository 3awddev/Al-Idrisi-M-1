from __future__ import annotations

import csv
import os

from PyQt6.QtCore import QThread, pyqtSignal, QTimer


class SimulationEngine(QThread):
    pressure_uplink = pyqtSignal(float)
    status_message = pyqtSignal(str)
    csv_loaded = pyqtSignal(bool, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._pending_load: str | None = None
        self._pending_start = False
        self._pending_stop = False

    def load_csv(self, path: str) -> None:
        self._pending_load = path

    def start_simulation(self) -> None:
        self._pending_start = True

    def stop_simulation(self) -> None:
        self._pending_stop = True

    def run(self) -> None:
        self._timer = QTimer()
        self._timer.timeout.connect(self._step)
        self._pressures: list[float] = []
        self._index = 0

        poll = QTimer()
        poll.timeout.connect(self._poll_controls)
        poll.start(50)

        self.exec()

        poll.stop()
        self._timer.stop()

    def _poll_controls(self) -> None:
        if self._pending_load is not None:
            path = self._pending_load
            self._pending_load = None
            self._do_load(path)

        if self._pending_start:
            self._pending_start = False
            self._do_start()

        if self._pending_stop:
            self._pending_stop = False
            self._do_stop()

    def _do_load(self, path: str) -> None:
        if not os.path.isfile(path):
            self.status_message.emit(f"[SIM] File not found: {path}")
            self.csv_loaded.emit(False, path)
            return
        self._pressures.clear()
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    self._pressures.append(float(row["PRESSURE"]))
                except (KeyError, ValueError):
                    pass
        if not self._pressures:
            self.status_message.emit("[SIM] No valid pressure data found")
            self.csv_loaded.emit(False, path)
            return
        self.status_message.emit(f"[SIM] Loaded {len(self._pressures)} pressures from {path}")
        self.csv_loaded.emit(True, path)

    def _do_start(self) -> None:
        self._index = 0
        self._timer.start(1000)

    def _do_stop(self) -> None:
        self._timer.stop()
        self._index = 0

    def _step(self) -> None:
        if self._index >= len(self._pressures):
            self._do_stop()
            self.status_message.emit("[SIM] Pressure profile complete")
            return
        pressure = self._pressures[self._index]
        self.pressure_uplink.emit(pressure)
        self._index += 1
