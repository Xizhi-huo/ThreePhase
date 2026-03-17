"""
services/pt_exam_service.py
PT 二次端子压差考核服务
"""

from domain.enums import BreakerPosition


class PtExamService:
    """
    PT 二次端子压差考核业务逻辑。
    从 PowerSyncController 提取，保持完全相同的方法签名和逻辑。
    """

    def __init__(self, ctrl):
        self._ctrl = ctrl

    # ── 状态工厂 ──────────────────────────────────────────────────────────────
    def _create_pt_exam_state(self):
        return {
            'records': {'A': None, 'B': None, 'C': None},
            'completed': False,
            'started': False,
            'feedback': "请先恢复小电阻接地，并将机组并入母排后，在母排拓扑页完成三相 PT 二次端子压差测量。",
            'feedback_color': '#444444',
        }

    def start_pt_exam(self, gen_id):
        self._ctrl.pt_exam_states[gen_id]['started'] = True

    def stop_pt_exam(self, gen_id):
        self._ctrl.pt_exam_states[gen_id]['started'] = False

    def _set_pt_exam_feedback(self, gen_id, message, color='#444444'):
        self._ctrl.pt_exam_states[gen_id]['feedback'] = message
        self._ctrl.pt_exam_states[gen_id]['feedback_color'] = color

    def _expected_pt_probe_pair(self, gen_id, phase):
        bus_node = f"PT2_{phase}"
        gen_node = f"PT1_{phase}" if gen_id == 1 else f"PT3_{phase}"
        return {bus_node, gen_node}

    def resolve_pt_node_plot_key(self, node_name):
        pt_name, terminal = node_name.split('_', 1)
        terminal_index = ('A', 'B', 'C').index(terminal)
        actual_phase = self._ctrl.pt_phase_orders[pt_name][terminal_index]
        if pt_name == 'PT3':
            gen2 = self._ctrl.sim_state.gen2
            prefix = 'g' if (gen2.breaker_closed and not gen2.running) else 'g2'
        else:
            prefix = {'PT1': 'g1', 'PT2': 'g'}[pt_name]
        return f"{prefix}{actual_phase.lower()}"

    def resolve_loop_node_phase(self, node_name):
        _, gen_name, terminal = node_name.split('_', 2)
        if gen_name == 'G2' and self._ctrl.sim_state.fault_reverse_bc:
            return {'A': 'A', 'B': 'C', 'C': 'B'}[terminal]
        return terminal

    def _get_current_pt_phase_match(self, gen_id):
        sim = self._ctrl.sim_state
        if not sim.probe1_node or not sim.probe2_node:
            return None
        pair = {sim.probe1_node, sim.probe2_node}
        for phase in ('A', 'B', 'C'):
            if pair == self._expected_pt_probe_pair(gen_id, phase):
                return phase
        return None

    def reset_pt_exam(self, gen_id=None):
        target_ids = (gen_id,) if gen_id in (1, 2) else (1, 2)
        for gid in target_ids:
            self._ctrl.pt_exam_states[gid] = self._create_pt_exam_state()

    def _is_pt_exam_setup_ready(self, gen_id):
        gen1, gen2 = self._ctrl.sim_state.gen1, self._ctrl.sim_state.gen2
        gnd_ok     = self._ctrl.sim_state.grounding_mode == "小电阻接地"
        gen1_on    = gen1.breaker_position == BreakerPosition.WORKING and gen1.breaker_closed
        if gen_id == 1:
            return gnd_ok and gen1_on and not gen2.breaker_closed
        else:
            return gnd_ok and gen1_on and gen2.running and not gen2.breaker_closed

    def record_pt_measurement(self, phase):
        gen_id = self._ctrl.ui._pt_target_bg.checkedId()
        if gen_id <= 0:
            gen_id = 1
        phase = phase.upper()
        gen1, gen2 = self._ctrl.sim_state.gen1, self._ctrl.sim_state.gen2

        # 第一步（回路连通性测试）必须先完成
        if not self._ctrl.is_loop_test_complete():
            self._set_pt_exam_feedback(
                gen_id,
                "请先完成第一步【回路连通性测试】，再进行 PT 二次端子压差测量。",
                "red")
            return

        # 强制 A→B→C 顺序录入
        phase_order = ('A', 'B', 'C')
        records = self._ctrl.pt_exam_states[gen_id]['records']
        for prev in phase_order[:phase_order.index(phase)]:
            if records[prev] is None:
                self._set_pt_exam_feedback(
                    gen_id,
                    f"请先完成 {prev} 相的测量记录，再记录 {phase} 相。",
                    "red")
                return

        if self._ctrl.sim_state.grounding_mode != "小电阻接地":
            self._set_pt_exam_feedback(gen_id, "请先恢复中性点小电阻接地，再进行 PT 二次端子压差测量。", "red")
            return

        if gen_id == 1:
            # 测 Gen1：Gen1 必须合闸建立母排，Gen2 不允许合闸
            if gen1.breaker_position != BreakerPosition.WORKING or not gen1.breaker_closed:
                self._set_pt_exam_feedback(1, "请将 Gen1 切至工作位置并合闸，建立母排参考电压。", "red")
                return
            if gen2.breaker_closed:
                self._set_pt_exam_feedback(1, "测试 Gen1 时请先断开 Gen2 断路器，Gen2 不应并入母排。", "red")
                return
        else:
            # 测 Gen2：Gen1 必须合闸作为母排参考，Gen2 运行但不合闸
            if gen1.breaker_position != BreakerPosition.WORKING or not gen1.breaker_closed:
                self._set_pt_exam_feedback(2, "请先确保 Gen1 已并入母排，作为母排参考电压来源。", "red")
                return
            if not gen2.running:
                self._set_pt_exam_feedback(2, "请先启动 Gen2，再进行 PT 二次端子压差测量。", "red")
                return
            if gen2.breaker_closed:
                self._set_pt_exam_feedback(2, "Gen2 断路器应保持断开，并入前才能测量有效压差。", "red")
                return
        if not self._ctrl.sim_state.multimeter_mode:
            self._set_pt_exam_feedback(gen_id, "请先开启万用表，再到母排拓扑页放置表笔。", "red")
            return
        if not self._ctrl.sim_state.probe1_node or not self._ctrl.sim_state.probe2_node:
            self._set_pt_exam_feedback(gen_id, "表笔尚未放置完成，请在母排拓扑页连接 PT 二次端子排上的同相端子。", "red")
            return

        matched_phase = self._get_current_pt_phase_match(gen_id)
        if matched_phase != phase:
            if matched_phase is None:
                msg = f"当前表笔不在 Gen {gen_id} {phase} 相 PT 二次端子与 PT2 同相端子之间，请重新放置。"
            else:
                msg = f"当前表笔落在 {matched_phase} 相，请记录对应相别或重新放置表笔。"
            self._set_pt_exam_feedback(gen_id, msg, "red")
            return

        meter_v      = getattr(self._ctrl.physics, 'meter_voltage', None)
        meter_status = getattr(self._ctrl.physics, 'meter_status', 'idle')
        if meter_v is None or meter_status not in ('ok', 'danger'):
            self._set_pt_exam_feedback(gen_id, "当前测量结果无效，请确认表笔接在 PT 二次端子排对应端子上。", "red")
            return
        if meter_status != 'ok':
            self._set_pt_exam_feedback(gen_id, f"{phase} 相 PT 二次端子压差为 {meter_v:.1f} V，暂不满足合闸条件，请继续调整。", "red")
            return

        self._ctrl.pt_exam_states[gen_id]['records'][phase] = {
            'voltage': meter_v,
            'reading': self._ctrl.physics.meter_reading,
        }
        all_rec = all(self._ctrl.pt_exam_states[gen_id]['records'][ph] is not None for ph in ('A', 'B', 'C'))
        if all_rec:
            msg = f"Gen {gen_id} 三相 PT 二次端子压差已全部记录完成。"
        else:
            msg = f"Gen {gen_id} {phase} 相 PT 二次端子压差记录完成：{meter_v:.1f} V。"
        self._set_pt_exam_feedback(gen_id, msg, "#006600")

    def get_pt_exam_steps(self, gen_id):
        state   = self._ctrl.pt_exam_states[gen_id]
        records = state['records']
        has_any = any(records[ph] is not None for ph in ('A', 'B', 'C'))
        gen1, gen2 = self._ctrl.sim_state.gen1, self._ctrl.sim_state.gen2
        gnd_ok = self._ctrl.sim_state.grounding_mode == "小电阻接地"
        gen1_on_bus = (gen1.breaker_position == BreakerPosition.WORKING and gen1.breaker_closed)

        if gen_id == 1:
            steps = [
                ("1. 恢复中性点小电阻接地",
                 gnd_ok or has_any),
                ("2. 将 Gen1 切至工作位置并合闸（建立母排参考）",
                 gen1_on_bus or has_any),
                ("3. 确认 Gen2 断路器处于断开状态",
                 (not gen2.breaker_closed) or has_any),
                ("4. 开启万用表并连接 PT1 与 PT2 同相端子",
                 self._ctrl.sim_state.multimeter_mode or has_any),
                ("5. 记录 A 相 PT 二次端子压差", records['A'] is not None),
                ("6. 记录 B 相 PT 二次端子压差", records['B'] is not None),
                ("7. 记录 C 相 PT 二次端子压差", records['C'] is not None),
            ]
        else:
            gen2_running_not_closed = gen2.running and not gen2.breaker_closed
            steps = [
                ("1. 恢复中性点小电阻接地",
                 gnd_ok or has_any),
                ("2. 确认 Gen1 已并入母排（作为母排参考）",
                 gen1_on_bus or has_any),
                ("3. 启动 Gen2，保持断路器断开",
                 gen2_running_not_closed or has_any),
                ("4. 开启万用表并连接 PT3 与 PT2 同相端子",
                 self._ctrl.sim_state.multimeter_mode or has_any),
                ("5. 记录 A 相 PT 二次端子压差", records['A'] is not None),
                ("6. 记录 B 相 PT 二次端子压差", records['B'] is not None),
                ("7. 记录 C 相 PT 二次端子压差", records['C'] is not None),
            ]
        if state.get('completed'):
            return [(text, True) for text, _ in steps]
        return steps

    def get_pt_exam_close_blockers(self, gen_id):
        generator = self._ctrl._get_generator_state(gen_id)
        records   = self._ctrl.pt_exam_states[gen_id]['records']
        blockers  = []
        if not any(records[ph] is not None for ph in ('A', 'B', 'C')):
            if self._ctrl.sim_state.grounding_mode != "小电阻接地":
                blockers.append("未恢复中性点小电阻接地")
            if generator.breaker_position != BreakerPosition.WORKING or not generator.breaker_closed:
                blockers.append("未在工作位置并入母排完成 PT 二次端子测量")
            if not self._ctrl.sim_state.multimeter_mode:
                blockers.append("未开启万用表")
        for phase in ('A', 'B', 'C'):
            if records[phase] is None:
                blockers.append(f"未记录 {phase} 相 PT 二次端子压差")
        return blockers

    def is_pt_exam_ready(self, gen_id):
        return self._ctrl.pt_exam_states[gen_id].get('completed', False)

    def finalize_pt_exam(self, gen_id):
        state = self._ctrl.pt_exam_states[gen_id]
        records = state['records']
        if not all(records[ph] is not None for ph in ('A', 'B', 'C')):
            self._set_pt_exam_feedback(gen_id, '请先完成 A/B/C 三相 PT 二次端子压差记录，再点击\u201c完成第二步测试\u201d。', "red")
            return
        state['completed'] = True
        self._set_pt_exam_feedback(gen_id, f"第二步【Gen {gen_id} PT 二次端子压差测试】已确认完成，后续操作将不再影响该步骤状态。", "#006600")

    def _should_enforce_pt_exam_before_close(self):
        return self._ctrl.sim_state.grounding_mode != "断开"

    def _should_limit_close_to_selected_pt_target(self):
        sim = self._ctrl.sim_state
        return (
            sim.grounding_mode == "小电阻接地" and
            sim.gen1.mode == "manual" and
            sim.gen2.mode == "manual" and
            not self._ctrl.is_sync_test_complete()
        )

    def is_pt_exam_recorded(self, gen_id):
        """仅检查三相是否已记录，不要求当前开关柜位置（用于后续步骤前提判断）。"""
        records = self._ctrl.pt_exam_states[gen_id]['records']
        return all(records[ph] is not None for ph in ('A', 'B', 'C'))
