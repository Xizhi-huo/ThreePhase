"""
ui/tabs/pt_exam_tab.py
PT 二次端子压差测试 Tab (Tab 5 — 第四步)
"""

from PyQt5 import QtWidgets

from ui.tabs.circuit_tab import _qs
from ui.tabs._step_style import apply_button_tone, apply_step_shell, set_props

_BTN      = "font-size:14px; padding:4px 8px;"
_BTN_BOLD = "font-size:14px; font-weight:bold; padding:4px 8px;"


class PtExamTabMixin:
    """
    混入类，提供 PT 二次端子压差测试 Tab 的构建和渲染方法。
    """

    # ── Tab4：PT 考核 ─────────────────────────────────────────────────────────
    def _setup_tab_pt_exam(self):
        tab_outer = QtWidgets.QWidget()
        self.tab_widget.addTab(tab_outer, " 🧪 第四步：PT二次端子压差测试")
        _tlay = QtWidgets.QVBoxLayout(tab_outer)
        _tlay.setContentsMargins(0, 0, 0, 0)
        _scroll = QtWidgets.QScrollArea()
        tab = QtWidgets.QWidget()
        _scroll.setWidget(tab)
        _tlay.addWidget(_scroll)

        outer = QtWidgets.QVBoxLayout(tab)
        outer.setContentsMargins(18, 14, 18, 14)
        outer.setSpacing(8)

        # 标题
        hdr = QtWidgets.QLabel("隔离母排合闸前 - 第四步：PT二次端子压差测试")
        outer.addWidget(hdr)

        desc = QtWidgets.QLabel(
            "完成第三步PT相序检查后，恢复中性点小电阻接地，并将机组切至工作位置并入母排。"
            "随后在母排拓扑页使用万用表测量并记录三相 PT 二次端子压差。"
        )
        desc.setWordWrap(True)
        outer.addWidget(desc)

        # ── 测试进行中横幅 ────────────────────────────────────────────────
        self.pt_exam_mode_banner = QtWidgets.QLabel(
            "🧪 第四步测试进行中 — 请在母排拓扑页完成 PT 二次端子压差测量"
        )
        self.pt_exam_mode_banner.setWordWrap(True)
        self.pt_exam_mode_banner.setVisible(False)
        outer.addWidget(self.pt_exam_mode_banner)
        apply_step_shell(
            tab_outer,
            _scroll,
            tab,
            hdr,
            desc,
            self.pt_exam_mode_banner,
            banner_tone="info",
        )

        # ── 考核对象选择 ──────────────────────────────────────────────────
        target_grp = QtWidgets.QGroupBox("测试对象")
        target_grp.setProperty("cardTone", "info")
        tg_lay = QtWidgets.QHBoxLayout(target_grp)
        self._pt_target_bg = QtWidgets.QButtonGroup(self)
        self._pt_target_rb = {}
        for txt, val in [("Gen 1", 1), ("Gen 2", 2)]:
            rb = QtWidgets.QRadioButton(txt)
            rb.setChecked(val == 1)
            self._pt_target_bg.addButton(rb, val)
            tg_lay.addWidget(rb)
            self._pt_target_rb[val] = rb
        outer.addWidget(target_grp)


        # ── 操作按钮 ──────────────────────────────────────────────────────
        act_row = QtWidgets.QWidget()
        ar = QtWidgets.QHBoxLayout(act_row)
        ar.setContentsMargins(0, 0, 0, 0)
        set_props(act_row, actionRow=True)

        self.btn_pt_exam_start = QtWidgets.QPushButton("开始第四步测试")
        self.btn_pt_exam_start.clicked.connect(self._on_toggle_pt_exam_mode)
        apply_button_tone(self, self.btn_pt_exam_start, "warning", hero=True)

        btn_topo = QtWidgets.QPushButton("打开母排拓扑页")
        btn_topo.clicked.connect(lambda: self.tab_widget.setCurrentIndex(1))
        apply_button_tone(self, btn_topo, "primary", secondary=True)

        btn_mm = QtWidgets.QPushButton("开启/关闭万用表")
        btn_mm.clicked.connect(
            lambda: self.multimeter_cb.setChecked(not self.multimeter_cb.isChecked()))
        apply_button_tone(self, btn_mm, "warning")

        btn_reset = QtWidgets.QPushButton("重置当前机组测试")
        btn_reset.clicked.connect(
            lambda: self.ctrl.reset_pt_exam(self._pt_target_bg.checkedId()))
        apply_button_tone(self, btn_reset, "danger")

        btn_done = QtWidgets.QPushButton("完成第四步测试")
        btn_done.clicked.connect(lambda: self.ctrl.finalize_all_pt_exams())
        apply_button_tone(self, btn_done, "success", hero=True)

        ar.addWidget(self.btn_pt_exam_start)
        ar.addWidget(btn_topo)
        ar.addWidget(btn_mm)
        ar.addWidget(btn_reset)
        ar.addWidget(btn_done)
        outer.addWidget(act_row)

        # ── 实时状态 ──────────────────────────────────────────────────────
        status_grp = QtWidgets.QGroupBox("实时状态")
        sg_lay = QtWidgets.QVBoxLayout(status_grp)

        self.pt_exam_summary_lbl = QtWidgets.QLabel("")
        self.pt_exam_summary_lbl.setStyleSheet("font-weight:bold; font-size:15px; color:#264653;")
        self.pt_exam_summary_lbl.setWordWrap(True)

        self.pt_exam_meter_lbl = QtWidgets.QLabel("")
        self.pt_exam_meter_lbl.setStyleSheet("font-size:15px;")
        self.pt_exam_meter_lbl.setWordWrap(True)

        self.pt_exam_feedback_lbl = QtWidgets.QLabel("")
        self.pt_exam_feedback_lbl.setStyleSheet("font-size:15px; color:#444444;")
        self.pt_exam_feedback_lbl.setWordWrap(True)

        sg_lay.addWidget(self.pt_exam_summary_lbl)
        sg_lay.addWidget(self.pt_exam_meter_lbl)
        sg_lay.addWidget(self.pt_exam_feedback_lbl)
        outer.addWidget(status_grp)

        # ── 步骤列表 ──────────────────────────────────────────────────────
        steps_grp = QtWidgets.QGroupBox("测试步骤")
        sl_lay = QtWidgets.QVBoxLayout(steps_grp)
        self.pt_exam_step_labels = []
        for _ in range(5):
            lbl = QtWidgets.QLabel("")
            set_props(lbl, stepListItem=True)
            sl_lay.addWidget(lbl)
            self.pt_exam_step_labels.append(lbl)
        outer.addWidget(steps_grp)

        # ── 9 组矢量压差记录（AA/AB/…/CC） ───────────────────────────────
        rec_grp = QtWidgets.QGroupBox("9 组矢量压差记录（机组相 × 母排相，AA~CC）")
        rec_lay = QtWidgets.QVBoxLayout(rec_grp)
        rec_lay.setSpacing(2)
        self.pt_exam_record_labels = {}
        _BTN_SM = "font-size:11px; padding:2px 6px;"
        for gp in ('A', 'B', 'C'):
            for bp in ('A', 'B', 'C'):
                key = f"{gp}{bp}"
                row_w = QtWidgets.QWidget()
                set_props(row_w, recordRow=True)
                row = QtWidgets.QHBoxLayout(row_w)
                row.setContentsMargins(10, 6, 10, 6)
                row.setSpacing(4)

                lbl_key = QtWidgets.QLabel(key)
                lbl_key.setFixedWidth(28)
                lbl_key.setStyleSheet("font-weight:bold; font-size:12px;")

                hint = QtWidgets.QLabel(f"机{gp}↔排{bp}")
                hint.setFixedWidth(60)
                hint.setStyleSheet("font-size:10px; color:#888;")

                val_lbl = QtWidgets.QLabel("未记录")
                val_lbl.setStyleSheet("font-size:11px; color:#999999;")

                rec_btn = QtWidgets.QPushButton(f"记录 {key}")
                rec_btn.setFixedWidth(72)
                rec_btn.clicked.connect(
                    lambda _, g=gp, b=bp: self.ctrl.record_pt_measurement(
                        g, b, self._pt_target_bg.checkedId()))
                apply_button_tone(self, rec_btn, "primary")

                row.addWidget(lbl_key)
                row.addWidget(hint)
                row.addWidget(val_lbl)
                row.addStretch()
                row.addWidget(rec_btn)
                rec_lay.addWidget(row_w)
                self.pt_exam_record_labels[key] = val_lbl

        outer.addWidget(rec_grp)
        outer.addStretch()

    def _on_toggle_pt_exam_mode(self):
        both_started = (self.ctrl.pt_exam_states[1].started and
                        self.ctrl.pt_exam_states[2].started)
        if both_started:
            self.ctrl.stop_pt_exam(1)
            self.ctrl.stop_pt_exam(2)
        else:
            self.ctrl.start_pt_exam(1)
            self.ctrl.start_pt_exam(2)

    def _render_pt_exam(self, p):
        gen_id = self._pt_target_bg.checkedId()
        if gen_id <= 0:
            gen_id = 1
        state     = self.ctrl.pt_exam_states[gen_id]
        records   = state.records
        both_completed = (self.ctrl.pt_exam_states[1].completed and
                          self.ctrl.pt_exam_states[2].completed)
        both_started   = (self.ctrl.pt_exam_states[1].started and
                          self.ctrl.pt_exam_states[2].started)

        # ── 已完成锁定：两台机组均已完成 ─────────────────────────────────
        if both_completed:
            self.pt_exam_mode_banner.setVisible(False)
            self.btn_pt_exam_start.setText("开始第四步测试")
            apply_button_tone(self, self.btn_pt_exam_start, "warning", hero=True)
            self.pt_exam_summary_lbl.setText(
                "✅ 第四步已确认完成：Gen1 和 Gen2 PT 二次端子压差测试均通过，数据已锁定。")
            self.pt_exam_summary_lbl.setStyleSheet(
                "font-weight:bold; font-size:15px; color:#006400;")
            self.pt_exam_meter_lbl.setText("")
            self.pt_exam_feedback_lbl.setText("考核提示：第四步测试已完成，请继续进行第五步。")
            self.pt_exam_feedback_lbl.setStyleSheet("font-size:15px; color:#006400;")
            for lbl, (text, _) in zip(self.pt_exam_step_labels,
                                      self.ctrl.get_pt_exam_steps(gen_id)):
                lbl.setText("√ " + text)
                lbl.setStyleSheet("font-size:15px; color:#006400;")
            for key, lbl in self.pt_exam_record_labels.items():
                rec = records.get(key)
                if rec is not None:
                    lbl.setText(f"{rec['voltage_sec']:.2f} V  ✓")
                    lbl.setStyleSheet("font-size:11px; color:#006400;")
            return
        

        # ── 更新测试横幅和按钮文字 ────────────────────────────────────────
        self.pt_exam_mode_banner.setVisible(both_started)
        if both_started:
            self.btn_pt_exam_start.setText("退出第四步测试")
            apply_button_tone(self, self.btn_pt_exam_start, "danger", hero=True)
        else:
            self.btn_pt_exam_start.setText("开始第四步测试")
            apply_button_tone(self, self.btn_pt_exam_start, "warning", hero=True)
        started = both_started

        # ── 动态显示 ──────────────────────────────────────────────────────
        feedback  = state.feedback
        fb_color  = state.feedback_color
        generator = self.ctrl._get_generator_state(gen_id)
        current_combo = self.ctrl._get_current_pt_phase_match(gen_id)

        _all_keys = [f'{g}{b}' for g in 'ABC' for b in 'ABC']
        other_id = 2 if gen_id == 1 else 1
        other_done = all(self.ctrl.pt_exam_states[other_id].records[k] is not None
                         for k in _all_keys)
        this_done  = all(records[k] is not None for k in _all_keys)
        if this_done and other_done:
            summary = "Gen1 和 Gen2 全部 9 组矢量压差已记录，可点击「完成第四步测试」锁定结果。"
            sc = '#006600'
        elif this_done:
            summary = (f"Gen {gen_id} 全部 9 组已记录，请切换至 Gen {other_id} 完成压差测量。")
            sc = '#cc6600'
        else:
            summary = f"Gen {gen_id} 当前开关柜位置：{generator.breaker_position}。"
            sc = '#264653'
        self.pt_exam_summary_lbl.setText(summary)
        self.pt_exam_summary_lbl.setStyleSheet(f"font-weight:bold; font-size:15px; color:{sc};")

        meter_text = p.meter_reading
        if current_combo:
            meter_text = f"当前表笔：机组{current_combo[0]}相 ↔ 母排{current_combo[1]}相。{meter_text}"
        self.pt_exam_meter_lbl.setText(f"实时测量：{meter_text}")
        self.pt_exam_meter_lbl.setStyleSheet(
            f"font-size:15px; color:{_qs(getattr(p, 'meter_color', 'black'))};")
        self.pt_exam_feedback_lbl.setText(f"考核提示：{feedback}")
        self.pt_exam_feedback_lbl.setStyleSheet(f"font-size:15px; color:{_qs(fb_color)};")

        if not started:
            for lbl, (text, _) in zip(self.pt_exam_step_labels,
                                      self.ctrl.get_pt_exam_steps(gen_id)):
                lbl.setText("□ " + text)
                lbl.setStyleSheet("font-size:15px; color:#aaaaaa;")
        else:
            for lbl, (text, done) in zip(self.pt_exam_step_labels,
                                         self.ctrl.get_pt_exam_steps(gen_id)):
                lbl.setText(("√ " if done else "□ ") + text)
                lbl.setStyleSheet(f"font-size:15px; color:{'#006400' if done else '#666666'};")

        for key, lbl in self.pt_exam_record_labels.items():
            record = records.get(key)
            if record is None:
                lbl.setText("未记录")
                lbl.setStyleSheet("font-size:11px; color:#999999;")
            else:
                lbl.setText(f"{record['voltage_sec']:.2f} V  [已记录]")
                lbl.setStyleSheet("font-size:11px; color:#006400;")
