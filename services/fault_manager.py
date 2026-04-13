from typing import Any, List

from domain.fault_scenarios import SCENARIOS


class FaultManager:
    def __init__(self, ctrl: Any):
        self._ctrl = ctrl

    def has_unrepaired_wiring_fault(self) -> bool:
        relevant_orders = self._get_repairable_wiring_orders()
        if not relevant_orders:
            return False
        normal_order = ['A', 'B', 'C']
        return any(order != normal_order for order in relevant_orders)

    def all_repairable_wiring_targets_normal(self) -> bool:
        relevant_orders = self._get_repairable_wiring_orders()
        if not relevant_orders:
            return False
        normal_order = ['A', 'B', 'C']
        return all(order == normal_order for order in relevant_orders)

    def fault_has_repairable_wiring_targets(self) -> bool:
        fc = self._ctrl.sim_state.fault_config
        if not fc.active:
            return False
        return any(
            fc.params.get(key) is not None
            for key in (
                'g1_blackbox_order',
                'pt1_pri_blackbox_order',
                'p1_pri_blackbox_order',
                'pt1_sec_blackbox_order',
                'pt2_sec_blackbox_order',
                'g2_blackbox_order',
            )
        )

    def _get_repairable_wiring_orders(self) -> List[list]:
        fc = self._ctrl.sim_state.fault_config
        if not (fc.active and not fc.repaired):
            return []

        relevant_orders = []
        if fc.params.get('g1_blackbox_order') is not None:
            relevant_orders.append(self._ctrl.g1_blackbox_order)
        if (fc.params.get('pt1_pri_blackbox_order') is not None
                or fc.params.get('p1_pri_blackbox_order') is not None):
            relevant_orders.append(self._ctrl.pt1_pri_blackbox_order)
        if (fc.params.get('pt1_sec_blackbox_order') is not None
                or fc.params.get('pt2_sec_blackbox_order') is not None):
            relevant_orders.append(self._ctrl.pt1_sec_blackbox_order)
        if fc.params.get('g2_blackbox_order') is not None:
            relevant_orders.append(self._ctrl.g2_blackbox_order)
        return relevant_orders

    def inject_fault(self, scenario_id: str):
        """注入故障场景（由管理员在训练前设置）。scenario_id='' 清除故障。"""
        fc = self._ctrl.sim_state.fault_config
        fc.scenario_id = scenario_id
        fc.active = bool(scenario_id)
        fc.detected = False
        fc.repaired = False
        self._ctrl._last_fault_detected = False
        scenario = SCENARIOS.get(scenario_id, {})
        fc.params = dict(scenario.get('params', {}))

        self._ctrl.sim_state.fault_reverse_bc = False
        self._ctrl.reset_blackbox_orders()

        if scenario_id == 'E01':
            self._ctrl.pt_phase_orders['PT1'] = ['B', 'A', 'C']
            self._ctrl.pt_phase_orders['PT2'] = ['B', 'A', 'C']
            self._ctrl.g1_blackbox_order = ['B', 'A', 'C']
        elif scenario_id == 'E02':
            self._ctrl.g2_blackbox_order = ['A', 'C', 'B']
            self._ctrl.blackbox_handler.sync_g2_blackbox_to_phase_orders()
        elif scenario_id == 'E04':
            self._ctrl.sim_state.pt3_ratio = 11000.0 / 93.0
            self._ctrl.request_pt_ratio_row_update('pt3_ratio', 11000, 93)

        self._ctrl.g1_blackbox_order = list(fc.params.get('g1_blackbox_order', self._ctrl.g1_blackbox_order))
        self._ctrl.g2_blackbox_order = list(fc.params.get('g2_blackbox_order', self._ctrl.g2_blackbox_order))
        self._ctrl.pt1_pri_blackbox_order = list(
            fc.params.get(
                'pt1_pri_blackbox_order',
                fc.params.get('p1_pri_blackbox_order', self._ctrl.pt1_pri_blackbox_order),
            )
        )
        self._ctrl.pt1_sec_blackbox_order = list(
            fc.params.get(
                'pt1_sec_blackbox_order',
                fc.params.get('pt2_sec_blackbox_order', self._ctrl.pt1_sec_blackbox_order),
            )
        )

        pt1_order = fc.params.get('pt1_phase_order')
        if pt1_order:
            self._ctrl.pt_phase_orders['PT1'] = list(pt1_order)

        swap = fc.params.get('g1_loop_swap')
        if swap and scenario_id != 'E01':
            p1, p2 = swap
            new_pt2 = list(self._ctrl.pt_phase_orders['PT2'])
            i1 = ('A', 'B', 'C').index(p1)
            i2 = ('A', 'B', 'C').index(p2)
            new_pt2[i1], new_pt2[i2] = new_pt2[i2], new_pt2[i1]
            self._ctrl.pt_phase_orders['PT2'] = new_pt2

        if scenario_id == 'E02':
            self._ctrl.blackbox_handler.sync_g2_blackbox_to_phase_orders()
        if any(
                fc.params.get(key) is not None
                for key in (
                    'g1_blackbox_order',
                    'pt1_phase_order',
                    'pt1_pri_blackbox_order',
                    'p1_pri_blackbox_order',
                    'pt1_sec_blackbox_order',
                    'pt2_sec_blackbox_order',
                )):
            self._ctrl.blackbox_handler.sync_pt1_blackbox_to_phase_orders()

    def repair_fault(self, step: int = 4, source: str = 'repair_fault'):
        """学员完成虚拟修复后调用，消除故障效果并重置检测标志。"""
        fc = self._ctrl.sim_state.fault_config
        sid = fc.scenario_id
        fc.repaired = True
        fc.detected = False
        self._ctrl.assessment_coord.append_assessment_event('fault_repaired', step=step, scene_id=sid, source=source)
        self._ctrl.reset_blackbox_orders()

        if sid == 'E01':
            self._ctrl.pt_phase_orders['PT1'] = ['A', 'B', 'C']
            self._ctrl.pt_phase_orders['PT2'] = ['A', 'B', 'C']
        elif sid == 'E02':
            self._ctrl.sim_state.fault_reverse_bc = False
            self._ctrl.pt_phase_orders['PT3'] = ['A', 'B', 'C']
        elif sid == 'E04':
            self._ctrl.sim_state.pt3_ratio = 11000.0 / 193.0
            self._ctrl.request_pt_ratio_row_update('pt3_ratio', 11000, 193)

        if fc.params.get('pt1_phase_order') is not None:
            self._ctrl.pt_phase_orders['PT1'] = ['A', 'B', 'C']
        if fc.params.get('g1_loop_swap') is not None:
            self._ctrl.pt_phase_orders['PT2'] = ['A', 'B', 'C']
