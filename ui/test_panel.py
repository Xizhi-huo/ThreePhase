"""
ui/test_panel.py
合闸前测试模式协调器组件
"""

from typing import Callable, Optional, Protocol

from PyQt5 import QtCore, QtWidgets

from domain.assessment import AssessmentEventType
from ui.tabs._step_style import (
    apply_badge_tone as _apply_badge_tone,
    apply_button_tone as _apply_button_tone,
    set_props as _set_props,
)
from ui.widgets.step_panels import (
    LoopTestPanel,
    PtExamPanel,
    PtPhaseCheckPanel,
    PtVoltageCheckPanel,
    SyncTestPanel,
)
from ui.widgets.step_panels._panel_builders import (
    show_assessment_result_dialog,
    show_blackbox_dialog,
    show_blackbox_required_dialog,
    show_random_fault_identification_dialog,
)


class TestPanelAPI(Protocol):
    @property
    def sim_state(self) -> object: ...
    @property
    def loop_test_state(self) -> object: ...
    @property
    def pt_voltage_check_state(self) -> object: ...
    @property
    def pt_phase_check_state(self) -> object: ...
    @property
    def pt_exam_states(self) -> object: ...
    @property
    def sync_test_state(self) -> object: ...
    @property
    def physics(self) -> object: ...
    @property
    def test_flow_mode(self) -> str: ...
    @test_flow_mode.setter
    def test_flow_mode(self, value: str) -> None: ...
    def reset_for_scenario(self, scenario_id: str) -> None: ...
    def inject_fault(self, fault_id: str) -> None: ...
    def enter_loop_test_mode(self) -> None: ...
    def exit_loop_test_mode(self) -> None: ...
    def start_pt_voltage_check(self) -> None: ...
    def stop_pt_voltage_check(self) -> None: ...
    def start_pt_phase_check(self) -> None: ...
    def stop_pt_phase_check(self) -> None: ...
    def start_pt_exam(self, gen_id: int) -> None: ...
    def stop_pt_exam(self, gen_id: int) -> None: ...
    def start_sync_test(self) -> None: ...
    def stop_sync_test(self) -> None: ...
    def reset_loop_test(self) -> None: ...
    def reset_pt_voltage_check(self) -> None: ...
    def reset_pt_phase_check(self) -> None: ...
    def reset_pt_exam(self, gen_id: int) -> None: ...
    def reset_sync_test(self) -> None: ...
    def finalize_loop_test(self) -> None: ...
    def finalize_pt_voltage_check(self) -> None: ...
    def finalize_pt_phase_check(self) -> None: ...
    def finalize_all_pt_exams(self) -> None: ...
    def finalize_sync_test(self) -> None: ...
    def record_loop_measurement(self, phase: str) -> None: ...
    def record_pt_voltage_measurement(self, pt_name: str, pair: str) -> None: ...
    def record_current_pt_measurement(self, gen_id: int) -> None: ...
    def record_all_pt_measurements_quick(self) -> None: ...
    def record_sync_round(self, round_no: int) -> None: ...
    def update_pt_ratio(self, attr: str, ratio: float) -> None: ...
    def get_loop_test_steps(self) -> list: ...
    def get_pt_voltage_check_steps(self) -> list: ...
    def get_pt_phase_check_steps(self) -> list: ...
    def get_pt_exam_steps(self, gen_id: int) -> list: ...
    def get_sync_test_steps(self) -> list: ...
    def is_loop_test_complete(self) -> bool: ...
    def is_pt_voltage_check_complete(self) -> bool: ...
    def is_pt_phase_check_complete(self) -> bool: ...
    def is_sync_test_complete(self) -> bool: ...
    def allow_admin_shortcuts(self) -> bool: ...
    def can_use_pt_exam_quick_record(self) -> bool: ...
    def should_show_fault_detected_banner(self) -> bool: ...
    def can_advance_with_fault(self) -> bool: ...
    def should_hold_at_step4_when_wiring_fault_unrepaired(self) -> bool: ...
    def has_unrepaired_wiring_fault(self) -> bool: ...
    def is_assessment_mode(self) -> bool: ...
    def start_assessment_session(self, scenario_id: str, *, preset_mode: str) -> None: ...
    def append_assessment_event(self, event_type, **kwargs) -> None: ...
    def get_test_progress_snapshot(self, step: int, pre_step5_repair_triggered: bool) -> object: ...
    def finish_assessment_session_if_ready(self, step: int) -> object: ...
    def mark_assessment_result_shown(self) -> None: ...
    def submit_random_fault_identification(self, scene_id: str) -> None: ...
    def can_inspect_blackbox(self) -> bool: ...
    def can_repair_in_blackbox(self) -> bool: ...
    def get_blackbox_runtime_state(self, target: str) -> object: ...
    def apply_blackbox_repair_attempt(self, **kwargs) -> object: ...
    def toggle_engine(self, gen_id: int) -> None: ...
    def toggle_breaker(self, gen_id: int) -> None: ...
    def record_phase_sequence(self, pt_name: str, seq: str) -> bool: ...


class TestPanelWidget(QtWidgets.QWidget):
    def __init__(
        self,
        api: TestPanelAPI,
        *,
        on_show_test_panel: Callable[[bool], None],
        on_set_current_tab: Callable[[int], None],
        on_set_step_tabs_visible: Callable[[bool], None],
        on_toggle_multimeter: Callable[[], None],
        on_force_multimeter_off: Callable[[], None],
        on_connect_phase_seq_meter: Callable[[str], None],
        on_disconnect_phase_seq_meter: Callable[[], None],
        get_phase_seq_meter_sequence: Callable[[], str],
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._api = api
        self._on_show_test_panel = on_show_test_panel
        self._on_set_current_tab = on_set_current_tab
        self._on_set_step_tabs_visible = on_set_step_tabs_visible
        self._on_toggle_multimeter = on_toggle_multimeter
        self._on_force_multimeter_off = on_force_multimeter_off
        self._on_connect_phase_seq_meter = on_connect_phase_seq_meter
        self._on_disconnect_phase_seq_meter = on_disconnect_phase_seq_meter
        self._get_phase_seq_meter_sequence = get_phase_seq_meter_sequence
        self.test_panel = self
        self._pre_test_scenario_id = ""
        self._pre_test_flow_mode = "teaching"
        self._pre_test_preset_mode = "normal"
        self._setup_test_panel()

    def set_pretest_config(self, scenario_id: str, flow_mode: str, preset_mode: str) -> None:
        self._pre_test_scenario_id = scenario_id
        self._pre_test_flow_mode = flow_mode
        self._pre_test_preset_mode = preset_mode

    def is_test_mode_active(self) -> bool:
        return getattr(self, "_test_mode_active", False)

    def _setup_test_panel(self):
        self._test_mode_active = False
        self._tp_gen_refs = {}
        self._tp_last_step = None
        self.setFixedWidth(520)
        _set_props(self.test_panel, testPanelRoot=True, panelSurface=True)
        self.test_panel.setVisible(False)

        tl = QtWidgets.QVBoxLayout(self.test_panel)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(0)

        top = QtWidgets.QWidget()
        _set_props(top, testPanelBar=True)
        top.setFixedHeight(44)
        trow = QtWidgets.QHBoxLayout(top)
        trow.setContentsMargins(8, 4, 8, 4)
        title = QtWidgets.QLabel("🔬 合闸前测试模式")
        _set_props(title, testPanelTitle=True)
        self.tp_btn_reset = QtWidgets.QPushButton("⚠️ 重置本步")
        self.tp_btn_reset.clicked.connect(self._on_tp_reset_step)
        _apply_button_tone(self, self.tp_btn_reset, "danger")
        btn_exit = QtWidgets.QPushButton("退出测试")
        btn_exit.clicked.connect(self.exit_test_mode)
        _apply_button_tone(self, btn_exit, "primary", secondary=True)
        self._tp_admin_mode = False
        self.tp_btn_admin = QtWidgets.QPushButton("🔧 管理员")
        self.tp_btn_admin.setCheckable(True)
        _set_props(self.tp_btn_admin, adminButton=True)
        self.tp_btn_admin.clicked.connect(self._on_tp_toggle_admin)
        trow.addWidget(title, 1)
        trow.addWidget(self.tp_btn_admin)
        trow.addWidget(self.tp_btn_reset)
        trow.addWidget(btn_exit)
        tl.addWidget(top)

        self._tp_forced_step = None
        step_bar = QtWidgets.QWidget()
        _set_props(step_bar, testPanelBar=True)
        step_bar.setFixedHeight(52)
        srow = QtWidgets.QHBoxLayout(step_bar)
        srow.setContentsMargins(8, 6, 8, 6)
        self.tp_step_btns = []
        for step_num, name in enumerate(["①回路", "②线压", "③相序", "④压差", "⑤同步"], start=1):
            btn = QtWidgets.QPushButton(f"●\n{name}")
            btn.setFlat(True)
            btn.setCheckable(True)
            btn.setCursor(QtCore.Qt.ArrowCursor)
            btn.setStyleSheet(self._tp_dot_style("idle"))
            btn.clicked.connect(lambda _chk, s=step_num: self._on_tp_step_btn_clicked(s))
            srow.addWidget(btn, 1)
            self.tp_step_btns.append(btn)
        tl.addWidget(step_bar)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll_content = QtWidgets.QWidget()
        _set_props(scroll_content, testPanelRoot=True)
        cl = QtWidgets.QVBoxLayout(scroll_content)
        cl.setContentsMargins(8, 6, 8, 6)
        cl.setSpacing(6)

        self._tp_fault_banner = QtWidgets.QLabel("")
        _set_props(self._tp_fault_banner, stepBanner=True, tone="danger")
        self._tp_fault_banner.setAlignment(QtCore.Qt.AlignCenter)
        self._tp_fault_banner.setWordWrap(True)
        self._tp_fault_banner.setMinimumHeight(40)
        self._tp_fault_banner.setVisible(False)
        cl.addWidget(self._tp_fault_banner)

        self.tp_bus_lbl = QtWidgets.QLabel("母排: --")
        self.tp_bus_lbl.setAlignment(QtCore.Qt.AlignCenter)
        _apply_badge_tone(self.tp_bus_lbl, "warning")
        cl.addWidget(self.tp_bus_lbl)

        self._tp_mm_btn = QtWidgets.QPushButton("🔌 开启 / 关闭万用表")
        self._tp_mm_btn.clicked.connect(self._on_toggle_multimeter)
        _apply_button_tone(self, self._tp_mm_btn, "warning")
        cl.addWidget(self._tp_mm_btn)

        self.tp_meter_lbl = QtWidgets.QLabel("万用表: 关闭")
        _set_props(self.tp_meter_lbl, stepStatus=True, mutedText=True)
        self.tp_meter_lbl.setWordWrap(True)
        self.tp_meter_lbl.setMaximumWidth(320)
        self.tp_meter_lbl.setMinimumHeight(36)
        cl.addWidget(self.tp_meter_lbl)

        self._tp_step_panels = {
            1: LoopTestPanel(
                self._api,
                get_current_test_step=self._current_test_step,
                is_step_complete=self._is_step_complete,
                on_toggle_multimeter=self._on_toggle_multimeter,
                show_blackbox_dialog=self._show_blackbox_dialog,
                parent=scroll_content,
            ),
            2: PtVoltageCheckPanel(
                self._api,
                get_current_test_step=self._current_test_step,
                is_step_complete=self._is_step_complete,
                on_toggle_multimeter=self._on_toggle_multimeter,
                show_blackbox_dialog=self._show_blackbox_dialog,
                parent=scroll_content,
            ),
            3: PtPhaseCheckPanel(
                self._api,
                get_current_test_step=self._current_test_step,
                is_step_complete=self._is_step_complete,
                on_connect_phase_seq_meter=self._on_connect_phase_seq_meter,
                on_disconnect_phase_seq_meter=self._on_disconnect_phase_seq_meter,
                get_phase_seq_meter_sequence=self._get_phase_seq_meter_sequence,
                on_force_multimeter_off=self._on_force_multimeter_off,
                show_blackbox_dialog=self._show_blackbox_dialog,
                parent=scroll_content,
            ),
            4: PtExamPanel(
                self._api,
                get_current_test_step=self._current_test_step,
                is_step_complete=self._is_step_complete,
                on_toggle_multimeter=self._on_toggle_multimeter,
                show_blackbox_dialog=self._show_blackbox_dialog,
                parent=scroll_content,
            ),
            5: SyncTestPanel(
                self._api,
                get_current_test_step=self._current_test_step,
                is_step_complete=self._is_step_complete,
                parent=scroll_content,
            ),
        }
        self._tp_step_grps = self._tp_step_panels
        for panel in self._tp_step_panels.values():
            self._tp_gen_refs.update(panel.gen_refs)
            cl.addWidget(panel)
        self._tp_s2_ratio_rows = self._tp_step_panels[2]._tp_s2_ratio_rows
        self._tp_s4_bg = self._tp_step_panels[4]._tp_s4_bg
        self._tp_s4_quick_btn = self._tp_step_panels[4]._tp_s4_quick_btn
        cl.addStretch()
        scroll.setWidget(scroll_content)
        tl.addWidget(scroll, 1)

        bottom = QtWidgets.QWidget()
        _set_props(bottom, testPanelBar=True, barRole="footer")
        brow = QtWidgets.QHBoxLayout(bottom)
        brow.setContentsMargins(8, 6, 8, 6)
        brow.setSpacing(6)
        self.tp_btn_start = QtWidgets.QPushButton("开始测试")
        self.tp_btn_start.clicked.connect(self._on_tp_start_step)
        _apply_button_tone(self, self.tp_btn_start, "warning", hero=True)
        self.tp_btn_complete = QtWidgets.QPushButton("完成本步 ✓")
        self.tp_btn_complete.clicked.connect(self._on_tp_complete_step)
        _apply_button_tone(self, self.tp_btn_complete, "success", hero=True)
        brow.addWidget(self.tp_btn_start, 1)
        brow.addWidget(self.tp_btn_complete, 1)
        tl.addWidget(bottom)

    def enter_test_mode(self):
        scenario_id = getattr(self, "_pre_test_scenario_id", "")
        self._api.test_flow_mode = getattr(self, "_pre_test_flow_mode", "teaching")
        if scenario_id:
            self._api.reset_for_scenario(scenario_id)
        else:
            self._api.inject_fault("")
        self._test_mode_active = True
        self._assessment_last_logged_step = None
        self._pre_step5_repair_triggered = False
        self._tp_last_step = None
        for panel in self._tp_step_panels.values():
            panel.reset()
        self._on_show_test_panel(True)
        self.test_panel.setVisible(True)
        self.tp_btn_admin.setVisible(self._api.allow_admin_shortcuts())
        self._tp_s4_quick_btn.setVisible(self._api.can_use_pt_exam_quick_record())
        if not self._api.allow_admin_shortcuts():
            self._tp_admin_mode = False
            self.tp_btn_admin.setChecked(False)
            self._tp_forced_step = None
        self._api.start_assessment_session(
            scenario_id,
            preset_mode=getattr(self, "_pre_test_preset_mode", "specified"),
        )
        self._on_set_current_tab(1)
        if not self._api.sim_state.loop_test_mode:
            self._api.enter_loop_test_mode()

    def exit_test_mode(self):
        self._test_mode_active = False
        self._tp_last_step = None
        for panel in self._tp_step_panels.values():
            panel.reset()
        self.test_panel.setVisible(False)
        self._on_show_test_panel(False)

    def _on_tp_reset_step(self):
        step = self._current_test_step()
        if step == 1:
            self._api.reset_loop_test()
        elif step == 2:
            self._api.reset_pt_voltage_check()
        elif step == 3:
            self._api.reset_pt_phase_check()
        elif step == 4:
            self._api.reset_pt_exam(max(1, self._tp_s4_bg.checkedId()))
        elif step == 5:
            self._api.reset_sync_test()
        self._tp_step_panels[step].reset()

    def _on_tp_start_step(self):
        step = self._current_test_step()
        if step == 1:
            if self._api.sim_state.loop_test_mode:
                self._api.exit_loop_test_mode()
            else:
                self._api.enter_loop_test_mode()
        elif step == 2:
            if self._api.pt_voltage_check_state.started:
                self._api.stop_pt_voltage_check()
            else:
                self._api.start_pt_voltage_check()
        elif step == 3:
            if self._api.pt_phase_check_state.started:
                self._api.stop_pt_phase_check()
            else:
                self._api.start_pt_phase_check()
        elif step == 4:
            both = self._api.pt_exam_states[1].started and self._api.pt_exam_states[2].started
            if both:
                self._api.stop_pt_exam(1)
                self._api.stop_pt_exam(2)
            else:
                self._api.start_pt_exam(1)
                self._api.start_pt_exam(2)
        elif step == 5:
            if self._api.sync_test_state.started:
                self._api.stop_sync_test()
            else:
                self._api.start_sync_test()

    def _on_tp_complete_step(self):
        step = self._current_test_step()
        before_complete = self._is_step_complete(step)
        if step == 1:
            self._api.finalize_loop_test()
        elif step == 2:
            self._api.finalize_pt_voltage_check()
            self._on_force_multimeter_off()
        elif step == 3:
            self._api.finalize_pt_phase_check()
            if self._api.pt_phase_check_state.completed:
                self._tp_step_panels[3].reset()
        elif step == 4:
            self._api.finalize_all_pt_exams()
        elif step == 5:
            self._api.finalize_sync_test()
        after_complete = self._is_step_complete(step)
        self._api.append_assessment_event(
            AssessmentEventType.STEP_FINALIZE_ATTEMPTED,
            step=step,
            allowed=after_complete,
            mode=self._api.test_flow_mode,
        )
        if after_complete and not before_complete:
            self._api.append_assessment_event(AssessmentEventType.STEP_COMPLETED, step=step)
        elif not after_complete:
            self._api.append_assessment_event(
                AssessmentEventType.ADVANCE_BLOCKED,
                step=step,
                from_step=step,
                to_step=min(step + 1, 5),
                reason="step_finalize_rejected",
            )

    @staticmethod
    def _tp_dot_style(state: str) -> str:
        base = "border:none; border-radius:4px; font-size:11px; padding:2px;"
        if state == "done":
            return f"QPushButton{{{base} color:#16a34a; background:#dcfce7;}}"
        if state == "active":
            return (
                f"QPushButton{{{base} color:#1d4ed8; background:#dbeafe; font-weight:bold; font-size:12px;}}"
            )
        if state == "admin_idle":
            return (
                f"QPushButton{{{base} color:#7c3aed; background:#ede9fe;}}"
                "QPushButton:hover{background:#c4b5fd;}"
                "QPushButton:checked{background:#7c3aed; color:white;}"
            )
        if state == "admin_active":
            return (
                f"QPushButton{{{base} color:white; background:#7c3aed; font-weight:bold;}}"
                "QPushButton:hover{background:#6d28d9;}"
            )
        return f"QPushButton{{{base} color:#94a3b8; background:transparent;}}"

    def _on_tp_toggle_admin(self, checked):
        if checked and not self._api.allow_admin_shortcuts():
            self.tp_btn_admin.setChecked(False)
            return
        self._tp_admin_mode = checked
        self.tp_btn_admin.setText("🔧 管理员 ✓" if checked else "🔧 管理员")
        if not checked:
            self._tp_forced_step = None
            for btn in self.tp_step_btns:
                btn.setChecked(False)
                btn.setCursor(QtCore.Qt.ArrowCursor)
        else:
            for btn in self.tp_step_btns:
                btn.setCursor(QtCore.Qt.PointingHandCursor)
        self._on_set_step_tabs_visible(checked)
        self._tp_s4_quick_btn.setVisible(checked or self._api.is_assessment_mode())

    def _update_fault_banner(self):
        fc = self._api.sim_state.fault_config
        if not self._api.should_show_fault_detected_banner():
            self._tp_fault_banner.setVisible(False)
            return
        if fc.active and fc.scenario_id:
            if fc.repaired:
                text, tone = "✅ 故障已修复，请继续按正常流程完成剩余步骤", "success"
            elif fc.detected:
                if self._api.can_advance_with_fault():
                    text = "🔍 已发现异常证据 | 请继续完成所有测试步骤，记录全部数据后将在第五步前统一进行检修"
                else:
                    text = "🔍 已发现异常证据 | 当前流程模式要求先排除故障并复测合格，再继续后续步骤"
                tone = "warning"
            else:
                text = "⚠ 故障训练模式已启用 | 请按正常流程测试，通过测量数据发现并定位异常"
                tone = "danger"
            _set_props(self._tp_fault_banner, stepBanner=True, tone=tone)
            self._tp_fault_banner.setText(text)
            self._tp_fault_banner.setVisible(True)
        else:
            self._tp_fault_banner.setVisible(False)

    def _on_tp_step_btn_clicked(self, step_num: int):
        if not self._tp_admin_mode:
            return
        if self._tp_forced_step == step_num:
            self._tp_forced_step = None
            for btn in self.tp_step_btns:
                btn.setChecked(False)
        else:
            self._tp_forced_step = step_num
            for i, btn in enumerate(self.tp_step_btns):
                btn.setChecked(i + 1 == step_num)

    def _current_test_step(self) -> int:
        if self._tp_admin_mode and self._tp_forced_step is not None:
            return self._tp_forced_step
        if not self._api.is_loop_test_complete():
            return 1
        if not self._api.is_pt_voltage_check_complete():
            return 2
        if not self._api.is_pt_phase_check_complete():
            return 3
        if not (self._api.pt_exam_states[1].completed and self._api.pt_exam_states[2].completed):
            return 4
        if self._api.should_hold_at_step4_when_wiring_fault_unrepaired() and self._api.has_unrepaired_wiring_fault():
            return 4
        return 5

    def _is_step_complete(self, step: int) -> bool:
        if step == 1:
            return self._api.is_loop_test_complete()
        if step == 2:
            return self._api.is_pt_voltage_check_complete()
        if step == 3:
            return self._api.is_pt_phase_check_complete()
        if step == 4:
            return self._api.pt_exam_states[1].completed and self._api.pt_exam_states[2].completed
        if step == 5:
            return self._api.is_sync_test_complete()
        return False

    def _show_assessment_result_dialog(self, result):
        show_assessment_result_dialog(self, result)

    def _show_random_fault_identification_dialog(self):
        show_random_fault_identification_dialog(
            self,
            submit_guess=self._api.submit_random_fault_identification,
        )

    def _show_blackbox_required_dialog(self, fc):
        show_blackbox_required_dialog(
            self,
            is_assessment=self._api.is_assessment_mode(),
            scene_id=fc.scenario_id,
        )

    def _show_blackbox_dialog(self, target):
        if not self._api.can_inspect_blackbox():
            return
        self._api.append_assessment_event(AssessmentEventType.BLACKBOX_OPENED, step=self._current_test_step(), target=target)
        show_blackbox_dialog(
            self,
            api=self._api,
            step=self._current_test_step(),
            target=target,
        )

    def render(self, rs):
        self._render_test_panel(rs)

    def _render_test_panel(self, rs):
        if not self._test_mode_active:
            return
        sim = self._api.sim_state
        step = self._current_test_step()
        self.tp_btn_admin.setVisible(self._api.allow_admin_shortcuts())
        self._tp_s4_quick_btn.setVisible(self._api.can_use_pt_exam_quick_record())
        if self._assessment_last_logged_step != step:
            self._api.append_assessment_event(AssessmentEventType.STEP_ENTERED, step=step)
            self._assessment_last_logged_step = step
        if not self._api.allow_admin_shortcuts():
            self._tp_admin_mode = False
            self.tp_btn_admin.setChecked(False)
            self._tp_forced_step = None
        auto_step = (
            1 if not self._api.is_loop_test_complete() else
            2 if not self._api.is_pt_voltage_check_complete() else
            3 if not self._api.is_pt_phase_check_complete() else
            4 if ((self._api.should_hold_at_step4_when_wiring_fault_unrepaired() and self._api.has_unrepaired_wiring_fault())
                  or not (self._api.pt_exam_states[1].completed and self._api.pt_exam_states[2].completed)) else 5
        )
        for s, btn in enumerate(self.tp_step_btns, start=1):
            if self._tp_admin_mode:
                style = "admin_active" if s == step else "admin_idle"
            elif s < auto_step:
                style = "done"
            elif s == auto_step:
                style = "active"
            else:
                style = "idle"
            btn.setStyleSheet(self._tp_dot_style(style))
        for s, grp in self._tp_step_grps.items():
            grp.setVisible(s == step)
        if self._tp_last_step != step:
            self._tp_step_panels[step].on_enter()
            self._tp_last_step = step

        msg = getattr(self._api.physics, "bus_status_msg", "母排: --")
        self.tp_bus_lbl.setText(msg)
        _apply_badge_tone(self.tp_bus_lbl, "success" if getattr(self._api.physics, "bus_live", False) else "warning")
        self._update_fault_banner()

        fc = sim.fault_config
        progress = self._api.get_test_progress_snapshot(step, getattr(self, "_pre_step5_repair_triggered", False))
        if progress.block_before_step5 and not getattr(self, "_pre_step5_repair_triggered", False):
            self._pre_step5_repair_triggered = True
            if progress.should_emit_assessment_gate_event:
                self._api.append_assessment_event(
                    AssessmentEventType.ASSESSMENT_GATE_BLOCKED,
                    step=4,
                    scene_id=fc.scenario_id,
                    reason="unrepaired_wiring_before_step5",
                )
            if progress.should_show_blackbox_required_dialog:
                self._show_blackbox_required_dialog(fc)
        elif not self._api.has_unrepaired_wiring_fault():
            self._pre_step5_repair_triggered = False

        mm_visible = step != 3
        self._tp_mm_btn.setVisible(mm_visible)
        self.tp_meter_lbl.setVisible(mm_visible)
        if sim.multimeter_mode:
            self.tp_meter_lbl.setText(f"万用表: {getattr(self._api.physics, 'meter_reading', '--')}")
            _set_props(self.tp_meter_lbl, stepStatus=True, mutedText=False)
        else:
            self.tp_meter_lbl.setText("万用表: 关闭")
            _set_props(self.tp_meter_lbl, stepStatus=True, mutedText=True)

        self._refresh_tp_gen_refs(sim, step)
        self._refresh_tp_bottom(step, sim)
        self._tp_step_panels[step].refresh(rs, step)

        if progress.random_fault_guess_required:
            self._show_random_fault_identification_dialog()
        result = self._api.finish_assessment_session_if_ready(step)
        if result is not None:
            self._show_assessment_result_dialog(result)
            self._api.mark_assessment_result_shown()

    def _refresh_tp_gen_refs(self, sim, step):
        step1_active = step == 1
        for (step_key, gen_id), (brk_lbl, eng_btn, brk_btn, mode_rbs) in self._tp_gen_refs.items():
            gen = sim.gen1 if gen_id == 1 else sim.gen2
            pos = {0: "脱开", 1: "试验", 2: "工作"}.get(getattr(gen, "breaker_position", None), str(gen.breaker_position))
            brk_lbl.setText(f"{'运行' if gen.running else '停机'} | {pos} | {'合闸' if gen.breaker_closed else '断路'}")
            _apply_badge_tone(brk_lbl, "success" if gen.breaker_closed else "danger")
            if eng_btn is not None:
                allow_engine_toggle = gen.running or gen.mode == "manual"
                eng_btn.setEnabled(allow_engine_toggle)
                eng_btn.setText("停机" if gen.running else "起机")
                if gen.running:
                    _apply_button_tone(self, eng_btn, "warning")
                elif allow_engine_toggle:
                    _apply_button_tone(self, eng_btn, "success")
                else:
                    _apply_button_tone(self, eng_btn, "primary", muted=True)
            if gen.breaker_closed:
                brk_btn.setText("分闸")
                _apply_button_tone(self, brk_btn, "danger")
            else:
                brk_btn.setText("合闸（测试）" if step_key == "s1" and step1_active else "合闸")
                _apply_button_tone(self, brk_btn, "primary")
            for val, rb in mode_rbs.items():
                rb.blockSignals(True)
                rb.setChecked(gen.mode == val)
                rb.blockSignals(False)

    def _refresh_tp_bottom(self, step, sim):
        name = {1: "回路检查", 2: "线电压检查", 3: "相序检查", 4: "压差测试", 5: "同步测试"}.get(step, f"第{step}步")
        if step == 1:
            started = sim.loop_test_mode
        elif step == 2:
            started = self._api.pt_voltage_check_state.started
        elif step == 3:
            started = self._api.pt_phase_check_state.started
        elif step == 4:
            started = self._api.pt_exam_states[1].started and self._api.pt_exam_states[2].started
        else:
            started = self._api.sync_test_state.started
        if started:
            self.tp_btn_start.setText(f"退出{name}")
            _apply_button_tone(self, self.tp_btn_start, "danger", hero=True)
        else:
            self.tp_btn_start.setText(f"开始{name}")
            _apply_button_tone(self, self.tp_btn_start, "warning", hero=True)
