from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class TelemetryPacket:
    team_id: int
    mission_time: int
    packet_count: int
    mode: str
    state: str
    altitude: float
    temperature: float
    pressure: float
    voltage: float
    current: float
    gyro_r: float
    gyro_p: float
    gyro_y: float
    accel_r: float
    accel_p: float
    accel_y: float
    gps_time: str
    gps_altitude: float
    gps_latitude: float
    gps_longitude: float
    gps_sats: int
    cmd_echo: str

    @staticmethod
    def from_csv(line: str) -> Optional["TelemetryPacket"]:
        line = line.strip()
        if not line:
            return None
        parts = line.split(",")
        if len(parts) < 22:
            return None
        try:
            return TelemetryPacket(
                team_id=int(parts[0]),
                mission_time=int(parts[1]),
                packet_count=int(parts[2]),
                mode=parts[3].strip(),
                state=parts[4].strip(),
                altitude=float(parts[5]),
                temperature=float(parts[6]),
                pressure=float(parts[7]),
                voltage=float(parts[8]),
                current=float(parts[9]),
                gyro_r=float(parts[10]),
                gyro_p=float(parts[11]),
                gyro_y=float(parts[12]),
                accel_r=float(parts[13]),
                accel_p=float(parts[14]),
                accel_y=float(parts[15]),
                gps_time=parts[16].strip(),
                gps_altitude=float(parts[17]),
                gps_latitude=float(parts[18]),
                gps_longitude=float(parts[19]),
                gps_sats=int(parts[20]),
                cmd_echo=parts[21].strip(),
            )
        except (ValueError, IndexError):
            return None

    HEADER = [
        "TEAM_ID", "MISSION_TIME", "PACKET_COUNT", "MODE", "STATE",
        "ALTITUDE", "TEMPERATURE", "PRESSURE", "VOLTAGE", "CURRENT",
        "GYRO_R", "GYRO_P", "GYRO_Y", "ACCEL_R", "ACCEL_P", "ACCEL_Y",
        "GPS_TIME", "GPS_ALTITUDE", "GPS_LATITUDE", "GPS_LONGITUDE",
        "GPS_SATS", "CMD_ECHO",
    ]

    def to_row(self) -> list:
        return [
            self.team_id, self.mission_time, self.packet_count, self.mode,
            self.state, self.altitude, self.temperature, self.pressure,
            self.voltage, self.current, self.gyro_r, self.gyro_p,
            self.gyro_y, self.accel_r, self.accel_p, self.accel_y,
            self.gps_time, self.gps_altitude, self.gps_latitude,
            self.gps_longitude, self.gps_sats, self.cmd_echo,
        ]
