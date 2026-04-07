"""
ui/tabs/pt_phase_check_tab.py
PT 相序检查 Tab (Tab 4 — 第三步)
"""

from PyQt5 import QtWidgets

from ui.tabs.circuit_tab import _qs
from ui.tabs._step_style import (
    apply_button_tone,
    apply_step_shell,
    set_live_text,
    set_props,
    set_record_value,
    set_step_item,
)

_ALL_KEYS = ('PT1_A', 'PT1_B', 'PT1_C', 'PT3_A', 'PT3_B', 'PT3_C')
_BTN      = "font-size:14px; padding:4px 8px;"
_BTN_BOLD = "font-size:14px; font-weight:bold; padding:4px 8px;"


class PtPhaseCheckTabMixin:
    """
    混入类，提供 PT 相序检查 Tab 的构建和渲染方法。
    """

    # ── Tab3：PT 相序检查 ─────────────────────────────────────────────────────
    def _setup_tab_pt_phase_check(self):
        tab_outer = QtWidgets.QWidget()
        self.tab_widget.addTab(tab_outer, " 🔀 第三步：PT相序检查 ")
        _tlay = QtWidgets.QVBoxLayout(tab_outer)
        _tlay.setContentsMargins(0, 0, 0, 0)
        _scroll = QtWidgets.QScrollArea()
        tab = QtWidgets.QWidget()
        _scroll.setWidget(tab)
        _tlay.addWidget(_scroll)

        outer = QtWidgets.QVBoxLayout(tab)
        outer.setContentsMargins(18, 14, 18, 14)
        outer.setSpacing(8)

        hdr = QtWidgets.QLabel("隔离母排合闸前 - 第三步：PT 相序检查")
        outer.addWidget(hdr)

        desc = QtWidgets.QLabel(
            "完成前两步后：① 恢复小电阻接地；② Gen1 手动工作模式起机并入母排（建立 PT1/PT2 参考）；"
            "③ Gen2 手动工作模式起机，保持断路器断开（Gen2 自身电压提供 PT3 参考）；"
            "④ 点击「开始第三步测试」，开启万用表，"
            "依次测量 PT1_A/PT2_A、PT1_B/PT2_B、PT1_C/PT2_C 和 PT3_A/PT2_A、PT3_B/PT2_B、PT3_C/PT2_C，"
            "逐项记录相序结果；⑤ 全部通过后点击「完成第三步测试」。\n"
            "相序判断以万用表内置相位比较为准，与电压幅值大小无关。"
        )
        desc.setWordWrap(True)
        outer.addWidget(desc)

        # ── 已开始横幅 ────────────────────────────────────────────────────
        self.pt_phase_check_started_banner = QtWidgets.QLabel(
            "⚡ 第三步测试进行中 — Gen1 已并网，Gen2 起机断路器断开，可开始测量相序"
        )
        self.pt_phase_check_started_banner.setWordWrap(True)
        self.pt_phase_check_started_banner.setVisible(False)
        outer.addWidget(self.pt_phase_check_started_banner)
        apply_step_shell(
            tab_outer,
            _scroll,
            tab,
            hdr,
            desc,
            self.pt_phase_check_started_banner,
            banner_tone="warning",
        )

        # ── 操作按钮 ──────────────────────────────────────────────────────
        act_row = QtWidgets.QWidget()
        ar = QtWidgets.QHBoxLayout(act_row)
        ar.setContentsMargins(0, 0, 0, 0)
        set_props(act_row, actionRow=True)

        self.btn_pt_phase_check_mode = QtWidgets.QPushButton("开始第三步测试")
        self.btn_pt_phase_check_mode.clicked.connect(self._on_toggle_pt_phase_check_mode)
        apply_button_tone(self, self.btn_pt_phase_check_mode, "warning", hero=True)

        btn_topo = QtWidgets.QPushButton("打开母排拓扑页")
        btn_topo.clicked.connect(lambda: self.tab_widget.setCurrentIndex(1))
        apply_button_tone(self, btn_topo, "primary", secondary=True)

        btn_mm = QtWidgets.QPushButton("开启/关闭万用表")
        btn_mm.clicked.connect(
            lambda: self.multimeter_cb.setChecked(not self.multimeter_cb.isChecked()))
        apply_button_tone(self, btn_mm, "warning")

        btn_reset = QtWidgets.QPushButton("重置相序检查")
        btn_reset.clicked.connect(lambda: self.ctrl.reset_pt_phase_check())
        apply_button_tone(self, btn_reset, "danger")

        btn_done = QtWidgets.QPushButton("完成第三步测试")
        btn_done.clicked.connect(lambda: self.ctrl.finalize_pt_phase_check())
        apply_button_tone(self, btn_done, "success", hero=True)

        ar.addWidget(self.btn_pt_phase_check_mode)
        ar.addWidget(btn_topo)
        ar.addWidget(btn_mm)
        ar.addWidget(btn_reset)
        ar.addWidget(btn_done)
        outer.addWidget(act_row)

        # ── 实时状态 ──────────────────────────────────────────────────────
        status_grp = QtWidgets.QGroupBox("实时状态")
        sg_lay = QtWidgets.QVBoxLayout(status_grp)

        self.pt_phase_check_summary_lbl = QtWidgets.QLabel("")
        set_live_text(self.pt_phase_check_summary_lbl, "info")
        self.pt_phase_check_summary_lbl.setWordWrap(True)

        self.pt_phase_check_meter_lbl = QtWidgets.QLabel("")
        set_props(self.pt_phase_check_meter_lbl, liveText=True, tone="neutral")
        self.pt_phase_check_meter_lbl.setWordWrap(True)

        self.pt_phase_check_feedback_lbl = QtWidgets.QLabel("")
        set_live_text(self.pt_phase_check_feedback_lbl, "neutral")
        self.pt_phase_check_feedback_lbl.setWordWrap(True)

        sg_lay.addWidget(self.pt_phase_check_summary_lbl)
        sg_lay.addWidget(self.pt_phase_check_meter_lbl)
        sg_lay.addWidget(self.pt_phase_check_feedback_lbl)
        outer.addWidget(status_grp)

        # ── 步骤列表 ──────────────────────────────────────────────────────
        steps_grp = QtWidgets.QGroupBox("测试步骤")
        sl_lay = QtWidgets.QVBoxLayout(steps_grp)
        self.pt_phase_check_step_labels = []
        for _ in range(12):
            lbl = QtWidgets.QLabel("")
            set_props(lbl, stepListItem=True)
            sl_lay.addWidget(lbl)
            self.pt_phase_check_step_labels.append(lbl)
        outer.addWidget(steps_grp)

        # ── 六相逐相测量记录（PT1 + PT3） ─────────────────────────────────
        rec_grp = QtWidgets.QGroupBox("PT 相序测量记录（PT1/PT3 各三相，共六组）")
        rec_lay = QtWidgets.QVBoxLayout(rec_grp)
        self.pt_phase_check_record_labels = {}

        for pt_name, pt_color in (('PT1', '#e8f4f8'), ('PT3', '#fff3e0')):
            pt_grp = QtWidgets.QGroupBox(
                f"{pt_name} 侧（{pt_name}_X ↔ PT2_X）"
                + ("  ←Gen1在母排，两侧同频同源，接线正确≈0V" if pt_name == 'PT1'
                   else "  ←Gen2起机断路器断开，自身电压提供PT3参考，相位比较判断相序")
            )
            pt_grp.setStyleSheet(
                f"QGroupBox{{background:{pt_color}; color:#444; font-size:13px;}}"
                "QGroupBox *{font-weight:normal; font-size:12px;}"
            )
            pt_lay = QtWidgets.QVBoxLayout(pt_grp)

            for phase in ('A', 'B', 'C'):
                key = f"{pt_name}_{phase}"
                row_w = QtWidgets.QWidget()
                set_props(row_w, recordRow=True)
                row = QtWidgets.QHBoxLayout(row_w)
                row.setContentsMargins(10, 6, 10, 6)

                ph_lbl = QtWidgets.QLabel(f"{phase} 相")
                ph_lbl.setFixedWidth(50)
                set_live_text(ph_lbl, "info")

                probe_hint = QtWidgets.QLabel(f"（{key} ↔ PT2_{phase}）")
                probe_hint.setFixedWidth(170)
                probe_hint.setStyleSheet("font-size:12px; color:#888888;")

                val_lbl = QtWidgets.QLabel("未记录")
                val_lbl.setFixedWidth(240)
                set_record_value(val_lbl, "neutral")

                rec_btn = QtWidgets.QPushButton(f"记录 {key}")
                rec_btn.clicked.connect(
                    lambda _, pt=pt_name, ph=phase: self.ctrl.record_pt_phase_check(pt, ph))
                apply_button_tone(self, rec_btn, "primary")

                row.addWidget(ph_lbl)
                row.addWidget(probe_hint)
                row.addWidget(val_lbl)
                row.addWidget(rec_btn)
                pt_lay.addWidget(row_w)
                self.pt_phase_check_record_labels[key] = val_lbl

            rec_lay.addWidget(pt_grp)

        outer.addWidget(rec_grp)
        outer.addStretch()

    def _on_toggle_pt_phase_check_mode(self):
        if self.ctrl.pt_phase_check_state.started:
            self.ctrl.stop_pt_phase_check()
        else:
            self.ctrl.start_pt_phase_check()

    def _render_pt_phase_check(self, p):
        state = self.ctrl.pt_phase_check_state
        records = state.records

        # ── 已完成锁定：所有 UI 完全冻结 ─────────────────────────────────
        if state.completed:
            self.pt_phase_check_started_banner.setVisible(False)
            self.btn_pt_phase_check_mode.setText("开始第三步测试")
            apply_button_tone(self, self.btn_pt_phase_check_mode, "warning", hero=True)
            self.pt_phase_check_summary_lbl.setText(
                "✅ 第三步已确认完成：PT1/PT3 相序检查通过，数据已锁定。")
            set_live_text(self.pt_phase_check_summary_lbl, "success")
            self.pt_phase_check_meter_lbl.setText("")
            self.pt_phase_check_feedback_lbl.setText(
                "操作提示：第三步测试已完成，请继续进行第四步 PT 二次端子压差测试。")
            set_live_text(self.pt_phase_check_feedback_lbl, "success")
            for lbl, (text, _) in zip(self.pt_phase_check_step_labels,
                                      self.ctrl.get_pt_phase_check_steps()):
                set_step_item(lbl, text, True, True)
            for key, lbl in self.pt_phase_check_record_labels.items():
                lbl.setText("相序正确 ✓")
                set_record_value(lbl, "success")
            return

        in_mode = state.started

        # ── 更新横幅和按钮文字 ────────────────────────────────────────────
        self.pt_phase_check_started_banner.setVisible(in_mode)
        if in_mode:
            self.btn_pt_phase_check_mode.setText("退出第三步测试")
            apply_button_tone(self, self.btn_pt_phase_check_mode, "danger", hero=True)
        else:
            self.btn_pt_phase_check_mode.setText("开始第三步测试")
            apply_button_tone(self, self.btn_pt_phase_check_mode, "warning", hero=True)

        # ── 动态显示 ──────────────────────────────────────────────────────
        feedback = state.feedback
        fb_color = state.feedback_color
        result = state.result

        if result == 'pass':
            summary = 'PT1/PT3 相序检查均通过，可点击\u201c完成第三步测试\u201d继续。'
            sc = '#006400'
        elif result == 'fail':
            summary = "⚠️ 检测到相序异常，请检查对应 PT 侧接线后重新记录。"
            sc = '#cc0000'
        else:
            summary = "请按步骤：Gen1并网 → 起机Gen2(不合闸) → 开始第三步测试 → 万用表 → 逐项记录PT1和PT3相序。"
            sc = '#264653'

        self.pt_phase_check_summary_lbl.setText(summary)
        set_live_text(self.pt_phase_check_summary_lbl, "success" if sc == '#006400' else ("danger" if sc == '#cc0000' else "info"))

        meter_text = p.meter_reading
        phase_match = getattr(p, 'meter_phase_match', None)
        if phase_match is True:
            match_color = "green"
        elif phase_match is False:
            match_color = "red"
        else:
            match_color = _qs(getattr(p, 'meter_color', 'black'))
        self.pt_phase_check_meter_lbl.setText(f"实时测量：{meter_text}")
        set_props(self.pt_phase_check_meter_lbl, liveText=True, tone=self._tone_from_color(match_color))

        self.pt_phase_check_feedback_lbl.setText(f"操作提示：{feedback}")
        set_live_text(self.pt_phase_check_feedback_lbl, self._tone_from_color(fb_color))

        if not in_mode:
            for lbl, (text, _) in zip(self.pt_phase_check_step_labels,
                                      self.ctrl.get_pt_phase_check_steps()):
                set_step_item(lbl, text, False, False)
        else:
            for lbl, (text, done) in zip(self.pt_phase_check_step_labels,
                                         self.ctrl.get_pt_phase_check_steps()):
                set_step_item(lbl, text, done, True)

        for key, lbl in self.pt_phase_check_record_labels.items():
            record = records.get(key)
            if record is None:
                lbl.setText("未记录")
                set_record_value(lbl, "neutral")
            elif record['phase_match']:
                lbl.setText("相序正确 ✓")
                set_record_value(lbl, "success")
            else:
                lbl.setText("相序错误 ✗（接线有误）")
                set_record_value(lbl, "danger")
