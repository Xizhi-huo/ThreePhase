"""
ui/tabs/pt_voltage_check_tab.py
PT 单体线电压检查 Tab (Tab 3 — 第二步)
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

_BTN      = "font-size:14px; padding:4px 8px;"
_BTN_BOLD = "font-size:14px; font-weight:bold; padding:4px 8px;"

_ALL_KEYS = (
    'PT1_AB', 'PT1_BC', 'PT1_CA',
    'PT2_AB', 'PT2_BC', 'PT2_CA',
    'PT3_AB', 'PT3_BC', 'PT3_CA',
)

_KEY_TO_NODES = {
    'PT1_AB': ('PT1_A', 'PT1_B'), 'PT1_BC': ('PT1_B', 'PT1_C'), 'PT1_CA': ('PT1_C', 'PT1_A'),
    'PT2_AB': ('PT2_A', 'PT2_B'), 'PT2_BC': ('PT2_B', 'PT2_C'), 'PT2_CA': ('PT2_C', 'PT2_A'),
    'PT3_AB': ('PT3_A', 'PT3_B'), 'PT3_BC': ('PT3_B', 'PT3_C'), 'PT3_CA': ('PT3_C', 'PT3_A'),
}


class PtVoltageCheckTabMixin:
    """
    混入类，提供 PT 单体线电压检查 Tab 的构建和渲染方法。
    """

    # ── Tab3：PT 单体线电压检查 ──────────────────────────────────────────────
    def _setup_tab_pt_voltage_check(self):
        tab_outer = QtWidgets.QWidget()
        self.tab_widget.addTab(tab_outer, " 📏 第二步：PT线电压检查 ")
        _tlay = QtWidgets.QVBoxLayout(tab_outer)
        _tlay.setContentsMargins(0, 0, 0, 0)
        _scroll = QtWidgets.QScrollArea()
        tab = QtWidgets.QWidget()
        _scroll.setWidget(tab)
        _tlay.addWidget(_scroll)

        outer = QtWidgets.QVBoxLayout(tab)
        outer.setContentsMargins(18, 14, 18, 14)
        outer.setSpacing(8)

        hdr = QtWidgets.QLabel("隔离母排合闸前 - 第二步：PT 单体线电压检查")
        outer.addWidget(hdr)

        desc = QtWidgets.QLabel(
            "完成第一步后：① 恢复小电阻接地；② Gen1 起机并入母排（提供 PT1/PT2 参考电压）；"
            "③ 启动 Gen2，保持断路器断开（提供 PT3 参考电压）；④ 开启万用表，"
            "将红/黑表笔分别接同一 PT 的两相端子，依次测量 PT1/PT2/PT3 各自的 AB/BC/CA 线电压；"
            "⑤ 确认三组 PT 输出电压量级一致（均约 100V AC）后，点击「完成第二步测试」。"
        )
        desc.setWordWrap(True)
        outer.addWidget(desc)

        # ── 测试进行中横幅 ────────────────────────────────────────────────
        self.pt_voltage_check_banner = QtWidgets.QLabel(
            "📏 第二步测试进行中 — 请在母排拓扑页完成 PT1/PT2/PT3 各相线电压测量"
        )
        self.pt_voltage_check_banner.setWordWrap(True)
        self.pt_voltage_check_banner.setVisible(False)
        outer.addWidget(self.pt_voltage_check_banner)
        apply_step_shell(
            tab_outer,
            _scroll,
            tab,
            hdr,
            desc,
            self.pt_voltage_check_banner,
            banner_tone="success",
        )

        # ── 操作按钮 ──────────────────────────────────────────────────────
        act_row = QtWidgets.QWidget()
        ar = QtWidgets.QHBoxLayout(act_row)
        ar.setContentsMargins(0, 0, 0, 0)
        set_props(act_row, actionRow=True)

        self.btn_pt_voltage_start = QtWidgets.QPushButton("开始第二步测试")
        self.btn_pt_voltage_start.clicked.connect(self._on_toggle_pt_voltage_check_mode)
        apply_button_tone(self, self.btn_pt_voltage_start, "warning", hero=True)

        btn_topo = QtWidgets.QPushButton("打开母排拓扑页")
        btn_topo.clicked.connect(lambda: self.tab_widget.setCurrentIndex(1))
        apply_button_tone(self, btn_topo, "primary", secondary=True)

        btn_mm = QtWidgets.QPushButton("开启/关闭万用表")
        btn_mm.clicked.connect(
            lambda: self.multimeter_cb.setChecked(not self.multimeter_cb.isChecked()))
        apply_button_tone(self, btn_mm, "warning")

        btn_reset = QtWidgets.QPushButton("重置线电压检查")
        btn_reset.clicked.connect(lambda: self.ctrl.reset_pt_voltage_check())
        apply_button_tone(self, btn_reset, "danger")

        btn_done = QtWidgets.QPushButton("完成第二步测试")
        btn_done.clicked.connect(lambda: self.ctrl.finalize_pt_voltage_check())
        apply_button_tone(self, btn_done, "success", hero=True)

        ar.addWidget(self.btn_pt_voltage_start)
        ar.addWidget(btn_topo)
        ar.addWidget(btn_mm)
        ar.addWidget(btn_reset)
        ar.addWidget(btn_done)
        outer.addWidget(act_row)

        # ── 实时状态 ──────────────────────────────────────────────────────
        status_grp = QtWidgets.QGroupBox("实时状态")
        sg_lay = QtWidgets.QVBoxLayout(status_grp)

        self.pt_voltage_summary_lbl = QtWidgets.QLabel("")
        set_live_text(self.pt_voltage_summary_lbl, "info")
        self.pt_voltage_summary_lbl.setWordWrap(True)

        self.pt_voltage_meter_lbl = QtWidgets.QLabel("")
        set_props(self.pt_voltage_meter_lbl, liveText=True, tone="neutral")
        self.pt_voltage_meter_lbl.setWordWrap(True)

        self.pt_voltage_feedback_lbl = QtWidgets.QLabel("")
        set_live_text(self.pt_voltage_feedback_lbl, "neutral")
        self.pt_voltage_feedback_lbl.setWordWrap(True)

        sg_lay.addWidget(self.pt_voltage_summary_lbl)
        sg_lay.addWidget(self.pt_voltage_meter_lbl)
        sg_lay.addWidget(self.pt_voltage_feedback_lbl)
        outer.addWidget(status_grp)

        # ── 步骤列表 ──────────────────────────────────────────────────────
        steps_grp = QtWidgets.QGroupBox("测试步骤")
        sl_lay = QtWidgets.QVBoxLayout(steps_grp)
        self.pt_voltage_step_labels = []
        for _ in range(9):
            lbl = QtWidgets.QLabel("")
            set_props(lbl, stepListItem=True)
            sl_lay.addWidget(lbl)
            self.pt_voltage_step_labels.append(lbl)
        outer.addWidget(steps_grp)

        # ── 九组线电压测量记录（PT1/PT2/PT3 各三组） ─────────────────────
        rec_grp = QtWidgets.QGroupBox("PT 线电压测量记录（PT1/PT2/PT3 各三组，共九组）")
        rec_lay = QtWidgets.QVBoxLayout(rec_grp)
        self.pt_voltage_record_labels = {}

        pt_colors = {'PT1': '#e8f4f8', 'PT2': '#f0fff0', 'PT3': '#fff3e0'}
        pt_hints = {
            'PT1': '←Gen1在母排，提供PT1二次参考电压',
            'PT2': '←母排电压，Gen1并入后与PT1同源',
            'PT3': '←Gen2起机（不合闸），提供PT3二次参考电压',
        }

        for pt_name in ('PT1', 'PT2', 'PT3'):
            pt_color = pt_colors[pt_name]
            pt_grp = QtWidgets.QGroupBox(
                f"{pt_name} 侧线电压  {pt_hints[pt_name]}"
            )
            pt_grp.setStyleSheet(
                f"QGroupBox{{background:{pt_color}; color:#444; font-size:13px;}}"
                "QGroupBox *{font-weight:normal; font-size:12px;}"
            )
            pt_lay = QtWidgets.QVBoxLayout(pt_grp)

            for pair in ('AB', 'BC', 'CA'):
                key = f"{pt_name}_{pair}"
                n1, n2 = _KEY_TO_NODES[key]
                row_w = QtWidgets.QWidget()
                set_props(row_w, recordRow=True)
                row = QtWidgets.QHBoxLayout(row_w)
                row.setContentsMargins(10, 6, 10, 6)

                pair_lbl = QtWidgets.QLabel(f"{pair} 线电压")
                pair_lbl.setFixedWidth(80)
                set_live_text(pair_lbl, "info")

                probe_hint = QtWidgets.QLabel(f"（{n1} ↔ {n2}）")
                probe_hint.setFixedWidth(180)
                probe_hint.setStyleSheet("font-size:12px; color:#888888;")

                val_lbl = QtWidgets.QLabel("未记录")
                val_lbl.setFixedWidth(200)
                set_record_value(val_lbl, "neutral")

                rec_btn = QtWidgets.QPushButton(f"记录 {key}")
                rec_btn.clicked.connect(
                    lambda _, pt=pt_name, pp=pair:
                        self.ctrl.record_pt_voltage_measurement(pt, pp))
                apply_button_tone(self, rec_btn, "primary")

                row.addWidget(pair_lbl)
                row.addWidget(probe_hint)
                row.addWidget(val_lbl)
                row.addWidget(rec_btn)
                pt_lay.addWidget(row_w)
                self.pt_voltage_record_labels[key] = val_lbl

            rec_lay.addWidget(pt_grp)

        outer.addWidget(rec_grp)
        outer.addStretch()

    def _on_toggle_pt_voltage_check_mode(self):
        state = self.ctrl.pt_voltage_check_state
        if state.started:
            self.ctrl.stop_pt_voltage_check()
        else:
            self.ctrl.start_pt_voltage_check()

    def _render_pt_voltage_check(self, p):
        state = self.ctrl.pt_voltage_check_state
        records = state.records

        # ── 已完成锁定：所有 UI 完全冻结 ─────────────────────────────────
        if state.completed:
            self.pt_voltage_check_banner.setVisible(False)
            self.btn_pt_voltage_start.setText("开始第二步测试")
            apply_button_tone(self, self.btn_pt_voltage_start, "warning", hero=True)
            self.pt_voltage_summary_lbl.setText(
                "✅ 第二步已确认完成：PT1/PT2/PT3 线电压检查通过，数据已锁定。")
            set_live_text(self.pt_voltage_summary_lbl, "success")
            self.pt_voltage_meter_lbl.setText("")
            self.pt_voltage_feedback_lbl.setText(
                "操作提示：第二步测试已完成，请继续进行第三步 PT 相序检查。")
            set_live_text(self.pt_voltage_feedback_lbl, "success")
            for lbl, (text, _) in zip(self.pt_voltage_step_labels,
                                      self.ctrl.get_pt_voltage_check_steps()):
                set_step_item(lbl, text, True, True)
            for key, lbl in self.pt_voltage_record_labels.items():
                rec = records.get(key)
                if rec is not None:
                    lbl.setText(f"{rec['voltage']/1000:.2f} kV ✓")
                    set_record_value(lbl, "success")
            return

        started = state.started

        # ── 更新测试横幅和按钮文字 ────────────────────────────────────────
        self.pt_voltage_check_banner.setVisible(started)
        if started:
            self.btn_pt_voltage_start.setText("退出第二步测试")
            apply_button_tone(self, self.btn_pt_voltage_start, "danger", hero=True)
        else:
            self.btn_pt_voltage_start.setText("开始第二步测试")
            apply_button_tone(self, self.btn_pt_voltage_start, "warning", hero=True)

        # ── 动态显示 ──────────────────────────────────────────────────────
        feedback = state.feedback
        fb_color = state.feedback_color

        done_count = sum(1 for k in _ALL_KEYS if records.get(k) is not None)
        if done_count == 9:
            summary = 'PT1/PT2/PT3 线电压已全部记录，请点击\u201c完成第二步测试\u201d继续。'
            sc = '#cc6600'
        elif done_count > 0:
            summary = f"已记录 {done_count}/9 组线电压，请继续完成剩余项目。"
            sc = '#264653'
        else:
            summary = "请按步骤：Gen1并网 → 启动Gen2(不合闸) → 万用表 → 逐项记录PT1/PT2/PT3线电压。"
            sc = '#264653'

        self.pt_voltage_summary_lbl.setText(summary)
        set_live_text(self.pt_voltage_summary_lbl, "warning" if sc == '#cc6600' else "info")

        meter_text = p.meter_reading
        self.pt_voltage_meter_lbl.setText(f"实时测量：{meter_text}")
        set_props(self.pt_voltage_meter_lbl, liveText=True, tone=self._tone_from_color(getattr(p, 'meter_color', 'black')))

        self.pt_voltage_feedback_lbl.setText(f"操作提示：{feedback}")
        set_live_text(self.pt_voltage_feedback_lbl, self._tone_from_color(fb_color))

        if not started:
            for lbl, (text, _) in zip(self.pt_voltage_step_labels,
                                      self.ctrl.get_pt_voltage_check_steps()):
                set_step_item(lbl, text, False, False)
        else:
            for lbl, (text, done) in zip(self.pt_voltage_step_labels,
                                         self.ctrl.get_pt_voltage_check_steps()):
                set_step_item(lbl, text, done, True)

        for key, lbl in self.pt_voltage_record_labels.items():
            rec = records.get(key)
            if rec is None:
                lbl.setText("未记录")
                set_record_value(lbl, "neutral")
            else:
                primary_v = rec['voltage']                 # 一次侧 V（额定 10500V）
                ok = 8925.0 <= primary_v <= 12075.0        # ±15% of 10500V
                lbl.setText(f"{primary_v/1000:.2f} kV {'✓' if ok else '⚠'}")
                set_record_value(lbl, "success" if ok else "warning")
