from dataclasses import dataclass
from typing import Optional

from config_qt5 import BreakerPosition, SystemMode


@dataclass
class GeneratorState:
    freq: float
    amp: float
    phase_deg: float
    mode: str = "stop"
    running: bool = False
    breaker_closed: bool = False
    breaker_position: str = BreakerPosition.DISCONNECTED
    cmd_close: bool = False
    actual_amp: float = 0.0


@dataclass
class SimulationState:
    gen1: GeneratorState
    gen2: GeneratorState
    system_mode: str = SystemMode.ISOLATED_BUS
    rotate_phasor: bool = True
    sim_speed: float = 0.3
    droop_enabled: bool = False
    sync_gain: float = 1.0
    gov_gain: float = 0.75
    first_start_time: int = 10
    multimeter_mode: bool = False
    fault_reverse_bc: bool = False
    remote_start_signal: bool = False
    paused: bool = False
    auto_sync_active: bool = False
    sync_target: Optional[str] = None
    feeder_position: str = BreakerPosition.DISCONNECTED
    feeder_closed: bool = False
    grounding_mode: str = "小电阻接地"
    probe1_node: Optional[str] = None
    probe2_node: Optional[str] = None