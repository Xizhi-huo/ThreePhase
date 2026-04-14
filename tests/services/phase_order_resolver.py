from __future__ import annotations


class PhaseOrderResolver:
    def __init__(self, ctrl):
        self._ctrl = ctrl

    def resolve_pt_node_plot_key(self, node_name):
        parts = node_name.split('_', 1)
        if len(parts) != 2:
            return None
        pt_name, terminal = parts
        if pt_name not in self._ctrl.pt_phase_orders or terminal not in ('A', 'B', 'C'):
            return None
        terminal_index = ('A', 'B', 'C').index(terminal)
        actual_phase = self._ctrl.pt_phase_orders[pt_name][terminal_index]
        if pt_name == 'PT3':
            prefix = 'g2'
        else:
            prefix = {'PT1': 'g1', 'PT2': 'g'}[pt_name]
        return f"{prefix}{actual_phase.lower()}"

    def get_pt_phase_sequence(self, pt_name: str) -> str:
        fc = self._ctrl.sim_state.fault_config
        if (fc.active and not fc.repaired
                and fc.scenario_id == 'E03' and pt_name == 'PT3'):
            return 'FAULT'
        phase_map = {}
        _rbc = self._ctrl.sim_state.fault_reverse_bc
        for ph in ('A', 'B', 'C'):
            node = f"{pt_name}_{ph}"
            key = self.resolve_pt_node_plot_key(node)
            if key is None or key[-1] not in ('a', 'b', 'c'):
                return 'FAULT'
            actual = key[-1]
            if _rbc and key == 'g2b':
                actual = 'c'
            elif _rbc and key == 'g2c':
                actual = 'b'
            phase_map[ph] = actual

        order = (phase_map['A'], phase_map['B'], phase_map['C'])
        if len(set(order)) < 3:
            return 'FAULT'
        return order[0].upper() + order[1].upper() + order[2].upper()

    def resolve_loop_node_phase(self, node_name):
        _, gen_name, terminal = node_name.split('_', 2)
        if gen_name == 'G1':
            idx = ('A', 'B', 'C').index(terminal)
            return self._ctrl.pt_phase_orders['PT2'][idx]
        if gen_name == 'G2':
            idx = ('A', 'B', 'C').index(terminal)
            phase = self._ctrl.g2_blackbox_order[idx]
            if self._ctrl.sim_state.fault_reverse_bc:
                if phase == 'B':
                    phase = 'C'
                elif phase == 'C':
                    phase = 'B'
            return phase
        return terminal
