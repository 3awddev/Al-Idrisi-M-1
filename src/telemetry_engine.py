from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal, QTimer
from PyQt6.QtSerialPort import QSerialPort, QSerialPortInfo

from src.mock_generator import MockGenerator
from src.telemetry_packet import TelemetryPacket


class TelemetryEngine(QThread):
    packet_received = pyqtSignal(object)
    status_message = pyqtSignal(str)
    serial_error = pyqtSignal(str)
    connection_result = pyqtSignal(bool, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._use_mock = False
        self._running = False

    def set_source(self, use_mock: bool) -> None:
        self._use_mock = use_mock

    def start_telemetry(self) -> None:
        self._running = True

    def stop_telemetry(self) -> None:
        self._running = False

    def connect_serial(self, port_name: str, baud: int = 115200) -> None:
        self._connect_args = (port_name, baud)

    def write_command(self, cmd: str) -> None:
        self._pending_cmd = cmd

    def available_ports(self) -> list[str]:
        return [p.portName() for p in QSerialPortInfo.availablePorts()]

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        self._serial = QSerialPort()
        self._serial.readyRead.connect(self._on_ready_read)
        self._serial.errorOccurred.connect(self._on_error)

        self._mock_gen = MockGenerator()
        self._mock_tick = 0
        self._buffer = b""
        self._pending_cmd: str | None = None
        self._connect_args: tuple[str, int] | None = None
        self._serial_port_open = False

        poll_timer = QTimer()
        poll_timer.timeout.connect(self._poll_controls)
        poll_timer.start(50)

        self.exec()

        poll_timer.stop()
        self._serial.close()

    def _poll_controls(self) -> None:
        if self._connect_args is not None:
            port, baud = self._connect_args
            self._connect_args = None
            self._do_connect(port, baud)

        if self._pending_cmd is not None:
            cmd = self._pending_cmd
            self._pending_cmd = None
            self._do_write(cmd)

        self._mock_tick += 1
        if self._running and self._use_mock and self._mock_tick >= 20:
            self._mock_tick = 0
            self._emit_mock()

    def _do_connect(self, port_name: str, baud: int) -> None:
        if self._serial.isOpen():
            self._serial.close()
            self._serial_port_open = False
        self._serial.setPortName(port_name)
        self._serial.setBaudRate(baud)
        opened = self._serial.open(QSerialPort.OpenModeFlag.ReadWrite)
        self._serial_port_open = opened
        if opened:
            self.status_message.emit(f"[CFC] Connected to {port_name} @ {baud}")
        else:
            self.serial_error.emit(f"[CFC] Failed to open {port_name}")
        self.connection_result.emit(opened, port_name)

    def _do_write(self, cmd: str) -> None:
        if self._use_mock:
            self.status_message.emit(f"[CFC] Mock CMD: {cmd}")
            return
        if self._serial_port_open:
            data = (cmd + "\n").encode("ascii")
            self._serial.write(data)
            self.status_message.emit(f"[CFC] TX: {cmd}")

    def _on_ready_read(self) -> None:
        if self._use_mock:
            return
        data = self._serial.readAll().data()
        self._buffer += data
        while b"\n" in self._buffer:
            line, self._buffer = self._buffer.split(b"\n", 1)
            self._parse_and_emit(line.decode("ascii", errors="replace"))

    def _on_error(self, error: QSerialPort.SerialError) -> None:
        self.serial_error.emit(f"[CFC] Serial error: {error}")

    def _emit_mock(self) -> None:
        if not self._running:
            return
        line = self._mock_gen.generate()
        self._parse_and_emit(line)

    def _parse_and_emit(self, line: str) -> None:
        packet = TelemetryPacket.from_csv(line)
        if packet is not None:
            self.packet_received.emit(packet)
