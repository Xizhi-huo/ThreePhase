"""
ui/panels/control_panel.py
右侧控制面板 + 槽函数

布局结构
────────
QVBoxLayout (ctrl_layout on ctrl_inner)
  ├─ 标题 QLabel
  ├─ 页切换 QWidget (2 × QPushButton, 横排)
  └─ QStackedWidget
       ├─ Page 0 — 运行控制 (系统模式 / Gen面板 / 接地 / 万用表 / 测试入口)
       └─ Page 1 — 参数设置 (仿真速度 / 增益 / 下垂 / PT黑盒 / 故障 / 相量 / 继电)
"""

from PyQt5 import QtWidgets, QtCore

from domain.constants import TRIP_CURRENT, AVAILABLE_MODES
from domain.enums import BreakerPosition, SystemMode
from domain.node_map import NODES


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
        title.setStyleSheet(
            "font-size:15px; font-weight:bold; padding:6px;"
            "color:#1e293b; background:#ffffff; border-bottom:2px solid #e2e8f0;")
        self.ctrl_layout.addWidget(title)

        # ── 页切换条 ──────────────────────────────────────────────────────
        switcher_w = QtWidgets.QWidget()
        switcher_w.setStyleSheet("background:#f1f5f9;")
        sw_lay = QtWidgets.QHBoxLayout(switcher_w)
        sw_lay.setContentsMargins(4, 4, 4, 0)
        sw_lay.setSpacing(4)

        self._cp_btn_run   = QtWidgets.QPushButton("▶ 运行控制")
        self._cp_btn_param = QtWidgets.QPushButton("⚙ 参数设置")

        for btn in (self._cp_btn_run, self._cp_btn_param):
            btn.setFixedHeight(28)
            btn.setStyleSheet(
                "QPushButton{background:#e2e8f0; color:#475569; border:none;"
                " border-radius:4px; font-size:12px; font-weight:bold;}"
                "QPushButton:checked{background:#1d4ed8; color:white;}"
            )
            btn.setCheckable(True)
            sw_lay.addWidget(btn)

        self._cp_btn_run.setChecked(True)
        self.ctrl_layout.addWidget(switcher_w)

        # ── QStackedWidget ────────────────────────────────────────────────
        self._cp_stack = QtWidgets.QStackedWidget()
        self.ctrl_layout.addWidget(self._cp_stack, 1)

        # — Page 0 —
        page0 = QtWidgets.QWidget()
        page0.setStyleSheet("background:#f1f5f9;")
        p0_lay = QtWidgets.QVBoxLayout(page0)
        p0_lay.setContentsMargins(0, 4, 0, 4)
        p0_lay.setSpacing(4)
        p0_lay.setAlignment(QtCore.Qt.AlignTop)
        self._cp_stack.addWidget(page0)

        # — Page 1 —
        page1 = QtWidgets.QWidget()
        page1.setStyleSheet("background:#f1f5f9;")
        p1_lay = QtWidgets.QVBoxLayout(page1)
        p1_lay.setContentsMargins(0, 4, 0, 4)
        p1_lay.setSpacing(4)
        p1_lay.setAlignment(QtCore.Qt.AlignTop)
        self._cp_stack.addWidget(page1)

        # 页切换连线
        def _switch(idx):
            self._cp_stack.setCurrentIndex(idx)
            self._cp_btn_run.setChecked(idx == 0)
            self._cp_btn_param.setChecked(idx == 1)

        self._cp_btn_run.clicked.connect(lambda: _switch(0))
        self._cp_btn_param.clicked.connect(lambda: _switch(1))

        # 填充两页
        self._build_page0(p0_lay, c)
        self._build_page1(p1_lay, c)

    # ── Page 0：运行控制 ─────────────────────────────────────────────────────
    def _build_page0(self, lay, c):

        # 系统运行模式
        mode_grp = QtWidgets.QGroupBox("🔧 系统运行模式")
        mode_lay = QtWidgets.QVBoxLayout(mode_grp)
        mode_lay.setSpacing(2)
        self._mode_bg = QtWidgets.QButtonGroup(self)
        for mode_val in AVAILABLE_MODES:
            available = (mode_val == SystemMode.ISOLATED_BUS)
            rb = QtWidgets.QRadioButton(mode_val if available else f"{mode_val} (待开发)")
            rb.setEnabled(available)
            rb.setChecked(c.sim_state.system_mode == mode_val)
            rb.toggled.connect(lambda checked, v=mode_val: self._on_mode_changed(v, checked))
            self._mode_bg.addButton(rb)
            mode_lay.addWidget(rb)
        lay.addWidget(mode_grp)

        # 合闸前测试入口
        self.btn_enter_test_mode = QtWidgets.QPushButton(
            "🔬 开始合闸前测试（进入测试模式）")
        self.btn_enter_test_mode.setStyleSheet(
            "background:#1d4ed8; color:white; font-weight:bold;"
            " font-size:13px; padding:8px; border-radius:4px;")
        self.btn_enter_test_mode.clicked.connect(self.enter_test_mode)
        lay.addWidget(self.btn_enter_test_mode)

        # 母排状态
        self.bus_status_lbl = QtWidgets.QLabel("母排: 无电 (死母线)")
        self.bus_status_lbl.setStyleSheet(
            "background:#fef3c7; color:#92400e; font-weight:bold;"
            " padding:5px; font-size:12px; border-radius:4px;"
            " border:1px solid #fcd34d;")
        self.bus_status_lbl.setAlignment(QtCore.Qt.AlignCenter)
        lay.addWidget(self.bus_status_lbl)

        self.bus_reference_lbl = QtWidgets.QLabel("参考基准: 无")
        self.bus_reference_lbl.setStyleSheet(
            "background:#f8fafc; color:#475569; font-weight:bold;"
            " padding:4px; font-size:12px; border-radius:4px;"
            " border:1px solid #e2e8f0;")
        self.bus_reference_lbl.setAlignment(QtCore.Qt.AlignCenter)
        lay.addWidget(self.bus_reference_lbl)

        # 仲裁器状态
        self.arbitrator_lbl = QtWidgets.QLabel("🛠️ 仲裁器: 待机")
        self.arbitrator_lbl.setStyleSheet(
            "background:#eff6ff; color:#1d4ed8; font-weight:bold;"
            " padding:6px; font-size:12px; border-radius:4px;"
            " border:1px solid #bfdbfe;")
        self.arbitrator_lbl.setAlignment(QtCore.Qt.AlignCenter)
        lay.addWidget(self.arbitrator_lbl)

        # 接地系统
        gnd_grp = QtWidgets.QGroupBox("🌍 中性点接地 (三相四线 N线)")
        gnd_lay = QtWidgets.QHBoxLayout(gnd_grp)
        gnd_lay.setSpacing(4)
        self._gnd_bg = QtWidgets.QButtonGroup(self)
        for label, val in [("断开(绝缘测试)", "断开"),
                           ("小电阻(10Ω)", "小电阻接地"),
                           ("直接接地", "直接接地")]:
            rb = QtWidgets.QRadioButton(label)
            rb.setChecked(c.sim_state.grounding_mode == val)
            rb.toggled.connect(lambda checked, v=val: self._on_grounding_changed(v, checked))
            self._gnd_bg.addButton(rb)
            gnd_lay.addWidget(rb)
        lay.addWidget(gnd_grp)

        # 远程启动信号
        self.remote_start_cb = QtWidgets.QCheckBox(
            "🔌 闭合全局【远程启动】信号 (触发自动模式)")
        self.remote_start_cb.setChecked(c.sim_state.remote_start_signal)
        self.remote_start_cb.setStyleSheet(
            "background:#f0fdf4; font-weight:bold; color:#15803d;"
            " font-size:12px; padding:5px; border-radius:4px;")
        self.remote_start_cb.toggled.connect(
            lambda v: setattr(c.sim_state, 'remote_start_signal', v))
        lay.addWidget(self.remote_start_cb)

        # 万用表
        self.multimeter_cb = QtWidgets.QCheckBox(
            "🔌 拿取万用表 (PT压差/回路连通演示)")
        self.multimeter_cb.setChecked(c.sim_state.multimeter_mode)
        self.multimeter_cb.setStyleSheet(
            "background:#fefce8; font-weight:bold; color:#854d0e;"
            " font-size:12px; padding:5px; border-radius:4px;")
        self.multimeter_cb.toggled.connect(self._on_multimeter_toggled)
        lay.addWidget(self.multimeter_cb)

        # 发电机面板
        self._build_gen_panel(1, lay)
        self._build_gen_panel(2, lay)

    # ── Page 1：参数设置 ─────────────────────────────────────────────────────
    def _build_page1(self, lay, c):

        # 仿真速度
        spd_grp = QtWidgets.QGroupBox("⏱️ 仿真全局时间流速")
        spd_lay = QtWidgets.QVBoxLayout(spd_grp)
        self.sim_speed_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.sim_speed_slider.setRange(5, 1000)
        self.sim_speed_slider.setValue(int(c.sim_state.sim_speed * 100))
        self.sim_speed_label = QtWidgets.QLabel(f"速度: {c.sim_state.sim_speed:.2f}×")
        self.sim_speed_slider.valueChanged.connect(self._on_sim_speed_changed)
        spd_lay.addWidget(self.sim_speed_label)
        spd_lay.addWidget(self.sim_speed_slider)
        lay.addWidget(spd_grp)

        # PCC 核心参数
        param_grp = QtWidgets.QGroupBox("🎛️ PCC核心参数整定 (Parameter Setup)")
        param_lay = QtWidgets.QFormLayout(param_grp)

        self.gov_gain_slider = self._make_slider(10, 200, int(c.sim_state.gov_gain * 100))
        self.gov_gain_label  = QtWidgets.QLabel(f"{c.sim_state.gov_gain:.2f}")
        self.gov_gain_slider.valueChanged.connect(self._on_gov_gain_changed)
        param_lay.addRow("调速增益(Gov):", self._slider_row(self.gov_gain_slider, self.gov_gain_label))

        self.sync_gain_slider = self._make_slider(50, 800, int(c.sim_state.sync_gain * 100))
        self.sync_gain_label  = QtWidgets.QLabel(f"{c.sim_state.sync_gain:.1f}")
        self.sync_gain_slider.valueChanged.connect(self._on_sync_gain_changed)
        param_lay.addRow("同步增益(Sync):", self._slider_row(self.sync_gain_slider, self.sync_gain_label))

        self.first_start_slider = self._make_slider(0, 30, c.sim_state.first_start_time)
        self.first_start_label  = QtWidgets.QLabel(f"{c.sim_state.first_start_time}s")
        self.first_start_slider.valueChanged.connect(self._on_first_start_changed)
        param_lay.addRow("死母线投入延时:", self._slider_row(self.first_start_slider, self.first_start_label))

        lay.addWidget(param_grp)

        # 下垂控制
        self.droop_cb = QtWidgets.QCheckBox("启用 P-f / Q-V 下垂控制 (自适应平衡)")
        self.droop_cb.setChecked(c.sim_state.droop_enabled)
        self.droop_cb.setStyleSheet(
            "background:#fff7ed; font-weight:bold; color:#9a3412;"
            " font-size:12px; padding:5px; border-radius:4px;")
        self.droop_cb.toggled.connect(lambda v: setattr(c.sim_state, 'droop_enabled', v))
        lay.addWidget(self.droop_cb)

        # PT 黑盒模式
        pt_grp = QtWidgets.QGroupBox("PT 黑盒教学模式")
        pt_lay = QtWidgets.QVBoxLayout(pt_grp)
        self.pt_blackbox_cb = QtWidgets.QCheckBox("随机打乱三相顺序")
        self.pt_blackbox_cb.setStyleSheet("font-weight:bold; color:#1d4ed8; font-size:12px;")
        self.pt_blackbox_cb.toggled.connect(c.on_pt_blackbox_toggle)
        pt_lay.addWidget(self.pt_blackbox_cb)
        reshuffle_btn = QtWidgets.QPushButton("重新打乱PT相序")
        reshuffle_btn.setProperty("secondary", "true")
        reshuffle_btn.setStyleSheet(
            "background:transparent; color:#475569; border:1px solid #cbd5e1;"
            " border-radius:4px; padding:4px 10px;")
        reshuffle_btn.clicked.connect(c.reshuffle_pt_phase_orders)
        pt_lay.addWidget(reshuffle_btn)
        lay.addWidget(pt_grp)

        # 故障注入
        self.fault_cb = QtWidgets.QCheckBox("陷阱：故意接反 Gen2 B/C相")
        self.fault_cb.setChecked(c.sim_state.fault_reverse_bc)
        self.fault_cb.setStyleSheet(
            "background:#fef2f2; font-weight:bold; color:#dc2626;"
            " font-size:12px; padding:5px; border-radius:4px;")
        self.fault_cb.toggled.connect(lambda v: setattr(c.sim_state, 'fault_reverse_bc', v))
        lay.addWidget(self.fault_cb)

        # 相量图参考系
        self.rotate_phasor_cb = QtWidgets.QCheckBox("相量图：绝对参考系 (电网旋转)")
        self.rotate_phasor_cb.setChecked(c.sim_state.rotate_phasor)
        self.rotate_phasor_cb.setStyleSheet(
            "background:#f8fafc; font-weight:bold; color:#1d4ed8;"
            " padding:4px; font-size:12px; border-radius:4px;")
        self.rotate_phasor_cb.toggled.connect(
            lambda v: setattr(c.sim_state, 'rotate_phasor', v))
        lay.addWidget(self.rotate_phasor_cb)

        # 继电保护
        self.relay_lbl = QtWidgets.QLabel(
            f"🛡️ 继电保护系统: 监控中 (阈值 {TRIP_CURRENT}A)")
        self.relay_lbl.setStyleSheet(
            "color:#1d4ed8; font-size:12px; padding:3px;")
        self.relay_lbl.setAlignment(QtCore.Qt.AlignCenter)
        self.relay_lbl.setWordWrap(True)
        lay.addWidget(self.relay_lbl)

        # 紧急合闸
        instant_btn = QtWidgets.QPushButton("⚡ 紧急一键强行合闸")
        instant_btn.setStyleSheet(
            "background:#dc2626; color:white; font-weight:bold;"
            " font-size:15px; padding:7px; border-radius:4px;")
        instant_btn.clicked.connect(c.instant_sync)
        lay.addWidget(instant_btn)

        # 暂停
        self.pause_btn = QtWidgets.QPushButton("⏸ 暂停整个物理空间")
        self.pause_btn.setStyleSheet(
            "background:#d97706; color:white; font-weight:bold;"
            " font-size:15px; padding:7px; border-radius:4px;")
        self.pause_btn.clicked.connect(c.toggle_pause)
        lay.addWidget(self.pause_btn)

        lay.addStretch()

    # ── 发电机子面板 ─────────────────────────────────────────────────────────
    def _build_gen_panel(self, gen_id: int, parent_lay: QtWidgets.QVBoxLayout):
        c = self.ctrl
        gen = c.sim_state.gen1 if gen_id == 1 else c.sim_state.gen2
        title = f"发电机 {gen_id} (Gen {gen_id} - {'虚线' if gen_id == 1 else '点划线'})"

        grp = QtWidgets.QGroupBox(title)
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

            def _sl_changed(val, _attr=attr, _scale=scale, _entry=entry, _gen_id=gen_id,
                            _clo=clamp_lo, _chi=clamp_hi):
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
        mr = QtWidgets.QHBoxLayout(mode_row)
        mr.setContentsMargins(0, 0, 0, 0)
        mr.addWidget(QtWidgets.QLabel("PCC模式:"))
        bg = QtWidgets.QButtonGroup(self)
        for txt, val in [("停机(0)", "stop"), ("手动", "manual"), ("自动", "auto")]:
            rb = QtWidgets.QRadioButton(txt)
            rb.setChecked(gen.mode == val)
            rb.toggled.connect(
                lambda checked, v=val, gid=gen_id: self._on_gen_mode(gid, v, checked))
            bg.addButton(rb)
            mr.addWidget(rb)
        setattr(self, f'_gen{gen_id}_mode_bg', bg)
        lay.addWidget(mode_row)

        # ── 断路器位置 ────────────────────────────────────────────────────
        pos_row = QtWidgets.QWidget()
        pr = QtWidgets.QHBoxLayout(pos_row)
        pr.setContentsMargins(0, 0, 0, 0)
        pr.addWidget(QtWidgets.QLabel("开关柜:"))
        pos_bg = QtWidgets.QButtonGroup(self)
        for txt, val in [("脱开", BreakerPosition.DISCONNECTED),
                         ("试验", BreakerPosition.TEST),
                         ("工作", BreakerPosition.WORKING)]:
            rb = QtWidgets.QRadioButton(txt)
            rb.setChecked(gen.breaker_position == val)
            rb.toggled.connect(
                lambda checked, v=val, gid=gen_id: self._on_brk_pos(gid, v, checked))
            pos_bg.addButton(rb)
            pr.addWidget(rb)
        setattr(self, f'_gen{gen_id}_pos_bg', pos_bg)
        lay.addWidget(pos_row)

        # ── 断路器状态标签 ────────────────────────────────────────────────
        status_lbl = QtWidgets.QLabel("断路器: OPEN")
        status_lbl.setStyleSheet(
            "background:#eff6ff; color:#1d4ed8; font-weight:bold;"
            " padding:3px; font-size:12px; border-radius:3px;"
            " border:1px solid #93c5fd;")
        status_lbl.setAlignment(QtCore.Qt.AlignCenter)
        setattr(self, f'status{gen_id}_lbl', status_lbl)
        lay.addWidget(status_lbl)

        # ── 起/停 + 合/分 按钮 ────────────────────────────────────────────
        btn_row = QtWidgets.QWidget()
        br = QtWidgets.QHBoxLayout(btn_row)
        br.setContentsMargins(0, 0, 0, 0)
        br.setSpacing(6)

        engine_btn = QtWidgets.QPushButton("起机 (Start)")
        engine_btn.setFixedWidth(130)
        engine_btn.setStyleSheet(
            "background:#16a34a; color:white; font-weight:bold;"
            " border-radius:4px; padding:5px;")
        engine_btn.clicked.connect(lambda: c.toggle_engine(gen_id))

        breaker_btn = QtWidgets.QPushButton("控合 (Close)")
        breaker_btn.setFixedWidth(130)
        breaker_btn.setStyleSheet(
            "background:#1d4ed8; color:white; font-weight:bold;"
            " border-radius:4px; padding:5px;")
        breaker_btn.clicked.connect(lambda: c.toggle_breaker(gen_id))

        setattr(self, f'btn_engine{gen_id}',  engine_btn)
        setattr(self, f'btn_breaker{gen_id}', breaker_btn)
        br.addWidget(engine_btn)
        br.addWidget(breaker_btn)
        lay.addWidget(btn_row)

        parent_lay.addWidget(grp)

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

    def _update_generator_buttons(self):
        for gen_id in (1, 2):
            sim = self.ctrl.sim_state
            gen = sim.gen1 if gen_id == 1 else sim.gen2
            is_manual  = gen.mode == "manual"
            is_running = gen.running
            brk_closed = gen.breaker_closed
            engine_btn  = getattr(self, f'btn_engine{gen_id}')
            breaker_btn = getattr(self, f'btn_breaker{gen_id}')

            engine_btn.setEnabled(is_manual)
            engine_btn.setText("停机 (Stop)" if is_running else "起机 (Start)")
            # 运行中 → 绿底警示 (停机操作); 停止 → 绿色邀请 (起机操作)
            if is_running:
                engine_btn.setStyleSheet(
                    "background:#16a34a; color:white; font-weight:bold;"
                    " border-radius:4px; padding:5px;")
            else:
                engine_btn.setStyleSheet(
                    "background:#e2e8f0; color:#475569; font-weight:bold;"
                    " border-radius:4px; padding:5px;")

            breaker_btn.setEnabled(is_manual)
            breaker_btn.setText("控分 (Open)" if brk_closed else "控合 (Close)")
            # 合闸 → 红色警示 (分闸操作); 分闸 → 蓝色邀请 (合闸操作)
            if brk_closed:
                breaker_btn.setStyleSheet(
                    "background:#dc2626; color:white; font-weight:bold;"
                    " border-radius:4px; padding:5px;")
            else:
                breaker_btn.setStyleSheet(
                    "background:#1d4ed8; color:white; font-weight:bold;"
                    " border-radius:4px; padding:5px;")

            # 同步滑块 / 输入框（物理引擎可能修改数值）
            em = getattr(self, f'_gen{gen_id}_entry_map', {})
            for attr, (sl, entry) in em.items():
                val   = getattr(gen, attr)
                scale = 10 if attr in ('freq', 'phase_deg') else 1
                sl.blockSignals(True)
                sl.setValue(int(val * scale))
                sl.blockSignals(False)
                if not entry.hasFocus():
                    entry.blockSignals(True)
                    entry.setText(f"{val:.1f}")
                    entry.blockSignals(False)
