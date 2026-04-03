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

import random as _random

from PyQt5 import QtWidgets, QtCore

from domain.constants import TRIP_CURRENT, AVAILABLE_MODES
from domain.enums import BreakerPosition, SystemMode
from domain.fault_scenarios import SCENARIOS
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

        # ── 故障训练场景预设（教师在进入测试前设置，学员不可见）──────────────
        self._pre_test_scenario_id = ''   # 默认无故障
        self._pre_test_flow_mode = 'teaching'
        fault_grp = QtWidgets.QGroupBox("故障训练场景（教师预设）")
        fault_grp.setStyleSheet(
            "QGroupBox{background:#fffbeb; color:#92400e; font-size:11px;"
            " font-weight:bold; border:1px solid #fcd34d; border-radius:5px;"
            " margin-top:6px; padding-top:6px;}"
            "QGroupBox::title{subcontrol-origin:margin; left:8px;"
            " background:#fffbeb; color:#92400e;}"
            "QGroupBox *{font-size:11px; color:#374151; font-weight:normal;}")
        fg_lay = QtWidgets.QVBoxLayout(fault_grp)
        fg_lay.setContentsMargins(6, 4, 6, 6)
        fg_lay.setSpacing(4)

        # 第一行：三个模式按钮
        btn_row = QtWidgets.QWidget()
        btn_row.setStyleSheet("background:transparent;")
        br_lay = QtWidgets.QHBoxLayout(btn_row)
        br_lay.setContentsMargins(0, 0, 0, 0)
        br_lay.setSpacing(4)

        _btn_ss_active   = ("background:#1d4ed8; color:white; font-size:11px;"
                            " font-weight:bold; padding:3px 6px; border-radius:3px;")
        _btn_ss_inactive = ("background:#e2e8f0; color:#475569; font-size:11px;"
                            " padding:3px 6px; border-radius:3px;")

        self._fp_btn_normal = QtWidgets.QPushButton("正常模式")
        self._fp_btn_random = QtWidgets.QPushButton("随机故障")
        self._fp_btn_choose = QtWidgets.QPushButton("指定场景...")

        self._fp_btn_normal.setStyleSheet(_btn_ss_active)
        self._fp_btn_random.setStyleSheet(_btn_ss_inactive)
        self._fp_btn_choose.setStyleSheet(_btn_ss_inactive)

        self._fp_btn_normal.clicked.connect(lambda: self._on_fp_set(''))
        self._fp_btn_random.clicked.connect(self._on_fp_random)
        self._fp_btn_choose.clicked.connect(self._on_fp_choose)

        br_lay.addWidget(self._fp_btn_normal, 1)
        br_lay.addWidget(self._fp_btn_random, 1)
        br_lay.addWidget(self._fp_btn_choose, 1)
        fg_lay.addWidget(btn_row)

        # 第二行：已选场景状态标签
        self._fp_status_lbl = QtWidgets.QLabel(
            "已选: 正常模式（无故障注入）\n流程模式: 教学模式")
        self._fp_status_lbl.setStyleSheet(
            "color:#92400e; font-size:11px; padding:2px 0;")
        self._fp_status_lbl.setWordWrap(True)
        fg_lay.addWidget(self._fp_status_lbl)

        lay.addWidget(fault_grp)

        # ── 合闸前测试入口 ────────────────────────────────────────────────
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

        # 发电机柜连线可见性（黑盒模式）
        self.show_gen_wires_cb = QtWidgets.QCheckBox(
            "显示发电机与母排之间的连线（取消勾选 = 黑盒模式）")
        self.show_gen_wires_cb.setChecked(c.sim_state.show_gen_wires)
        self.show_gen_wires_cb.setStyleSheet(
            "background:#f0f9ff; font-weight:bold; color:#0369a1;"
            " font-size:12px; padding:5px; border-radius:4px;")
        self.show_gen_wires_cb.toggled.connect(
            lambda v: setattr(c.sim_state, 'show_gen_wires', v))
        lay.addWidget(self.show_gen_wires_cb)

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
        self.fault_cb.setChecked(c.g2_blackbox_order != ['A', 'B', 'C'])
        self.fault_cb.setStyleSheet(
            "background:#fef2f2; font-weight:bold; color:#dc2626;"
            " font-size:12px; padding:5px; border-radius:4px;")
        self.fault_cb.toggled.connect(c.set_g2_terminal_fault)
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
        self.relay_lbl.setMinimumHeight(40)
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
    # 故障预设槽函数
    # ════════════════════════════════════════════════════════════════════════
    def _on_fp_set(self, scenario_id: str):
        """设置预选故障场景，更新按钮样式和状态标签。"""
        _active   = ("background:#1d4ed8; color:white; font-size:11px;"
                     " font-weight:bold; padding:3px 6px; border-radius:3px;")
        _inactive = ("background:#e2e8f0; color:#475569; font-size:11px;"
                     " padding:3px 6px; border-radius:3px;")
        _fault    = ("background:#b45309; color:white; font-size:11px;"
                     " font-weight:bold; padding:3px 6px; border-radius:3px;")
        self._pre_test_scenario_id = scenario_id
        # 更新按钮高亮
        self._fp_btn_normal.setStyleSheet(_active if not scenario_id else _inactive)
        self._fp_btn_random.setStyleSheet(_inactive)
        self._fp_btn_choose.setStyleSheet(_fault if scenario_id else _inactive)
        # 更新状态标签
        self._refresh_pretest_status_label()

    def _refresh_pretest_status_label(self):
        mode_text = self._flow_mode_label(self._pre_test_flow_mode)
        scenario_id = self._pre_test_scenario_id
        if not scenario_id:
            self._fp_status_lbl.setText(
                f"已选: 正常模式（无故障注入）\n流程模式: {mode_text}")
            self._fp_status_lbl.setStyleSheet(
                "color:#92400e; font-size:11px; padding:2px 0;")
            return
        info = SCENARIOS.get(scenario_id, {})
        cat_label = info.get('label', '')
        self._fp_status_lbl.setText(
            f"已选: {scenario_id} — {cat_label}\n{info.get('title', '')}\n流程模式: {mode_text}")
        self._fp_status_lbl.setStyleSheet(
            "color:#dc2626; font-size:11px; padding:2px 0; font-weight:bold;")

    def _on_fp_random(self):
        """随机选取一个故障场景，不对外显示具体场景。"""
        fault_ids = [k for k in SCENARIOS if k]   # 排除空键
        sid = _random.choice(fault_ids)
        _active = ("background:#dc2626; color:white; font-size:11px;"
                   " font-weight:bold; padding:3px 6px; border-radius:3px;")
        _inactive = ("background:#e2e8f0; color:#475569; font-size:11px;"
                     " padding:3px 6px; border-radius:3px;")
        self._pre_test_scenario_id = sid
        self._fp_btn_normal.setStyleSheet(_inactive)
        self._fp_btn_random.setStyleSheet(_active)
        self._fp_btn_choose.setStyleSheet(_inactive)
        mode_text = self._flow_mode_label(self._pre_test_flow_mode)
        self._fp_status_lbl.setText(
            f"已选: 随机故障（进入测试后自动注入，内容对学员保密）\n流程模式: {mode_text}")
        self._fp_status_lbl.setStyleSheet(
            "color:#dc2626; font-size:11px; padding:2px 0; font-weight:bold;")

    def _on_fp_choose(self):
        """弹出故障场景选择对话框（手动指定）。"""
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("指定故障场景")
        dlg.setModal(True)
        dlg.resize(500, 620)

        lay = QtWidgets.QVBoxLayout(dlg)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)

        hdr = QtWidgets.QLabel(
            "选择要注入的故障场景\n（进入测试模式后学员不可见具体场景信息）")
        hdr.setStyleSheet("color:#1d4ed8; font-size:12px; font-weight:bold; padding:2px;")
        hdr.setWordWrap(True)
        lay.addWidget(hdr)

        current_id = self._pre_test_scenario_id
        btn_grp = QtWidgets.QButtonGroup(dlg)
        _COLORS = {None: '#64748b', 'I': '#dc2626', 'II': '#d97706',
                   'III': '#2563eb', 'IV': '#7c3aed'}
        scene_scroll = QtWidgets.QScrollArea()
        scene_scroll.setWidgetResizable(True)
        scene_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scene_wrap = QtWidgets.QWidget()
        scene_lay = QtWidgets.QVBoxLayout(scene_wrap)
        scene_lay.setContentsMargins(0, 0, 0, 0)
        scene_lay.setSpacing(4)
        for sid, info in SCENARIOS.items():
            cat = info.get('category')
            color = _COLORS.get(cat, '#64748b')
            cat_tag = f"[{info['label']}]  " if cat else ""
            rb = QtWidgets.QRadioButton(f"{cat_tag}{info['title']}")
            rb.setProperty('scenario_id', sid)
            rb.setStyleSheet(f"color:{color}; font-size:12px; padding:2px 0;")
            if sid == current_id:
                rb.setChecked(True)
            btn_grp.addButton(rb)
            scene_lay.addWidget(rb)
        scene_lay.addStretch()
        scene_scroll.setWidget(scene_wrap)
        lay.addWidget(scene_scroll, 1)

        mode_grp = QtWidgets.QGroupBox("流程模式")
        mode_lay = QtWidgets.QVBoxLayout(mode_grp)
        mode_lay.setContentsMargins(8, 6, 8, 6)
        mode_lay.setSpacing(4)
        mode_hint = QtWidgets.QLabel(
            "教学模式允许带故障继续后续步骤；工程模式要求当前步骤合格后才能进入下一步；"
            "考核模式在第四步闭环完成时自动结算成绩，第五步不计分。")
        mode_hint.setWordWrap(True)
        mode_hint.setStyleSheet("color:#475569; font-size:11px;")
        mode_lay.addWidget(mode_hint)
        mode_bg = QtWidgets.QButtonGroup(dlg)
        rb_teaching = QtWidgets.QRadioButton("教学模式")
        rb_engineering = QtWidgets.QRadioButton("工程模式")
        rb_assessment = QtWidgets.QRadioButton("考核模式")
        rb_teaching.setChecked(self._pre_test_flow_mode == 'teaching')
        rb_engineering.setChecked(self._pre_test_flow_mode == 'engineering')
        rb_assessment.setChecked(self._pre_test_flow_mode == 'assessment')
        mode_bg.addButton(rb_teaching)
        mode_bg.addButton(rb_engineering)
        mode_bg.addButton(rb_assessment)
        mode_lay.addWidget(rb_teaching)
        mode_lay.addWidget(rb_engineering)
        mode_lay.addWidget(rb_assessment)
        lay.addWidget(mode_grp)

        lay.addStretch()

        brow = QtWidgets.QHBoxLayout()
        btn_cancel = QtWidgets.QPushButton("取消")
        btn_ok = QtWidgets.QPushButton("确认")
        btn_ok.setStyleSheet(
            "background:#1d4ed8; color:white; font-weight:bold; padding:5px 14px;")
        btn_cancel.clicked.connect(dlg.reject)
        btn_ok.clicked.connect(dlg.accept)
        brow.addStretch()
        brow.addWidget(btn_cancel)
        brow.addWidget(btn_ok)
        lay.addLayout(brow)

        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            selected_id = ''
            for btn in btn_grp.buttons():
                if btn.isChecked():
                    selected_id = btn.property('scenario_id')
                    break
            self._pre_test_flow_mode = (
                'engineering' if rb_engineering.isChecked()
                else 'assessment' if rb_assessment.isChecked()
                else 'teaching'
            )
            self._on_fp_set(selected_id)

    @staticmethod
    def _flow_mode_label(mode: str) -> str:
        return {
            'teaching': '教学模式',
            'engineering': '工程模式',
            'assessment': '考核模式',
        }.get(mode, '教学模式')

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
            allow_engine_toggle = is_running or is_manual
            engine_btn  = getattr(self, f'btn_engine{gen_id}')
            breaker_btn = getattr(self, f'btn_breaker{gen_id}')

            engine_btn.setEnabled(allow_engine_toggle)
            engine_btn.setText("停机 (Stop)" if is_running else "起机 (Start)")
            # 运行中 → 绿底警示 (停机操作); 停止 → 绿色邀请 (起机操作)
            if is_running:
                engine_btn.setStyleSheet(
                    "background:#16a34a; color:white; font-weight:bold;"
                    " border-radius:4px; padding:5px;")
            elif allow_engine_toggle:
                engine_btn.setStyleSheet(
                    "background:#e2e8f0; color:#475569; font-weight:bold;"
                    " border-radius:4px; padding:5px;")
            else:
                engine_btn.setStyleSheet(
                    "background:#f1f5f9; color:#94a3b8; font-weight:bold;"
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
