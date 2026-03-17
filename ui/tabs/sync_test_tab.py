"""
ui/tabs/sync_test_tab.py
同步功能测试 Tab (Tab 5 — 第四步)
"""

from PyQt5 import QtWidgets

from ui.tabs.circuit_tab import _qs

_BTN      = "font-size:14px; padding:4px 8px;"
_BTN_BOLD = "font-size:14px; font-weight:bold; padding:4px 8px;"


class SyncTestTabMixin:
    """
    混入类，提供同步功能测试 Tab 的构建和渲染方法。
    """

    # ── Tab5：同步功能测试 ───────────────────────────────────────────────────
    def _setup_tab_sync_test(self):
        tab_outer = QtWidgets.QWidget()
        self.tab_widget.addTab(tab_outer, " ⚡ 第四步：同步功能测试 ")
        _tlay = QtWidgets.QVBoxLayout(tab_outer)
        _tlay.setContentsMargins(0, 0, 0, 0)
        _scroll = QtWidgets.QScrollArea()
        _scroll.setWidgetResizable(True)
        _scroll.setStyleSheet("QScrollArea{border:none;background:#fffbf0;}")
        tab = QtWidgets.QWidget()
        tab.setStyleSheet("background:#fffbf0;")
        _scroll.setWidget(tab)
        _tlay.addWidget(_scroll)

        outer = QtWidgets.QVBoxLayout(tab)
        outer.setContentsMargins(18, 14, 18, 14)
        outer.setSpacing(8)

        hdr = QtWidgets.QLabel("隔离母排合闸前 - 第四步：同步功能测试")
        hdr.setStyleSheet("font-size:18px; font-weight:bold; color:#7a4f00;")
        outer.addWidget(hdr)

        desc = QtWidgets.QLabel(
            "验证两台发电机的同步功能是否正常：第一轮以 Gen 1 为基准合闸，"
            "Gen 2 切至自动模式同步跟踪；第二轮互换角色，Gen 2 为基准，Gen 1 自动同步。"
            "两轮均记录后测试完成。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color:#5a3a00; font-size:15px;")
        outer.addWidget(desc)

        # ── 测试进行中横幅 ────────────────────────────────────────────────
        self.sync_test_mode_banner = QtWidgets.QLabel(
            "⚡ 第四步测试进行中 — 请按两轮步骤完成同步功能验证"
        )
        self.sync_test_mode_banner.setWordWrap(True)
        self.sync_test_mode_banner.setStyleSheet(
            "background:#fff3cd; color:#7a4f00; font-size:14px; "
            "font-weight:bold; padding:6px; border:1px solid #e6b800; border-radius:4px;"
        )
        self.sync_test_mode_banner.setVisible(False)
        outer.addWidget(self.sync_test_mode_banner)

        # ── 操作按钮 ──────────────────────────────────────────────────────
        act_row = QtWidgets.QWidget()
        act_row.setStyleSheet("background:#fffbf0;")
        ar = QtWidgets.QHBoxLayout(act_row)
        ar.setContentsMargins(0, 0, 0, 0)

        self.btn_sync_test_start = QtWidgets.QPushButton("开始第四步测试")
        self.btn_sync_test_start.setStyleSheet(f"background:#ffe082; {_BTN_BOLD}")
        self.btn_sync_test_start.clicked.connect(self._on_toggle_sync_test_mode)

        btn_wave = QtWidgets.QPushButton("打开波形/相量页")
        btn_wave.setStyleSheet(f"background:#d9ecff; {_BTN}")
        btn_wave.clicked.connect(lambda: self.tab_widget.setCurrentIndex(0))

        btn_reset = QtWidgets.QPushButton("重置同步测试")
        btn_reset.setStyleSheet(f"background:#ffd6d6; {_BTN}")
        btn_reset.clicked.connect(lambda: self.ctrl.reset_sync_test())

        btn_done = QtWidgets.QPushButton("完成第四步测试")
        btn_done.setStyleSheet(f"background:#cdeccf; {_BTN_BOLD}")
        btn_done.clicked.connect(lambda: self.ctrl.finalize_sync_test())

        ar.addWidget(self.btn_sync_test_start)
        ar.addWidget(btn_wave)
        ar.addWidget(btn_reset)
        ar.addWidget(btn_done)
        outer.addWidget(act_row)

        # ── 实时状态 ──────────────────────────────────────────────────────
        status_grp = QtWidgets.QGroupBox("实时同步状态")
        status_grp.setStyleSheet(
            "QGroupBox{background:white; color:#264653; font-size:15px;}"
            "QGroupBox::title{font-weight:bold;}"
            "QGroupBox *{font-weight:normal; font-size:12px;}"
        )
        sg_lay = QtWidgets.QVBoxLayout(status_grp)

        self.sync_test_summary_lbl = QtWidgets.QLabel("")
        self.sync_test_summary_lbl.setStyleSheet("font-weight:bold; font-size:15px; color:#264653;")
        self.sync_test_summary_lbl.setWordWrap(True)

        self.sync_test_live_lbl = QtWidgets.QLabel("")
        self.sync_test_live_lbl.setStyleSheet("font-size:15px; color:#444444;")
        self.sync_test_live_lbl.setWordWrap(True)

        self.sync_test_feedback_lbl = QtWidgets.QLabel("")
        self.sync_test_feedback_lbl.setStyleSheet("font-size:15px; color:#444444;")
        self.sync_test_feedback_lbl.setWordWrap(True)

        sg_lay.addWidget(self.sync_test_summary_lbl)
        sg_lay.addWidget(self.sync_test_live_lbl)
        sg_lay.addWidget(self.sync_test_feedback_lbl)
        outer.addWidget(status_grp)

        # ── 步骤列表 ──────────────────────────────────────────────────────
        steps_grp = QtWidgets.QGroupBox("测试步骤（共两轮，需按顺序完成）")
        steps_grp.setStyleSheet(
            "QGroupBox{background:white; color:#264653; font-size:15px;}"
            "QGroupBox::title{font-weight:bold;}"
            "QGroupBox *{font-weight:normal; font-size:12px;}"
        )
        sl_lay = QtWidgets.QVBoxLayout(steps_grp)
        self.sync_test_step_labels = []
        for _ in range(11):
            lbl = QtWidgets.QLabel("")
            lbl.setStyleSheet("font-size:15px; color:#666666;")
            sl_lay.addWidget(lbl)
            self.sync_test_step_labels.append(lbl)
        outer.addWidget(steps_grp)

        # ── 记录按钮 ──────────────────────────────────────────────────────
        rec_grp = QtWidgets.QGroupBox("记录测试结果")
        rec_grp.setStyleSheet(
            "QGroupBox{background:white; color:#264653; font-size:15px;}"
            "QGroupBox::title{font-weight:bold;}"
            "QGroupBox *{font-weight:normal; font-size:12px;}"
        )
        rec_lay = QtWidgets.QVBoxLayout(rec_grp)

        # 第一轮记录行
        row1_w = QtWidgets.QWidget()
        row1_w.setStyleSheet("background:white;")
        row1 = QtWidgets.QHBoxLayout(row1_w)
        row1.setContentsMargins(0, 0, 0, 0)
        self.sync_round1_lbl = QtWidgets.QLabel("Gen 1 基准 → Gen 2 同步：未记录")
        self.sync_round1_lbl.setStyleSheet("font-size:15px; color:#999999;")
        btn_r1 = QtWidgets.QPushButton("记录第一轮")
        btn_r1.setStyleSheet(f"background:#d8f3dc; {_BTN}")
        btn_r1.clicked.connect(lambda: self.ctrl.record_sync_round(1))
        row1.addWidget(self.sync_round1_lbl, 1)
        row1.addWidget(btn_r1)
        rec_lay.addWidget(row1_w)

        # 第二轮记录行
        row2_w = QtWidgets.QWidget()
        row2_w.setStyleSheet("background:white;")
        row2 = QtWidgets.QHBoxLayout(row2_w)
        row2.setContentsMargins(0, 0, 0, 0)
        self.sync_round2_lbl = QtWidgets.QLabel("Gen 2 基准 → Gen 1 同步：未记录")
        self.sync_round2_lbl.setStyleSheet("font-size:15px; color:#999999;")
        btn_r2 = QtWidgets.QPushButton("记录第二轮")
        btn_r2.setStyleSheet(f"background:#d8f3dc; {_BTN}")
        btn_r2.clicked.connect(lambda: self.ctrl.record_sync_round(2))
        row2.addWidget(self.sync_round2_lbl, 1)
        row2.addWidget(btn_r2)
        rec_lay.addWidget(row2_w)

        outer.addWidget(rec_grp)
        outer.addStretch()

    def _on_toggle_sync_test_mode(self):
        state = self.ctrl.sync_test_state
        if state.started:
            self.ctrl.stop_sync_test()
        else:
            self.ctrl.start_sync_test()

    def _render_sync_test(self, p):
        state    = self.ctrl.sync_test_state
        started  = state.started

        # ── 已完成锁定：所有 UI 完全冻结 ─────────────────────────────────
        if state.completed:
            self.sync_test_mode_banner.setVisible(False)
            self.btn_sync_test_start.setText("开始第四步测试")
            self.btn_sync_test_start.setStyleSheet(f"background:#ffe082; {_BTN_BOLD}")
            self.sync_test_summary_lbl.setText(
                "✅ 第四步已确认完成：同步功能测试通过，数据已锁定。")
            self.sync_test_summary_lbl.setStyleSheet(
                "font-weight:bold; font-size:15px; color:#006400;")
            self.sync_test_live_lbl.setText("")
            self.sync_test_feedback_lbl.setText("操作提示：第四步测试已完成，全部预合闸测量流程通过。")
            self.sync_test_feedback_lbl.setStyleSheet("font-size:15px; color:#006400;")
            for lbl, (text, _) in zip(self.sync_test_step_labels,
                                      self.ctrl.get_sync_test_steps()):
                lbl.setText("√ " + text)
                lbl.setStyleSheet("font-size:15px; color:#006400;")
            self.sync_round1_lbl.setText("Gen 1 基准 → Gen 2 同步：已记录 ✓")
            self.sync_round1_lbl.setStyleSheet("font-size:15px; color:#006400;")
            self.sync_round2_lbl.setText("Gen 2 基准 → Gen 1 同步：已记录 ✓")
            self.sync_round2_lbl.setStyleSheet("font-size:15px; color:#006400;")
            return

        # ── 更新测试横幅和按钮文字 ────────────────────────────────────────
        self.sync_test_mode_banner.setVisible(started)
        if started:
            self.btn_sync_test_start.setText("退出第四步测试")
            self.btn_sync_test_start.setStyleSheet(
                f"background:#f4a261; color:white; {_BTN_BOLD}")
        else:
            self.btn_sync_test_start.setText("开始第四步测试")
            self.btn_sync_test_start.setStyleSheet(f"background:#ffe082; {_BTN_BOLD}")

        # ── 动态显示 ──────────────────────────────────────────────────────
        feedback = state.feedback
        fb_color = state.feedback_color
        sim      = self.ctrl.sim_state
        gen1, gen2 = sim.gen1, sim.gen2

        if self.ctrl.is_sync_test_complete():
            summary = "第四步已确认完成：同步功能测试通过，系统已恢复正常自动合闸逻辑。"
            sc = '#006400'
        elif state.round1_done and state.round2_done:
            summary = '两轮同步测试记录已完成，请点击\u201c完成第四步测试\u201d。'
            sc = '#cc6600'
        elif state.round1_done:
            summary = "第一轮已完成，请互换角色进行第二轮测试。"
            sc = '#cc6600'
        else:
            summary = "请按步骤完成两轮同步测试。"
            sc = '#264653'
        self.sync_test_summary_lbl.setText(summary)
        self.sync_test_summary_lbl.setStyleSheet(f"font-weight:bold; font-size:15px; color:{sc};")

        ref_gen = getattr(p, 'bus_reference_gen', None)
        if ref_gen == 1 and gen2.mode == "auto":
            df = abs(gen2.freq - gen1.freq)
            dv = abs(gen2.amp - gen1.amp)
            ok = self.ctrl._is_gen_synced(gen2, gen1)
            color = '#006400' if ok else '#cc4400'
            self.sync_test_live_lbl.setText(
                f"[第一轮] Gen2跟踪Gen1 — Δf={df:.3f} Hz，ΔV={dv:.0f} V  "
                f"{'[已同步 ✓]' if ok else '[同步中…]'}")
            self.sync_test_live_lbl.setStyleSheet(f"font-size:15px; color:{color};")
        elif ref_gen == 2 and gen1.mode == "auto":
            df = abs(gen1.freq - gen2.freq)
            dv = abs(gen1.amp - gen2.amp)
            ok = self.ctrl._is_gen_synced(gen1, gen2)
            color = '#006400' if ok else '#cc4400'
            self.sync_test_live_lbl.setText(
                f"[第二轮] Gen1跟踪Gen2 — Δf={df:.3f} Hz，ΔV={dv:.0f} V  "
                f"{'[已同步 ✓]' if ok else '[同步中…]'}")
            self.sync_test_live_lbl.setStyleSheet(f"font-size:15px; color:{color};")
        else:
            self.sync_test_live_lbl.setText(
                f"母排基准: {'Gen ' + str(ref_gen) if ref_gen else '无（死母线）'}  "
                f"| Gen1: {gen1.freq:.2f}Hz/{gen1.amp:.0f}V ({gen1.mode})  "
                f"| Gen2: {gen2.freq:.2f}Hz/{gen2.amp:.0f}V ({gen2.mode})")
            self.sync_test_live_lbl.setStyleSheet("font-size:15px; color:#444444;")

        self.sync_test_feedback_lbl.setText(f"操作提示：{feedback}")
        self.sync_test_feedback_lbl.setStyleSheet(f"font-size:15px; color:{_qs(fb_color)};")

        if not started:
            for lbl, (text, _) in zip(self.sync_test_step_labels,
                                      self.ctrl.get_sync_test_steps()):
                lbl.setText("□ " + text)
                lbl.setStyleSheet("font-size:15px; color:#aaaaaa;")
        else:
            for lbl, (text, done) in zip(self.sync_test_step_labels,
                                         self.ctrl.get_sync_test_steps()):
                lbl.setText(("√ " if done else "□ ") + text)
                lbl.setStyleSheet(f"font-size:15px; color:{'#006400' if done else '#666666'};")

        if state.round1_done:
            self.sync_round1_lbl.setText("Gen 1 基准 → Gen 2 同步：已记录 ✓")
            self.sync_round1_lbl.setStyleSheet("font-size:15px; color:#006400;")
        else:
            self.sync_round1_lbl.setText("Gen 1 基准 → Gen 2 同步：未记录")
            self.sync_round1_lbl.setStyleSheet("font-size:15px; color:#999999;")

        if state.round2_done:
            self.sync_round2_lbl.setText("Gen 2 基准 → Gen 1 同步：已记录 ✓")
            self.sync_round2_lbl.setStyleSheet("font-size:15px; color:#006400;")
        else:
            self.sync_round2_lbl.setText("Gen 2 基准 → Gen 1 同步：未记录")
            self.sync_round2_lbl.setStyleSheet("font-size:15px; color:#999999;")
