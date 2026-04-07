"""
ui/tabs/loop_test_tab.py
回路连通性测试 Tab (Tab 2)
"""

from PyQt5 import QtWidgets

from domain.enums import BreakerPosition
from ui.tabs.circuit_tab import _qs
from ui.tabs._step_style import (
    apply_button_tone,
    apply_step_shell,
    set_live_text,
    set_props,
    set_record_value,
    set_step_item,
)

_BTN  = "font-size:14px; padding:4px 8px;"
_BTN_BOLD = "font-size:14px; font-weight:bold; padding:4px 8px;"


class LoopTestTabMixin:
    """
    混入类，提供回路连通性测试 Tab 的构建和渲染方法。
    """

    # ── Tab2：回路连通性测试 ─────────────────────────────────────────────────
    def _setup_tab_loop_test(self):
        tab_outer = QtWidgets.QWidget()
        self.tab_widget.addTab(tab_outer, " 🔌 第一步：回路连通性测试 ")
        _tlay = QtWidgets.QVBoxLayout(tab_outer)
        _tlay.setContentsMargins(0, 0, 0, 0)
        _scroll = QtWidgets.QScrollArea()
        tab = QtWidgets.QWidget()
        _scroll.setWidget(tab)
        _tlay.addWidget(_scroll)

        outer = QtWidgets.QVBoxLayout(tab)
        outer.setContentsMargins(18, 14, 18, 14)
        outer.setSpacing(8)

        hdr = QtWidgets.QLabel("隔离母排合闸前 - 第一步：回路连通性测试")
        outer.addWidget(hdr)

        desc = QtWidgets.QLabel(
            "合闸前首先验证三相回路连通性：断开中性点小电阻，将两台发电机切至手动模式，"
            "依次合闸（不要起机），再用万用表通断挡分别测量 A/B/C 三相回路（万用表靠自身电池"
            "注入微小电流），确认 G1 与 G2 同相回路导通正常（可在母排拓扑页观察电流流向动画）。"
        )
        desc.setWordWrap(True)
        outer.addWidget(desc)

        # ── 回路检查模式横幅 ──────────────────────────────────────────────
        self.loop_test_mode_banner = QtWidgets.QLabel(
            "⚡ 回路检查模式已激活 — 开关机械合闸，发电机未起机，母排无电压（高压侧悬空）"
        )
        self.loop_test_mode_banner.setWordWrap(True)
        self.loop_test_mode_banner.setVisible(False)
        outer.addWidget(self.loop_test_mode_banner)
        apply_step_shell(
            tab_outer,
            _scroll,
            tab,
            hdr,
            desc,
            self.loop_test_mode_banner,
            banner_tone="warning",
        )

        # ── 操作按钮 ──────────────────────────────────────────────────────
        act_row = QtWidgets.QWidget()
        ar = QtWidgets.QHBoxLayout(act_row)
        ar.setContentsMargins(0, 0, 0, 0)
        set_props(act_row, actionRow=True)

        self.btn_loop_mode = QtWidgets.QPushButton("进入回路检查模式")
        self.btn_loop_mode.clicked.connect(self._on_toggle_loop_test_mode)
        apply_button_tone(self, self.btn_loop_mode, "warning", hero=True)

        btn_topo = QtWidgets.QPushButton("打开母排拓扑页")
        btn_topo.clicked.connect(lambda: self.tab_widget.setCurrentIndex(1))
        apply_button_tone(self, btn_topo, "primary", secondary=True)

        btn_mm = QtWidgets.QPushButton("开启/关闭万用表")
        btn_mm.clicked.connect(
            lambda: self.multimeter_cb.setChecked(not self.multimeter_cb.isChecked()))
        apply_button_tone(self, btn_mm, "warning")

        btn_reset = QtWidgets.QPushButton("重置回路测试")
        btn_reset.clicked.connect(lambda: self.ctrl.reset_loop_test())
        apply_button_tone(self, btn_reset, "danger")

        btn_done = QtWidgets.QPushButton("完成第一步测试")
        btn_done.clicked.connect(lambda: self.ctrl.finalize_loop_test())
        apply_button_tone(self, btn_done, "success", hero=True)

        ar.addWidget(self.btn_loop_mode)
        ar.addWidget(btn_topo)
        ar.addWidget(btn_mm)
        ar.addWidget(btn_reset)
        ar.addWidget(btn_done)
        outer.addWidget(act_row)

        # ── 实时状态 ──────────────────────────────────────────────────────
        status_grp = QtWidgets.QGroupBox("实时状态")
        sg_lay = QtWidgets.QVBoxLayout(status_grp)

        self.loop_test_summary_lbl = QtWidgets.QLabel("")
        set_live_text(self.loop_test_summary_lbl, "info")
        self.loop_test_summary_lbl.setWordWrap(True)

        self.loop_test_meter_lbl = QtWidgets.QLabel("")
        set_live_text(self.loop_test_meter_lbl, "neutral")
        self.loop_test_meter_lbl.setWordWrap(True)

        self.loop_test_feedback_lbl = QtWidgets.QLabel("")
        set_live_text(self.loop_test_feedback_lbl, "neutral")
        self.loop_test_feedback_lbl.setWordWrap(True)

        sg_lay.addWidget(self.loop_test_summary_lbl)
        sg_lay.addWidget(self.loop_test_meter_lbl)
        sg_lay.addWidget(self.loop_test_feedback_lbl)
        outer.addWidget(status_grp)

        # ── 步骤列表 ──────────────────────────────────────────────────────
        steps_grp = QtWidgets.QGroupBox("测试步骤")
        sl_lay = QtWidgets.QVBoxLayout(steps_grp)
        self.loop_test_step_labels = []
        for _ in range(7):
            lbl = QtWidgets.QLabel("")
            set_props(lbl, stepListItem=True)
            sl_lay.addWidget(lbl)
            self.loop_test_step_labels.append(lbl)
        outer.addWidget(steps_grp)

        # ── 三相记录 ──────────────────────────────────────────────────────
        rec_grp = QtWidgets.QGroupBox("三相回路测量记录")
        rec_lay = QtWidgets.QVBoxLayout(rec_grp)
        self.loop_test_record_labels = {}
        for phase in ('A', 'B', 'C'):
            row_w = QtWidgets.QWidget()
            set_props(row_w, recordRow=True)
            row = QtWidgets.QHBoxLayout(row_w)
            row.setContentsMargins(10, 6, 10, 6)

            ph_lbl = QtWidgets.QLabel(f"{phase} 相")
            ph_lbl.setFixedWidth(60)
            set_live_text(ph_lbl, "info")

            val_lbl = QtWidgets.QLabel("未记录")
            val_lbl.setFixedWidth(280)
            set_record_value(val_lbl, "neutral")

            rec_btn = QtWidgets.QPushButton(f"记录 {phase} 相")
            rec_btn.clicked.connect(
                lambda _, ph=phase: self.ctrl.record_loop_measurement(ph))
            apply_button_tone(self, rec_btn, "primary")

            row.addWidget(ph_lbl)
            row.addWidget(val_lbl)
            row.addWidget(rec_btn)
            rec_lay.addWidget(row_w)
            self.loop_test_record_labels[phase] = val_lbl

        outer.addWidget(rec_grp)
        outer.addStretch()

    def _on_toggle_loop_test_mode(self):
        if self.ctrl.sim_state.loop_test_mode:
            self.ctrl.exit_loop_test_mode()
        else:
            self.ctrl.enter_loop_test_mode()

    def _render_loop_test(self, p):
        state    = self.ctrl.loop_test_state
        records  = state.records
        in_mode  = self.ctrl.sim_state.loop_test_mode

        # ── 已完成锁定：所有 UI 完全冻结 ─────────────────────────────────
        if state.completed:
            self.loop_test_mode_banner.setVisible(False)
            self.btn_loop_mode.setText("进入回路检查模式")
            apply_button_tone(self, self.btn_loop_mode, "warning", hero=True)
            self.loop_test_summary_lbl.setText(
                "✅ 第一步已确认完成：三相回路连通性测试通过，数据已锁定。")
            set_live_text(self.loop_test_summary_lbl, "success")
            self.loop_test_meter_lbl.setText("")
            self.loop_test_feedback_lbl.setText("操作提示：第一步测试已完成，请继续进行第二步 PT 单体线电压检查。")
            set_live_text(self.loop_test_feedback_lbl, "success")
            for lbl, (text, _) in zip(self.loop_test_step_labels,
                                      self.ctrl.get_loop_test_steps()):
                set_step_item(lbl, text, True, True)
            for phase, lbl in self.loop_test_record_labels.items():
                lbl.setText("导通 [≈0Ω] ✓")
                set_record_value(lbl, "success")
            return

        # ── 更新模式横幅和按钮文字 ────────────────────────────────────────
        self.loop_test_mode_banner.setVisible(in_mode)
        if in_mode:
            self.btn_loop_mode.setText("退出回路检查模式")
            apply_button_tone(self, self.btn_loop_mode, "danger", hero=True)
        else:
            self.btn_loop_mode.setText("进入回路检查模式")
            apply_button_tone(self, self.btn_loop_mode, "warning", hero=True)

        # ── 动态显示 ──────────────────────────────────────────────────────
        feedback = state.feedback
        fb_color = state.feedback_color
        current_phase = self.ctrl._get_current_loop_phase_match()
        sim = self.ctrl.sim_state

        if self.ctrl.is_loop_test_complete():
            summary = "第一步已确认完成：三相回路连通性测试通过，后续操作不再影响本步骤。"
            sc = '#006400'
        elif (sim.gen1.breaker_closed
              and sim.gen1.breaker_position == BreakerPosition.WORKING
              and sim.gen2.breaker_closed
              and sim.gen2.breaker_position == BreakerPosition.WORKING):
            summary = "两台发电机均已切至工作位置并合闸，可在母排拓扑页开始通断测试（可观察电流流向动画）。"
            sc = '#cc6600'
        else:
            summary = "请按步骤操作：断开小电阻 → 手动模式 → 合闸（不起机）→ 母排拓扑页通断测试。"
            sc = '#264653'
        self.loop_test_summary_lbl.setText(summary)
        set_live_text(self.loop_test_summary_lbl, "success" if sc == '#006400' else ("warning" if sc == '#cc6600' else "info"))

        meter_text = p.meter_reading
        if current_phase:
            meter_text = f"当前表笔对准 {current_phase} 相回路。{meter_text}"
        self.loop_test_meter_lbl.setText(f"实时测量：{meter_text}")
        set_live_text(self.loop_test_meter_lbl, self._tone_from_color(getattr(p, 'meter_color', 'black')))
        self.loop_test_feedback_lbl.setText(f"操作提示：{feedback}")
        set_live_text(self.loop_test_feedback_lbl, self._tone_from_color(fb_color))

        # 未进入回路检查模式前，子步骤全部保持灰色，不响应实时状态
        if not in_mode:
            for lbl, (text, _) in zip(self.loop_test_step_labels,
                                      self.ctrl.get_loop_test_steps()):
                set_step_item(lbl, text, False, False)
        else:
            for lbl, (text, done) in zip(self.loop_test_step_labels,
                                         self.ctrl.get_loop_test_steps()):
                set_step_item(lbl, text, done, True)

        for phase, lbl in self.loop_test_record_labels.items():
            record = records[phase]
            if record is None:
                lbl.setText("未记录")
                set_record_value(lbl, "neutral")
            elif record.get('status') == 'ok':
                lbl.setText("导通 [≈0Ω] ✓")
                set_record_value(lbl, "success")
            else:
                lbl.setText("断路 [∞Ω] ⚠")
                set_record_value(lbl, "warning")
