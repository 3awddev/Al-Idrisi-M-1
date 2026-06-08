from __future__ import annotations

import math
import random
import time


class MockGenerator:
    TEAM_ID = 1234

    def __init__(self) -> None:
        self.start_time = time.time()
        self.packet_count = 0
        self.mode = "NONE"
        self.state = "LAUNCH_WAIT"
        self.base_pressure = 101325.0
        self.altitude = 0.0
        self.voltage = 16.8
        self.latitude = 40.4432
        self.longitude = -79.9428
        self.released = False

    def generate(self, elapsed: float | None = None) -> str:
        if elapsed is None:
            elapsed = time.time() - self.start_time
        self.packet_count += 1

        alt = self._compute_altitude(elapsed)
        pres = self._compute_pressure(alt)
        temp = 20.0 - alt * 0.0065 + random.uniform(-0.5, 0.5)
        volt = max(12.0, self.voltage - elapsed * 0.0006 + random.uniform(-0.02, 0.02))
        curr = 0.2 + random.uniform(-0.01, 0.01)
        if self.released:
            curr += 0.1

        gyro = {
            "r": random.uniform(-2.0, 2.0),
            "p": random.uniform(-2.0, 2.0),
            "y": random.uniform(-2.0, 2.0),
        }
        accel = {
            "r": random.uniform(-1.0, 1.0),
            "p": random.uniform(-1.0, 1.0),
            "y": 9.81 + random.uniform(-0.2, 0.2),
        }

        gps_time = self._format_gps_time(elapsed)
        mode = self.mode or "NONE"
        state = self.state or "LAUNCH_WAIT"

        fields = [
            str(self.TEAM_ID),
            str(int(elapsed)),
            str(self.packet_count),
            mode,
            state,
            f"{alt:.2f}",
            f"{temp:.2f}",
            f"{pres:.2f}",
            f"{volt:.3f}",
            f"{curr:.3f}",
            f"{gyro['r']:.3f}",
            f"{gyro['p']:.3f}",
            f"{gyro['y']:.3f}",
            f"{accel['r']:.3f}",
            f"{accel['p']:.3f}",
            f"{accel['y']:.3f}",
            gps_time,
            f"{alt:.2f}",
            f"{self.latitude:.6f}",
            f"{self.longitude:.6f}",
            "10",
            "",
        ]
        return ",".join(fields)

    def _compute_altitude(self, t: float) -> float:
        if t < 30:
            alt = (t / 30.0) * 300.0
            self.state = "ASCENT"
            self.mode = "FLIGHT"
        elif t < 35:
            alt = 300.0 + random.uniform(-5, 5)
            self.state = "RELEASE"
            self.mode = "FLIGHT"
            self.released = True
        elif t < 120:
            progress = (t - 35) / 85.0
            alt = 300.0 * (1.0 - progress) + random.uniform(-2, 2)
            self.state = "DESCENT"
            self.mode = "FLIGHT"
        else:
            alt = random.uniform(-0.5, 0.5)
            self.state = "LANDED"
            self.mode = "IDLE"
        self.altitude = max(0.0, alt)
        return self.altitude

    def _compute_pressure(self, alt: float) -> float:
        return self.base_pressure * math.exp(-alt / 8500.0) + random.uniform(-10, 10)

    def _format_gps_time(self, elapsed: float) -> str:
        h = int(elapsed // 3600)
        m = int((elapsed % 3600) // 60)
        s = int(elapsed % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def reset(self) -> None:
        self.start_time = time.time()
        self.packet_count = 0
        self.released = False
        self.altitude = 0.0
        self.voltage = 16.8
        self.mode = "NONE"
        self.state = "LAUNCH_WAIT"
