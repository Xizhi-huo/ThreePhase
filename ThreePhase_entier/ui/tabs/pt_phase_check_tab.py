"""
ui/tabs/pt_phase_check_tab.py
PT 相序检查 Tab (Tab 4 — 第三步)
"""

from PyQt5 import QtWidgets

from ui.tabs.circuit_tab import _qs

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
        _scroll.setWidgetResizable(True)
        _scroll.setStyleSheet("QScrollArea{border:none;background:#fff8f0;}")
        tab = QtWidgets.QWidget()
        tab.setStyleSheet("background:#fff8f0;")
        _scroll.setWidget(tab)
        _tlay.addWidget(_scroll)

        outer = QtWidgets.QVBoxLayout(tab)
        outer.setContentsMargins(18, 14, 18, 14)
        outer.setSpacing(8)

        hdr = QtWidgets.QLabel("隔离母排合闸前 - 第三步：PT 相序检查")
        hdr.setStyleSheet("font-size:18px; font-weight:bold; color:#7a3800;")
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
        desc.setStyleSheet("color:#7a3800; font-size:14px;")
        outer.addWidget(desc)

        # ── 已开始横幅 ────────────────────────────────────────────────────
        self.pt_phase_check_started_banner = QtWidgets.QLabel(
            "⚡ 第三步测试进行中 — Gen1 已并网，Gen2 起机断路器断开，可开始测量相序"
        )
        self.pt_phase_check_started_banner.setWordWrap(True)
        self.pt_phase_check_started_banner.setStyleSheet(
            "background:#fff3cd; color:#7a4f00; font-size:14px; "
            "font-weight:bold; padding:6px; border:1px solid #e6b800; border-radius:4px;"
        )
        self.pt_phase_check_started_banner.setVisible(False)
        outer.addWidget(self.pt_phase_check_started_banner)

        # ── 操作按钮 ──────────────────────────────────────────────────────
        act_row = QtWidgets.QWidget()
        act_row.setStyleSheet("background:#fff8f0;")
        ar = QtWidgets.QHBoxLayout(act_row)
        ar.setContentsMargins(0, 0, 0, 0)

        self.btn_pt_phase_check_mode = QtWidgets.QPushButton("开始第三步测试")
        self.btn_pt_phase_check_mode.setStyleSheet(f"background:#ffe082; {_BTN_BOLD}")
        self.btn_pt_phase_check_mode.clicked.connect(self._on_toggle_pt_phase_check_mode)

        btn_topo = QtWidgets.QPushButton("打开母排拓扑页")
        btn_topo.setStyleSheet(f"background:#d9ecff; {_BTN}")
        btn_topo.clicked.connect(lambda: self.tab_widget.setCurrentIndex(1))

        btn_mm = QtWidgets.QPushButton("开启/关闭万用表")
        btn_mm.setStyleSheet(f"background:#fff3bf; {_BTN}")
        btn_mm.clicked.connect(
            lambda: self.multimeter_cb.setChecked(not self.multimeter_cb.isChecked()))

        btn_reset = QtWidgets.QPushButton("重置相序检查")
        btn_reset.setStyleSheet(f"background:#ffd6d6; {_BTN}")
        btn_reset.clicked.connect(lambda: self.ctrl.reset_pt_phase_check())

        btn_done = QtWidgets.QPushButton("完成第三步测试")
        btn_done.setStyleSheet(f"background:#ffe0b2; {_BTN_BOLD}")
        btn_done.clicked.connect(lambda: self.ctrl.finalize_pt_phase_check())

        ar.addWidget(self.btn_pt_phase_check_mode)
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

        self.pt_phase_check_summary_lbl = QtWidgets.QLabel("")
        self.pt_phase_check_summary_lbl.setStyleSheet(
            "font-weight:bold; font-size:15px; color:#264653;")
        self.pt_phase_check_summary_lbl.setWordWrap(True)

        self.pt_phase_check_meter_lbl = QtWidgets.QLabel("")
        self.pt_phase_check_meter_lbl.setStyleSheet("font-size:13px;")
        self.pt_phase_check_meter_lbl.setWordWrap(True)

        self.pt_phase_check_feedback_lbl = QtWidgets.QLabel("")
        self.pt_phase_check_feedback_lbl.setStyleSheet("font-size:15px; color:#444444;")
        self.pt_phase_check_feedback_lbl.setWordWrap(True)

        sg_lay.addWidget(self.pt_phase_check_summary_lbl)
        sg_lay.addWidget(self.pt_phase_check_meter_lbl)
        sg_lay.addWidget(self.pt_phase_check_feedback_lbl)
        outer.addWidget(status_grp)

        # ── 步骤列表 ──────────────────────────────────────────────────────
        steps_grp = QtWidgets.QGroupBox("测试步骤")
        steps_grp.setStyleSheet(
            "QGroupBox{background:white; color:#264653; font-size:15px;}"
            "QGroupBox::title{font-weight:bold;}"
            "QGroupBox *{font-weight:normal; font-size:12px;}"
        )
        sl_lay = QtWidgets.QVBoxLayout(steps_grp)
        self.pt_phase_check_step_labels = []
        for _ in range(12):
            lbl = QtWidgets.QLabel("")
            lbl.setStyleSheet("font-size:14px; color:#666666;")
            sl_lay.addWidget(lbl)
            self.pt_phase_check_step_labels.append(lbl)
        outer.addWidget(steps_grp)

        # ── 六相逐相测量记录（PT1 + PT3） ─────────────────────────────────
        rec_grp = QtWidgets.QGroupBox("PT 相序测量记录（PT1/PT3 各三相，共六组）")
        rec_grp.setStyleSheet(
            "QGroupBox{background:white; color:#264653; font-size:15px;}"
            "QGroupBox::title{font-weight:bold;}"
            "QGroupBox *{font-weight:normal; font-size:12px;}"
        )
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
                row_w.setStyleSheet(f"background:{pt_color};")
                row = QtWidgets.QHBoxLayout(row_w)
                row.setContentsMargins(0, 0, 0, 0)

                ph_lbl = QtWidgets.QLabel(f"{phase} 相")
                ph_lbl.setFixedWidth(50)
                ph_lbl.setStyleSheet("font-weight:bold; font-size:15px;")

                probe_hint = QtWidgets.QLabel(f"（{key} ↔ PT2_{phase}）")
                probe_hint.setFixedWidth(170)
                probe_hint.setStyleSheet("font-size:12px; color:#888888;")

                val_lbl = QtWidgets.QLabel("未记录")
                val_lbl.setFixedWidth(240)
                val_lbl.setStyleSheet("font-size:14px; color:#999999;")

                rec_btn = QtWidgets.QPushButton(f"记录 {key}")
                rec_btn.setStyleSheet(f"background:#ffe4c4; {_BTN}")
                rec_btn.clicked.connect(
                    lambda _, pt=pt_name, ph=phase: self.ctrl.record_pt_phase_check(pt, ph))

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
            self.btn_pt_phase_check_mode.setStyleSheet(f"background:#ffe082; {_BTN_BOLD}")
            self.pt_phase_check_summary_lbl.setText(
                "✅ 第三步已确认完成：PT1/PT3 相序检查通过，数据已锁定。")
            self.pt_phase_check_summary_lbl.setStyleSheet(
                "font-weight:bold; font-size:15px; color:#006400;")
            self.pt_phase_check_meter_lbl.setText("")
            self.pt_phase_check_feedback_lbl.setText(
                "操作提示：第三步测试已完成，请继续进行第四步 PT 二次端子压差测试。")
            self.pt_phase_check_feedback_lbl.setStyleSheet("font-size:15px; color:#006400;")
            for lbl, (text, _) in zip(self.pt_phase_check_step_labels,
                                      self.ctrl.get_pt_phase_check_steps()):
                lbl.setText("√ " + text)
                lbl.setStyleSheet("font-size:14px; color:#006400;")
            for key, lbl in self.pt_phase_check_record_labels.items():
                lbl.setText("相序正确 ✓")
                lbl.setStyleSheet("font-size:14px; color:#006400;")
            return

        in_mode = state.started

        # ── 更新横幅和按钮文字 ────────────────────────────────────────────
        self.pt_phase_check_started_banner.setVisible(in_mode)
        if in_mode:
            self.btn_pt_phase_check_mode.setText("退出第三步测试")
            self.btn_pt_phase_check_mode.setStyleSheet(
                f"background:#f4a261; color:white; {_BTN_BOLD}")
        else:
            self.btn_pt_phase_check_mode.setText("开始第三步测试")
            self.btn_pt_phase_check_mode.setStyleSheet(f"background:#ffe082; {_BTN_BOLD}")

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
        self.pt_phase_check_summary_lbl.setStyleSheet(
            f"font-weight:bold; font-size:15px; color:{sc};")

        meter_text = p.meter_reading
        phase_match = getattr(p, 'meter_phase_match', None)
        if phase_match is True:
            match_color = "green"
        elif phase_match is False:
            match_color = "red"
        else:
            match_color = _qs(getattr(p, 'meter_color', 'black'))
        self.pt_phase_check_meter_lbl.setText(f"实时测量：{meter_text}")
        self.pt_phase_check_meter_lbl.setStyleSheet(
            f"font-size:13px; color:{match_color};")

        self.pt_phase_check_feedback_lbl.setText(f"操作提示：{feedback}")
        self.pt_phase_check_feedback_lbl.setStyleSheet(
            f"font-size:15px; color:{_qs(fb_color)};")

        if not in_mode:
            for lbl, (text, _) in zip(self.pt_phase_check_step_labels,
                                      self.ctrl.get_pt_phase_check_steps()):
                lbl.setText("□ " + text)
                lbl.setStyleSheet("font-size:14px; color:#aaaaaa;")
        else:
            for lbl, (text, done) in zip(self.pt_phase_check_step_labels,
                                         self.ctrl.get_pt_phase_check_steps()):
                lbl.setText(("√ " if done else "□ ") + text)
                lbl.setStyleSheet(
                    f"font-size:14px; color:{'#006400' if done else '#666666'};")

        for key, lbl in self.pt_phase_check_record_labels.items():
            record = records.get(key)
            if record is None:
                lbl.setText("未记录")
                lbl.setStyleSheet("font-size:14px; color:#999999;")
            elif record['phase_match']:
                lbl.setText("相序正确 ✓")
                lbl.setStyleSheet("font-size:14px; color:#006400;")
            else:
                lbl.setText("相序错误 ✗（接线有误）")
                lbl.setStyleSheet("font-size:14px; color:#cc0000;")
