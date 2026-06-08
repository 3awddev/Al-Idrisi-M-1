from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal


class CommandBuilder:
    @staticmethod
    def cal(team_id: int) -> str:
        return f"CMD,{team_id},CAL"

    @staticmethod
    def sim(team_id: int, action: str) -> str:
        return f"CMD,{team_id},SIM,{action.upper()}"

    @staticmethod
    def simp(team_id: int, pressure: float) -> str:
        return f"CMD,{team_id},SIMP,{pressure:.2f}"

    @staticmethod
    def st_time(team_id: int, mission_time: int) -> str:
        return f"CMD,{team_id},ST,{mission_time}"

    @staticmethod
    def st_gps(team_id: int) -> str:
        return f"CMD,{team_id},ST,GPS"

    @staticmethod
    def mec(team_id: int, device: str, state: str) -> str:
        return f"CMD,{team_id},MEC,{device},{state.upper()}"

    @staticmethod
    def cx(team_id: int, state: str) -> str:
        return f"CMD,{team_id},CX,{state.upper()}"


class CommandSender(QObject):
    command_to_send = pyqtSignal(str)
