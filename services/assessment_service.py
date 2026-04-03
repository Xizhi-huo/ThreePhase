from datetime import datetime
from typing import Dict, List, Set

from domain.assessment import (
    AssessmentPenalty,
    AssessmentResult,
    AssessmentScoreItem,
    AssessmentSession,
)
from domain.fault_scenarios import SCENARIOS


class AssessmentService:
    """Build a stricter assessment result from the recorded event stream and controller state."""

    def __init__(self, ctrl):
        self._ctrl = ctrl

    def build_result(self, session: AssessmentSession) -> AssessmentResult:
        now = datetime.now()
        finished_at = now.isoformat(timespec="seconds")
        started_at_dt = datetime.fromisoformat(session.started_at)
        elapsed_seconds = max(0, int((now - started_at_dt).total_seconds()))

        events = session.events
        penalties: List[AssessmentPenalty] = []
        score_items: List[AssessmentScoreItem] = []
        scene_info = SCENARIOS.get(session.scene_id, {})
        detection_step = scene_info.get("detection_step")
        expected_targets = self._expected_blackbox_targets(scene_info)

        def add_penalty(code: str, message: str, score_delta: int, step: int = 0, timestamp: str = ""):
            if score_delta == 0:
                return
            penalties.append(
                AssessmentPenalty(
                    code=code,
                    message=message,
                    score_delta=score_delta,
                    step=step,
                    timestamp=timestamp,
                )
            )

        def add_score_item(
            code: str,
            title: str,
            category: str,
            max_score: int,
            earned_score: int,
            step: int = 0,
            detail: str = "",
        ):
            if earned_score >= max_score:
                status = "通过"
            elif earned_score <= 0:
                status = "未通过"
            else:
                status = "部分扣分"
            score_items.append(
                AssessmentScoreItem(
                    code=code,
                    title=title,
                    category=category,
                    status=status,
                    max_score=max_score,
                    earned_score=earned_score,
                    step=step,
                    detail=detail,
                )
            )

        def count(event_type: str) -> int:
            return sum(1 for event in events if event.event_type == event_type)

        def all_events(event_type: str):
            return [event for event in events if event.event_type == event_type]

        def first(event_type: str):
            for event in events:
                if event.event_type == event_type:
                    return event
            return None

        def happened_before(lhs, rhs) -> bool:
            if lhs is None:
                return False
            if rhs is None:
                return True
            return lhs.timestamp <= rhs.timestamp

        blocked_events = all_events("advance_blocked")
        finalize_rejected = [
            event for event in all_events("step_finalize_attempted")
            if not bool(event.payload.get("allowed", False))
        ]
        gate_block_events = all_events("assessment_gate_blocked")
        invalid_measurements = count("measurement_invalid")
        blackbox_failed_confirms = sum(
            1 for event in all_events("blackbox_confirm_attempted")
            if not bool(event.payload.get("success", False))
        )
        blackbox_swap_count = count("blackbox_swap")
        serious_misoperations = count("hazard_action")
        blackbox_open_events = all_events("blackbox_opened")
        opened_targets = []
        for event in blackbox_open_events:
            target = event.payload.get("target")
            if target:
                opened_targets.append(target)
        opened_target_set: Set[str] = set(opened_targets)

        loop_complete = self._ctrl.is_loop_test_complete()
        voltage_complete = self._ctrl.is_pt_voltage_check_complete()
        phase_complete = self._ctrl.is_pt_phase_check_complete()
        pt_exam_complete = (
            self._ctrl.pt_exam_states[1].completed
            and self._ctrl.pt_exam_states[2].completed
        )
        closure_complete = self._ctrl.is_assessment_closed_loop_ready()

        fault_detected_event = first("fault_detected")
        fault_repaired_event = first("fault_repaired")
        first_gate_block = first("assessment_gate_blocked")
        first_blackbox_open = first("blackbox_opened")

        step_enter_order = [event.step for event in all_events("step_entered")]
        step_sequence_errors = 0
        previous_step = None
        for step in step_enter_order:
            if previous_step is not None and (step < previous_step or step - previous_step > 1):
                step_sequence_errors += 1
            previous_step = step

        detected_before_gate = happened_before(fault_detected_event, first_gate_block)
        blackbox_open_before_gate = happened_before(first_blackbox_open, first_gate_block)

        # A1-A3 流程纪律
        a1_penalty = min(8, step_sequence_errors * 2)
        a1_score = 8 - a1_penalty
        add_penalty("A1", "存在乱序推进或异常步骤跳转。", -a1_penalty)
        add_score_item(
            "A1", "按顺序推进", "流程纪律", 8, a1_score, detail=
            "步骤推进顺序正确。" if a1_score == 8 else f"检测到 {step_sequence_errors} 次乱序或跳步。"
        )

        a2_penalty = min(6, len(finalize_rejected) * 2)
        a2_score = 6 - a2_penalty
        add_penalty("A2", "异常后仍尝试完成当前步骤。", -a2_penalty, finalize_rejected[0].step if finalize_rejected else 0)
        add_score_item(
            "A2", "异常后停留当前步骤", "流程纪律", 6, a2_score, detail=
            "未出现错误完成步骤尝试。" if a2_score == 6 else f"共发生 {len(finalize_rejected)} 次错误完成步骤尝试。"
        )

        a3_penalty = min(6, len(gate_block_events) * 2)
        a3_score = 6 - a3_penalty
        add_penalty("A3", "闭环未完成仍尝试结束考核或进入后续流程。", -a3_penalty, 4)
        add_score_item(
            "A3", "遵守闭环门禁", "流程纪律", 6, a3_score, 4, detail=
            "未触发第四步闭环门禁。" if a3_score == 6 else f"第四步闭环门禁触发 {len(gate_block_events)} 次。"
        )

        # B1-B4 测量完整性
        b1_score = 5 if loop_complete else 0
        if not loop_complete:
            add_penalty("B1", "第一步测量记录不完整。", -5, 1)
        add_score_item("B1", "第一步记录完整", "测量完整性", 5, b1_score, 1, "回路记录齐全。" if b1_score else "回路记录存在缺项。")

        b2_score = 5 if voltage_complete else 0
        if not voltage_complete:
            add_penalty("B2", "第二步测量记录不完整。", -5, 2)
        add_score_item("B2", "第二步记录完整", "测量完整性", 5, b2_score, 2, "PT 电压记录齐全。" if b2_score else "PT 电压记录存在缺项。")

        b3_score = 5 if phase_complete else 0
        if not phase_complete:
            add_penalty("B3", "第三步测量记录不完整。", -5, 3)
        add_score_item("B3", "第三步记录完整", "测量完整性", 5, b3_score, 3, "PT 相序记录齐全。" if b3_score else "PT 相序记录存在缺项。")

        b4_score = 5 if pt_exam_complete else 0
        if not pt_exam_complete:
            add_penalty("B4", "第四步测量记录不完整。", -5, 4)
        add_score_item("B4", "第四步记录完整", "测量完整性", 5, b4_score, 4, "压差记录齐全。" if b4_score else "压差记录存在缺项。")

        # C1-C2 异常识别
        if not session.scene_id:
            c1_score = 10
        else:
            c1_score = 10 if detected_before_gate else 0
            if c1_score == 0:
                add_penalty("C1", "未在第四步闭环门禁前形成有效异常识别。", -10)
        add_score_item(
            "C1", "前四步内识别出异常", "异常识别", 10, c1_score, getattr(fault_detected_event, "step", 0),
            "在门禁拦截前已识别异常。" if c1_score else "直到系统门禁拦截后仍未形成有效异常识别。"
        )

        hidden_fault = bool(session.scene_id) and detection_step is None and bool(expected_targets)
        if hidden_fault:
            c2_score = 10 if blackbox_open_before_gate else 0
            if c2_score == 0:
                add_penalty("C2", "隐性故障未在系统拦截前主动识别。", -10)
            c2_detail = "已在系统拦截前主动进入黑盒确认隐性故障。" if c2_score else "依赖系统闭环门禁后才意识到仍有隐性故障。"
        else:
            c2_score = 10
            c2_detail = "本场景不属于隐性故障，或已满足识别要求。"
        add_score_item("C2", "隐性故障识别", "异常识别", 10, c2_score, detail=c2_detail)

        # D1-D3 故障定位
        if not expected_targets:
            d1_score = 8
            d1_detail = "本场景无额外黑盒定位要求。"
        else:
            expected_set = set(expected_targets)
            if opened_target_set == expected_set:
                d1_score = 8
                d1_detail = "打开黑盒范围与场景所需定位层级一致。"
            elif opened_target_set & expected_set:
                d1_score = 4
                d1_detail = "命中了部分正确定位层级，但仍存在额外或缺失的黑盒打开。"
                add_penalty("D1", "故障定位层级不够准确。", -4)
            else:
                d1_score = 0
                d1_detail = "未打开正确的黑盒目标，定位层级错误。"
                add_penalty("D1", "故障定位层级错误。", -8)
        add_score_item("D1", "定位到正确设备层级", "故障定位", 8, d1_score, 4, d1_detail)

        if not expected_targets:
            d2_score = 6
            d2_detail = "本场景无黑盒定位提示依赖问题。"
        else:
            d2_score = 6 if blackbox_open_before_gate else 0
            d2_detail = "在系统门禁前完成了黑盒确认。" if d2_score else "在系统门禁拦截后才进入黑盒确认，存在依赖系统提示定位的情况。"
            if d2_score == 0:
                add_penalty("D2", "依赖系统门禁后才进入黑盒确认。", -6)
        add_score_item("D2", "不依赖系统提示定位", "故障定位", 6, d2_score, 4, d2_detail)

        if not expected_targets:
            d3_score = 6
            d3_detail = "本场景无额外黑盒范围控制要求。"
        else:
            extra_targets = max(0, len(opened_target_set - set(expected_targets)))
            d3_penalty = min(6, extra_targets * 2)
            d3_score = 6 - d3_penalty
            if d3_penalty:
                add_penalty("D3", "打开了不必要的黑盒目标。", -d3_penalty)
            d3_detail = "黑盒查看范围合理。" if d3_score == 6 else f"多打开了 {extra_targets} 个无关黑盒。"
        add_score_item("D3", "黑盒开启范围合理", "故障定位", 6, d3_score, 4, d3_detail)

        # E1-E3 黑盒修复
        repair_required = bool(expected_targets)
        if not repair_required:
            e1_score = 8
            e1_detail = "本场景不依赖黑盒接线修复闭环。"
        else:
            e1_score = 8 if self._ctrl.sim_state.fault_config.repaired else 0
            if e1_score == 0:
                add_penalty("E1", "最终未完成正确修复。", -8, 4)
            e1_detail = "黑盒目标已全部恢复正确。" if e1_score else "考核结束时仍存在未完成修复的黑盒目标。"
        add_score_item("E1", "修复结果正确", "黑盒修复", 8, e1_score, 4, e1_detail)

        if not repair_required:
            e2_score = 4
            e2_detail = "本场景无额外修复步骤要求。"
        else:
            if self._ctrl.sim_state.fault_config.repaired and opened_target_set.issuperset(set(expected_targets)):
                e2_score = 4
                e2_detail = "修复步骤与场景要求一致。"
            elif self._ctrl.sim_state.fault_config.repaired:
                e2_score = 2
                e2_detail = "虽然完成了修复，但修复过程存在绕行或定位偏差。"
                add_penalty("E2", "修复步骤合理性不足。", -2)
            else:
                e2_score = 0
                e2_detail = "未形成有效修复闭环。"
                add_penalty("E2", "未形成有效修复闭环。", -4)
        add_score_item("E2", "修复步骤合理", "黑盒修复", 4, e2_score, 4, e2_detail)

        e3_penalty = min(3, blackbox_failed_confirms + max(0, blackbox_swap_count - 2))
        e3_score = 3 - e3_penalty
        if e3_penalty:
            add_penalty("E3", "黑盒操作存在无效交换或错误确认。", -e3_penalty)
        add_score_item(
            "E3", "黑盒操作效率", "黑盒修复", 3, e3_score, 4,
            "黑盒操作效率正常。" if e3_score == 3 else f"交换 {blackbox_swap_count} 次，错误确认 {blackbox_failed_confirms} 次。"
        )

        # F1-F2 效率与规范性
        if elapsed_seconds <= 420:
            f1_score = 3
            f1_detail = "总耗时控制良好。"
        elif elapsed_seconds <= 600:
            f1_score = 2
            f1_detail = "总耗时略长。"
            add_penalty("F1", "总耗时略长。", -1)
        elif elapsed_seconds <= 900:
            f1_score = 1
            f1_detail = "总耗时明显偏长。"
            add_penalty("F1", "总耗时明显偏长。", -2)
        else:
            f1_score = 0
            f1_detail = "总耗时严重超标。"
            add_penalty("F1", "总耗时严重超标。", -3)
        add_score_item("F1", "总耗时", "效率与规范性", 3, f1_score, detail=f1_detail)

        f2_penalty = min(2, max(0, invalid_measurements - 2))
        f2_score = 2 - f2_penalty
        if f2_penalty:
            add_penalty("F2", "无效重复测量次数偏多。", -f2_penalty)
        add_score_item(
            "F2", "无效重复测量控制", "效率与规范性", 2, f2_score,
            detail="无效重复测量控制正常。" if f2_score == 2 else f"无效测量共 {invalid_measurements} 次。"
        )

        step_scores = {
            "flow_discipline": a1_score + a2_score + a3_score,
            "measurement_completeness": b1_score + b2_score + b3_score + b4_score,
            "anomaly_identification": c1_score + c2_score,
            "fault_localization": d1_score + d2_score + d3_score,
            "blackbox_repair": e1_score + e2_score + e3_score,
            "efficiency": f1_score + f2_score,
        }
        step_max_scores = {
            "flow_discipline": 20,
            "measurement_completeness": 20,
            "anomaly_identification": 20,
            "fault_localization": 20,
            "blackbox_repair": 15,
            "efficiency": 5,
        }
        total_score = sum(step_scores.values())

        veto_reason = None
        if serious_misoperations > 0:
            veto_reason = "存在严重误操作"
        elif not closure_complete:
            veto_reason = "第四步结束时仍未完成正确修复"
        elif not (loop_complete and voltage_complete and phase_complete and pt_exam_complete):
            veto_reason = "前四步记录不完整，无法形成有效考核"

        passed = veto_reason is None and total_score >= 60

        metrics: Dict[str, object] = {
            "step_entered_order": [event.step for event in all_events("step_entered")],
            "step_finalize_attempts": count("step_finalize_attempted"),
            "blocked_advances": len(blocked_events),
            "gate_blocks": len(gate_block_events),
            "measurements_recorded": count("measurement_recorded"),
            "invalid_measurements": invalid_measurements,
            "blackboxes_opened": opened_targets,
            "blackbox_swap_count": blackbox_swap_count,
            "blackbox_failed_confirms": blackbox_failed_confirms,
            "fault_detected_at_step": getattr(fault_detected_event, "step", 0),
            "fault_repaired_at": getattr(fault_repaired_event, "timestamp", ""),
            "serious_misoperations": serious_misoperations,
        }

        if veto_reason:
            summary = f"未通过：{veto_reason}"
        elif total_score >= 90:
            summary = "通过：识别、定位与修复过程均较严谨。"
        elif total_score >= 75:
            summary = "通过：完成了有效闭环，但过程上仍有扣分点。"
        elif total_score >= 60:
            summary = "通过：达到了基本考核要求。"
        else:
            summary = "未通过：分数未达到及格线。"

        return AssessmentResult(
            session_id=session.session_id,
            scene_id=session.scene_id,
            mode=session.mode,
            started_at=session.started_at,
            finished_at=finished_at,
            elapsed_seconds=elapsed_seconds,
            passed=passed,
            total_score=total_score,
            max_score=100,
            veto_reason=veto_reason,
            step_scores=step_scores,
            step_max_scores=step_max_scores,
            score_items=score_items,
            penalties=penalties,
            metrics=metrics,
            summary=summary,
        )

    @staticmethod
    def _expected_blackbox_targets(scene_info: Dict) -> List[str]:
        params = scene_info.get("params", {}) if scene_info else {}
        targets: List[str] = []
        if any(params.get(key) is not None for key in ("g1_blackbox_order", "p1_pri_blackbox_order", "pt2_sec_blackbox_order")):
            targets.extend(["G1", "PT1"])
        if params.get("g2_blackbox_order") is not None:
            targets.append("G2")
        return targets
