from __future__ import annotations

import math

from domain.constants import GRID_FREQ, GRID_AMP
from domain.enums import BreakerPosition


class HardwareActions:
    def __init__(self, ctrl):
        self._ctrl = ctrl

    def get_preclose_flow_blockers(self, gen_id):
        sections = []
        loop_done = self._ctrl.loop_svc.is_loop_test_complete()

        if not loop_done:
            # 第一步未完成：同时列出所有后续步骤，让用户一次看到全部要求
            sections.append(("第一步：回路连通性测试", ["三相回路连通性测试尚未完成"]))
            if not self._ctrl.pt_voltage_svc.is_pt_voltage_check_complete():
                sections.append(("第二步：PT 单体线电压检查", ["PT1/PT2/PT3 线电压检查尚未完成"]))
            if not self._ctrl.pt_phase_svc.is_pt_phase_check_complete():
                sections.append(("第三步：PT 相序检查", ["PT1/PT3 相序检查尚未完成"]))
            if not self._ctrl.pt_exam_svc.is_pt_exam_recorded(2):
                sections.append(("第四步：PT 二次端子压差考核（Gen 2）",
                                 ["Gen 2 三相 PT 二次端子压差尚未全部记录"]))
            if not self._ctrl.sync_svc.is_sync_test_complete() and not self._ctrl.is_sync_test_active():
                sections.append(("第五步：同步功能测试",
                                 ["同步功能测试尚未完成（需完成两轮同步跟踪记录）"]))
        elif gen_id == 1:
            # Gen1 合闸：若母排已由 Gen2 供电，Gen1 也必须先完成同期测试
            bus_live = getattr(self._ctrl.physics, 'bus_live', False)
            bus_ref = getattr(self._ctrl.physics, 'bus_reference_gen', None)
            if bus_live and bus_ref == 2:
                if not self._ctrl.sync_svc.is_sync_test_complete() and not self._ctrl.is_sync_test_active():
                    sections.append(("第五步：同步功能测试",
                                     ["母排当前由 Gen 2 供电，Gen 1 合闸前需完成同步功能测试"]))
        elif gen_id == 2:
            # 第一步已完成；Gen1 已建立母排参考，Gen2 需完成第二至五步
            if not self._ctrl.pt_voltage_svc.is_pt_voltage_check_complete():
                sections.append(("第二步：PT 单体线电压检查", ["PT1/PT2/PT3 线电压检查尚未完成"]))
            if not self._ctrl.pt_phase_svc.is_pt_phase_check_complete():
                sections.append(("第三步：PT 相序检查", ["PT1/PT3 相序检查尚未完成"]))
            if not self._ctrl.pt_exam_svc.is_pt_exam_recorded(2):
                sections.append(("第四步：PT 二次端子压差考核（Gen 2）",
                                 ["Gen 2 三相 PT 二次端子压差尚未全部记录"]))
            # 同步测试进行中（Gen2 需合闸作第二轮基准）不拦截
            if not self._ctrl.sync_svc.is_sync_test_complete() and not self._ctrl.is_sync_test_active():
                sections.append(("第五步：同步功能测试",
                                 ["同步功能测试尚未完成（需完成两轮同步跟踪记录）"]))
        return sections

    def _should_enforce_pt_exam_before_close(self):
        return self._ctrl.sim_state.grounding_mode != "断开"

    def _should_limit_close_to_selected_pt_target(self):
        sim = self._ctrl.sim_state
        return (
            sim.grounding_mode == "小电阻接地" and
            sim.gen1.mode == "manual" and
            sim.gen2.mode == "manual" and
            not self._ctrl.sync_svc.is_sync_test_complete() and
            self._ctrl.pt_exam_states[1].started
        )

    def instant_sync(self):
        # 若母排已带电，相位必须跟随母排当前动态相角，不能强行清零
        # （bus_phase 由物理引擎实时维护，单位为弧度）
        if getattr(self._ctrl.physics, 'bus_live', False):
            target_phase_deg = math.degrees(self._ctrl.physics.bus_phase)
        else:
            target_phase_deg = 0.0   # 母排无电时建立参考，0° 合法
        for gen in (self._ctrl.sim_state.gen1, self._ctrl.sim_state.gen2):
            gen.freq = GRID_FREQ
            gen.amp = GRID_AMP
            gen.phase_deg = target_phase_deg

    def toggle_engine(self, gen_id: int):
        gen = self._ctrl._get_generator_state(gen_id)
        if not gen.running and gen.mode != "manual":
            self._on_engine_blocked(
                gen_id,
                "起机条件不满足",
                f"Gen {gen_id} 只有在手动工作模式下才能起机。\n请先将工作模式切换为“手动”，再执行起机。"
            )
            return
        gen.running = not gen.running

    def _on_engine_blocked(self, gen_id: int, title: str, message: str):
        self._ctrl.ui.show_warning(title, message)

    def _on_breaker_blocked(self, gen_id: int, title: str, message: str):
        """合闸被拦截时的 UI 响应钩子。由 UI 层覆写以控制弹窗和 Tab 跳转。
        控制器本身只负责状态，不直接操作视图。"""
        self._ctrl.request_ui_tab(5)
        self._ctrl.ui.show_warning(title, message)

    def toggle_breaker(self, gen_id: int):
        generator = self._ctrl._get_generator_state(gen_id)
        if generator.breaker_closed:
            generator.breaker_closed = False
            return
        # ── 拦截：Gen1 考核期间禁止 Gen2 合闸 ─────────────────────────────
        if gen_id == 2 and self._should_limit_close_to_selected_pt_target():
            self._ctrl.pt_exam_svc._set_pt_exam_feedback(
                1,
                "当前第四步正在测试 Gen 1，请先完成 Gen 1 的 PT 二次端子压差测试，再合闸 Gen 2。",
                "red"
            )
            self._on_breaker_blocked(
                gen_id,
                "当前机组不允许合闸",
                "第四步 PT 测试当前锁定在 Gen 1。\n请先完成 Gen 1 的测试，再合闸 Gen 2。"
            )
            return
        # ── 拦截：E01/E02/E03 故障未修复时 Gen2 工作位合闸（仅第五步同步测试中）→ 并网事故 ──
        fc = self._ctrl.sim_state.fault_config
        if (gen_id == 2
                and generator.breaker_position == BreakerPosition.WORKING
                and fc.active and not fc.repaired
                and self._ctrl.is_sync_test_active()):
            if fc.scenario_id == 'E01':
                self._ctrl.append_assessment_event('hazard_action', step=5, action='close_gen2_breaker', reason='E01 accident')
                self._ctrl.ui.show_e01_accident_dialog()
                return
            elif fc.scenario_id == 'E02':
                self._ctrl.append_assessment_event('hazard_action', step=5, action='close_gen2_breaker', reason='E02 accident')
                self._ctrl.ui.show_e02_accident_dialog()
                return
            elif fc.scenario_id == 'E03':
                self._ctrl.append_assessment_event('hazard_action', step=5, action='close_gen2_breaker', reason='E03 accident')
                self._ctrl.ui.show_e03_accident_dialog()
                return
        # ── 拦截：工作位合闸前置流程检查 ───────────────────────────────────
        if (generator.breaker_position == BreakerPosition.WORKING
                and self._should_enforce_pt_exam_before_close()):
            blocker_sections = self.get_preclose_flow_blockers(gen_id)
            if blocker_sections:
                msg_lines = ["隔离母排模式下合闸前流程尚未完成，当前不能合闸："]
                for section_title, items in blocker_sections:
                    msg_lines.append(f"\n{section_title}")
                    msg_lines.extend(f"{i}. {item}" for i, item in enumerate(items, 1))
                warn_msg = "\n".join(msg_lines)
                self._ctrl.pt_exam_svc._set_pt_exam_feedback(
                    gen_id, warn_msg.replace("\n", "；"), "red")
                self._on_breaker_blocked(gen_id, "合闸前步骤未完成", warn_msg)
                return
        generator.cmd_close = True
