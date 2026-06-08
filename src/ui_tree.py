from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem, QPushButton, QWidget, QVBoxLayout

from src.telemetry_packet import TelemetryPacket


class ResourcesTree(QTreeWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setHeaderLabel("Resources")
        self.setMinimumWidth(240)
        self.setIndentation(16)

        self._mission_item = QTreeWidgetItem(self, ["Mission"])
        self._hardware_item = QTreeWidgetItem(self, ["Hardware"])
        self._telemetry_item = QTreeWidgetItem(self, ["Telemetry"])
        self._commands_item = QTreeWidgetItem(self, ["Commands"])

        self._port_sub = QTreeWidgetItem(self._hardware_item, ["Serial Port: --"])
        self._batt_sub = QTreeWidgetItem(self._hardware_item, ["Battery: -- V"])

        self._tele_fields: dict[str, QTreeWidgetItem] = {}
        for field in [
            "Altitude", "Temperature", "Pressure",
            "Voltage", "Current",
            "GPS Latitude", "GPS Longitude", "GPS Sats",
            "Mode", "State",
        ]:
            item = QTreeWidgetItem(self._telemetry_item, [f"{field}: --"])
            self._tele_fields[field] = item

        self._cmd_widget = QWidget()
        cmd_layout = QVBoxLayout(self._cmd_widget)
        cmd_layout.setContentsMargins(8, 4, 8, 4)
        cmd_layout.setSpacing(4)

        self.btn_cal = QPushButton("CAL")
        self.btn_sim = QPushButton("SIM ENABLE")
        self.btn_mec = QPushButton("MEC")
        self.btn_cx = QPushButton("CX ON")
        self.btn_st = QPushButton("ST GPS")

        for btn in [self.btn_cal, self.btn_sim, self.btn_mec, self.btn_cx, self.btn_st]:
            btn.setMinimumHeight(28)
            cmd_layout.addWidget(btn)
        cmd_layout.addStretch()

        self._commands_item.setExpanded(True)

    def update_telemetry(self, pkt: TelemetryPacket) -> None:
        self._port_sub.setText(0, "Serial Port: Connected")
        self._batt_sub.setText(0, f"Battery: {pkt.voltage:.3f} V")
        self._tele_fields["Altitude"].setText(0, f"Altitude: {pkt.altitude:.2f} m")
        self._tele_fields["Temperature"].setText(0, f"Temperature: {pkt.temperature:.2f} °C")
        self._tele_fields["Pressure"].setText(0, f"Pressure: {pkt.pressure:.2f} hPa")
        self._tele_fields["Voltage"].setText(0, f"Voltage: {pkt.voltage:.3f} V")
        self._tele_fields["Current"].setText(0, f"Current: {pkt.current:.3f} A")
        self._tele_fields["GPS Latitude"].setText(0, f"GPS Latitude: {pkt.gps_latitude:.6f}")
        self._tele_fields["GPS Longitude"].setText(0, f"GPS Longitude: {pkt.gps_longitude:.6f}")
        self._tele_fields["GPS Sats"].setText(0, f"GPS Sats: {pkt.gps_sats}")
        self._tele_fields["Mode"].setText(0, f"Mode: {pkt.mode}")
        self._tele_fields["State"].setText(0, f"State: {pkt.state}")

    def set_port_disconnected(self) -> None:
        self._port_sub.setText(0, "Serial Port: Disconnected")
        self._batt_sub.setText(0, "Battery: -- V")
