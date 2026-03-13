"""
services/sync_test_service.py
同步功能测试服务
"""

from domain.enums import BreakerPosition


class SyncTestService:
    """
    同步功能测试业务逻辑。
    从 PowerSyncController 提取，保持完全相同的方法签名和逻辑。
    """

    def __init__(self, ctrl):
        self._ctrl = ctrl

    # ── 状态工厂 ──────────────────────────────────────────────────────────────
    def _create_sync_test_state(self):
        return {
            'round1_done': False,   # Gen1基准 → Gen2同步
            'round2_done': False,   # Gen2基准 → Gen1同步
            'completed': False,
            'feedback': "请先完成第一步（回路测试）和第二步（PT测试），再进行同步功能测试。",
            'feedback_color': '#444444',
        }

    def _set_sync_test_feedback(self, message, color='#444444'):
        self._ctrl.sync_test_state['feedback'] = message
        self._ctrl.sync_test_state['feedback_color'] = color

    def _is_gen_synced(self, follower, master, freq_tol=0.5, amp_tol=500.0):
        """判断 follower 是否已同步到 master 的频率和幅值。"""
        return (abs(follower.freq - master.freq) < freq_tol and
                abs(follower.amp - master.amp) < amp_tol)

    def get_sync_test_steps(self):
        sim = self._ctrl.sim_state
        gen1, gen2 = sim.gen1, sim.gen2
        p = self._ctrl.physics
        state = self._ctrl.sync_test_state

        loop_done = self._ctrl.is_loop_test_complete()
        pt_done   = self._ctrl.is_pt_exam_recorded(1) and self._ctrl.is_pt_exam_recorded(2)

        # 第一轮实时状态
        r1_master_ok    = (gen1.breaker_closed and
                           gen1.breaker_position == BreakerPosition.WORKING and
                           gen1.mode == "manual")
        r1_follower_ok  = gen2.mode == "auto"
        r1_synced       = (r1_master_ok and r1_follower_ok and
                           self._is_gen_synced(gen2, gen1))

        # 第二轮实时状态
        r2_master_ok    = (gen2.breaker_closed and
                           gen2.breaker_position == BreakerPosition.WORKING and
                           gen2.mode == "manual" and
                           getattr(p, 'bus_reference_gen', None) == 2)
        r2_follower_ok  = gen1.mode == "auto"
        r2_synced       = (r2_master_ok and r2_follower_ok and
                           self._is_gen_synced(gen1, gen2))

        steps = [
            ("1. 前提：第一步回路连通性测试已完成",
             loop_done),
            ("2. 前提：第二步 PT 二次端子压差测试已完成（Gen1 & Gen2）",
             pt_done),
            ("3. [第一轮] 将 Gen 1 切至手动模式并在工作位置合闸（建立母排电压）",
             r1_master_ok or state['round1_done']),
            ("4. [第一轮] 将 Gen 2 切至自动（Auto）同步模式",
             r1_follower_ok or state['round1_done']),
            ("5. [第一轮] 确认 Gen 2 已同步完成（频率/幅值与 Gen 1 匹配）",
             r1_synced or state['round1_done']),
            ("6. [第一轮] 记录结果：Gen 1 基准 → Gen 2 同步完成",
             state['round1_done']),
            ("7. [第二轮] 断开 Gen 1，将 Gen 2 切至手动模式并合闸（互换基准）",
             r2_master_ok or state['round2_done']),
            ("8. [第二轮] 将 Gen 1 切至自动（Auto）同步模式",
             r2_follower_ok or state['round2_done']),
            ("9. [第二轮] 确认 Gen 1 已同步完成（频率/幅值与 Gen 2 匹配）",
             r2_synced or state['round2_done']),
            ("10. [第二轮] 记录结果：Gen 2 基准 → Gen 1 同步完成",
             state['round2_done']),
        ]
        if state.get('completed'):
            return [(text, True) for text, _ in steps]
        return steps

    def record_sync_round(self, round_num):
        sim = self._ctrl.sim_state
        gen1, gen2 = sim.gen1, sim.gen2
        p = self._ctrl.physics
        state = self._ctrl.sync_test_state

        # 前提：第一步、第二步必须已完成
        if not self._ctrl.is_loop_test_complete():
            self._set_sync_test_feedback("请先完成第一步【回路连通性测试】。", "red")
            return
        if not (self._ctrl.is_pt_exam_recorded(1) and self._ctrl.is_pt_exam_recorded(2)):
            self._set_sync_test_feedback(
                "请先完成第二步【PT二次端子压差测试】（Gen1 和 Gen2 均需完成）。", "red")
            return

        if round_num == 1:
            if not (gen1.breaker_closed and
                    gen1.breaker_position == BreakerPosition.WORKING and
                    gen1.mode == "manual"):
                self._set_sync_test_feedback(
                    "请先将 Gen 1 切至手动模式并在工作位置合闸，建立母排电压。", "red")
                return
            if gen2.mode != "auto":
                self._set_sync_test_feedback(
                    "请先将 Gen 2 切至自动（Auto）同步模式。", "red")
                return
            if not self._is_gen_synced(gen2, gen1):
                df = abs(gen2.freq - gen1.freq)
                dv = abs(gen2.amp - gen1.amp)
                self._set_sync_test_feedback(
                    f"Gen 2 尚未同步完成（Δf={df:.2f} Hz，ΔV={dv:.0f} V），请等待同步后再记录。",
                    "red")
                return
            state['round1_done'] = True
            self._set_sync_test_feedback(
                "第一轮记录成功：Gen 1 作基准，Gen 2 同步功能正常。"
                "请断开 Gen 1，互换角色进行第二轮测试。", "#006600")

        elif round_num == 2:
            if not state['round1_done']:
                self._set_sync_test_feedback(
                    "请先完成第一轮测试并记录，再进行第二轮。", "red")
                return
            if not (gen2.breaker_closed and
                    gen2.breaker_position == BreakerPosition.WORKING and
                    gen2.mode == "manual" and
                    getattr(p, 'bus_reference_gen', None) == 2):
                self._set_sync_test_feedback(
                    "请先断开 Gen 1，将 Gen 2 切至手动模式并在工作位置合闸作为新基准。", "red")
                return
            if gen1.mode != "auto":
                self._set_sync_test_feedback(
                    "请先将 Gen 1 切至自动（Auto）同步模式。", "red")
                return
            if not self._is_gen_synced(gen1, gen2):
                df = abs(gen1.freq - gen2.freq)
                dv = abs(gen1.amp - gen2.amp)
                self._set_sync_test_feedback(
                    f"Gen 1 尚未同步完成（Δf={df:.2f} Hz，ΔV={dv:.0f} V），请等待同步后再记录。",
                    "red")
                return
            state['round2_done'] = True
            self._set_sync_test_feedback(
                "第二轮记录成功：Gen 2 作基准，Gen 1 同步功能正常。两台发电机同步功能测试全部完成！",
                "#006600")

    def reset_sync_test(self):
        self._ctrl.sync_test_state = self._create_sync_test_state()

    def is_sync_test_complete(self):
        return (self._ctrl.sync_test_state['round1_done'] and
                self._ctrl.sync_test_state['round2_done'])

    def is_sync_test_rounds_done(self):
        return (self._ctrl.sync_test_state['round1_done'] and
                self._ctrl.sync_test_state['round2_done'])

    def finalize_sync_test(self):
        if not self.is_sync_test_rounds_done():
            self._set_sync_test_feedback('请先完成并记录两轮同步测试，再点击\u201c完成第三步测试\u201d。', "red")
            return
        self._ctrl.sync_test_state['completed'] = True
        self._set_sync_test_feedback("第三步【同步功能测试】已确认完成，系统恢复正常自动合闸逻辑。", "#006600")

    def get_sync_test_blockers(self):
        return [text for text, done in self.get_sync_test_steps() if not done]
