"""
ui_widgets.py  ──  PyQt5 控件搭建模块
三相电并网仿真教学系统 · Qt 控件层

职责：
  - 右侧控制面板的所有 QWidget 构建（_build_control_panel / _build_gen_panel）
  - 三个 Tab 的 Qt 框架搭建（不含 matplotlib 图形内容）
  - 全部槽函数 / 事件处理器
  - 静态辅助控件工厂（_make_slider / _slider_row）

不依赖任何 matplotlib 绘图逻辑；通过 self.ctrl 访问控制器。
"""

from PyQt5 import QtWidgets, QtCore

from config_qt5 import (
    TRIP_CURRENT, BreakerPosition, AVAILABLE_MODES, SystemMode
)
from ui_nodes import NODES


# ════════════════════════════════════════════════════════════════════════════
# Mixin：控件搭建
# ════════════════════════════════════════════════════════════════════════════
class WidgetBuilderMixin:
    """
    混入类，为 PowerSyncUI 提供所有 Qt 控件的构建方法。
    使用时直接继承，无需实例化。
    """

    # ── 控制面板入口 ─────────────────────────────────────────────────────────
    def _build_control_panel(self):
        c = self.ctrl

        # 标题
        title = QtWidgets.QLabel("⚡ 并网仿真教学系统")
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("font-size:15px; font-weight:bold; padding:5px;")
        self.ctrl_layout.addWidget(title)

        # ── 系统运行模式 ──────────────────────────────────────────────────
        mode_grp = QtWidgets.QGroupBox("🔧 系统运行模式")
        mode_grp.setStyleSheet(
            "QGroupBox{background:#d6eaf8; color:#1a5276; font-size:12px;}"
            "QGroupBox::title{font-weight:bold;}"
            "QGroupBox *{font-weight:normal; font-size:12px;}"
        )
        mode_lay = QtWidgets.QVBoxLayout(mode_grp)
        self._mode_bg = QtWidgets.QButtonGroup(self)
        for mode_val in AVAILABLE_MODES:
            available = (mode_val == SystemMode.ISOLATED_BUS)
            rb = QtWidgets.QRadioButton(mode_val if available else f"{mode_val} (待开发)")
            rb.setEnabled(available)
            rb.setChecked(c.sim_state.system_mode == mode_val)
            rb.setStyleSheet("background:#d6eaf8;")
            rb.toggled.connect(lambda checked, v=mode_val: self._on_mode_changed(v, checked))
            self._mode_bg.addButton(rb)
            mode_lay.addWidget(rb)
        self.ctrl_layout.addWidget(mode_grp)

        # ── 母排状态 ──────────────────────────────────────────────────────
        self.bus_status_lbl = QtWidgets.QLabel("母排: 无电 (死母线)")
        self.bus_status_lbl.setStyleSheet(
            "background:#1a1a2e; color:#ff6600; font-weight:bold; padding:5px; font-size:12px;")
        self.bus_status_lbl.setAlignment(QtCore.Qt.AlignCenter)
        self.ctrl_layout.addWidget(self.bus_status_lbl)

        self.bus_reference_lbl = QtWidgets.QLabel("参考基准: 无")
        self.bus_reference_lbl.setStyleSheet(
            "background:#f4f4f4; color:#444; font-weight:bold; padding:4px; font-size:12px;")
        self.bus_reference_lbl.setAlignment(QtCore.Qt.AlignCenter)
        self.ctrl_layout.addWidget(self.bus_reference_lbl)

        # ── 仿真速度 ──────────────────────────────────────────────────────
        spd_grp = QtWidgets.QGroupBox("⏱️ 仿真全局时间流速")
        spd_grp.setStyleSheet(
            "QGroupBox{background:#e6f2ff; color:#003366; font-size:12px;}"
            "QGroupBox::title{font-weight:bold;}"
            "QGroupBox *{font-weight:normal; font-size:12px;}"
        )
        spd_lay = QtWidgets.QVBoxLayout(spd_grp)
        self.sim_speed_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.sim_speed_slider.setRange(5, 1000)
        self.sim_speed_slider.setValue(int(c.sim_state.sim_speed * 100))
        self.sim_speed_label = QtWidgets.QLabel(f"速度: {c.sim_state.sim_speed:.2f}×")
        self.sim_speed_slider.valueChanged.connect(self._on_sim_speed_changed)
        spd_lay.addWidget(self.sim_speed_label)
        spd_lay.addWidget(self.sim_speed_slider)
        self.ctrl_layout.addWidget(spd_grp)

        # ── 接地系统 ──────────────────────────────────────────────────────
        gnd_grp = QtWidgets.QGroupBox("🌍 中性点接地 (三相四线 N线)")
        gnd_grp.setStyleSheet(
            "QGroupBox{background:#e6ffe6; font-size:12px;}"
            "QGroupBox::title{font-weight:bold;}"
            "QGroupBox *{font-weight:normal; font-size:12px;}"
        )
        gnd_lay = QtWidgets.QHBoxLayout(gnd_grp)
        self._gnd_bg = QtWidgets.QButtonGroup(self)
        for label, val in [("断开(绝缘测试)", "断开"), ("小电阻(10Ω)", "小电阻接地"), ("直接接地", "直接接地")]:
            rb = QtWidgets.QRadioButton(label)
            rb.setChecked(c.sim_state.grounding_mode == val)
            rb.setStyleSheet("background:#e6ffe6;")
            rb.toggled.connect(lambda checked, v=val: self._on_grounding_changed(v, checked))
            self._gnd_bg.addButton(rb)
            gnd_lay.addWidget(rb)
        self.ctrl_layout.addWidget(gnd_grp)

        # ── 紧急合闸 ──────────────────────────────────────────────────────
        instant_btn = QtWidgets.QPushButton("⚡ 紧急一键强行合闸")
        instant_btn.setStyleSheet(
            "background:#ff3333; color:black; font-weight:bold; font-size:15px; padding:7px;")
        instant_btn.clicked.connect(c.instant_sync)
        self.ctrl_layout.addWidget(instant_btn)

        # ── 远程启动信号 ──────────────────────────────────────────────────
        self.remote_start_cb = QtWidgets.QCheckBox("🔌 闭合全局【远程启动】信号 (触发自动模式)")
        self.remote_start_cb.setChecked(c.sim_state.remote_start_signal)
        self.remote_start_cb.setStyleSheet(
            "background:#d9ead3; font-weight:bold; color:#274e13; font-size:12px; padding:5px;")
        self.remote_start_cb.toggled.connect(
            lambda v: setattr(c.sim_state, 'remote_start_signal', v))
        self.ctrl_layout.addWidget(self.remote_start_cb)

        # ── PCC 核心参数 ──────────────────────────────────────────────────
        param_grp = QtWidgets.QGroupBox("🎛️ PCC核心参数整定 (Parameter Setup)")
        param_grp.setStyleSheet(
            "QGroupBox{background:#ffebd6; color:#cc5500; font-size:12px;}"
            "QGroupBox::title{font-weight:bold;}"
            "QGroupBox *{font-weight:normal; font-size:12px;}"
        )
        param_lay = QtWidgets.QFormLayout(param_grp)

        self.gov_gain_slider = self._make_slider(10, 200, int(c.sim_state.gov_gain * 100), scale=100)
        self.gov_gain_label  = QtWidgets.QLabel(f"{c.sim_state.gov_gain:.2f}")
        self.gov_gain_slider.valueChanged.connect(self._on_gov_gain_changed)
        param_lay.addRow("调速增益(Gov):", self._slider_row(self.gov_gain_slider, self.gov_gain_label))

        self.sync_gain_slider = self._make_slider(50, 800, int(c.sim_state.sync_gain * 100), scale=100)
        self.sync_gain_label  = QtWidgets.QLabel(f"{c.sim_state.sync_gain:.1f}")
        self.sync_gain_slider.valueChanged.connect(self._on_sync_gain_changed)
        param_lay.addRow("同步增益(Sync):", self._slider_row(self.sync_gain_slider, self.sync_gain_label))

        self.first_start_slider = self._make_slider(0, 30, c.sim_state.first_start_time)
        self.first_start_label  = QtWidgets.QLabel(f"{c.sim_state.first_start_time}s")
        self.first_start_slider.valueChanged.connect(self._on_first_start_changed)
        param_lay.addRow("死母线投入延时:", self._slider_row(self.first_start_slider, self.first_start_label))

        self.ctrl_layout.addWidget(param_grp)

        # ── 仲裁器状态标签 ────────────────────────────────────────────────
        self.arbitrator_lbl = QtWidgets.QLabel("🛠️ 仲裁器: 待机")
        self.arbitrator_lbl.setStyleSheet(
            "background:black; color:#00ff00; font-weight:bold; padding:6px; font-size:12px;")
        self.arbitrator_lbl.setAlignment(QtCore.Qt.AlignCenter)
        self.ctrl_layout.addWidget(self.arbitrator_lbl)

        # ── 下垂控制 ──────────────────────────────────────────────────────
        self.droop_cb = QtWidgets.QCheckBox("启用 P-f / Q-V 下垂控制 (自适应平衡)")
        self.droop_cb.setChecked(c.sim_state.droop_enabled)
        self.droop_cb.setStyleSheet(
            "background:#ffcc99; font-weight:bold; color:#cc3300; font-size:12px; padding:5px;")
        self.droop_cb.toggled.connect(lambda v: setattr(c.sim_state, 'droop_enabled', v))
        self.ctrl_layout.addWidget(self.droop_cb)

        # ── 万用表 ────────────────────────────────────────────────────────
        self.multimeter_cb = QtWidgets.QCheckBox("🔌 拿取万用表 (PT压差/回路连通演示)")
        self.multimeter_cb.setChecked(c.sim_state.multimeter_mode)
        self.multimeter_cb.setStyleSheet(
            "background:#ffffcc; font-weight:bold; color:#aa5500; font-size:12px; padding:5px;")
        self.multimeter_cb.toggled.connect(self._on_multimeter_toggled)
        self.ctrl_layout.addWidget(self.multimeter_cb)

        # ── 故障注入 ──────────────────────────────────────────────────────
        self.fault_cb = QtWidgets.QCheckBox("陷阱：故意接反 Gen2 B/C相")
        self.fault_cb.setChecked(c.sim_state.fault_reverse_bc)
        self.fault_cb.setStyleSheet(
            "background:#ffcccc; font-weight:bold; color:red; font-size:12px; padding:5px;")
        self.fault_cb.toggled.connect(lambda v: setattr(c.sim_state, 'fault_reverse_bc', v))
        self.ctrl_layout.addWidget(self.fault_cb)

        # ── PT 黑盒模式 ───────────────────────────────────────────────────
        pt_grp = QtWidgets.QGroupBox()
        pt_grp.setStyleSheet(
            "QGroupBox{background:#eef3ff; font-size:12px;}"
            "QGroupBox::title{font-weight:bold;}"
            "QGroupBox *{font-weight:normal; font-size:12px;}"
        )
        pt_lay = QtWidgets.QVBoxLayout(pt_grp)
        self.pt_blackbox_cb = QtWidgets.QCheckBox("PT黑盒教学模式（随机打乱三相顺序）")
        self.pt_blackbox_cb.setStyleSheet(
            "background:#eef3ff; font-weight:bold; color:#224488; font-size:12px;")
        self.pt_blackbox_cb.toggled.connect(c.on_pt_blackbox_toggle)
        pt_lay.addWidget(self.pt_blackbox_cb)
        reshuffle_btn = QtWidgets.QPushButton("重新打乱PT相序")
        reshuffle_btn.setStyleSheet("background:#d9e8ff;")
        reshuffle_btn.clicked.connect(c.reshuffle_pt_phase_orders)
        pt_lay.addWidget(reshuffle_btn)
        self.ctrl_layout.addWidget(pt_grp)

        # ── 相量图参考系 ──────────────────────────────────────────────────
        self.rotate_phasor_cb = QtWidgets.QCheckBox("相量图：绝对参考系 (电网旋转)")
        self.rotate_phasor_cb.setChecked(c.sim_state.rotate_phasor)
        self.rotate_phasor_cb.setStyleSheet(
            "background:#ececec; font-weight:bold; color:#0055aa; padding:4px; font-size:12px;")
        self.rotate_phasor_cb.toggled.connect(
            lambda v: setattr(c.sim_state, 'rotate_phasor', v))
        self.ctrl_layout.addWidget(self.rotate_phasor_cb)

        # ── 发电机面板 ────────────────────────────────────────────────────
        self._build_gen_panel(1)
        self._build_gen_panel(2)

        # ── 继电保护标签 ──────────────────────────────────────────────────
        self.relay_lbl = QtWidgets.QLabel(f"🛡️ 继电保护系统: 监控中 (阈值 {TRIP_CURRENT}A)")
        self.relay_lbl.setStyleSheet("color:blue; font-size:12px; padding:3px;")
        self.relay_lbl.setAlignment(QtCore.Qt.AlignCenter)
        self.relay_lbl.setWordWrap(True)
        self.ctrl_layout.addWidget(self.relay_lbl)

        # ── 暂停按钮 ──────────────────────────────────────────────────────
        self.pause_btn = QtWidgets.QPushButton("⏸ 暂停整个物理空间")
        self.pause_btn.setStyleSheet(
            "background:#ffcc00; font-weight:bold; font-size:15px; padding:7px;")
        self.pause_btn.clicked.connect(c.toggle_pause)
        self.ctrl_layout.addWidget(self.pause_btn)

        self.ctrl_layout.addStretch()

    # ── 发电机子面板 ─────────────────────────────────────────────────────────
    def _build_gen_panel(self, gen_id: int):
        c = self.ctrl
        gen = c.sim_state.gen1 if gen_id == 1 else c.sim_state.gen2
        title = f"发电机 {gen_id} (Gen {gen_id} - {'虚线' if gen_id == 1 else '点划线'})"

        grp = QtWidgets.QGroupBox(title)
        grp.setStyleSheet(
            "QGroupBox{background:#ececec; color:#333; font-size:12px;}"
            "QGroupBox::title{font-weight:bold;}"
            "QGroupBox *{font-weight:normal; font-size:12px;}"
        )
        lay = QtWidgets.QVBoxLayout(grp)
        lay.setSpacing(3)

        # ── 频率 / 幅值 / 相位 滑块 ──────────────────────────────────────
        specs = [
            ("频率(Hz)", 450, 550, int(gen.freq * 10),       10, 'freq',      48.0,  52.0),
            ("幅值(V)",  0, 15000, int(gen.amp),               1, 'amp',       0.0,  15000.0),
            ("相位(°)", -1800, 1800, int(gen.phase_deg * 10), 10, 'phase_deg', -180.0, 180.0),
        ]
        entry_map = {}
        for label, vmin, vmax, init, scale, attr, clamp_lo, clamp_hi in specs:
            row_w = QtWidgets.QWidget()
            row_w.setStyleSheet("background:#ececec;")
            row = QtWidgets.QHBoxLayout(row_w)
            row.setContentsMargins(0, 0, 0, 0)

            lbl = QtWidgets.QLabel(label)
            lbl.setFixedWidth(80)
            lbl.setStyleSheet("font-size:12px;")

            sl = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            sl.setRange(vmin, vmax)
            sl.setValue(init)
            sl.setFixedWidth(145)

            entry = QtWidgets.QLineEdit(f"{gen.__dict__[attr]:.1f}")
            entry.setFixedWidth(68)
            entry.setStyleSheet("font-size:12px;")

            def _sl_changed(val, _attr=attr, _scale=scale, _entry=entry,
                            _gen_id=gen_id, _clo=clamp_lo, _chi=clamp_hi):
                v = round(val / _scale, 3)
                setattr(c.sim_state.gen1 if _gen_id == 1 else c.sim_state.gen2, _attr, v)
                _entry.setText(f"{v:.1f}")

            def _entry_changed(_attr=attr, _scale=scale, _sl=sl, _gen_id=gen_id,
                               _clo=clamp_lo, _chi=clamp_hi, _entry=entry):
                try:
                    v = max(_clo, min(_chi, float(_entry.text())))
                    setattr(c.sim_state.gen1 if _gen_id == 1 else c.sim_state.gen2, _attr, v)
                    _sl.blockSignals(True)
                    _sl.setValue(int(v * _scale))
                    _sl.blockSignals(False)
                    _entry.setText(f"{v:.1f}")
                except ValueError:
                    pass

            sl.valueChanged.connect(_sl_changed)
            entry.returnPressed.connect(_entry_changed)
            entry.editingFinished.connect(_entry_changed)

            row.addWidget(lbl)
            row.addWidget(sl)
            row.addWidget(entry)
            lay.addWidget(row_w)
            entry_map[attr] = (sl, entry)

        setattr(self, f'_gen{gen_id}_entry_map', entry_map)

        # ── PCC 运行模式 ──────────────────────────────────────────────────
        mode_row = QtWidgets.QWidget()
        mode_row.setStyleSheet("background:#ececec;")
        mr = QtWidgets.QHBoxLayout(mode_row)
        mr.setContentsMargins(0, 0, 0, 0)
        mr.addWidget(QtWidgets.QLabel("PCC模式:"))
        bg = QtWidgets.QButtonGroup(self)
        for txt, val in [("停机(0)", "stop"), ("手动", "manual"), ("自动", "auto")]:
            rb = QtWidgets.QRadioButton(txt)
            rb.setChecked(gen.mode == val)
            rb.setStyleSheet("background:#ececec;")
            rb.toggled.connect(
                lambda checked, v=val, gid=gen_id: self._on_gen_mode(gid, v, checked))
            bg.addButton(rb)
            mr.addWidget(rb)
        setattr(self, f'_gen{gen_id}_mode_bg', bg)
        lay.addWidget(mode_row)

        # ── 断路器位置 ────────────────────────────────────────────────────
        pos_row = QtWidgets.QWidget()
        pos_row.setStyleSheet("background:#ececec;")
        pr = QtWidgets.QHBoxLayout(pos_row)
        pr.setContentsMargins(0, 0, 0, 0)
        pr.addWidget(QtWidgets.QLabel("开关柜:"))
        pos_bg = QtWidgets.QButtonGroup(self)
        for txt, val in [("脱开", BreakerPosition.DISCONNECTED),
                         ("试验", BreakerPosition.TEST),
                         ("工作", BreakerPosition.WORKING)]:
            rb = QtWidgets.QRadioButton(txt)
            rb.setChecked(gen.breaker_position == val)
            rb.setStyleSheet("background:#ececec;")
            rb.toggled.connect(
                lambda checked, v=val, gid=gen_id: self._on_brk_pos(gid, v, checked))
            pos_bg.addButton(rb)
            pr.addWidget(rb)
        setattr(self, f'_gen{gen_id}_pos_bg', pos_bg)
        lay.addWidget(pos_row)

        # ── 断路器状态标签 ────────────────────────────────────────────────
        status_lbl = QtWidgets.QLabel("断路器: OPEN")
        status_lbl.setStyleSheet(
            "background:gray; color:white; font-weight:bold; padding:3px; font-size:12px;")
        status_lbl.setAlignment(QtCore.Qt.AlignCenter)
        setattr(self, f'status{gen_id}_lbl', status_lbl)
        lay.addWidget(status_lbl)

        # ── 起/停 + 合/分 按钮 ────────────────────────────────────────────
        btn_row = QtWidgets.QWidget()
        btn_row.setStyleSheet("background:#ececec;")
        br = QtWidgets.QHBoxLayout(btn_row)
        br.setContentsMargins(0, 0, 0, 0)

        engine_btn = QtWidgets.QPushButton("起机 (Start)")
        engine_btn.setFixedWidth(130)
        engine_btn.setStyleSheet("background:#99ff99;")
        engine_btn.clicked.connect(lambda: c.toggle_engine(gen_id))

        breaker_btn = QtWidgets.QPushButton("控合 (Close)")
        breaker_btn.setFixedWidth(130)
        breaker_btn.setStyleSheet("background:#99ff99;")
        breaker_btn.clicked.connect(lambda: c.toggle_breaker(gen_id))

        setattr(self, f'btn_engine{gen_id}',  engine_btn)
        setattr(self, f'btn_breaker{gen_id}', breaker_btn)
        br.addWidget(engine_btn)
        br.addWidget(breaker_btn)
        lay.addWidget(btn_row)

        self.ctrl_layout.addWidget(grp)

    # ── Tab 3：回路连通性测试 ─────────────────────────────────────────────────
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

    # ── Tab 4：同步功能测试 ───────────────────────────────────────────────────
    def _setup_tab_sync_test(self):
        tab = QtWidgets.QWidget()
        tab.setStyleSheet("background:#fffbf0;")
        self.tab_widget.addTab(tab, " ⚡ 第三步：同步功能测试 ")
        outer = QtWidgets.QVBoxLayout(tab)
        outer.setContentsMargins(18, 14, 18, 14)
        outer.setSpacing(8)

        hdr = QtWidgets.QLabel("隔离母排合闸前 - 第三步：同步功能测试")
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

        # ── 操作按钮 ──────────────────────────────────────────────────────
        act_row = QtWidgets.QWidget()
        act_row.setStyleSheet("background:#fffbf0;")
        ar = QtWidgets.QHBoxLayout(act_row)
        ar.setContentsMargins(0, 0, 0, 0)
        btn_wave = QtWidgets.QPushButton("打开波形/相量页")
        btn_wave.setStyleSheet("background:#d9ecff;")
        btn_wave.clicked.connect(lambda: self.tab_widget.setCurrentIndex(0))
        btn_reset = QtWidgets.QPushButton("重置同步测试")
        btn_reset.setStyleSheet("background:#ffd6d6;")
        btn_reset.clicked.connect(lambda: self.ctrl.reset_sync_test())
        btn_done = QtWidgets.QPushButton("完成第三步测试")
        btn_done.setStyleSheet("background:#cdeccf; font-size:15px; font-weight:bold;")
        btn_done.clicked.connect(lambda: self.ctrl.finalize_sync_test())
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
        for _ in range(10):
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
        btn_r1.setStyleSheet("background:#d8f3dc; font-size:15px;")
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
        btn_r2.setStyleSheet("background:#d8f3dc; font-size:15px;")
        btn_r2.clicked.connect(lambda: self.ctrl.record_sync_round(2))
        row2.addWidget(self.sync_round2_lbl, 1)
        row2.addWidget(btn_r2)
        rec_lay.addWidget(row2_w)

        outer.addWidget(rec_grp)
        outer.addStretch()

    # ── Tab 5：PT 考核 ────────────────────────────────────────────────────────
    def _setup_tab_pt_exam(self):
        tab = QtWidgets.QWidget()
        tab.setStyleSheet("background:#f8fbff;")
        self.tab_widget.addTab(tab, " 🧪 第二步：PT二次端子压差测试 ")
        outer = QtWidgets.QVBoxLayout(tab)
        outer.setContentsMargins(18, 14, 18, 14)
        outer.setSpacing(8)

        # 标题
        hdr = QtWidgets.QLabel("隔离母排合闸前 - 第二步：PT二次端子压差测试")
        hdr.setStyleSheet("font-size:18px; font-weight:bold; color:#16324f;")
        outer.addWidget(hdr)

        desc = QtWidgets.QLabel(
            "完成第一步后，恢复中性点小电阻接地，并将机组切至工作位置并入母排。"
            "随后在母排拓扑页使用万用表测量并记录三相 PT 二次端子压差。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color:#334e68; font-size:15px;")
        outer.addWidget(desc)

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
        btn_topo = QtWidgets.QPushButton("打开母排拓扑页")
        btn_topo.setStyleSheet("background:#d9ecff;")
        btn_topo.clicked.connect(lambda: self.tab_widget.setCurrentIndex(1))
        btn_mm = QtWidgets.QPushButton("开启/关闭万用表")
        btn_mm.setStyleSheet("background:#fff3bf;")
        btn_mm.clicked.connect(
            lambda: self.multimeter_cb.setChecked(not self.multimeter_cb.isChecked()))
        btn_reset = QtWidgets.QPushButton("重置当前机组测试")
        btn_reset.setStyleSheet("background:#ffd6d6;")
        btn_reset.clicked.connect(
            lambda: self.ctrl.reset_pt_exam(self._pt_target_bg.checkedId()))
        btn_done = QtWidgets.QPushButton("完成第二步测试")
        btn_done.setStyleSheet("background:#cdeccf; font-size:15px; font-weight:bold;")
        btn_done.clicked.connect(
            lambda: self.ctrl.finalize_pt_exam(self._pt_target_bg.checkedId()))
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
            rec_btn.setStyleSheet("background:#d8f3dc; font-size:15px;")
            rec_btn.clicked.connect(
                lambda _, ph=phase: self.ctrl.record_pt_measurement(ph))

            row.addWidget(ph_lbl)
            row.addWidget(val_lbl)
            row.addWidget(rec_btn)
            rec_lay.addWidget(row_w)
            self.pt_exam_record_labels[phase] = val_lbl

        outer.addWidget(rec_grp)
        outer.addStretch()

    # ════════════════════════════════════════════════════════════════════════
    # 辅助控件工厂
    # ════════════════════════════════════════════════════════════════════════
    @staticmethod
    def _make_slider(vmin, vmax, init, scale=1) -> QtWidgets.QSlider:
        sl = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        sl.setRange(vmin, vmax)
        sl.setValue(init)
        return sl

    @staticmethod
    def _slider_row(slider, label) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        lay = QtWidgets.QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(slider, 1)
        lay.addWidget(label)
        return w

    # ════════════════════════════════════════════════════════════════════════
    # 槽函数 / 事件处理器
    # ════════════════════════════════════════════════════════════════════════
    def _on_mode_changed(self, val, checked):
        if checked:
            self.ctrl.sim_state.system_mode = val

    def _on_grounding_changed(self, val, checked):
        if checked:
            self.ctrl.sim_state.grounding_mode = val

    def _on_sim_speed_changed(self, v):
        speed = v / 100.0
        self.ctrl.sim_state.sim_speed = speed
        self.sim_speed_label.setText(f"速度: {speed:.2f}×")

    def _on_gov_gain_changed(self, v):
        val = v / 100.0
        self.ctrl.sim_state.gov_gain = val
        self.gov_gain_label.setText(f"{val:.2f}")

    def _on_sync_gain_changed(self, v):
        val = v / 100.0
        self.ctrl.sim_state.sync_gain = val
        self.sync_gain_label.setText(f"{val:.1f}")

    def _on_first_start_changed(self, v):
        self.ctrl.sim_state.first_start_time = v
        self.first_start_label.setText(f"{v}s")

    def _on_multimeter_toggled(self, checked):
        self.ctrl.sim_state.multimeter_mode = checked

    def _on_gen_mode(self, gen_id, val, checked):
        if checked:
            gen = self.ctrl.sim_state.gen1 if gen_id == 1 else self.ctrl.sim_state.gen2
            gen.mode = val

    def _on_brk_pos(self, gen_id, val, checked):
        if checked:
            gen = self.ctrl.sim_state.gen1 if gen_id == 1 else self.ctrl.sim_state.gen2
            gen.breaker_position = val

    def _on_circuit_click(self, event):
        """母排拓扑图鼠标点击 → 万用表表笔落点。"""
        if not self.ctrl.sim_state.multimeter_mode:
            return
        if event.inaxes != self.ax_circuit:
            return
        if event.xdata is None or event.ydata is None:
            return

        closest_node = None
        min_dist = 0.04
        for name, data in NODES.items():
            dist = ((event.xdata - data[0])**2 + (event.ydata - data[1])**2) ** 0.5
            if dist < min_dist:
                closest_node = name
                min_dist = dist

        if closest_node:
            sim = self.ctrl.sim_state
            if sim.probe1_node is None:
                sim.probe1_node = closest_node
            elif sim.probe2_node is None and closest_node != sim.probe1_node:
                sim.probe2_node = closest_node
            else:
                sim.probe1_node = closest_node
                sim.probe2_node = None