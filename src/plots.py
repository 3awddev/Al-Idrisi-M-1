from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QColor, QFont

from src.telemetry_packet import TelemetryPacket


pg.setConfigOptions(antialias=True)


class BasePlot(pg.PlotWidget):
    COLORS = [
        QColor("#00BFFF"),
        QColor("#FF6B35"),
        QColor("#39FF14"),
        QColor("#FF1493"),
        QColor("#FFD700"),
        QColor("#00FF7F"),
    ]

    def __init__(
        self,
        title: str,
        ylabel: str,
        max_samples: int = 600,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.max_samples = max_samples
        self._daylight = False
        self._curves: list[pg.PlotDataItem] = []
        self._data: dict[str, np.ndarray] = {}

        self.setLabel("left", ylabel)
        self.setLabel("bottom", "Time (s)")
        self.setTitle(title)
        self.showGrid(x=True, y=True, alpha=0.3)
        self.setLimits(xMin=-10, xMax=600)
        self._apply_daylight(False)

    def add_curve(self, name: str, color: QColor | None = None) -> pg.PlotDataItem:
        if color is None:
            color = self.COLORS[len(self._curves) % len(self.COLORS)]
        pen = pg.mkPen(color, width=1.5)
        curve = self.plot(pen=pen, name=name)
        self._curves.append(curve)
        self._data[name] = np.empty(0)
        if self._daylight:
            pen.setWidth(3)
        return curve

    def append(self, name: str, t: float, value: float) -> None:
        if name not in self._data:
            self._data[name] = np.empty(0)
        arr = self._data[name]
        arr = np.append(arr, value)
        if len(arr) > self.max_samples:
            arr = arr[-self.max_samples :]
        self._data[name] = arr

        x = np.arange(len(arr))
        idx = list(self._data.keys()).index(name)
        self._curves[idx].setData(x, arr)

    def set_daylight(self, enabled: bool) -> None:
        self._daylight = enabled
        self._apply_daylight(enabled)

    def _apply_daylight(self, enabled: bool) -> None:
        if enabled:
            self.setBackground("w")
            self.getAxis("left").setPen(pg.mkPen(color="k", width=2))
            self.getAxis("bottom").setPen(pg.mkPen(color="k", width=2))
            font = QFont("Segoe UI", 11, QFont.Weight.Bold)
            self.getAxis("left").setTickFont(font)
            self.getAxis("bottom").setTickFont(font)
            for i, c in enumerate(self._curves):
                color = self.COLORS[i % len(self.COLORS)]
                c.setPen(pg.mkPen(color, width=3))
            self.getAxis("left").setTextPen("k")
            self.getAxis("bottom").setTextPen("k")
        else:
            self.setBackground("k")
            self.getAxis("left").setPen(pg.mkPen(color="#888", width=1))
            self.getAxis("bottom").setPen(pg.mkPen(color="#888", width=1))
            font = QFont("Segoe UI", 10)
            self.getAxis("left").setTickFont(font)
            self.getAxis("bottom").setTickFont(font)
            for i, c in enumerate(self._curves):
                color = self.COLORS[i % len(self.COLORS)]
                c.setPen(pg.mkPen(color, width=1.5))
            self.getAxis("left").setTextPen("#888")
            self.getAxis("bottom").setTextPen("#888")


class AltitudePlot(BasePlot):
    def __init__(self, parent=None) -> None:
        super().__init__("Altitude", "Altitude (m)", parent=parent)
        self.add_curve("Altitude", QColor("#00BFFF"))


class VoltagePlot(BasePlot):
    def __init__(self, parent=None) -> None:
        super().__init__("Battery Voltage", "Voltage (V)", parent=parent)
        self.add_curve("Voltage", QColor("#39FF14"))


class CurrentPlot(BasePlot):
    def __init__(self, parent=None) -> None:
        super().__init__("Battery Current", "Current (A)", parent=parent)
        self.add_curve("Current", QColor("#FF6B35"))


class AccelPlot(BasePlot):
    def __init__(self, parent=None) -> None:
        super().__init__("Acceleration (3-axis)", "Accel (m/s²)", parent=parent)
        self.add_curve("Accel_R", QColor("#FF1493"))
        self.add_curve("Accel_P", QColor("#39FF14"))
        self.add_curve("Accel_Y", QColor("#FFD700"))
        self.addLegend()


class GyroPlot(BasePlot):
    def __init__(self, parent=None) -> None:
        super().__init__("Rotation Rates (3-axis)", "Gyro (°/s)", parent=parent)
        self.add_curve("Gyro_R", QColor("#FF1493"))
        self.add_curve("Gyro_P", QColor("#39FF14"))
        self.add_curve("Gyro_Y", QColor("#FFD700"))
        self.addLegend()
