from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, Iterable

import numpy as np

from domain.enums import BreakerPosition, SystemMode
from domain.models import FaultConfig, GeneratorState, SimulationState
from services.flow_mode_manager import FlowModeManager
from services.phase_order_resolver import PhaseOrderResolver
from domain.test_states import (
    LoopTestState,
    PtExamState,
    PtPhaseCheckState,
    PtVoltageCheckState,
    SyncTestState,
)


FIXED_NOW = "2026-04-09T12:00:00"


class ControllerStub:
    def __init__(
        self,
        *,
        sim_state: SimulationState | None = None,
        pt_phase_orders: Dict[str, list[str]] | None = None,
    ):
        self.sim_state = sim_state or make_sim_state()
        self.flow_mgr = FlowModeManager()
        self.pt_phase_orders = pt_phase_orders or {
            "PT1": ["A", "B", "C"],
            "PT2": ["A", "B", "C"],
            "PT3": ["A", "B", "C"],
        }
        self.g1_blackbox_order = ["A", "B", "C"]
        self.g2_blackbox_order = ["A", "B", "C"]
        self.pt1_pri_blackbox_order = ["A", "B", "C"]
        self.pt1_sec_blackbox_order = ["A", "B", "C"]
        self.pt2_sec_blackbox_order = ["A", "B", "C"]
        self.phase_resolver = PhaseOrderResolver(
            sim_state=self.sim_state,
            get_pt_phase_orders=lambda: self.pt_phase_orders,
            get_g1_blackbox_order=lambda: self.g1_blackbox_order,
            get_g2_blackbox_order=lambda: self.g2_blackbox_order,
        )
        self.loop_svc = self
        self.pt_voltage_svc = self
        self.pt_phase_svc = self
        self.pt_exam_svc = self
        self.sync_svc = self

        self.loop_test_state = LoopTestState()
        self.pt_voltage_check_state = PtVoltageCheckState()
        self.pt_phase_check_state = PtPhaseCheckState()
        self.pt_exam_states = {1: PtExamState(), 2: PtExamState()}
        self.sync_test_state = SyncTestState()

        self.detected_fault_events: list[dict[str, Any]] = []
        self.queued_accident_dialogs: list[str] = []

    @property
    def test_flow_mode(self) -> str:
        return self.flow_mgr.test_flow_mode

    @test_flow_mode.setter
    def test_flow_mode(self, value: str):
        self.flow_mgr.test_flow_mode = value

    def flow_policy(self):
        return self.flow_mgr.flow_policy()

    def flow_policy_flag(self, name: str) -> bool:
        return self.flow_mgr.flow_policy_flag(name)

    def is_teaching_mode(self) -> bool:
        return self.flow_mgr.is_teaching_mode()

    def is_engineering_mode(self) -> bool:
        return self.flow_mgr.is_engineering_mode()

    def should_show_diagnostic_hints(self) -> bool:
        return self.flow_mgr.should_show_diagnostic_hints()

    def mark_fault_detected(self, step: int, source: str, **payload) -> bool:
        self.sim_state.fault_config.detected = True
        self.detected_fault_events.append(
            {"step": step, "source": source, "payload": dict(payload)}
        )
        return True

    def resolve_pt_node_plot_key(self, node_name: str) -> str | None:
        return self.phase_resolver.resolve_pt_node_plot_key(node_name)

    def get_pt_phase_sequence(self, pt_name: str) -> str:
        return self.phase_resolver.get_pt_phase_sequence(pt_name)

    def resolve_loop_node_phase(self, node_name: str) -> str:
        return self.phase_resolver.resolve_loop_node_phase(node_name)

    def is_sync_test_active(self) -> bool:
        return self.sync_test_state.started and not self.sync_test_state.completed

    def is_sync_test_complete(self) -> bool:
        return self.sync_test_state.completed

    def get_sync_test_steps(self):
        return []

    def is_sync_test_rounds_done(self) -> bool:
        return self.sync_test_state.completed

    def is_gen_synced(self, follower, master, freq_tol=0.5, amp_tol=500.0):
        return True

    def queue_accident_dialog(self, scene_id: str):
        self.queued_accident_dialogs.append(scene_id)

    def is_loop_test_complete(self) -> bool:
        return self.loop_test_state.completed

    def is_pt_voltage_check_complete(self) -> bool:
        return self.pt_voltage_check_state.completed

    def is_pt_phase_check_complete(self) -> bool:
        return self.pt_phase_check_state.completed

    def get_pt_exam_steps(self, gen_id: int):
        return []

    def is_pt_exam_recorded(self, gen_id: int) -> bool:
        return self.pt_exam_states[gen_id].completed

    def _get_current_pt_phase_match(self, gen_id: int):
        return None

    def _expected_pt_probe_pair(self, gen_id: int, gen_phase: str, bus_phase: str):
        return gen_phase, bus_phase


def make_generator(
    *,
    freq: float = 50.0,
    amp: float = 10500.0,
    phase_deg: float = 0.0,
    mode: str = "manual",
    running: bool = False,
    breaker_closed: bool = False,
    breaker_position: str = BreakerPosition.DISCONNECTED,
    actual_amp: float | None = None,
) -> GeneratorState:
    return GeneratorState(
        freq=freq,
        amp=amp,
        phase_deg=phase_deg,
        mode=mode,
        running=running,
        breaker_closed=breaker_closed,
        breaker_position=breaker_position,
        actual_amp=amp if actual_amp is None else actual_amp,
    )


def make_sim_state() -> SimulationState:
    return SimulationState(
        gen1=make_generator(),
        gen2=make_generator(phase_deg=5.0),
        system_mode=SystemMode.ISOLATED_BUS,
        sim_speed=0.3,
    )


def configure_loop_measurement_state(ctrl: ControllerStub):
    sim = ctrl.sim_state
    sim.loop_test_mode = True
    sim.multimeter_mode = True
    sim.grounding_mode = "断开"
    sim.probe1_node = "Loop_G1_A"
    sim.probe2_node = "Loop_G2_A"
    sim.gen1.breaker_closed = True
    sim.gen2.breaker_closed = True
    sim.gen1.breaker_position = BreakerPosition.TEST
    sim.gen2.breaker_position = BreakerPosition.TEST


def apply_fault_e01(ctrl: ControllerStub):
    ctrl.sim_state.fault_config = FaultConfig(
        scenario_id="E01",
        active=True,
        detected=False,
        repaired=False,
        params={"pt1_phase_order": ["B", "A", "C"], "g1_loop_swap": ("A", "B")},
    )
    ctrl.pt_phase_orders["PT1"] = ["B", "A", "C"]
    ctrl.pt_phase_orders["PT2"] = ["B", "A", "C"]
    ctrl.g1_blackbox_order = ["B", "A", "C"]


def normalize_snapshot_value(value: Any) -> Any:
    if is_dataclass(value):
        return normalize_snapshot_value(asdict(value))
    if isinstance(value, np.ndarray):
        return [normalize_snapshot_value(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return normalize_snapshot_value(value.item())
    if isinstance(value, float):
        return round(value, 4)
    if isinstance(value, dict):
        return {
            str(key): normalize_snapshot_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple, set)):
        items: Iterable[Any] = value
        if isinstance(value, set):
            items = sorted(value, key=str)
        return [normalize_snapshot_value(item) for item in items]
    if isinstance(value, Path):
        return str(value)
    return value
