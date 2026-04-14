from __future__ import annotations

from dataclasses import dataclass

from domain.assessment import AssessmentEventType


@dataclass(frozen=True)
class BlackboxRepairOutcome:
    target: str
    component_correct: bool
    fault_cleared: bool
    message: str
    message_color: str
    disable_repair_button: bool = False


class BlackboxRepairHandler:
    def __init__(self, ctrl):
        self._ctrl = ctrl

    def get_blackbox_runtime_state(self, target: str) -> dict:
        fault_active = bool(self._ctrl.sim_state.fault_config.active and not self._ctrl.sim_state.fault_config.repaired)
        if target == 'G1':
            return {
                'fault_active': fault_active,
                'order': list(
                    self._ctrl.g1_blackbox_order
                    if fault_active else self._ctrl.pt_phase_orders.get('PT2', ['A', 'B', 'C'])
                ),
                'repair_target': 'G1' if self._ctrl.flow_mgr.can_repair_in_blackbox() else None,
            }
        if target == 'G2':
            return {
                'fault_active': fault_active,
                'order': list(
                    self._ctrl.g2_blackbox_order
                    if fault_active else self._ctrl.pt_phase_orders.get('PT3', ['A', 'B', 'C'])
                ),
                'repair_target': 'G2' if self._ctrl.flow_mgr.can_repair_in_blackbox() else None,
            }
        if target == 'PT1':
            if fault_active:
                pri_input_order = list(self._ctrl.g1_blackbox_order)
                pri_order = list(self._ctrl.pt1_pri_blackbox_order)
                sec_order = list(self._ctrl.pt1_sec_blackbox_order)
            else:
                pri_input_order = ['A', 'B', 'C']
                pri_order = ['A', 'B', 'C']
                sec_order = ['A', 'B', 'C']
            return {
                'fault_active': fault_active,
                'pri_input_order': pri_input_order,
                'pri_order': pri_order,
                'sec_order': sec_order,
                'repair_target': 'PT1' if self._ctrl.flow_mgr.can_repair_in_blackbox() else None,
            }
        if target == 'PT3':
            pri_input_order = ['A', 'B', 'C']
            if self._ctrl.sim_state.fault_reverse_bc:
                pri_input_order = ['A', 'C', 'B']
            return {
                'fault_active': fault_active,
                'pri_input_order': pri_input_order,
                'pri_order': ['A', 'B', 'C'],
                'sec_order': list(self._ctrl.pt_phase_orders.get('PT3', ['A', 'B', 'C'])),
                'repair_target': 'PT3' if self._ctrl.flow_mgr.can_repair_in_blackbox() else None,
            }
        raise ValueError(f"Unsupported blackbox target: {target}")

    def apply_blackbox_repair_attempt(
            self,
            target: str,
            step: int,
            *,
            initial_order=None,
            new_order=None,
            initial_pri_order=None,
            new_pri_order=None,
            initial_sec_order=None,
            new_sec_order=None) -> BlackboxRepairOutcome:
        component_correct = False
        touched_layers = []

        if target == 'G1':
            if initial_order is not None and list(new_order) != list(initial_order):
                self._ctrl.assessment_coord.append_assessment_event(
                    AssessmentEventType.BLACKBOX_SWAP,
                    step=step,
                    target='G1',
                    layer='terminal',
                    from_order=list(initial_order),
                    to_order=list(new_order),
                )
                touched_layers.append('terminal')
            self._ctrl.g1_blackbox_order = list(new_order)
            self.sync_pt1_blackbox_to_phase_orders()
            component_correct = (list(new_order) == ['A', 'B', 'C'])
        elif target == 'G2':
            if initial_order is not None and list(new_order) != list(initial_order):
                self._ctrl.assessment_coord.append_assessment_event(
                    AssessmentEventType.BLACKBOX_SWAP,
                    step=step,
                    target='G2',
                    layer='terminal',
                    from_order=list(initial_order),
                    to_order=list(new_order),
                )
                touched_layers.append('terminal')
            self._ctrl.g2_blackbox_order = list(new_order)
            self.sync_g2_blackbox_to_phase_orders()
            component_correct = (list(new_order) == ['A', 'B', 'C'])
        elif target == 'PT1':
            if initial_pri_order is not None and list(new_pri_order) != list(initial_pri_order):
                self._ctrl.assessment_coord.append_assessment_event(
                    AssessmentEventType.BLACKBOX_SWAP,
                    step=step,
                    target='PT1',
                    layer='primary',
                    from_order=list(initial_pri_order),
                    to_order=list(new_pri_order),
                )
                touched_layers.append('primary')
            if initial_sec_order is not None and list(new_sec_order) != list(initial_sec_order):
                self._ctrl.assessment_coord.append_assessment_event(
                    AssessmentEventType.BLACKBOX_SWAP,
                    step=step,
                    target='PT1',
                    layer='secondary',
                    from_order=list(initial_sec_order),
                    to_order=list(new_sec_order),
                )
                touched_layers.append('secondary')
            self._ctrl.pt1_pri_blackbox_order = list(new_pri_order)
            self._ctrl.pt1_sec_blackbox_order = list(new_sec_order)
            self.sync_pt1_blackbox_to_phase_orders()
            component_correct = (
                list(new_pri_order) == ['A', 'B', 'C']
                and list(new_sec_order) == ['A', 'B', 'C']
            )
        elif target == 'PT3':
            if initial_sec_order is not None and list(new_sec_order) != list(initial_sec_order):
                self._ctrl.assessment_coord.append_assessment_event(
                    AssessmentEventType.BLACKBOX_SWAP,
                    step=step,
                    target='PT3',
                    layer='secondary',
                    from_order=list(initial_sec_order),
                    to_order=list(new_sec_order),
                )
                touched_layers.append('secondary')
            self._ctrl.pt_phase_orders['PT3'] = list(new_sec_order)
            component_correct = (list(new_sec_order) == ['A', 'B', 'C'])
        else:
            raise ValueError(f"Unsupported blackbox repair target: {target}")

        self._ctrl.assessment_coord.append_assessment_event(
            AssessmentEventType.BLACKBOX_CONFIRM_ATTEMPTED,
            step=step,
            target=target,
            layers=touched_layers,
            success=bool(component_correct),
        )

        if not component_correct:
            return BlackboxRepairOutcome(
                target=target,
                component_correct=False,
                fault_cleared=False,
                message="X 接线仍有错误，请重新调整后再提交。",
                message_color="#dc2626",
            )

        fault_active = bool(self._ctrl.sim_state.fault_config.active and not self._ctrl.sim_state.fault_config.repaired)
        fault_cleared = False
        disable_repair_button = False
        if (
            fault_active
            and self._ctrl.fault_mgr.all_repairable_wiring_targets_normal()
            and self._ctrl.flow_mgr.should_auto_clear_fault_only_when_all_blackboxes_normal()
        ):
            self._ctrl.repair_fault(step=step, source=f'{target}_blackbox')
            fault_cleared = True
            disable_repair_button = True
            message = "OK 全部接线均已修复，故障已完全清除。"
            message_color = "#15803d"
        else:
            message = "OK 此处接线已修复。请关闭并检查其他位置的接线。"
            message_color = "#0369a1"

        return BlackboxRepairOutcome(
            target=target,
            component_correct=True,
            fault_cleared=fault_cleared,
            message=message,
            message_color=message_color,
            disable_repair_button=disable_repair_button,
        )

    def _compute_pt1_net_order(self, bus_order=None, pri_order=None, sec_order=None):
        labels = ('A', 'B', 'C')
        bus_order = list(bus_order if bus_order is not None else self._ctrl.g1_blackbox_order)
        pri_order = list(pri_order if pri_order is not None else self._ctrl.pt1_pri_blackbox_order)
        sec_order = list(sec_order if sec_order is not None else self._ctrl.pt1_sec_blackbox_order)

        primary_actual = [bus_order[labels.index(cable_label)] for cable_label in pri_order]
        return [primary_actual[labels.index(sec_label)] for sec_label in sec_order]

    def sync_pt1_blackbox_to_phase_orders(self):
        self._ctrl.pt_phase_orders['PT2'] = list(self._ctrl.g1_blackbox_order)
        self._ctrl.pt_phase_orders['PT1'] = self._compute_pt1_net_order()

    def sync_g2_blackbox_to_phase_orders(self):
        self._ctrl.pt_phase_orders['PT3'] = list(self._ctrl.g2_blackbox_order)
