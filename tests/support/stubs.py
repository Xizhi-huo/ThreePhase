from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, Iterable

import numpy as np

from domain.assessment import AssessmentEvent, AssessmentSession
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
        assessment_closed_loop_ready: bool = False,
    ):
        self.sim_state = sim_state or make_sim_state()
        self._flow_mgr = FlowModeManager()
        self.pt_phase_orders = pt_phase_orders or {
            "PT1": ["A", "B", "C"],
            "PT2": ["A", "B", "C"],
            "PT3": ["A", "B", "C"],
        }
        self.g1_blackbox_order = ["A", "B", "C"]
        self.g2_blackbox_order = ["A", "B", "C"]
        self.pt1_pri_blackbox_order = ["A", "B", "C"]
        self.pt1_sec_blackbox_order = ["A", "B", "C"]
        self.phase_resolver = PhaseOrderResolver(self)
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

        self.assessment_closed_loop_ready = assessment_closed_loop_ready
        self.detected_fault_events: list[dict[str, Any]] = []
        self.queued_accident_dialogs: list[str] = []

    @property
    def test_flow_mode(self) -> str:
        return self._flow_mgr.test_flow_mode

    @test_flow_mode.setter
    def test_flow_mode(self, value: str):
        self._flow_mgr.test_flow_mode = value

    def flow_policy(self):
        return self._flow_mgr.flow_policy()

    def flow_policy_flag(self, name: str) -> bool:
        return self._flow_mgr.flow_policy_flag(name)

    def is_teaching_mode(self) -> bool:
        return self._flow_mgr.is_teaching_mode()

    def is_engineering_mode(self) -> bool:
        return self._flow_mgr.is_engineering_mode()

    def is_assessment_mode(self) -> bool:
        return self._flow_mgr.is_assessment_mode()

    def should_show_diagnostic_hints(self) -> bool:
        return self._flow_mgr.should_show_diagnostic_hints()

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

    def _is_gen_synced(self, follower, master, freq_tol=0.5, amp_tol=500.0):
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

    def is_assessment_closed_loop_ready(self) -> bool:
        return self.assessment_closed_loop_ready


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


def build_full_records() -> dict[str, Any]:
    return {
        "loop_records": {
            "A": {"status": "ok", "reading": "通路"},
            "B": {"status": "ok", "reading": "通路"},
            "C": {"status": "ok", "reading": "通路"},
        },
        "voltage_records": {
            "PT1_AB": {"reading": 184.5},
            "PT1_BC": {"reading": 184.5},
            "PT1_CA": {"reading": 184.5},
            "PT2_AB": {"reading": 105.0},
            "PT2_BC": {"reading": 105.0},
            "PT2_CA": {"reading": 105.0},
            "PT3_AB": {"reading": 184.5},
            "PT3_BC": {"reading": 184.5},
            "PT3_CA": {"reading": 184.5},
        },
        "phase_records": {
            "PT1_A": {"reading": "正序"},
            "PT1_B": {"reading": "正序"},
            "PT1_C": {"reading": "正序"},
            "PT3_A": {"reading": "正序"},
            "PT3_B": {"reading": "正序"},
            "PT3_C": {"reading": "正序"},
        },
        "pt_exam_records": {
            1: {f"{g}{b}": {"reading": 0.0} for g in "ABC" for b in "ABC"},
            2: {f"{g}{b}": {"reading": 0.0} for g in "ABC" for b in "ABC"},
        },
        "completed": {
            "loop": True,
            "voltage": True,
            "phase": True,
            "pt_exam_1": True,
            "pt_exam_2": True,
            "closure": True,
        },
    }


def build_normal_assessment_session() -> AssessmentSession:
    session = AssessmentSession(
        session_id="ASM-SNAPSHOT-NORMAL",
        scene_id="",
        mode="assessment",
        started_at="2026-04-09T11:55:00",
    )
    session.events.extend(
        [
            AssessmentEvent("assessment_started", "2026-04-09T11:55:00"),
            AssessmentEvent("step_entered", "2026-04-09T11:55:10", step=1),
            AssessmentEvent("step_entered", "2026-04-09T11:56:00", step=2),
            AssessmentEvent("step_entered", "2026-04-09T11:57:00", step=3),
            AssessmentEvent("step_entered", "2026-04-09T11:58:00", step=4),
            AssessmentEvent("step_finalize_attempted", "2026-04-09T11:58:30", step=4, payload={"allowed": True}),
        ]
    )
    session.state_snapshot = build_full_records()
    session.state_snapshot["fault"] = {"repaired": False}
    return session


def build_random_fault_assessment_session() -> AssessmentSession:
    session = AssessmentSession(
        session_id="ASM-SNAPSHOT-RANDOM",
        scene_id="E02",
        mode="assessment",
        started_at="2026-04-09T11:50:00",
        fault_selection_mode="random",
        fault_guess_scene_id="E01",
        fault_guess_submitted=True,
        fault_guess_correct=False,
    )
    session.events.extend(
        [
            AssessmentEvent("assessment_started", "2026-04-09T11:50:00", payload={"fault_selection_mode": "random"}),
            AssessmentEvent("step_entered", "2026-04-09T11:50:10", step=1),
            AssessmentEvent("fault_detected", "2026-04-09T11:50:20", step=1, payload={"scene_id": "E02"}),
            AssessmentEvent("step_entered", "2026-04-09T11:51:00", step=2),
            AssessmentEvent("step_entered", "2026-04-09T11:52:00", step=3),
            AssessmentEvent("step_entered", "2026-04-09T11:53:00", step=4),
            AssessmentEvent("blackbox_opened", "2026-04-09T11:53:20", step=4, payload={"target": "G2"}),
            AssessmentEvent("blackbox_swap", "2026-04-09T11:53:40", step=4, payload={"target": "G2", "layer": "terminal"}),
            AssessmentEvent(
                "blackbox_confirm_attempted",
                "2026-04-09T11:54:00",
                step=4,
                payload={"target": "G2", "layers": ["terminal"], "success": True},
            ),
            AssessmentEvent("fault_repaired", "2026-04-09T11:54:20", step=4, payload={"scene_id": "E02"}),
            AssessmentEvent("step_finalize_attempted", "2026-04-09T11:54:30", step=4, payload={"allowed": True}),
        ]
    )
    session.state_snapshot = build_full_records()
    session.state_snapshot["fault"] = {"repaired": True}
    return session


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
