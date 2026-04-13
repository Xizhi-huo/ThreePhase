from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from domain.assessment import AssessmentEvent, AssessmentSession


@dataclass(frozen=True)
class StepProgressSnapshot:
    current_step: int
    ready_for_step5: bool
    block_before_step5: bool
    should_emit_assessment_gate_event: bool
    should_show_blackbox_required_dialog: bool
    random_fault_guess_required: bool
    assessment_result_ready: bool



class AssessmentCoordinator:
    def __init__(self, ctrl):
        self._ctrl = ctrl

    def start_assessment_session(self, scene_id: str, preset_mode: str = 'specified'):
        if not self._ctrl.should_record_assessment_metrics():
            self._ctrl.assessment_session = None
            return
        now = datetime.now().isoformat(timespec='seconds')
        session_id = f"ASM-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        fault_selection_mode = 'random' if preset_mode == 'random' else 'specified'
        self._ctrl.assessment_session = AssessmentSession(
            session_id=session_id,
            scene_id=scene_id,
            mode=self._ctrl.test_flow_mode,
            started_at=now,
            fault_selection_mode=fault_selection_mode,
        )
        self.append_assessment_event(
            'assessment_started',
            scene_id=scene_id,
            mode=self._ctrl.test_flow_mode,
            fault_selection_mode=fault_selection_mode,
        )


    def append_assessment_event(self, event_type: str, step: int = 0, **payload):
        if not self._ctrl.should_record_assessment_metrics():
            return
        session = self._ctrl.assessment_session
        if session is None or session.finished_at is not None:
            return
        session.events.append(
            AssessmentEvent(
                event_type=event_type,
                timestamp=datetime.now().isoformat(timespec='seconds'),
                step=step,
                payload=dict(payload),
            )
        )



    

    def mark_fault_detected(self, step: int, source: str, **payload) -> bool:
        fc = self._ctrl.sim_state.fault_config
        if not fc.active or fc.repaired:
            return False

        fc.detected = True
        self._ctrl._last_fault_detected = True

        if not self._ctrl.should_record_assessment_metrics():
            return True

        session = self._ctrl.assessment_session
        if session is None or session.finished_at is not None:
            return True

        payload = dict(payload)
        payload.setdefault('scene_id', fc.scenario_id)
        payload['source'] = source

        existing = None
        for event in session.events:
            if event.event_type == 'fault_detected':
                existing = event
                break

        if existing is None:
            self.append_assessment_event('fault_detected', step=step, **payload)
            return True

        if step > 0 and (existing.step <= 0 or existing.step > step):
            existing.step = step
        existing.payload.update(payload)
        return True

    def capture_assessment_state_snapshot(self) -> Dict[str, Any]:
        return {
            'loop_records': deepcopy(self._ctrl.loop_test_state.records),
            'voltage_records': deepcopy(self._ctrl.pt_voltage_check_state.records),
            'phase_records': deepcopy(self._ctrl.pt_phase_check_state.records),
            'pt_exam_records': {
                1: deepcopy(self._ctrl.pt_exam_states[1].records),
                2: deepcopy(self._ctrl.pt_exam_states[2].records),
            },
            'completed': {
                'loop': bool(self._ctrl.loop_test_state.completed),
                'voltage': bool(self._ctrl.pt_voltage_check_state.completed),
                'phase': bool(self._ctrl.pt_phase_check_state.completed),
                'pt_exam_1': bool(self._ctrl.pt_exam_states[1].completed),
                'pt_exam_2': bool(self._ctrl.pt_exam_states[2].completed),
                'closure': bool(self.is_assessment_closed_loop_ready()),
            },
            'fault': {
                'active': bool(self._ctrl.sim_state.fault_config.active),
                'repaired': bool(self._ctrl.sim_state.fault_config.repaired),
                'detected': bool(self._ctrl.sim_state.fault_config.detected),
                'scene_id': self._ctrl.sim_state.fault_config.scenario_id,
            },
            'blackbox_orders': {
                'g1': list(self._ctrl.g1_blackbox_order),
                'g2': list(self._ctrl.g2_blackbox_order),
                'pt1_primary': list(self._ctrl.pt1_pri_blackbox_order),
                'pt1_secondary': list(self._ctrl.pt1_sec_blackbox_order),
            },
        }

    def finish_assessment_session(self):
        if not self._ctrl.should_auto_score_assessment():
            return None
        session = self._ctrl.assessment_session
        if session is None:
            return None
        if session.result is not None:
            return session.result
        if not session.state_snapshot:
            session.state_snapshot = self.capture_assessment_state_snapshot()
        self.append_assessment_event('assessment_finished')
        result = self._ctrl._assessment_svc.build_result(session)
        session.finished_at = result.finished_at
        session.result = result
        return result

    def requires_random_fault_identification(self, current_step: int) -> bool:
        session = self._ctrl.assessment_session
        if session is None or session.finished_at is not None:
            return False
        if not self._ctrl.is_assessment_mode():
            return False
        if session.fault_selection_mode != 'random':
            return False
        if session.fault_guess_submitted:
            return False
        if not session.scene_id:
            return False
        if current_step < 4:
            return False
        if not self._ctrl.assessment_ends_after_step4_closed_loop():
            return False
        return self.is_assessment_closed_loop_ready()

    def submit_random_fault_identification(self, guessed_scene_id: str) -> bool:
        session = self._ctrl.assessment_session
        if session is None:
            return False
        guessed_scene_id = (guessed_scene_id or '').strip()
        correct = bool(guessed_scene_id) and guessed_scene_id == session.scene_id
        session.fault_guess_scene_id = guessed_scene_id
        session.fault_guess_submitted = bool(guessed_scene_id)
        session.fault_guess_correct = correct
        self.append_assessment_event(
            'fault_guess_submitted',
            step=4,
            guessed_scene_id=guessed_scene_id,
            actual_scene_id=session.scene_id,
            correct=correct,
            fault_selection_mode=session.fault_selection_mode,
        )
        return correct

    def mark_assessment_result_shown(self):
        if self._ctrl.assessment_session is not None:
            self._ctrl.assessment_session.result_shown = True

    def is_assessment_closed_loop_ready(self) -> bool:
        if not (
            self._ctrl.is_loop_test_complete()
            and self._ctrl.is_pt_voltage_check_complete()
            and self._ctrl.is_pt_phase_check_complete()
            and self._ctrl.pt_exam_states[1].completed
            and self._ctrl.pt_exam_states[2].completed
        ):
            return False
        fc = self._ctrl.sim_state.fault_config
        if fc.active and self._ctrl.fault_has_repairable_wiring_targets():
            return fc.repaired
        return True

    def get_test_progress_snapshot(
        self,
        current_step: int,
        pre_step5_repair_triggered: bool,
    ) -> StepProgressSnapshot:
        ready_for_step5 = (
            self._ctrl.is_loop_test_complete()
            and self._ctrl.is_pt_voltage_check_complete()
            and self._ctrl.is_pt_phase_check_complete()
            and self._ctrl.pt_exam_states[1].completed
            and self._ctrl.pt_exam_states[2].completed
        )
        fc = self._ctrl.sim_state.fault_config
        block_before_step5 = (
            ready_for_step5
            and self._ctrl.should_block_step5_until_blackbox_fixed()
            and self._ctrl.has_unrepaired_wiring_fault()
            and fc.scenario_id not in ('E01', 'E02', 'E03')
        )
        should_emit_assessment_gate_event = (
            block_before_step5
            and self._ctrl.is_assessment_mode()
            and not pre_step5_repair_triggered
        )
        should_show_blackbox_required_dialog = (
            block_before_step5
            and self._ctrl.should_show_blackbox_required_dialog_before_step5()
            and not pre_step5_repair_triggered
        )
        assessment_result_ready = (
            self._ctrl.is_assessment_mode()
            and self._ctrl.assessment_ends_after_step4_closed_loop()
            and self.is_assessment_closed_loop_ready()
            and self._ctrl.assessment_session is not None
            and not self.requires_random_fault_identification(current_step)
            and not self._ctrl.assessment_session.result_shown
        )
        return StepProgressSnapshot(
            current_step=current_step,
            ready_for_step5=ready_for_step5,
            block_before_step5=block_before_step5,
            should_emit_assessment_gate_event=should_emit_assessment_gate_event,
            should_show_blackbox_required_dialog=should_show_blackbox_required_dialog,
            random_fault_guess_required=self.requires_random_fault_identification(current_step),
            assessment_result_ready=assessment_result_ready,
        )

    def finish_assessment_session_if_ready(self, current_step: int) -> Optional[object]:
        snapshot = self.get_test_progress_snapshot(current_step, pre_step5_repair_triggered=False)
        if not snapshot.assessment_result_ready:
            return None
        return self.finish_assessment_session()
