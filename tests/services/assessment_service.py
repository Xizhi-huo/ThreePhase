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
    """Build a 30-item assessment result from the recorded event stream."""

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
        expected_target_set = set(expected_targets)
        expected_device_set = {target.split('.', 1)[0] for target in expected_targets}
        snapshot = session.state_snapshot or {}

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
            penalty_message: str = "",
        ):
            earned_score = max(0, min(max_score, earned_score))
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
            lost_score = max_score - earned_score
            if lost_score > 0 and penalty_message:
                add_penalty(code, penalty_message, -lost_score, step)

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

        def first_step_index(step: int):
            for idx, event in enumerate(step_enter_events):
                if event.step == step:
                    return idx
            return None

        def trio_completion_score(count_value: int) -> int:
            if count_value >= 3:
                return 3
            if count_value == 2:
                return 2
            if count_value == 1:
                return 1
            return 0

        def nine_group_completion_score(count_value: int) -> int:
            if count_value >= 9:
                return 4
            if count_value >= 7:
                return 3
            if count_value >= 5:
                return 2
            if count_value >= 3:
                return 1
            return 0

        def count_present(records: Dict[str, object]) -> int:
            return sum(1 for value in records.values() if value is not None)

        blocked_events = all_events("advance_blocked")
        finalize_rejected = [
            event for event in all_events("step_finalize_attempted")
            if not bool(event.payload.get("allowed", False))
        ]
        gate_block_events = all_events("assessment_gate_blocked")
        invalid_events = all_events("measurement_invalid")
        invalid_by_step = {
            1: sum(1 for event in invalid_events if event.step == 1),
            2: sum(1 for event in invalid_events if event.step == 2),
            3: sum(1 for event in invalid_events if event.step == 3),
            4: sum(1 for event in invalid_events if event.step == 4),
        }
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
        early_pt_blackbox_open_events = [
            event for event in blackbox_open_events
            if event.step in (1, 2) and event.payload.get("target") in {"PT1", "PT3"}
        ]
        opened_target_set: Set[str] = set(opened_targets)
        touched_layers = set()
        for event in all_events("blackbox_swap"):
            target = event.payload.get("target")
            layer = event.payload.get("layer")
            if target and layer:
                touched_layers.add(f"{target}.{layer}")
        for event in all_events("blackbox_confirm_attempted"):
            target = event.payload.get("target")
            for layer in event.payload.get("layers", []):
                touched_layers.add(f"{target}.{layer}")

        step_enter_events = all_events("step_entered")
        blocked_by_step = {
            1: sum(1 for event in blocked_events if event.payload.get("from_step") == 1 or event.step == 1),
            2: sum(1 for event in blocked_events if event.payload.get("from_step") == 2 or event.step == 2),
            3: sum(1 for event in blocked_events if event.payload.get("from_step") == 3 or event.step == 3),
            4: sum(1 for event in blocked_events if event.payload.get("from_step") == 4 or event.step == 4),
        }
        finalize_rejected_by_step = {
            1: sum(1 for event in finalize_rejected if event.step == 1),
            2: sum(1 for event in finalize_rejected if event.step == 2),
            3: sum(1 for event in finalize_rejected if event.step == 3),
            4: sum(1 for event in finalize_rejected if event.step == 4),
        }

        fault_detected_event = first("fault_detected")
        fault_repaired_event = first("fault_repaired")
        first_gate_block = first("assessment_gate_blocked")
        first_blackbox_open = first("blackbox_opened")

        detected_before_gate = happened_before(fault_detected_event, first_gate_block)
        blackbox_open_before_gate = happened_before(first_blackbox_open, first_gate_block)
        hidden_fault = bool(session.scene_id) and detection_step is None and bool(expected_targets)

        loop_records = snapshot.get('loop_records', self._ctrl.loop_test_state.records)
        voltage_records = snapshot.get('voltage_records', self._ctrl.pt_voltage_check_state.records)
        phase_records = snapshot.get('phase_records', self._ctrl.pt_phase_check_state.records)
        pt_exam_records = snapshot.get('pt_exam_records', {})
        pt_exam_records_1 = pt_exam_records.get(1, self._ctrl.pt_exam_states[1].records)
        pt_exam_records_2 = pt_exam_records.get(2, self._ctrl.pt_exam_states[2].records)

        completed = snapshot.get('completed', {})
        loop_complete = bool(completed.get('loop', self._ctrl.is_loop_test_complete()))
        voltage_complete = bool(completed.get('voltage', self._ctrl.is_pt_voltage_check_complete()))
        phase_complete = bool(completed.get('phase', self._ctrl.is_pt_phase_check_complete()))
        pt_exam_complete = (
            bool(completed.get('pt_exam_1', self._ctrl.pt_exam_states[1].completed))
            and bool(completed.get('pt_exam_2', self._ctrl.pt_exam_states[2].completed))
        )
        closure_complete = bool(completed.get('closure', self._ctrl.is_assessment_closed_loop_ready()))
        repair_required = bool(expected_targets)
        fault_snapshot = snapshot.get('fault', {})
        repaired = bool(fault_snapshot.get('repaired', self._ctrl.sim_state.fault_config.repaired))

        pt1_voltage_count = sum(1 for key in ("PT1_AB", "PT1_BC", "PT1_CA") if voltage_records.get(key) is not None)
        pt2_voltage_count = sum(1 for key in ("PT2_AB", "PT2_BC", "PT2_CA") if voltage_records.get(key) is not None)
        pt3_voltage_count = sum(1 for key in ("PT3_AB", "PT3_BC", "PT3_CA") if voltage_records.get(key) is not None)
        pt1_phase_count = sum(1 for key in ("PT1_A", "PT1_B", "PT1_C") if phase_records.get(key) is not None)
        pt3_phase_count = sum(1 for key in ("PT3_A", "PT3_B", "PT3_C") if phase_records.get(key) is not None)
        gen1_exam_count = count_present(pt_exam_records_1)
        gen2_exam_count = count_present(pt_exam_records_2)

        score_context = {
            "session": session,
            "add_score_item": add_score_item,
            "first_step_index": first_step_index,
            "blocked_events": blocked_events,
            "finalize_rejected": finalize_rejected,
            "gate_block_events": gate_block_events,
            "loop_records": loop_records,
            "loop_complete": loop_complete,
            "count_present": count_present,
            "trio_completion_score": trio_completion_score,
            "nine_group_completion_score": nine_group_completion_score,
            "pt1_voltage_count": pt1_voltage_count,
            "pt2_voltage_count": pt2_voltage_count,
            "pt3_voltage_count": pt3_voltage_count,
            "detection_step": detection_step,
            "fault_detected_event": fault_detected_event,
            "pt1_phase_count": pt1_phase_count,
            "pt3_phase_count": pt3_phase_count,
            "invalid_by_step": invalid_by_step,
            "gen1_exam_count": gen1_exam_count,
            "gen2_exam_count": gen2_exam_count,
            "finalize_rejected_by_step": finalize_rejected_by_step,
            "hidden_fault": hidden_fault,
            "blackbox_open_before_gate": blackbox_open_before_gate,
            "detected_before_gate": detected_before_gate,
            "expected_targets": expected_targets,
            "expected_target_set": expected_target_set,
            "expected_device_set": expected_device_set,
            "opened_target_set": opened_target_set,
            "touched_layers": touched_layers,
            "repair_required": repair_required,
            "repaired": repaired,
            "blackbox_failed_confirms": blackbox_failed_confirms,
            "blackbox_swap_count": blackbox_swap_count,
            "elapsed_seconds": elapsed_seconds,
            "invalid_events": invalid_events,
        }
        self._score_flow_discipline(score_context)
        self._score_loop_test(score_context)
        self._score_pt_voltage_check(score_context)
        self._score_pt_phase_check(score_context)
        self._score_pt_exam(score_context)
        self._score_fault_localization(score_context)
        self._score_blackbox_repair(score_context)
        self._score_efficiency(score_context)

        step_scores, step_max_scores = self._build_step_score_summaries(score_items)
        total_score = sum(step_scores.values())
        max_score = sum(step_max_scores.values())

        extra_deduction_total = self._apply_extra_deductions(
            session=session,
            early_pt_blackbox_open_events=early_pt_blackbox_open_events,
            penalties=penalties,
            finished_at=finished_at,
        )
        total_score = max(0, total_score - extra_deduction_total)

        veto_reason = self._resolve_veto_reason(
            serious_misoperations=serious_misoperations,
            closure_complete=closure_complete,
            loop_complete=loop_complete,
            voltage_complete=voltage_complete,
            phase_complete=phase_complete,
            pt_exam_complete=pt_exam_complete,
        )
        passed = veto_reason is None and total_score >= 60

        metrics = self._build_metrics(
            session=session,
            early_pt_blackbox_open_events=early_pt_blackbox_open_events,
            extra_deduction_total=extra_deduction_total,
            step_enter_events=step_enter_events,
            blocked_events=blocked_events,
            gate_block_events=gate_block_events,
            invalid_events=invalid_events,
            opened_targets=opened_targets,
            blackbox_swap_count=blackbox_swap_count,
            blackbox_failed_confirms=blackbox_failed_confirms,
            fault_detected_event=fault_detected_event,
            fault_repaired_event=fault_repaired_event,
            serious_misoperations=serious_misoperations,
            measurement_count=count("measurement_recorded"),
            finalize_attempt_count=count("step_finalize_attempted"),
        )
        summary = self._build_summary(total_score, veto_reason, extra_deduction_total)

        return AssessmentResult(
            session_id=session.session_id,
            scene_id=session.scene_id,
            mode=session.mode,
            started_at=session.started_at,
            finished_at=finished_at,
            elapsed_seconds=elapsed_seconds,
            passed=passed,
            total_score=total_score,
            max_score=max_score,
            veto_reason=veto_reason,
            step_scores=step_scores,
            step_max_scores=step_max_scores,
            score_items=score_items,
            penalties=penalties,
            metrics=metrics,
            summary=summary,
        )

    def _score_flow_discipline(self, ctx: Dict[str, object]):
        add_score_item = ctx["add_score_item"]
        first_step_index = ctx["first_step_index"]
        blocked_events = ctx["blocked_events"]
        finalize_rejected = ctx["finalize_rejected"]
        gate_block_events = ctx["gate_block_events"]

        idx1 = first_step_index(1)
        idx2 = first_step_index(2)
        idx3 = first_step_index(3)
        idx4 = first_step_index(4)

        a1_score = 2 if idx1 is not None and idx2 is not None and idx1 < idx2 else 0
        add_score_item("A1", "顺序进入第二步", "流程纪律", 2, a1_score, 2,
                       "第二步进入顺序正确。" if a1_score else "第二步进入顺序异常。", "第二步进入顺序异常。")

        a2_score = 2 if idx2 is not None and idx3 is not None and idx2 < idx3 else 0
        add_score_item("A2", "顺序进入第三步", "流程纪律", 2, a2_score, 3,
                       "第三步进入顺序正确。" if a2_score else "第三步进入顺序异常。", "第三步进入顺序异常。")

        a3_score = 2 if idx3 is not None and idx4 is not None and idx3 < idx4 else 0
        add_score_item("A3", "顺序进入第四步", "流程纪律", 2, a3_score, 4,
                       "第四步进入顺序正确。" if a3_score else "第四步进入顺序异常。", "第四步进入顺序异常。")

        a4_deduction = min(5, len(blocked_events))
        a4_score = 5 - a4_deduction
        add_score_item(
            "A4", "不越级推进", "流程纪律", 5, a4_score, detail=
            "未出现越级推进尝试。" if a4_score == 5 else f"共发生 {len(blocked_events)} 次越级或门禁拦截。",
            penalty_message="存在越级推进或门禁拦截记录。"
        )

        gate_violations = len(finalize_rejected) + len(gate_block_events)
        a5_deduction = min(5, gate_violations)
        a5_score = 5 - a5_deduction
        add_score_item(
            "A5", "遵守异常与闭环门禁", "流程纪律", 5, a5_score, 4, detail=
            "未出现异常后强行完成步骤或闭环未完成仍继续推进。" if a5_score == 5 else f"共发生 {gate_violations} 次违规推进尝试。",
            penalty_message="未严格遵守异常停留或闭环门禁。"
        )

    def _score_loop_test(self, ctx: Dict[str, object]):
        add_score_item = ctx["add_score_item"]
        loop_records = ctx["loop_records"]
        loop_complete = ctx["loop_complete"]
        count_present = ctx["count_present"]

        for code, phase, step_score in (("B1", "A", 2), ("B2", "B", 2), ("B3", "C", 2)):
            recorded = loop_records.get(phase) is not None
            add_score_item(
                code,
                f"{phase}相回路记录完成",
                "第一步回路测试",
                step_score,
                step_score if recorded else 0,
                1,
                f"{phase}相回路已完成记录。" if recorded else f"{phase}相回路记录缺失。",
                f"{phase}相回路记录缺失。"
            )

        b4_score = 4 if loop_complete else 2 if count_present(loop_records) >= 2 else 0
        add_score_item(
            "B4", "第一步结果提交规范",
            "第一步回路测试", 4, b4_score, 1,
            "第一步已形成完整闭环。" if b4_score == 4 else "第一步存在漏项或未完成确认。",
            "第一步结果提交不规范。"
        )

    def _score_pt_voltage_check(self, ctx: Dict[str, object]):
        add_score_item = ctx["add_score_item"]
        trio_completion_score = ctx["trio_completion_score"]
        pt1_voltage_count = ctx["pt1_voltage_count"]
        pt2_voltage_count = ctx["pt2_voltage_count"]
        pt3_voltage_count = ctx["pt3_voltage_count"]
        session = ctx["session"]
        detection_step = ctx["detection_step"]
        fault_detected_event = ctx["fault_detected_event"]

        c1_score = trio_completion_score(pt1_voltage_count)
        add_score_item("C1", "PT1电压记录完整", "第二步PT电压检查", 3, c1_score, 2,
                       f"PT1 已记录 {pt1_voltage_count}/3 项。", "PT1 电压记录不完整。")
        c2_score = trio_completion_score(pt2_voltage_count)
        add_score_item("C2", "PT2电压记录完整", "第二步PT电压检查", 3, c2_score, 2,
                       f"PT2 已记录 {pt2_voltage_count}/3 项。", "PT2 电压记录不完整。")
        c3_score = trio_completion_score(pt3_voltage_count)
        add_score_item("C3", "PT3电压记录完整", "第二步PT电压检查", 3, c3_score, 2,
                       f"PT3 已记录 {pt3_voltage_count}/3 项。", "PT3 电压记录不完整。")

        if not session.scene_id or detection_step != 2:
            c4_score = 3
            c4_detail = "第二步不承担本场景的关键异常识别。"
        else:
            c4_score = 3 if fault_detected_event is not None and fault_detected_event.step <= 2 else 0
            c4_detail = "已在第二步形成有效电压异常判断。" if c4_score else "未在第二步形成有效电压异常判断。"
        add_score_item("C4", "第二步结果判读有效", "第二步PT电压检查", 3, c4_score, 2, c4_detail, "第二步结果判读不足。")

    def _score_pt_phase_check(self, ctx: Dict[str, object]):
        add_score_item = ctx["add_score_item"]
        trio_completion_score = ctx["trio_completion_score"]
        pt1_phase_count = ctx["pt1_phase_count"]
        pt3_phase_count = ctx["pt3_phase_count"]
        invalid_by_step = ctx["invalid_by_step"]
        session = ctx["session"]
        detection_step = ctx["detection_step"]
        fault_detected_event = ctx["fault_detected_event"]

        d1_score = trio_completion_score(pt1_phase_count)
        add_score_item("D1", "PT1相序记录完整", "第三步PT相序检查", 3, d1_score, 3,
                       f"PT1 已记录 {pt1_phase_count}/3 项。", "PT1 相序记录不完整。")
        d2_score = trio_completion_score(pt3_phase_count)
        add_score_item("D2", "PT3相序记录完整", "第三步PT相序检查", 3, d2_score, 3,
                       f"PT3 已记录 {pt3_phase_count}/3 项。", "PT3 相序记录不完整。")

        d3_score = 2 if invalid_by_step[3] == 0 else 1 if invalid_by_step[3] == 1 else 0
        add_score_item(
            "D3", "第三步记录顺序规范", "第三步PT相序检查", 2, d3_score, 3,
            "第三步记录顺序与接线选择规范。" if d3_score == 2 else f"第三步存在 {invalid_by_step[3]} 次无效测量。",
            "第三步记录顺序或接线操作不规范。"
        )

        if not session.scene_id or detection_step != 3:
            d4_score = 4
            d4_detail = "第三步不承担本场景的关键异常识别。"
        else:
            d4_score = 4 if fault_detected_event is not None and fault_detected_event.step <= 3 else 0
            d4_detail = "已在第三步形成有效相序异常判断。" if d4_score else "未在第三步形成有效相序异常判断。"
        add_score_item("D4", "第三步能识别相序异常", "第三步PT相序检查", 4, d4_score, 3, d4_detail, "第三步异常识别不足。")

    def _score_pt_exam(self, ctx: Dict[str, object]):
        add_score_item = ctx["add_score_item"]
        nine_group_completion_score = ctx["nine_group_completion_score"]
        gen1_exam_count = ctx["gen1_exam_count"]
        gen2_exam_count = ctx["gen2_exam_count"]
        invalid_by_step = ctx["invalid_by_step"]
        finalize_rejected_by_step = ctx["finalize_rejected_by_step"]
        session = ctx["session"]
        hidden_fault = ctx["hidden_fault"]
        blackbox_open_before_gate = ctx["blackbox_open_before_gate"]
        fault_detected_event = ctx["fault_detected_event"]

        e1_score = nine_group_completion_score(gen1_exam_count)
        add_score_item("E1", "Gen1压差记录完整", "第四步压差考核", 4, e1_score, 4,
                       f"Gen1 已记录 {gen1_exam_count}/9 组。", "Gen1 压差记录不完整。")
        e2_score = nine_group_completion_score(gen2_exam_count)
        add_score_item("E2", "Gen2压差记录完整", "第四步压差考核", 4, e2_score, 4,
                       f"Gen2 已记录 {gen2_exam_count}/9 组。", "Gen2 压差记录不完整。")

        e3_score = 2 if invalid_by_step[4] == 0 and finalize_rejected_by_step[4] == 0 else 1 if invalid_by_step[4] <= 1 else 0
        add_score_item(
            "E3", "第四步操作顺序规范", "第四步压差考核", 2, e3_score, 4,
            "第四步操作顺序规范。" if e3_score == 2 else "第四步存在无效测量或过早完成尝试。",
            "第四步操作顺序不规范。"
        )

        if not session.scene_id:
            e4_score = 6
            e4_detail = "正常场景无需形成故障判断。"
        elif hidden_fault:
            e4_score = 6 if blackbox_open_before_gate else 0
            e4_detail = "已在系统拦截前通过拆检形成判断。" if e4_score else "直到系统门禁拦截后才意识到第四步仍未闭环。"
        else:
            e4_score = 6 if fault_detected_event is not None and fault_detected_event.step <= 4 else 0
            e4_detail = "已在第四步内形成有效判断。" if e4_score else "未在第四步内形成有效判断。"
        add_score_item("E4", "第四步形成有效判断", "第四步压差考核", 6, e4_score, 4, e4_detail, "第四步未形成有效判断。")

    def _score_fault_localization(self, ctx: Dict[str, object]):
        add_score_item = ctx["add_score_item"]
        session = ctx["session"]
        hidden_fault = ctx["hidden_fault"]
        blackbox_open_before_gate = ctx["blackbox_open_before_gate"]
        detected_before_gate = ctx["detected_before_gate"]
        expected_targets = ctx["expected_targets"]
        expected_target_set = ctx["expected_target_set"]
        expected_device_set = ctx["expected_device_set"]
        opened_target_set = ctx["opened_target_set"]
        touched_layers = ctx["touched_layers"]

        if not session.scene_id:
            f1_score = 4
            f1_detail = "正常场景不要求故障识别。"
        else:
            identified = detected_before_gate or (hidden_fault and blackbox_open_before_gate)
            f1_score = 4 if identified else 0
            f1_detail = "已在第四步门禁前识别到异常。" if f1_score else "未在第四步门禁前识别到异常。"
        add_score_item("F1", "第四步门禁前识别异常", "异常识别与故障定位", 4, f1_score, 4, f1_detail, "未在第四步门禁前识别异常。")

        if hidden_fault:
            f2_score = 4 if blackbox_open_before_gate else 0
            f2_detail = "已主动识别隐性故障。" if f2_score else "依赖系统门禁后才意识到隐性故障。"
        else:
            f2_score = 4
            f2_detail = "本场景不属于隐性故障，或已满足识别要求。"
        add_score_item("F2", "隐性故障识别能力", "异常识别与故障定位", 4, f2_score, 4, f2_detail, "隐性故障识别能力不足。")

        if not expected_targets:
            f3_score = 3
            f3_detail = "本场景无黑盒定位要求。"
        else:
            correct_side_hit = bool(opened_target_set & expected_device_set)
            f3_score = 3 if correct_side_hit else 0
            f3_detail = "已命中正确设备侧。" if f3_score else "未命中正确设备侧。"
        add_score_item("F3", "定位到正确设备侧", "异常识别与故障定位", 3, f3_score, 4, f3_detail, "故障定位未命中正确设备侧。")

        if not expected_targets:
            f4_score = 3
            f4_detail = "本场景无黑盒门禁定位要求。"
        else:
            layer_hit = bool(touched_layers & expected_target_set)
            f4_score = 3 if layer_hit else 0
            f4_detail = "已命中正确故障层级。" if f4_score else "未命中正确故障层级。"
        add_score_item("F4", "定位到正确故障层级", "异常识别与故障定位", 3, f4_score, 4, f4_detail, "故障层级定位不准确。")

    def _score_blackbox_repair(self, ctx: Dict[str, object]):
        add_score_item = ctx["add_score_item"]
        expected_targets = ctx["expected_targets"]
        expected_target_set = ctx["expected_target_set"]
        expected_device_set = ctx["expected_device_set"]
        opened_target_set = ctx["opened_target_set"]
        touched_layers = ctx["touched_layers"]
        repair_required = ctx["repair_required"]
        repaired = ctx["repaired"]
        blackbox_failed_confirms = ctx["blackbox_failed_confirms"]
        blackbox_swap_count = ctx["blackbox_swap_count"]

        if not expected_targets:
            g1_score = 3
            g1_detail = "本场景无黑盒范围控制要求。"
        else:
            extra_targets = len(opened_target_set - expected_device_set)
            missing_targets = len(expected_device_set - opened_target_set)
            if extra_targets == 0 and missing_targets == 0:
                g1_score = 3
            elif extra_targets <= 1 and missing_targets <= 1:
                g1_score = 1
            else:
                g1_score = 0
            g1_detail = (
                "黑盒开启范围与场景需求一致。"
                if g1_score == 3 else
                f"存在额外打开 {extra_targets} 个、缺失 {missing_targets} 个目标。"
            )
        add_score_item("G1", "黑盒开启范围合理", "黑盒修复", 3, g1_score, 4, g1_detail, "黑盒开启范围不合理。")

        if not repair_required:
            g2_score = 5
            g2_detail = "本场景不依赖黑盒修复闭环。"
        else:
            g2_score = 5 if repaired else 0
            g2_detail = "最终修复结果正确。" if g2_score else "考核结束时仍未完成正确修复。"
        add_score_item("G2", "最终修复结果正确", "黑盒修复", 5, g2_score, 4, g2_detail, "最终修复结果不正确。")

        if not repair_required:
            g3_score = 4
            g3_detail = "本场景无黑盒修复路径要求。"
        elif not repaired:
            g3_score = 0
            g3_detail = "未形成有效修复闭环。"
        else:
            g3_score = 4
            if not touched_layers.issuperset(expected_target_set):
                g3_score -= 2
            g3_score -= min(1, blackbox_failed_confirms)
            g3_score -= min(1, max(0, blackbox_swap_count - max(1, len(expected_target_set))))
            g3_score = max(0, g3_score)
            g3_detail = (
                "修复路径合理，操作效率正常。"
                if g3_score == 4 else
                f"存在黑盒操作折返：交换 {blackbox_swap_count} 次，错误确认 {blackbox_failed_confirms} 次。"
            )
        add_score_item("G3", "修复路径合理", "黑盒修复", 4, g3_score, 4, g3_detail, "黑盒修复路径合理性不足。")

    def _score_efficiency(self, ctx: Dict[str, object]):
        add_score_item = ctx["add_score_item"]
        elapsed_seconds = ctx["elapsed_seconds"]
        blocked_events = ctx["blocked_events"]
        finalize_rejected = ctx["finalize_rejected"]
        invalid_events = ctx["invalid_events"]

        if elapsed_seconds <= 300:
            h1_score = 4
        elif elapsed_seconds <= 480:
            h1_score = 3
        elif elapsed_seconds <= 660:
            h1_score = 2
        elif elapsed_seconds <= 900:
            h1_score = 1
        else:
            h1_score = 0
        h1_detail = {
            4: "总耗时控制优秀。",
            3: "总耗时控制良好。",
            2: "总耗时偏长。",
            1: "总耗时明显偏长。",
            0: "总耗时严重超标。",
        }[h1_score]
        add_score_item("H1", "总耗时控制", "效率与规范性", 4, h1_score, detail=h1_detail, penalty_message="总耗时控制未达到理想水平。")

        invalid_operation_count = len(blocked_events) + len(finalize_rejected) + len(invalid_events)
        if invalid_operation_count <= 2:
            h2_score = 4
        elif invalid_operation_count <= 4:
            h2_score = 3
        elif invalid_operation_count <= 6:
            h2_score = 2
        elif invalid_operation_count <= 8:
            h2_score = 1
        else:
            h2_score = 0
        h2_detail = (
            "无效测量与违规操作控制良好。"
            if h2_score == 4 else
            f"累计无效/违规操作 {invalid_operation_count} 次。"
        )
        add_score_item("H2", "无效操作控制", "效率与规范性", 4, h2_score, detail=h2_detail, penalty_message="无效测量或违规操作次数偏多。")

    @staticmethod
    def _build_step_score_summaries(score_items: List[AssessmentScoreItem]):
        step_scores = {
            "flow_discipline": sum(item.earned_score for item in score_items if item.code.startswith("A")),
            "loop_test": sum(item.earned_score for item in score_items if item.code.startswith("B")),
            "pt_voltage_check": sum(item.earned_score for item in score_items if item.code.startswith("C")),
            "pt_phase_check": sum(item.earned_score for item in score_items if item.code.startswith("D")),
            "pt_exam": sum(item.earned_score for item in score_items if item.code.startswith("E")),
            "anomaly_localization": sum(item.earned_score for item in score_items if item.code.startswith("F")),
            "blackbox_repair": sum(item.earned_score for item in score_items if item.code.startswith("G")),
            "efficiency": sum(item.earned_score for item in score_items if item.code.startswith("H")),
        }
        step_max_scores = {
            "flow_discipline": sum(item.max_score for item in score_items if item.code.startswith("A")),
            "loop_test": sum(item.max_score for item in score_items if item.code.startswith("B")),
            "pt_voltage_check": sum(item.max_score for item in score_items if item.code.startswith("C")),
            "pt_phase_check": sum(item.max_score for item in score_items if item.code.startswith("D")),
            "pt_exam": sum(item.max_score for item in score_items if item.code.startswith("E")),
            "anomaly_localization": sum(item.max_score for item in score_items if item.code.startswith("F")),
            "blackbox_repair": sum(item.max_score for item in score_items if item.code.startswith("G")),
            "efficiency": sum(item.max_score for item in score_items if item.code.startswith("H")),
        }
        return step_scores, step_max_scores

    @staticmethod
    def _apply_extra_deductions(
        session: AssessmentSession,
        early_pt_blackbox_open_events,
        penalties: List[AssessmentPenalty],
        finished_at: str,
    ) -> int:
        extra_deduction_total = 0
        for idx, event in enumerate(early_pt_blackbox_open_events, start=1):
            extra_deduction_total += 10
            penalties.append(
                AssessmentPenalty(
                    code="X1",
                    message=f"前两步第 {idx} 次提前打开 PT 黑盒，属于高危违规，额外扣 10 分。",
                    score_delta=-10,
                    step=event.step,
                    timestamp=event.timestamp,
                )
            )
        if session.fault_selection_mode == "random" and session.scene_id and not session.fault_guess_correct:
            extra_deduction_total += 10
            penalties.append(
                AssessmentPenalty(
                    code="X2",
                    message="随机故障最终场景判定错误，额外扣 10 分。",
                    score_delta=-10,
                    step=4,
                    timestamp=finished_at,
                )
            )
        return extra_deduction_total

    @staticmethod
    def _resolve_veto_reason(
        *,
        serious_misoperations: int,
        closure_complete: bool,
        loop_complete: bool,
        voltage_complete: bool,
        phase_complete: bool,
        pt_exam_complete: bool,
    ) -> str:
        if serious_misoperations > 0:
            return "存在严重误操作"
        if not closure_complete:
            return "第四步结束时仍未完成正确修复"
        if not (loop_complete and voltage_complete and phase_complete and pt_exam_complete):
            return "前四步记录不完整，无法形成有效考核"
        return None

    @staticmethod
    def _build_metrics(
        *,
        session: AssessmentSession,
        early_pt_blackbox_open_events,
        extra_deduction_total: int,
        step_enter_events,
        blocked_events,
        gate_block_events,
        invalid_events,
        opened_targets,
        blackbox_swap_count: int,
        blackbox_failed_confirms: int,
        fault_detected_event,
        fault_repaired_event,
        serious_misoperations: int,
        measurement_count: int,
        finalize_attempt_count: int,
    ) -> Dict[str, object]:
        return {
            "fault_selection_mode": "随机故障" if session.fault_selection_mode == "random" else "指定/正常",
            "fault_guess_scene_id": session.fault_guess_scene_id or "-",
            "fault_guess_correct": (
                "-"
                if session.fault_selection_mode != "random"
                else ("正确" if session.fault_guess_correct else "错误")
            ),
            "actual_fault_scene_id": session.scene_id or "-",
            "early_pt_blackbox_opened": len(early_pt_blackbox_open_events),
            "extra_deduction_total": extra_deduction_total,
            "step_entered_order": [event.step for event in step_enter_events],
            "step_finalize_attempts": finalize_attempt_count,
            "blocked_advances": len(blocked_events),
            "gate_blocks": len(gate_block_events),
            "measurements_recorded": measurement_count,
            "invalid_measurements": len(invalid_events),
            "blackboxes_opened": opened_targets,
            "blackbox_swap_count": blackbox_swap_count,
            "blackbox_failed_confirms": blackbox_failed_confirms,
            "fault_detected_at_step": getattr(fault_detected_event, "step", 0),
            "fault_repaired_at": getattr(fault_repaired_event, "timestamp", ""),
            "serious_misoperations": serious_misoperations,
        }

    @staticmethod
    def _build_summary(total_score: int, veto_reason: str, extra_deduction_total: int) -> str:
        if veto_reason:
            summary = f"未通过：{veto_reason}"
        elif total_score >= 90:
            summary = "通过：流程规范、判断准确，整体表现优秀。"
        elif total_score >= 75:
            summary = "通过：完成了有效闭环，但过程上仍存在若干扣分点。"
        elif total_score >= 60:
            summary = "通过：达到基本考核要求。"
        else:
            summary = "未通过：总分未达到及格线。"
        if extra_deduction_total > 0:
            summary = f"{summary} 另有额外扣分 {extra_deduction_total} 分。"
        return summary

    @staticmethod
    def _expected_blackbox_targets(scene_info: Dict) -> List[str]:
        params = scene_info.get("params", {}) if scene_info else {}
        targets: List[str] = []
        if params.get("g1_blackbox_order") is not None:
            targets.append("G1.terminal")
        if (params.get("pt1_pri_blackbox_order") is not None
                or params.get("p1_pri_blackbox_order") is not None):
            targets.append("PT1.primary")
        if (params.get("pt1_sec_blackbox_order") is not None
                or params.get("pt2_sec_blackbox_order") is not None):
            targets.append("PT1.secondary")
        if params.get("g2_blackbox_order") is not None:
            targets.append("G2.terminal")
        return targets
