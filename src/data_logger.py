from __future__ import annotations

import pandas as pd
from PyQt6.QtCore import QObject, pyqtSignal

from src.telemetry_packet import TelemetryPacket


class DataLogger(QObject):
    packet_appended = pyqtSignal(TelemetryPacket)

    def __init__(self, max_rows: int = 600, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.max_rows = max_rows
        self._df = pd.DataFrame(columns=TelemetryPacket.HEADER)
        self.packets_received = 0
        self.packets_lost = 0
        self._last_seq = -1

    @property
    def df(self) -> pd.DataFrame:
        return self._df

    def append(self, packet: TelemetryPacket) -> None:
        self._check_sequence(packet)
        self._df = pd.concat(
            [self._df, pd.DataFrame([packet.to_row()], columns=TelemetryPacket.HEADER)],
            ignore_index=True,
        )
        if len(self._df) > self.max_rows:
            self._df = self._df.iloc[-self.max_rows:].reset_index(drop=True)
        self.packets_received += 1
        self.packet_appended.emit(packet)

    def _check_sequence(self, packet: TelemetryPacket) -> None:
        expected = self._last_seq + 1
        if self._last_seq >= 0 and packet.packet_count != expected:
            gap = packet.packet_count - expected
            if gap > 0:
                self.packets_lost += gap
        self._last_seq = packet.packet_count

    def export_csv(self, path: str, team_id: int) -> None:
        full_df = self._df.copy()
        full_df.to_csv(path, index=False)
