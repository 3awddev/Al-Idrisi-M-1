from __future__ import annotations

import os

import qdarkstyle
from PyQt6.QtCore import Qt, QThread, QTimer
from PyQt6.QtGui import QAction, QFont
from PyQt6.QtSerialPort import QSerialPortInfo
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QDockWidget,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from src.commands import CommandBuilder, CommandSender
from src.data_logger import DataLogger
from src.plots import AltitudePlot, VoltagePlot, CurrentPlot, AccelPlot, GyroPlot
from src.simulation_engine import SimulationEngine
from src.telemetry_engine import TelemetryEngine
from src.telemetry_packet import TelemetryPacket
from src.ui_console import MessageConsole, PacketMonitor
from src.ui_tree import ResourcesTree
from src.visualizer_3d import ThreeDVisualizer


LIGHT_STYLESHEET = """
QMainWindow, QWidget, QDockWidget, QToolBar {
    background: #ffffff;
    color: #000000;
}
QPlainTextEdit, QListWidget, QTreeWidget {
    background: #ffffff;
    color: #000000;
    font: 11pt "Segoe UI";
    font-weight: bold;
}
QPushButton {
    font: 11pt "Segoe UI";
    font-weight: bold;
    padding: 6px 16px;
}
QLabel {
    font: 11pt "Segoe UI";
    font-weight: bold;
    color: #000000;
}
QDockWidget {
    font: 10pt "Segoe UI";
    font-weight: bold;
    color: #000000;
}
QToolBar {
    font: 10pt "Segoe UI";
    font-weight: bold;
    spacing: 8px;
}
"""

TEAM_ID = 1234


class PortDialog(QDialog):
    def __init__(self, ports: list[str], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Select Serial Port")
        self.setMinimumWidth(300)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Available ports:"))
        self.list_widget = QListWidget()
        for p in ports:
            self.list_widget.addItem(p)
        layout.addWidget(self.list_widget)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_port(self) -> str:
        item = self.list_widget.currentItem()
        return item.text() if item else ""


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"CFC - CanSat Flight Control (Team {TEAM_ID})")
        self.resize(1400, 900)

        self._daylight = False
        self._mock_active = False
        self._serial_port_name: str | None = None

        self.telemetry_engine = TelemetryEngine(self)

        self.simulation_engine = SimulationEngine(self)

        self.command_sender = CommandSender(self)
        self.data_logger = DataLogger(parent=self)

        self._setup_ui()
        self._wire_signals()
        self._start_refresh_timer()

        self.telemetry_engine.start_telemetry()
        self.telemetry_engine.start()
        self.simulation_engine.start()
        self._pending_connect_port: str | None = None
        self._pending_sim_path: str | None = None

    def _setup_ui(self) -> None:
        self._setup_toolbar()
        self._setup_central_area()
        self._setup_left_dock()
        self._setup_right_dock()
        self._setup_bottom_dock()

    def _setup_toolbar(self) -> None:
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(toolbar.iconSize() * 1.2)
        self.addToolBar(toolbar)

        self.action_connect = QAction("Connect")
        self.action_connect.triggered.connect(self._on_connect)
        toolbar.addAction(self.action_connect)

        self.action_st = QAction("ST")
        self.action_st.triggered.connect(self._on_st)
        toolbar.addAction(self.action_st)

        self.action_cal = QAction("CAL")
        self.action_cal.triggered.connect(self._on_cal)
        toolbar.addAction(self.action_cal)

        self.action_sim = QAction("SIM")
        self.action_sim.triggered.connect(self._on_sim)
        toolbar.addAction(self.action_sim)

        self.action_mec = QAction("MEC")
        self.action_mec.triggered.connect(self._on_mec)
        toolbar.addAction(self.action_mec)

        self.action_export = QAction("Export CSV")
        self.action_export.triggered.connect(self._on_export)
        toolbar.addAction(self.action_export)

        toolbar.addSeparator()

        self.action_mock_toggle = QAction("Mock OFF")
        self.action_mock_toggle.triggered.connect(self._on_toggle_mock)
        toolbar.addAction(self.action_mock_toggle)

        self.action_daylight = QAction("Daylight")
        self.action_daylight.setCheckable(True)
        self.action_daylight.triggered.connect(self._on_toggle_daylight)
        toolbar.addAction(self.action_daylight)

    def _setup_central_area(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(4, 4, 4, 4)

        self.three_d = ThreeDVisualizer()

        plot_grid = QWidget()
        grid = QGridLayout(plot_grid)
        grid.setSpacing(4)

        self.alt_plot = AltitudePlot()
        self.volt_plot = VoltagePlot()
        self.curr_plot = CurrentPlot()
        self.accel_plot = AccelPlot()
        self.gyro_plot = GyroPlot()

        grid.addWidget(self.alt_plot, 0, 0, 1, 2)
        grid.addWidget(self.volt_plot, 0, 2)
        grid.addWidget(self.curr_plot, 0, 3)
        grid.addWidget(self.accel_plot, 1, 0, 1, 4)
        grid.addWidget(self.gyro_plot, 2, 0, 1, 4)

        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)
        grid.setRowStretch(2, 1)
        grid.setColumnStretch(0, 2)
        grid.setColumnStretch(1, 2)
        grid.setColumnStretch(2, 1)
        grid.setColumnStretch(3, 1)

        main_layout.addWidget(plot_grid)

    def _setup_right_dock(self) -> None:
        dock = QDockWidget("3D Simulation", self)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)
        dock.setWidget(self.three_d)
        dock.setMinimumWidth(320)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

    def _setup_left_dock(self) -> None:
        dock = QDockWidget("Resources", self)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.resources_tree = ResourcesTree()
        dock.setWidget(self.resources_tree)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)

        self._cmd_sender_widget = self.resources_tree._cmd_widget
        self.resources_tree.setItemWidget(self.resources_tree._commands_item, 0, self._cmd_sender_widget)
        self._cmd_sender_widget.show()

        self.resources_tree.btn_cal.clicked.connect(self._on_cal)
        self.resources_tree.btn_sim.clicked.connect(self._on_sim_tree)
        self.resources_tree.btn_mec.clicked.connect(self._on_mec)
        self.resources_tree.btn_cx.clicked.connect(self._on_cx)
        self.resources_tree.btn_st.clicked.connect(self._on_st)

    def _setup_bottom_dock(self) -> None:
        dock = QDockWidget("Console", self)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)

        self.console = MessageConsole()
        self.packet_monitor = PacketMonitor()

        layout.addWidget(self.console, 3)
        layout.addWidget(self.packet_monitor, 1)

        dock.setWidget(container)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)

    def _wire_signals(self) -> None:
        self.telemetry_engine.packet_received.connect(self._on_packet_received)
        self.telemetry_engine.status_message.connect(self.console.log)
        self.telemetry_engine.serial_error.connect(self._on_serial_error)
        self.telemetry_engine.connection_result.connect(self._on_connection_result)
        self.command_sender.command_to_send.connect(self.telemetry_engine.write_command)
        self.simulation_engine.pressure_uplink.connect(self._on_pressure_uplink)
        self.simulation_engine.status_message.connect(self.console.log)
        self.simulation_engine.csv_loaded.connect(self._on_csv_loaded)

    def _start_refresh_timer(self) -> None:
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_ui)
        self._refresh_timer.start(30)

    def _refresh_ui(self) -> None:
        self.three_d.view.update()

    def _on_packet_received(self, packet: TelemetryPacket) -> None:
        self.data_logger.append(packet)
        self.resources_tree.update_telemetry(packet)
        self.packet_monitor.update_counts(
            self.data_logger.packets_received,
            self.data_logger.packets_lost,
        )

        t = float(packet.mission_time)
        self.alt_plot.append("Altitude", t, packet.altitude)
        self.volt_plot.append("Voltage", t, packet.voltage)
        self.curr_plot.append("Current", t, packet.current)
        self.accel_plot.append("Accel_R", t, packet.accel_r)
        self.accel_plot.append("Accel_P", t, packet.accel_p)
        self.accel_plot.append("Accel_Y", t, packet.accel_y)
        self.gyro_plot.append("Gyro_R", t, packet.gyro_r)
        self.gyro_plot.append("Gyro_P", t, packet.gyro_p)
        self.gyro_plot.append("Gyro_Y", t, packet.gyro_y)

        self.three_d.update_orientation(packet.gyro_r, packet.gyro_p, packet.gyro_y, packet.altitude)

        if packet.cmd_echo:
            self.console.log(f"[ECHO] {packet.cmd_echo}")

    def _on_serial_error(self, msg: str) -> None:
        self.console.log(msg)
        self.resources_tree.set_port_disconnected()

    def _on_connect(self) -> None:
        if self._serial_port_name:
            self.telemetry_engine.stop_telemetry()
            self.telemetry_engine.set_source(True)
            self._serial_port_name = None
            self.action_connect.setText("Connect")
            self.console.log("[CFC] Disconnected")
            self.resources_tree.set_port_disconnected()
            return

        ports = self.telemetry_engine.available_ports()
        if not ports:
            QMessageBox.warning(self, "No Ports", "No serial ports found. Using Mock mode.")
            self._on_toggle_mock()
            return

        port = ports[0]
        if len(ports) > 1:
            dialog = PortDialog(ports, self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            port = dialog.selected_port()
            if not port:
                return

        self._pending_connect_port = port
        self.telemetry_engine.connect_serial(port)

    def _on_connection_result(self, success: bool, port_name: str) -> None:
        if success:
            self._serial_port_name = port_name
            self.telemetry_engine.set_source(False)
            self.action_connect.setText("Disconnect")
            self.action_mock_toggle.setText("Mock OFF")
            self._mock_active = False
            self.telemetry_engine.start_telemetry()
        else:
            self._serial_port_name = None
        self._pending_connect_port = None

    def _on_toggle_mock(self) -> None:
        self._mock_active = not self._mock_active
        self.telemetry_engine.set_source(self._mock_active)
        self.action_mock_toggle.setText("Mock ON" if self._mock_active else "Mock OFF")
        if self._mock_active:
            self.telemetry_engine.start_telemetry()

    def _on_toggle_daylight(self) -> None:
        self._daylight = self.action_daylight.isChecked()
        app = QApplication.instance()
        if self._daylight:
            app.setStyleSheet(LIGHT_STYLESHEET)
            self._apply_daylight_overrides()
        else:
            app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt6())
            self._apply_dark_overrides()

    def _apply_daylight_overrides(self) -> None:
        self.alt_plot.set_daylight(True)
        self.volt_plot.set_daylight(True)
        self.curr_plot.set_daylight(True)
        self.accel_plot.set_daylight(True)
        self.gyro_plot.set_daylight(True)
        self.three_d.set_daylight(True)
        self.console.set_daylight(True)
        self.packet_monitor.set_daylight(True)

    def _apply_dark_overrides(self) -> None:
        self.alt_plot.set_daylight(False)
        self.volt_plot.set_daylight(False)
        self.curr_plot.set_daylight(False)
        self.accel_plot.set_daylight(False)
        self.gyro_plot.set_daylight(False)
        self.three_d.set_daylight(False)
        self.console.set_daylight(False)
        self.packet_monitor.set_daylight(False)

    def _on_st(self) -> None:
        import time
        mission_time = int(time.time())
        cmd = CommandBuilder.st_time(TEAM_ID, mission_time)
        self.command_sender.command_to_send.emit(cmd)

    def _on_cal(self) -> None:
        cmd = CommandBuilder.cal(TEAM_ID)
        self.command_sender.command_to_send.emit(cmd)

    def _on_sim(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Pressure CSV", "", "CSV Files (*.csv)"
        )
        if not path:
            return
        self._pending_sim_path = path
        self.simulation_engine.load_csv(path)

    def _on_csv_loaded(self, success: bool, path: str) -> None:
        if success:
            enable_cmd = CommandBuilder.sim(TEAM_ID, "ENABLE")
            self.command_sender.command_to_send.emit(enable_cmd)
            self.simulation_engine.start_simulation()
            activate_cmd = CommandBuilder.sim(TEAM_ID, "ACTIVATE")
            self.command_sender.command_to_send.emit(activate_cmd)
            self.console.log(f"[SIM] Loaded {path}, started simulation")
        self._pending_sim_path = None

    def _on_sim_tree(self) -> None:
        self._on_sim()

    def _on_mec(self) -> None:
        cmd = CommandBuilder.mec(TEAM_ID, "1", "ON")
        self.command_sender.command_to_send.emit(cmd)

    def _on_cx(self) -> None:
        btn = self.resources_tree.btn_cx
        state = "OFF" if "ON" in btn.text() else "ON"
        btn.setText(f"CX {state}")
        cmd = CommandBuilder.cx(TEAM_ID, state)
        self.command_sender.command_to_send.emit(cmd)

    def _on_pressure_uplink(self, pressure: float) -> None:
        cmd = CommandBuilder.simp(TEAM_ID, pressure)
        self.command_sender.command_to_send.emit(cmd)

    def _on_export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export CSV",
            f"Flight_{TEAM_ID}.csv",
            "CSV Files (*.csv)",
        )
        if not path:
            return
        self.data_logger.export_csv(path, TEAM_ID)
        self.console.log(f"[CFC] Exported session to {path}")

    def closeEvent(self, event) -> None:
        self.telemetry_engine.stop()
        self.telemetry_engine.quit()
        self.telemetry_engine.wait(2000)
        self.simulation_engine.stop_simulation()
        self.simulation_engine.quit()
        self.simulation_engine.wait(2000)
        super().closeEvent(event)
