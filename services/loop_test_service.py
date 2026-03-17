"""
services/loop_test_service.py
回路连通性测试服务
"""

from domain.enums import BreakerPosition
from domain.test_states import LoopTestState


class LoopTestService:
    """
    回路连通性测试业务逻辑。
    状态以 LoopTestState dataclass 持有，避免裸字典的字段漂移。
    """

    def __init__(self, ctrl):
        self._ctrl = ctrl

    # ── 状态工厂 ──────────────────────────────────────────────────────────────
    def create_loop_test_state(self) -> LoopTestState:
        return LoopTestState()

    def _set_loop_test_feedback(self, message, color='#444444'):
        self._ctrl.loop_test_state.feedback = message
        self._ctrl.loop_test_state.feedback_color = color

    def _get_current_loop_phase_match(self):
        sim = self._ctrl.sim_state
        n1, n2 = sim.probe1_node, sim.probe2_node
        if not n1 or not n2:
            return None
        if not (n1.startswith('LOOP_G') and n2.startswith('LOOP_G')):
            return None
        parts1 = n1.split('_')   # ['LOOP', 'G1', 'A']
        parts2 = n2.split('_')   # ['LOOP', 'G2', 'A']
        if parts1[1] == parts2[1]:
            return None
        if parts1[2] == parts2[2]:
            return parts1[2]
        return None

    def get_loop_test_steps(self):
        sim = self._ctrl.sim_state
        gen1, gen2 = sim.gen1, sim.gen2
        state = self._ctrl.loop_test_state
        records = state.records
        all_rec = all(records[ph] is not None for ph in ('A', 'B', 'C'))
        steps = [
            ("1. 断开中性点小电阻连接",
             sim.grounding_mode == "断开"),
            ("2. 将 Gen 1 切至手动模式并切至工作位置",
             gen1.mode == "manual" and gen1.breaker_position == BreakerPosition.WORKING),
            ("3. 将 Gen 2 切至手动模式并切至工作位置",
             gen2.mode == "manual" and gen2.breaker_position == BreakerPosition.WORKING),
            ("4. 合闸 Gen 1（不要起机，仅闭合开关）",
             gen1.breaker_position == BreakerPosition.WORKING and gen1.breaker_closed),
            ("5. 合闸 Gen 2（不要起机，仅闭合开关）",
             gen2.breaker_position == BreakerPosition.WORKING and gen2.breaker_closed),
            ("6. 开启万用表，在母排拓扑页测量三相回路",
             sim.multimeter_mode),
            ("7. 记录 A/B/C 三相回路连通性结果",
             all_rec),
        ]
        if state.completed:
            return [(text, True) for text, _ in steps]
        return steps

    def record_loop_measurement(self, phase):
        sim = self._ctrl.sim_state
        gen1, gen2 = sim.gen1, sim.gen2
        phase = phase.upper()

        if sim.grounding_mode != "断开":
            self._set_loop_test_feedback('请先断开中性点小电阻连接（接地系统选"断开"）。', "red")
            return
        if gen1.mode != "manual" or gen2.mode != "manual":
            self._set_loop_test_feedback("请先将两台发电机都切至手动（Manual）模式。", "red")
            return
        if gen1.running or gen2.running:
            self._set_loop_test_feedback(
                "回路测试期间发电机不应起机！合闸但不起机，处于高压侧断路状态。", "red")
            return
        if not (gen1.breaker_closed and gen1.breaker_position == BreakerPosition.WORKING):
            self._set_loop_test_feedback("请先将 Gen 1 切至工作位置并合闸。", "red")
            return
        if not (gen2.breaker_closed and gen2.breaker_position == BreakerPosition.WORKING):
            self._set_loop_test_feedback("请先将 Gen 2 切至工作位置并合闸。", "red")
            return
        if not sim.multimeter_mode:
            self._set_loop_test_feedback("请先开启万用表。", "red")
            return

        phase_order = ('A', 'B', 'C')
        for prev in phase_order[:phase_order.index(phase)]:
            if self._ctrl.loop_test_state.records[prev] is None:
                self._set_loop_test_feedback(
                    f"请先完成 {prev} 相的测量记录，再记录 {phase} 相。", "red")
                return

        current_phase = self._get_current_loop_phase_match()
        if current_phase != phase:
            if current_phase is None:
                msg = (f"当前表笔未正确对准 {phase} 相回路，"
                       f"请在母排拓扑页将表笔分别放在 G1 与 G2 的 {phase} 相回路测点。")
            else:
                msg = f"当前表笔对准的是 {current_phase} 相，请记录对应相别或重新放置表笔。"
            self._set_loop_test_feedback(msg, "red")
            return

        meter_status = getattr(self._ctrl.physics, 'meter_status', 'idle')
        if meter_status not in ('ok', 'danger'):
            self._set_loop_test_feedback("测量结果无效，请确认表笔放在 G1 与 G2 的同相回路测点上。", "red")
            return
        if meter_status != 'ok':
            self._set_loop_test_feedback(f"{phase} 相回路测量显示相序不对应，请检查接线后重试。", "red")
            return

        self._ctrl.loop_test_state.records[phase] = {
            'status': meter_status,
            'reading': self._ctrl.physics.meter_reading,
        }
        all_rec = all(self._ctrl.loop_test_state.records[ph] is not None for ph in ('A', 'B', 'C'))
        if all_rec:
            self._set_loop_test_feedback(
                "三相回路连通性测试全部完成，电路连通正常，可进行第二步 PT 相序检查。", "#006600")
        else:
            self._set_loop_test_feedback(f"{phase} 相回路连通正常，请继续测量其余相别。", "#006600")

    def reset_loop_test(self):
        self._ctrl.loop_test_state = self.create_loop_test_state()

    def is_loop_test_complete(self):
        records = self._ctrl.loop_test_state.records
        return all(records[ph] is not None for ph in ('A', 'B', 'C'))

    def finalize_loop_test(self):
        records = self._ctrl.loop_test_state.records
        if not all(records[ph] is not None for ph in ('A', 'B', 'C')):
            self._set_loop_test_feedback(
                '请先完成 A/B/C 三相回路连通性记录，再点击\u201c完成第一步测试\u201d。', "red")
            return
        self._ctrl.loop_test_state.completed = True
        self._set_loop_test_feedback(
            "第一步【回路连通性测试】已确认完成，后续操作将不再影响该步骤状态。", "#006600")

    def get_loop_test_blockers(self):
        return [text for text, done in self.get_loop_test_steps() if not done]
