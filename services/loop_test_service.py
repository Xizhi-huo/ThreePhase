"""
services/loop_test_service.py
回路连通性测试服务
"""

from domain.enums import BreakerPosition
from domain.assessment import AssessmentEventType
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
        self._ctrl.set_loop_test_feedback(message, color)

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
            ("6. 开启万用表，在母排拓扑页进行三相通断测试",
             sim.multimeter_mode),
            ("7. 逐相记录 A/B/C 通断结果（导通 ≈0Ω / 断路 ∞Ω）",
             all_rec),
        ]
        if state.completed:
            return [(text, True) for text, _ in steps]
        return steps

    def record_loop_measurement(self, phase):
        sim = self._ctrl.sim_state
        gen1, gen2 = sim.gen1, sim.gen2
        phase = phase.upper()
        def _record_invalid(reason):
            self._ctrl.assessment_coord.append_assessment_event(
                AssessmentEventType.MEASUREMENT_INVALID,
                step=1,
                target='loop',
                point=phase,
                reason=reason,
            )

        if sim.grounding_mode != "断开":
            _record_invalid("grounding_not_disconnected")
            self._set_loop_test_feedback('请先断开中性点小电阻连接（接地系统选"断开"）。', "red")
            return
        if gen1.mode != "manual" or gen2.mode != "manual":
            _record_invalid("generators_not_manual")
            self._set_loop_test_feedback("请先将两台发电机都切至手动（Manual）模式。", "red")
            return
        if gen1.running or gen2.running:
            _record_invalid("generator_running")
            self._set_loop_test_feedback(
                "通断测试须在发电机停机状态下进行（万用表靠自身电池注入微小电流，"
                "发电机运行时高压会干扰测量并损坏万用表）。", "red")
            return
        if not (gen1.breaker_closed and gen1.breaker_position == BreakerPosition.WORKING):
            _record_invalid("gen1_not_closed")
            self._set_loop_test_feedback("请先将 Gen 1 切至工作位置并合闸。", "red")
            return
        if not (gen2.breaker_closed and gen2.breaker_position == BreakerPosition.WORKING):
            _record_invalid("gen2_not_closed")
            self._set_loop_test_feedback("请先将 Gen 2 切至工作位置并合闸。", "red")
            return
        if not sim.multimeter_mode:
            _record_invalid("multimeter_disabled")
            self._set_loop_test_feedback("请先开启万用表。", "red")
            return

        current_phase = self._get_current_loop_phase_match()
        if current_phase != phase:
            _record_invalid("probe_phase_mismatch")
            if current_phase is None:
                msg = (f"当前表笔未正确对准 {phase} 相回路，"
                       f"请在母排拓扑页将表笔分别放在 G1 与 G2 的 {phase} 相回路测点。")
            else:
                msg = f"当前表笔对准的是 {current_phase} 相，请记录对应相别或重新放置表笔。"
            self._set_loop_test_feedback(msg, "red")
            return

        meter_status = getattr(self._ctrl.physics, 'meter_status', 'idle')
        if meter_status not in ('ok', 'danger'):
            _record_invalid("invalid_meter_status")
            self._set_loop_test_feedback("测量结果无效，请确认表笔放在 G1 与 G2 的同相回路测点上。", "red")
            return

        # 记录测量结果（导通/断路均可记录，故障分析在完成阶段进行）
        self._ctrl.record_loop_test_result(
            phase,
            meter_status,
            self._ctrl.physics.meter_reading,
        )
        self._ctrl.assessment_coord.append_assessment_event(
            AssessmentEventType.MEASUREMENT_RECORDED,
            step=1,
            target='loop',
            point=phase,
            value=meter_status,
        )
        all_rec = all(self._ctrl.loop_test_state.records[ph] is not None for ph in ('A', 'B', 'C'))
        if meter_status == 'ok':
            if all_rec:
                self._set_loop_test_feedback(
                    "三相已全部记录，请点击「完成第一步测试」确认结果。", "#006600")
            else:
                self._set_loop_test_feedback(f"{phase} 相导通 [≈0Ω]，请继续测量其余相别。", "#006600")
        else:
            # 断路结果：记录但给出故障提示
            if all_rec:
                self._set_loop_test_feedback(
                    f"{phase} 相断路 [∞Ω]，三相已全部记录，请点击「完成第一步测试」查看故障分析。",
                    "#cc6600")
            else:
                self._set_loop_test_feedback(
                    f"{phase} 相断路 [∞Ω]（疑似接线错误），已记录结果，请继续测量其余相别。",
                    "#cc6600")

    def reset_loop_test(self):
        self._ctrl.loop_test_state = self.create_loop_test_state()

    def is_loop_test_complete(self):
        """流程门禁：只有用户点击"完成第一步测试"后才返回 True。"""
        return self._ctrl.loop_test_state.completed

    def _are_loop_records_complete(self):
        """内部辅助：三相记录是否齐全（用于 finalize 前置校验）。"""
        records = self._ctrl.loop_test_state.records
        return all(records[ph] is not None for ph in ('A', 'B', 'C'))

    def finalize_loop_test(self):
        if not self._are_loop_records_complete():
            self._set_loop_test_feedback(
                '请先完成 A/B/C 三相回路连通性记录，再点击"完成第一步测试"。', "red")
            return
        # 检查是否存在断路故障相
        records = self._ctrl.loop_test_state.records
        fault_phases = [ph for ph in ('A', 'B', 'C')
                        if records[ph] and records[ph]['status'] != 'ok']
        fc = self._ctrl.sim_state.fault_config
        fault_training = (
            fc.active and fc.detected and not fc.repaired
            and self._ctrl.flow_mgr.can_advance_with_fault()
        )
        if fault_phases and not fault_training:
            # 当前流程策略要求先纠正异常后再完成该步
            fault_str = '、'.join(fault_phases)
            if self._ctrl.flow_mgr.should_show_diagnostic_hints():
                msg = (
                    f"回路测试发现故障：{fault_str} 相断路 [∞Ω]，说明对应相接线错误。"
                    f"请检查并纠正接线后重置重测。"
                )
            else:
                msg = (
                    f"回路测试发现异常：{fault_str} 相断路 [∞Ω]。"
                    f"请继续排查并在修正后重新测量。"
                )
            self._set_loop_test_feedback(msg, "red")
            return
        self._ctrl.exit_loop_test_mode()   # 退出回路检查模式，恢复断路器联锁
        self._ctrl.mark_loop_test_completed()
        if fault_phases:
            # 当前流程策略允许带异常完成，提示继续后续步骤
            fault_str = '、'.join(fault_phases)
            self._set_loop_test_feedback(
                f"第一步完成（发现异常）：{fault_str} 相断路 [∞Ω]，"
                f"已记录故障证据，请继续后续步骤收集更多数据，将在第五步前统一检修。",
                "#92400e")
        else:
            self._set_loop_test_feedback(
                "第一步【回路连通性测试】已确认完成：三相回路全部导通 [≈0Ω]，接线正确。",
                "#006600")

    def get_loop_test_blockers(self):
        return [text for text, done in self.get_loop_test_steps() if not done]

    def are_loop_records_complete(self):
        """供 UI 步骤显示使用：三相是否已记录（未必已点完成按钮）。"""
        return self._are_loop_records_complete()
