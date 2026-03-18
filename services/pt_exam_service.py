"""
services/pt_exam_service.py
PT 二次端子压差考核服务
"""

from domain.enums import BreakerPosition
from domain.test_states import PtExamState


class PtExamService:
    """
    PT 二次端子压差考核业务逻辑。
    gen_id 由调用方（UI/Controller）显式传入，服务层不再直接读取任何 UI 控件状态。
    """

    def __init__(self, ctrl):
        self._ctrl = ctrl

    # ── 状态工厂 ──────────────────────────────────────────────────────────────
    def create_pt_exam_state(self) -> PtExamState:
        return PtExamState()

    def start_pt_exam(self, gen_id):
        self._ctrl.pt_exam_states[gen_id].started = True

    def stop_pt_exam(self, gen_id):
        self._ctrl.pt_exam_states[gen_id].started = False

    def _set_pt_exam_feedback(self, gen_id, message, color='#444444'):
        self._ctrl.pt_exam_states[gen_id].feedback = message
        self._ctrl.pt_exam_states[gen_id].feedback_color = color

    def _expected_pt_probe_pair(self, gen_id, phase):
        bus_node = f"PT2_{phase}"
        gen_node = f"PT1_{phase}" if gen_id == 1 else f"PT3_{phase}"
        return {bus_node, gen_node}

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
            self._ctrl.pt_exam_states[gid] = self.create_pt_exam_state()

    def _is_pt_exam_setup_ready(self, gen_id):
        gen1, gen2 = self._ctrl.sim_state.gen1, self._ctrl.sim_state.gen2
        gnd_ok     = self._ctrl.sim_state.grounding_mode == "小电阻接地"
        gen1_on    = gen1.breaker_position == BreakerPosition.WORKING and gen1.breaker_closed
        if gen_id == 1:
            return gnd_ok and gen1_on and not gen2.breaker_closed
        else:
            return gnd_ok and gen1_on and gen2.running and not gen2.breaker_closed

    def record_pt_measurement(self, phase, gen_id):
        """
        记录 PT 二次端子压差测量结果。

        Parameters
        ----------
        phase  : str   – 'A'、'B' 或 'C'
        gen_id : int   – 1 或 2，由调用方（UI 按钮回调）显式传入，
                         服务层不访问任何 UI 控件。
        """
        if gen_id <= 0:
            gen_id = 1
        phase = phase.upper()
        gen1, gen2 = self._ctrl.sim_state.gen1, self._ctrl.sim_state.gen2

        if not self._ctrl.is_loop_test_complete():
            self._set_pt_exam_feedback(
                gen_id,
                "请先完成第一步【回路连通性测试】，再进行 PT 二次端子压差测量。",
                "red")
            return
        if not self._ctrl.is_pt_voltage_check_complete():
            self._set_pt_exam_feedback(
                gen_id,
                "请先完成第二步【PT 单体线电压检查】，再进行 PT 二次端子压差测量。",
                "red")
            return
        if not self._ctrl.is_pt_phase_check_complete():
            self._set_pt_exam_feedback(
                gen_id,
                "请先完成第三步【PT 相序检查】，确认 PT1/PT3 各相连线正确后，再进行压差测量。",
                "red")
            return

        phase_order = ('A', 'B', 'C')
        records = self._ctrl.pt_exam_states[gen_id].records
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
            if gen1.breaker_position != BreakerPosition.WORKING or not gen1.breaker_closed:
                self._set_pt_exam_feedback(1, "请将 Gen1 切至工作位置并合闸，建立母排参考电压。", "red")
                return
            if gen2.breaker_closed:
                self._set_pt_exam_feedback(1, "测试 Gen1 时请先断开 Gen2 断路器，Gen2 不应并入母排。", "red")
                return
        else:
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

        self._ctrl.pt_exam_states[gen_id].records[phase] = {
            'voltage': meter_v,
            'reading': self._ctrl.physics.meter_reading,
        }
        all_rec = all(self._ctrl.pt_exam_states[gen_id].records[ph] is not None for ph in ('A', 'B', 'C'))
        if all_rec:
            msg = f"Gen {gen_id} 三相 PT 二次端子压差已全部记录完成。"
        else:
            msg = f"Gen {gen_id} {phase} 相 PT 二次端子压差记录完成：{meter_v:.1f} V。"
        self._set_pt_exam_feedback(gen_id, msg, "#006600")

    def get_pt_exam_steps(self, gen_id):
        state   = self._ctrl.pt_exam_states[gen_id]
        records = state.records
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
        if state.completed:
            return [(text, True) for text, _ in steps]
        return steps

    def get_pt_exam_close_blockers(self, gen_id):
        generator = self._ctrl._get_generator_state(gen_id)
        records   = self._ctrl.pt_exam_states[gen_id].records
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
        return self._ctrl.pt_exam_states[gen_id].completed

    def finalize_pt_exam(self, gen_id):
        state = self._ctrl.pt_exam_states[gen_id]
        if not self._are_pt_exam_records_complete(gen_id):
            self._set_pt_exam_feedback(
                gen_id,
                '请先完成 A/B/C 三相 PT 二次端子压差记录，再点击\u201c完成第四步测试\u201d。',
                "red")
            return
        state.completed = True
        self._set_pt_exam_feedback(
            gen_id,
            f"第四步【Gen{gen_id} PT 二次端子压差测试】已确认完成，后续操作将不再影响该步骤状态。",
            "#006600")

    def finalize_all_pt_exams(self):
        """完成第四步：Gen1 和 Gen2 均须完成三相记录，才能锁定结果。"""
        gen1_ok = self._are_pt_exam_records_complete(1)
        gen2_ok = self._are_pt_exam_records_complete(2)
        if not gen1_ok:
            self._set_pt_exam_feedback(
                1,
                'Gen1 尚未完成三相 PT 二次端子压差记录，请先切换至 Gen1 完成测量，'
                '再点击\u201c完成第四步测试\u201d。',
                'red')
            if not gen2_ok:
                self._set_pt_exam_feedback(
                    2,
                    'Gen1 和 Gen2 均尚未完成三相 PT 二次端子压差记录。',
                    'red')
            else:
                self._set_pt_exam_feedback(
                    2,
                    'Gen2 已完成，但 Gen1 尚未完成测量，请切换至 Gen1 完成后再点击完成。',
                    '#cc6600')
            return
        if not gen2_ok:
            self._set_pt_exam_feedback(
                2,
                'Gen2 尚未完成三相 PT 二次端子压差记录，请先切换至 Gen2 完成测量，'
                '再点击\u201c完成第四步测试\u201d。',
                'red')
            self._set_pt_exam_feedback(
                1,
                'Gen1 已完成，但 Gen2 尚未完成测量，请切换至 Gen2 完成后再点击完成。',
                '#cc6600')
            return
        for gid in (1, 2):
            self._ctrl.pt_exam_states[gid].completed = True
            self._set_pt_exam_feedback(
                gid,
                '第四步【PT 二次端子压差测试】Gen1 和 Gen2 均已确认完成，'
                '后续操作将不再影响该步骤状态。',
                '#006600')

    def _should_enforce_pt_exam_before_close(self):
        return self._ctrl.sim_state.grounding_mode != "断开"

    def is_pt_exam_recorded(self, gen_id):
        """流程门禁：只有用户点击"完成第四步测试"后才返回 True。"""
        return self._ctrl.pt_exam_states[gen_id].completed

    def _are_pt_exam_records_complete(self, gen_id):
        """内部辅助：三相是否已记录（用于 finalize 前置校验）。"""
        records = self._ctrl.pt_exam_states[gen_id].records
        return all(records[ph] is not None for ph in ('A', 'B', 'C'))
