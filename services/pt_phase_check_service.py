"""
services/pt_phase_check_service.py
PT 相序检查服务（第三步）

通过万用表手动测量 PT1_X/PT2_X 和 PT3_X/PT2_X 端子对（共6组），
根据物理引擎返回的 meter_phase_match 判断 ABC 各相是否连线正确。

电气状态与第二步相同：
  - Gen1：手动工作位，起机，合闸并入母排（提供 PT1/PT2 参考电压）
  - Gen2：手动工作位，起机，断路器断开（提供 PT3 参考电压）
相序判断以 meter_phase_match 为准（物理引擎比较两路波形的实际相位），
与电压大小无关。
"""

from domain.enums import BreakerPosition
from domain.test_states import PtPhaseCheckState

_ALL_KEYS = ('PT1_A', 'PT1_B', 'PT1_C', 'PT3_A', 'PT3_B', 'PT3_C')


class PtPhaseCheckService:
    """PT 相序检查业务逻辑。"""

    def __init__(self, ctrl):
        self._ctrl = ctrl

    # ── 状态工厂 ──────────────────────────────────────────────────────────────
    def create_pt_phase_check_state(self) -> PtPhaseCheckState:
        return PtPhaseCheckState()

    def start_pt_phase_check(self):
        self._ctrl.pt_phase_check_state.started = True

    def stop_pt_phase_check(self):
        self._ctrl.pt_phase_check_state.started = False

    def _set_feedback(self, message, color='#444444'):
        self._ctrl.pt_phase_check_state.feedback = message
        self._ctrl.pt_phase_check_state.feedback_color = color

    # ── 步骤列表 ──────────────────────────────────────────────────────────────
    def get_pt_phase_check_steps(self):
        sim = self._ctrl.sim_state
        gen1, gen2 = sim.gen1, sim.gen2
        state = self._ctrl.pt_phase_check_state
        loop_done = self._ctrl.is_loop_test_complete()
        gnd_ok = sim.grounding_mode == "小电阻接地"
        gen1_on_bus = (gen1.breaker_position == BreakerPosition.WORKING and gen1.breaker_closed)
        gen2_running_open = gen2.running and not gen2.breaker_closed
        rec = state.records

        vol_done = self._ctrl.is_pt_voltage_check_complete()
        steps = [
            ("1. 前提：第一步回路连通性测试已完成", loop_done),
            ("2. 前提：第二步 PT 单体线电压检查已完成", vol_done),
            ("3. 恢复中性点小电阻接地", gnd_ok),
            ("4. 确认 Gen1 在工作位并入母排（提供 PT1/PT2 参考电压）", gen1_on_bus),
            ("5. 启动 Gen2，保持断路器断开（提供 PT3 参考电压）", gen2_running_open),
            ("6. 接入相序仪至 PT1，记录 PT1 三相相序", all(rec[f'PT1_{p}'] is not None for p in 'ABC')),
            ("7. 接入相序仪至 PT3，记录 PT3 三相相序", all(rec[f'PT3_{p}'] is not None for p in 'ABC')),
        ]
        if state.completed:
            return [(text, True) for text, _ in steps]
        return steps

    # ── 逐相记录 ──────────────────────────────────────────────────────────────
    def record_pt_phase_check(self, pt_name, phase):
        pt_name = pt_name.upper()
        phase = phase.upper()
        key = f"{pt_name}_{phase}"
        sim = self._ctrl.sim_state
        gen1, gen2 = sim.gen1, sim.gen2
        state = self._ctrl.pt_phase_check_state

        if not state.started:
            self._set_feedback("请先点击「开始第三步测试」，再进行相序记录。", "red")
            return
        if not self._ctrl.is_loop_test_complete():
            self._set_feedback("请先完成第一步【回路连通性测试】，再进行 PT 相序检查。", "red")
            return
        if not self._ctrl.is_pt_voltage_check_complete():
            self._set_feedback("请先完成第二步【PT 单体线电压检查】，再进行 PT 相序检查。", "red")
            return
        if sim.grounding_mode != "小电阻接地":
            self._set_feedback("请先恢复中性点小电阻接地，再进行 PT 相序检查。", "red")
            return
        if gen1.breaker_position != BreakerPosition.WORKING or not gen1.breaker_closed:
            self._set_feedback("请先确认 Gen1 已并入母排，建立 PT1/PT2 参考电压。", "red")
            return

        if pt_name == 'PT3':
            if not gen2.running:
                self._set_feedback(
                    "测量 PT3 相序时，请先启动 Gen2（保持断路器断开）。", "red")
                return
            if gen2.breaker_closed:
                self._set_feedback(
                    "测量 PT3 相序时，Gen2 断路器应保持断开状态。", "red")
                return

        phase_order = ('A', 'B', 'C')
        for prev in phase_order[:phase_order.index(phase)]:
            prev_key = f"{pt_name}_{prev}"
            if state.records[prev_key] is None:
                self._set_feedback(
                    f"请先完成 {pt_name} {prev} 相的测量记录，再记录 {phase} 相。", "red")
                return

        expected_pair = {key, f"PT2_{phase}"}
        actual_pair = (
            {sim.probe1_node, sim.probe2_node}
            if sim.probe1_node and sim.probe2_node else set()
        )
        if actual_pair != expected_pair:
            self._set_feedback(
                f"请在母排拓扑页将表笔放在 {key} 和 PT2_{phase} 端子上，再点击记录。", "red")
            return

        phase_match = getattr(self._ctrl.physics, 'meter_phase_match', None)
        if phase_match is None:
            self._set_feedback("当前测量结果无效，请确认表笔接在 PT 和 PT2 同相端子上。", "red")
            return

        state.records[key] = {
            'phase_match': phase_match,
            'reading': self._ctrl.physics.meter_reading,
        }

        all_rec = all(state.records[k] is not None for k in _ALL_KEYS)
        any_fail = any(
            r is not None and not r['phase_match'] for r in state.records.values()
        )

        if any_fail:
            state.result = 'fail'
            self._set_feedback(
                f"⚠️ 相序异常！{key} 检测到端子接线错误，请检查对应侧 B/C 接线。", "red")
        elif all_rec:
            state.result = 'pass'
            self._set_feedback(
                "PT 相序检查通过：PT1/PT3 各相连线均正确，可点击\u201c完成第三步测试\u201d继续。",
                "#006600")
        elif phase_match:
            self._set_feedback(f"{key} 相序正确，请继续测量其余项目。", "#006600")
        else:
            state.result = 'fail'
            self._set_feedback(f"⚠️ {key} 相序异常！请检查对应侧接线。", "red")

    def reset_pt_phase_check(self):
        self._ctrl.pt_phase_check_state = self.create_pt_phase_check_state()

    def is_pt_phase_check_complete(self):
        """流程门禁：只有用户点击"完成第三步测试"后才返回 True。"""
        return self._ctrl.pt_phase_check_state.completed

    def _are_phase_check_records_complete(self):
        """内部辅助：六相记录是否齐全且全部通过（用于 finalize 前置校验）。"""
        records = self._ctrl.pt_phase_check_state.records
        return all(
            records.get(k) is not None and records[k]['phase_match']
            for k in _ALL_KEYS
        )

    def finalize_pt_phase_check(self):
        state = self._ctrl.pt_phase_check_state
        if not self._are_phase_check_records_complete():
            self._set_feedback(
                '请先完成 PT1/PT3 全部六相相序测量（且全部通过），再点击\u201c完成第三步测试\u201d。',
                "red")
            return
        state.completed = True
        self._set_feedback(
            "第三步【PT 相序检查】已确认完成，后续操作将不再影响该步骤状态。",
            "#006600")

    def get_pt_phase_check_blockers(self):
        return [text for text, done in self.get_pt_phase_check_steps() if not done]
