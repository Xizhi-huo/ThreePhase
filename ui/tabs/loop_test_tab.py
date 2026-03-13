"""
ui/tabs/loop_test_tab.py
回路连通性测试 Tab (Tab 2)
"""

from PyQt5 import QtWidgets

from ui.tabs.circuit_tab import _qs


class LoopTestTabMixin:
    """
    混入类，提供回路连通性测试 Tab 的构建和渲染方法。
    """

    # ── Tab2：回路连通性测试 ─────────────────────────────────────────────────
    def _setup_tab_loop_test(self):
        tab = QtWidgets.QWidget()
        tab.setStyleSheet("background:#f5fff5;")
        self.tab_widget.addTab(tab, " 🔌 第一步：回路连通性测试 ")
        outer = QtWidgets.QVBoxLayout(tab)
        outer.setContentsMargins(18, 14, 18, 14)
        outer.setSpacing(8)

        hdr = QtWidgets.QLabel("隔离母排合闸前 - 第一步：回路连通性测试")
        hdr.setStyleSheet("font-size:18px; font-weight:bold; color:#1a5c1a;")
        outer.addWidget(hdr)

        desc = QtWidgets.QLabel(
            "合闸前首先验证三相回路连通性：断开中性点小电阻，将两台发电机切至手动模式，"
            "设置频率/幅值/相位后依次合闸，再用万用表分别测量 A/B/C 三相回路，"
            "确认 G1 与 G2 同相回路导通正常。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color:#2d5a27; font-size:15px;")
        outer.addWidget(desc)

        # ── 操作按钮 ──────────────────────────────────────────────────────
        act_row = QtWidgets.QWidget()
        act_row.setStyleSheet("background:#f5fff5;")
        ar = QtWidgets.QHBoxLayout(act_row)
        ar.setContentsMargins(0, 0, 0, 0)
        btn_topo = QtWidgets.QPushButton("打开母排拓扑页")
        btn_topo.setStyleSheet("background:#d9ecff;")
        btn_topo.clicked.connect(lambda: self.tab_widget.setCurrentIndex(1))
        btn_mm = QtWidgets.QPushButton("开启/关闭万用表")
        btn_mm.setStyleSheet("background:#fff3bf;")
        btn_mm.clicked.connect(
            lambda: self.multimeter_cb.setChecked(not self.multimeter_cb.isChecked()))
        btn_reset = QtWidgets.QPushButton("重置回路测试")
        btn_reset.setStyleSheet("background:#ffd6d6;")
        btn_reset.clicked.connect(lambda: self.ctrl.reset_loop_test())
        btn_done = QtWidgets.QPushButton("完成第一步测试")
        btn_done.setStyleSheet("background:#cdeccf; font-size:15px; font-weight:bold;")
        btn_done.clicked.connect(lambda: self.ctrl.finalize_loop_test())
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

        self.loop_test_summary_lbl = QtWidgets.QLabel("")
        self.loop_test_summary_lbl.setStyleSheet("font-weight:bold; font-size:15px; color:#264653;")
        self.loop_test_summary_lbl.setWordWrap(True)

        self.loop_test_meter_lbl = QtWidgets.QLabel("")
        self.loop_test_meter_lbl.setStyleSheet("font-size:15px;")
        self.loop_test_meter_lbl.setWordWrap(True)

        self.loop_test_feedback_lbl = QtWidgets.QLabel("")
        self.loop_test_feedback_lbl.setStyleSheet("font-size:15px; color:#444444;")
        self.loop_test_feedback_lbl.setWordWrap(True)

        sg_lay.addWidget(self.loop_test_summary_lbl)
        sg_lay.addWidget(self.loop_test_meter_lbl)
        sg_lay.addWidget(self.loop_test_feedback_lbl)
        outer.addWidget(status_grp)

        # ── 步骤列表 ──────────────────────────────────────────────────────
        steps_grp = QtWidgets.QGroupBox("测试步骤")
        steps_grp.setStyleSheet(
            "QGroupBox{background:white; color:#264653; font-size:15px;}"
            "QGroupBox::title{font-weight:bold;}"
            "QGroupBox *{font-weight:normal; font-size:12px;}"
        )
        sl_lay = QtWidgets.QVBoxLayout(steps_grp)
        self.loop_test_step_labels = []
        for _ in range(8):
            lbl = QtWidgets.QLabel("")
            lbl.setStyleSheet("font-size:15px; color:#666666;")
            sl_lay.addWidget(lbl)
            self.loop_test_step_labels.append(lbl)
        outer.addWidget(steps_grp)

        # ── 三相记录 ──────────────────────────────────────────────────────
        rec_grp = QtWidgets.QGroupBox("三相回路测量记录")
        rec_grp.setStyleSheet(
            "QGroupBox{background:white; color:#264653; font-size:15px;}"
            "QGroupBox::title{font-weight:bold;}"
            "QGroupBox *{font-weight:normal; font-size:12px;}"
        )
        rec_lay = QtWidgets.QVBoxLayout(rec_grp)
        self.loop_test_record_labels = {}
        for phase in ('A', 'B', 'C'):
            row_w = QtWidgets.QWidget()
            row_w.setStyleSheet("background:white;")
            row = QtWidgets.QHBoxLayout(row_w)
            row.setContentsMargins(0, 0, 0, 0)

            ph_lbl = QtWidgets.QLabel(f"{phase} 相")
            ph_lbl.setFixedWidth(60)
            ph_lbl.setStyleSheet("font-weight:bold; font-size:15px;")

            val_lbl = QtWidgets.QLabel("未记录")
            val_lbl.setFixedWidth(280)
            val_lbl.setStyleSheet("font-size:15px; color:#999999;")

            rec_btn = QtWidgets.QPushButton(f"记录 {phase} 相")
            rec_btn.setStyleSheet("background:#d8f3dc; font-size:15px;")
            rec_btn.clicked.connect(
                lambda _, ph=phase: self.ctrl.record_loop_measurement(ph))

            row.addWidget(ph_lbl)
            row.addWidget(val_lbl)
            row.addWidget(rec_btn)
            rec_lay.addWidget(row_w)
            self.loop_test_record_labels[phase] = val_lbl

        outer.addWidget(rec_grp)
        outer.addStretch()

    def _render_loop_test(self, p):
        state    = self.ctrl.loop_test_state
        records  = state['records']

        # ── 已完成锁定：不再响应任何硬件状态变化 ──────────────────────────
        if state.get('completed'):
            self.loop_test_summary_lbl.setText(
                "✅ 第一步已确认完成：三相回路连通性测试通过，数据已锁定。")
            self.loop_test_summary_lbl.setStyleSheet(
                "font-weight:bold; font-size:15px; color:#006400;")
            self.loop_test_meter_lbl.setText("")
            self.loop_test_feedback_lbl.setText("操作提示：第一步测试已完成，请继续进行第二步。")
            self.loop_test_feedback_lbl.setStyleSheet("font-size:15px; color:#006400;")
            for lbl, (text, _) in zip(self.loop_test_step_labels,
                                      self.ctrl.get_loop_test_steps()):
                lbl.setText("√ " + text)
                lbl.setStyleSheet("font-size:15px; color:#006400;")
            for phase, lbl in self.loop_test_record_labels.items():
                lbl.setText("回路导通 [连通正常]")
                lbl.setStyleSheet("font-size:15px; color:#006400;")
            return
        # ── 动态显示 ──────────────────────────────────────────────────────

        feedback = state['feedback']
        fb_color = state['feedback_color']
        current_phase = self.ctrl._get_current_loop_phase_match()
        sim = self.ctrl.sim_state

        if self.ctrl.is_loop_test_complete():
            summary = "第一步已确认完成：三相回路连通性测试通过，后续操作不再影响本步骤。"
            sc = '#006400'
        elif sim.gen1.breaker_closed and sim.gen2.breaker_closed:
            summary = "两台发电机已合闸，可开始测量三相回路。"
            sc = '#cc6600'
        else:
            summary = "请按步骤操作：断开小电阻 → 手动模式 → 起机合闸 → 万用表测量。"
            sc = '#264653'
        self.loop_test_summary_lbl.setText(summary)
        self.loop_test_summary_lbl.setStyleSheet(f"font-weight:bold; font-size:15px; color:{sc};")

        meter_text = p.meter_reading
        if current_phase:
            meter_text = f"当前表笔对准 {current_phase} 相回路。{meter_text}"
        self.loop_test_meter_lbl.setText(f"实时测量：{meter_text}")
        self.loop_test_meter_lbl.setStyleSheet(
            f"font-size:15px; color:{_qs(getattr(p, 'meter_color', 'black'))};")
        self.loop_test_feedback_lbl.setText(f"操作提示：{feedback}")
        self.loop_test_feedback_lbl.setStyleSheet(f"font-size:15px; color:{_qs(fb_color)};")

        for lbl, (text, done) in zip(self.loop_test_step_labels,
                                     self.ctrl.get_loop_test_steps()):
            lbl.setText(("√ " if done else "□ ") + text)
            lbl.setStyleSheet(f"font-size:15px; color:{'#006400' if done else '#666666'};")

        for phase, lbl in self.loop_test_record_labels.items():
            record = records[phase]
            if record is None:
                lbl.setText("未记录")
                lbl.setStyleSheet("font-size:15px; color:#999999;")
            else:
                lbl.setText("回路导通 [连通正常]")
                lbl.setStyleSheet("font-size:15px; color:#006400;")
