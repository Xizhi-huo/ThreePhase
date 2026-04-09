from __future__ import annotations

from pathlib import Path

from services.physics_engine import PhysicsEngine
from tests.support.snapshots import assert_json_snapshot
from tests.support.stubs import (
    ControllerStub,
    apply_fault_e01,
    configure_loop_measurement_state,
)


SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


def _render_state_payload(render_state):
    return {
        "bus_live": render_state.bus_live,
        "bus_amp": render_state.bus_amp,
        "bus_source": render_state.bus_source,
        "bus_reference_gen": render_state.bus_reference_gen,
        "bus_status_msg": render_state.bus_status_msg,
        "bus_reference_msg": render_state.bus_reference_msg,
        "relay_msg": render_state.relay_msg,
        "relay_color": render_state.relay_color,
        "arb_msg": render_state.arb_msg,
        "arb_color": render_state.arb_color,
        "meter_reading": render_state.meter_reading,
        "meter_color": render_state.meter_color,
        "meter_voltage": render_state.meter_voltage,
        "meter_status": render_state.meter_status,
        "meter_nodes": render_state.meter_nodes,
        "meter_phase_match": render_state.meter_phase_match,
        "pt1_v": render_state.pt1_v,
        "pt2_v": render_state.pt2_v,
        "pt3_v": render_state.pt3_v,
        "brk1_text": render_state.brk1_text,
        "brk2_text": render_state.brk2_text,
        "plot_data": render_state.plot_data,
        "fixed_deg": render_state.fixed_deg,
    }


def _build_engine(ctrl: ControllerStub) -> PhysicsEngine:
    engine = PhysicsEngine(ctrl)
    engine.update_physics()
    return engine


def test_physics_engine_runs_without_ui():
    ctrl = ControllerStub()
    configure_loop_measurement_state(ctrl)
    engine = _build_engine(ctrl)
    render_state = engine.build_render_state()
    assert render_state.meter_reading
    assert render_state.plot_data


def test_physics_snapshot_normal():
    ctrl = ControllerStub()
    configure_loop_measurement_state(ctrl)
    engine = _build_engine(ctrl)
    assert_json_snapshot(
        SNAPSHOT_DIR / "physics_normal.json",
        _render_state_payload(engine.build_render_state()),
    )


def test_physics_snapshot_fault_e01():
    ctrl = ControllerStub()
    configure_loop_measurement_state(ctrl)
    apply_fault_e01(ctrl)
    engine = _build_engine(ctrl)
    assert_json_snapshot(
        SNAPSHOT_DIR / "physics_fault_E01.json",
        _render_state_payload(engine.build_render_state()),
    )
