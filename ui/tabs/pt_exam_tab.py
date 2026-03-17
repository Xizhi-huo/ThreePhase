"""
ui/tabs/pt_exam_tab.py
PT 二次端子压差测试 Tab (Tab 4 — 第三步)
"""

from PyQt5 import QtWidgets

from ui.tabs.circuit_tab import _qs

_BTN      = "font-size:14px; padding:4px 8px;"
_BTN_BOLD = "font-size:14px; font-weight:bold; padding:4px 8px;"


class PtExamTabMixin:
    """
    混入类，提供 PT 二次端子压差测试 Tab 的构建和渲染方法。
    """

    # ── Tab4：PT 考核 ─────────────────────────────────────────────────────────
    def _setup_tab_pt_exam(self):
        tab_outer = QtWidgets.QWidget()
        self.tab_widget.addTab(tab_outer, " 🧪 第三步：PT二次端子压差测试 ")
        _tlay = QtWidgets.QVBoxLayout(tab_outer)
        _tlay.setContentsMargins(0, 0, 0, 0)
        _scroll = QtWidgets.QScrollArea()
        _scroll.setWidgetResizable(True)
        _scroll.setStyleSheet("QScrollArea{border:none;background:#f8fbff;}")
        tab = QtWidgets.QWidget()
        tab.setStyleSheet("background:#f8fbff;")
        _scroll.setWidget(tab)
        _tlay.addWidget(_scroll)

        outer = QtWidgets.QVBoxLayout(tab)
        outer.setContentsMargins(18, 14, 18, 14)
        outer.setSpacing(8)

        # 标题
        hdr = QtWidgets.QLabel("隔离母排合闸前 - 第三步：PT二次端子压差测试")
        hdr.setStyleSheet("font-size:18px; font-weight:bold; color:#16324f;")
        outer.addWidget(hdr)

        desc = QtWidgets.QLabel(
            "完成第二步PT相序检查后，恢复中性点小电阻接地，并将机组切至工作位置并入母排。"
            "随后在母排拓扑页使用万用表测量并记录三相 PT 二次端子压差。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color:#334e68; font-size:15px;")
        outer.addWidget(desc)

        # ── 测试进行中横幅 ────────────────────────────────────────────────
        self.pt_exam_mode_banner = QtWidgets.QLabel(
            "🧪 第三步测试进行中 — 请在母排拓扑页完成 PT 二次端子压差测量"
        )
        self.pt_exam_mode_banner.setWordWrap(True)
        self.pt_exam_mode_banner.setStyleSheet(
            "background:#e8f4fd; color:#0c5460; font-size:14px; "
            "font-weight:bold; padding:6px; border:1px solid #bee5eb; border-radius:4px;"
        )
        self.pt_exam_mode_banner.setVisible(False)
        outer.addWidget(self.pt_exam_mode_banner)

        # ── 考核对象选择 ──────────────────────────────────────────────────
        target_grp = QtWidgets.QGroupBox("测试对象")
        target_grp.setStyleSheet(
            "QGroupBox{background:#eef4ff; color:#264653; font-size:15px;}"
            "QGroupBox::title{font-weight:bold;}"
            "QGroupBox *{font-weight:normal; font-size:12px;}"
        )
        tg_lay = QtWidgets.QHBoxLayout(target_grp)
        self._pt_target_bg = QtWidgets.QButtonGroup(self)
        self._pt_target_rb = {}
        for txt, val in [("Gen 1", 1), ("Gen 2", 2)]:
            rb = QtWidgets.QRadioButton(txt)
            rb.setChecked(val == 1)
            rb.setStyleSheet("background:#eef4ff; font-size:15px;")
            self._pt_target_bg.addButton(rb, val)
            tg_lay.addWidget(rb)
            self._pt_target_rb[val] = rb
        outer.addWidget(target_grp)

        # ── 操作按钮 ──────────────────────────────────────────────────────
        act_row = QtWidgets.QWidget()
        act_row.setStyleSheet("background:#f8fbff;")
        ar = QtWidgets.QHBoxLayout(act_row)
        ar.setContentsMargins(0, 0, 0, 0)

        self.btn_pt_exam_start = QtWidgets.QPushButton("开始第三步测试")
        self.btn_pt_exam_start.setStyleSheet(f"background:#ffe082; {_BTN_BOLD}")
        self.btn_pt_exam_start.clicked.connect(self._on_toggle_pt_exam_mode)

        btn_topo = QtWidgets.QPushButton("打开母排拓扑页")
        btn_topo.setStyleSheet(f"background:#d9ecff; {_BTN}")
        btn_topo.clicked.connect(lambda: self.tab_widget.setCurrentIndex(1))

        btn_mm = QtWidgets.QPushButton("开启/关闭万用表")
        btn_mm.setStyleSheet(f"background:#fff3bf; {_BTN}")
        btn_mm.clicked.connect(
            lambda: self.multimeter_cb.setChecked(not self.multimeter_cb.isChecked()))

        btn_reset = QtWidgets.QPushButton("重置当前机组测试")
        btn_reset.setStyleSheet(f"background:#ffd6d6; {_BTN}")
        btn_reset.clicked.connect(
            lambda: self.ctrl.reset_pt_exam(self._pt_target_bg.checkedId()))

        btn_done = QtWidgets.QPushButton("完成第三步测试")
        btn_done.setStyleSheet(f"background:#cdeccf; {_BTN_BOLD}")
        btn_done.clicked.connect(
            lambda: self.ctrl.finalize_pt_exam(self._pt_target_bg.checkedId()))

        ar.addWidget(self.btn_pt_exam_start)
        ar.addWidget(btn_topo)
        ar.addWidget(btn_mm)
        ar.addWidget(btn_reset)
        ar.addWidget(btn_done)
        outer.addWidget(act_row)

        # ── 实时状态 ──────────────────────────────────────────────────────
        status_grp = QtWidgets.QGroupBox("实时状态")
        status_grp.setStyleSheet(
            "QGroupBox{background:white; color:#264653; font-size:15px;}"
            "QGroupBox::title{font-weight:bold;}"
            "QGroupBox *{font-weight:normal; font-size:12px;}"
        )
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
        steps_grp.setStyleSheet(
            "QGroupBox{background:white; color:#264653; font-size:15px;}"
            "QGroupBox::title{font-weight:bold;}"
            "QGroupBox *{font-weight:normal; font-size:12px;}"
        )
        sl_lay = QtWidgets.QVBoxLayout(steps_grp)
        self.pt_exam_step_labels = []
        for _ in range(7):
            lbl = QtWidgets.QLabel("")
            lbl.setStyleSheet("font-size:15px; color:#666666;")
            sl_lay.addWidget(lbl)
            self.pt_exam_step_labels.append(lbl)
        outer.addWidget(steps_grp)

        # ── 三相记录 ──────────────────────────────────────────────────────
        rec_grp = QtWidgets.QGroupBox("三相记录")
        rec_grp.setStyleSheet(
            "QGroupBox{background:white; color:#264653; font-size:15px;}"
            "QGroupBox::title{font-weight:bold;}"
            "QGroupBox *{font-weight:normal; font-size:12px;}"
        )
        rec_lay = QtWidgets.QVBoxLayout(rec_grp)
        self.pt_exam_record_labels = {}
        for phase in ('A', 'B', 'C'):
            row_w = QtWidgets.QWidget()
            row_w.setStyleSheet("background:white;")
            row = QtWidgets.QHBoxLayout(row_w)
            row.setContentsMargins(0, 0, 0, 0)

            ph_lbl = QtWidgets.QLabel(f"{phase} 相")
            ph_lbl.setFixedWidth(60)
            ph_lbl.setStyleSheet("font-weight:bold; font-size:15px;")

            val_lbl = QtWidgets.QLabel("未记录")
            val_lbl.setFixedWidth(230)
            val_lbl.setStyleSheet("font-size:15px; color:#999999;")

            rec_btn = QtWidgets.QPushButton(f"记录 {phase} 相")
            rec_btn.setStyleSheet(f"background:#d8f3dc; {_BTN}")
            rec_btn.clicked.connect(
                lambda _, ph=phase: self.ctrl.record_pt_measurement(ph))

            row.addWidget(ph_lbl)
            row.addWidget(val_lbl)
            row.addWidget(rec_btn)
            rec_lay.addWidget(row_w)
            self.pt_exam_record_labels[phase] = val_lbl

        outer.addWidget(rec_grp)
        outer.addStretch()

    def _on_toggle_pt_exam_mode(self):
        gen_id = self._pt_target_bg.checkedId()
        if gen_id <= 0:
            gen_id = 1
        state = self.ctrl.pt_exam_states[gen_id]
        if state.get('started'):
            self.ctrl.stop_pt_exam(gen_id)
        else:
            self.ctrl.start_pt_exam(gen_id)

    def _render_pt_exam(self, p):
        gen_id = self._pt_target_bg.checkedId()
        if gen_id <= 0:
            gen_id = 1
        state     = self.ctrl.pt_exam_states[gen_id]
        records   = state['records']
        started   = state.get('started', False)

        # ── 已完成锁定：所有 UI 完全冻结 ─────────────────────────────────
        if state.get('completed'):
            self.pt_exam_mode_banner.setVisible(False)
            self.btn_pt_exam_start.setText("开始第三步测试")
            self.btn_pt_exam_start.setStyleSheet(f"background:#ffe082; {_BTN_BOLD}")
            self.pt_exam_summary_lbl.setText(
                f"✅ 第三步已确认完成：Gen {gen_id} PT 二次端子压差测试通过，数据已锁定。")
            self.pt_exam_summary_lbl.setStyleSheet(
                "font-weight:bold; font-size:15px; color:#006400;")
            self.pt_exam_meter_lbl.setText("")
            self.pt_exam_feedback_lbl.setText("考核提示：第三步测试已完成，请继续进行第四步。")
            self.pt_exam_feedback_lbl.setStyleSheet("font-size:15px; color:#006400;")
            for lbl, (text, _) in zip(self.pt_exam_step_labels,
                                      self.ctrl.get_pt_exam_steps(gen_id)):
                lbl.setText("√ " + text)
                lbl.setStyleSheet("font-size:15px; color:#006400;")
            for phase, lbl in self.pt_exam_record_labels.items():
                rec = records[phase]
                if rec is not None:
                    lbl.setText(f"{rec['voltage']:.1f} V  [可合闸]")
                    lbl.setStyleSheet("font-size:15px; color:#006400;")
            return

        # ── 更新测试横幅和按钮文字 ────────────────────────────────────────
        self.pt_exam_mode_banner.setVisible(started)
        if started:
            self.btn_pt_exam_start.setText("退出第三步测试")
            self.btn_pt_exam_start.setStyleSheet(
                f"background:#f4a261; color:white; {_BTN_BOLD}")
        else:
            self.btn_pt_exam_start.setText("开始第三步测试")
            self.btn_pt_exam_start.setStyleSheet(f"background:#ffe082; {_BTN_BOLD}")

        # ── 动态显示 ──────────────────────────────────────────────────────
        feedback  = state['feedback']
        fb_color  = state['feedback_color']
        generator = self.ctrl._get_generator_state(gen_id)
        current_phase = self.ctrl._get_current_pt_phase_match(gen_id)

        if self.ctrl.is_pt_exam_ready(gen_id):
            summary = f"第三步已确认完成：Gen {gen_id} PT 二次端子压差测试通过，后续操作不再影响本步骤。"
            sc = '#006400'
        elif all(records[ph] is not None for ph in ('A', 'B', 'C')):
            summary = (f"Gen {gen_id} 三相 PT 二次端子压差已记录，"
                       f"当前开关柜位置：{generator.breaker_position}。")
            sc = '#cc6600'
        else:
            summary = f"Gen {gen_id} 当前开关柜位置：{generator.breaker_position}。"
            sc = '#264653'
        self.pt_exam_summary_lbl.setText(summary)
        self.pt_exam_summary_lbl.setStyleSheet(f"font-weight:bold; font-size:15px; color:{sc};")

        meter_text = p.meter_reading
        if current_phase:
            meter_text = f"当前表笔对准 Gen {gen_id} {current_phase} 相。{meter_text}"
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

        for phase, lbl in self.pt_exam_record_labels.items():
            record = records[phase]
            if record is None:
                lbl.setText("未记录")
                lbl.setStyleSheet("font-size:15px; color:#999999;")
            else:
                lbl.setText(f"{record['voltage']:.1f} V  [可合闸]")
                lbl.setStyleSheet("font-size:15px; color:#006400;")
