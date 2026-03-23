"""
ui/test_panel.py
合闸前测试模式 — 竖向测试控制条 Mixin

进入测试模式后，右侧控制台隐藏，本 Mixin 提供的竖向测试条替代之。
母排拓扑图自动保持前台，所有测试步骤的必要按钮全部集中在此条内。
"""

from PyQt5 import QtWidgets, QtCore
from domain.enums import BreakerPosition

# ── 主题色常量（清新工业教学风）────────────────────────────────────────────
_PANEL_BG   = "#f1f5f9"
_TITLE_BG   = "#ffffff"
_SECTION_BG = "#f8fafc"
_BTN        = "font-size:12px; padding:3px 8px; border-radius:3px;"
_GRP_STYLE  = (
    "QGroupBox{{background:{bg}; color:#1d4ed8; font-size:12px; font-weight:bold;"
    " border:1px solid #e2e8f0; border-radius:6px; margin-top:8px; padding-top:8px;}}"
    "QGroupBox::title{{subcontrol-origin:margin; left:10px;"
    " background:{bg}; color:#1d4ed8;}}"
    "QGroupBox *{{font-size:12px; color:#334155; font-weight:normal;}}"
)


class TestPanelMixin:
    """
    混入类，为 PowerSyncUI 提供合闸前测试模式的竖向控制条。
    """

    # ════════════════════════════════════════════════════════════════════
    # 构建入口
    # ════════════════════════════════════════════════════════════════════
    def _setup_test_panel(self):
        self._test_mode_active = False
        # dict: (step_key, gen_id) -> (brk_lbl, eng_btn_or_None, brk_btn, mode_rbs)
        self._tp_gen_refs: dict = {}

        # ── 外层容器（与 ctrl_container 同宽，初始隐藏）────────────────
        self.test_panel = QtWidgets.QWidget()
        self.test_panel.setFixedWidth(520)
        self.test_panel.setStyleSheet(f"background:{_PANEL_BG};")
        self.test_panel.setVisible(False)

        tl = QtWidgets.QVBoxLayout(self.test_panel)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(0)

        # ── 顶部标题栏 ────────────────────────────────────────────────
        top = QtWidgets.QWidget()
        top.setStyleSheet(
            f"background:{_TITLE_BG}; border-bottom:2px solid #e2e8f0;")
        top.setFixedHeight(44)
        trow = QtWidgets.QHBoxLayout(top)
        trow.setContentsMargins(8, 4, 8, 4)

        title = QtWidgets.QLabel("🔬 合闸前测试模式")
        title.setStyleSheet(
            "color:#1d4ed8; font-weight:bold; font-size:14px; border:none;")

        self.tp_btn_reset = QtWidgets.QPushButton("⚠️ 重置本步")
        self.tp_btn_reset.setStyleSheet(
            "background:#dc2626; color:white; font-weight:bold;"
            " font-size:12px; padding:2px 10px; border-radius:3px;")
        self.tp_btn_reset.clicked.connect(self._on_tp_reset_step)

        btn_exit = QtWidgets.QPushButton("退出测试")
        btn_exit.setStyleSheet(
            "background:#e2e8f0; color:#475569; font-size:12px;"
            " padding:2px 10px; border-radius:3px;")
        btn_exit.clicked.connect(self.exit_test_mode)

        self._tp_admin_mode = False
        self.tp_btn_admin = QtWidgets.QPushButton("🔧 管理员")
        self.tp_btn_admin.setCheckable(True)
        self.tp_btn_admin.setStyleSheet(
            "QPushButton{background:#7c3aed; color:white; font-size:12px;"
            " padding:2px 8px; border-radius:3px;}"
            "QPushButton:checked{background:#4c1d95;}")
        self.tp_btn_admin.clicked.connect(self._on_tp_toggle_admin)

        trow.addWidget(title, 1)
        trow.addWidget(self.tp_btn_admin)
        trow.addWidget(self.tp_btn_reset)
        trow.addWidget(btn_exit)
        tl.addWidget(top)

        # ── 步骤进度点（管理员模式下变为可点击按钮）─────────────────────
        self._tp_forced_step: int | None = None   # None = 自动推算
        step_bar = QtWidgets.QWidget()
        step_bar.setStyleSheet(
            f"background:{_TITLE_BG}; border-bottom:1px solid #e2e8f0;")
        step_bar.setFixedHeight(52)
        srow = QtWidgets.QHBoxLayout(step_bar)
        srow.setContentsMargins(8, 6, 8, 6)
        self.tp_step_btns: list = []   # list of QPushButton, index 0 = step 1
        _step_names = ["①回路", "②线压", "③相序", "④压差", "⑤同步"]
        for idx, name in enumerate(_step_names):
            step_num = idx + 1
            btn = QtWidgets.QPushButton(f"●\n{name}")
            btn.setFlat(True)
            btn.setCheckable(True)
            btn.setCursor(QtCore.Qt.ArrowCursor)   # 默认不可点击外观
            btn.setStyleSheet(self._tp_dot_style("idle"))
            btn.clicked.connect(
                lambda _chk, s=step_num: self._on_tp_step_btn_clicked(s))
            srow.addWidget(btn, 1)
            self.tp_step_btns.append(btn)
        tl.addWidget(step_bar)

        # ── 滚动内容区 ────────────────────────────────────────────────
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            f"QScrollArea{{border:none; background:{_PANEL_BG};}}")

        content = QtWidgets.QWidget()
        content.setStyleSheet(f"background:{_PANEL_BG};")
        cl = QtWidgets.QVBoxLayout(content)
        cl.setContentsMargins(8, 6, 8, 6)
        cl.setSpacing(6)

        # 全步骤共用：母排状态 + 万用表
        self.tp_bus_lbl = QtWidgets.QLabel("母排: --")
        self.tp_bus_lbl.setStyleSheet(
            f"background:#fef3c7; color:#92400e; font-weight:bold;"
            " font-size:12px; padding:4px; border-radius:4px;"
            " border:1px solid #fcd34d;")
        self.tp_bus_lbl.setAlignment(QtCore.Qt.AlignCenter)
        cl.addWidget(self.tp_bus_lbl)

        self._tp_mm_btn = QtWidgets.QPushButton("🔌 开启 / 关闭万用表")
        self._tp_mm_btn.setStyleSheet(
            "background:#fefce8; color:#854d0e; font-weight:bold;"
            " font-size:12px; padding:3px 8px; border-radius:3px;"
            " border:1px solid #fde68a;")
        self._tp_mm_btn.clicked.connect(
            lambda: self.multimeter_cb.setChecked(
                not self.multimeter_cb.isChecked()))
        cl.addWidget(self._tp_mm_btn)

        self.tp_meter_lbl = QtWidgets.QLabel("万用表: 关闭")
        self.tp_meter_lbl.setStyleSheet(
            "color:#94a3b8; font-size:12px; padding:2px;")
        self.tp_meter_lbl.setWordWrap(True)
        self.tp_meter_lbl.setMaximumWidth(320)
        cl.addWidget(self.tp_meter_lbl)

        # ── 各步骤专属区 ─────────────────────────────────────────────
        self._tp_step_grps = {
            1: self._build_step1(cl),
            2: self._build_step2(cl),
            3: self._build_step3(cl),
            4: self._build_step4(cl),
            5: self._build_step5(cl),
        }
        cl.addStretch()

        scroll.setWidget(content)
        tl.addWidget(scroll, 1)

        # ── 底部操作按钮 ──────────────────────────────────────────────
        bottom = QtWidgets.QWidget()
        bottom.setStyleSheet(
            f"background:{_TITLE_BG}; border-top:2px solid #e2e8f0;")
        brow = QtWidgets.QHBoxLayout(bottom)
        brow.setContentsMargins(8, 6, 8, 6)
        brow.setSpacing(6)

        self.tp_btn_start = QtWidgets.QPushButton("开始测试")
        self.tp_btn_start.setStyleSheet(
            "background:#d97706; color:white; font-weight:bold;"
            " font-size:13px; padding:6px; border-radius:4px;")
        self.tp_btn_start.clicked.connect(self._on_tp_start_step)

        self.tp_btn_complete = QtWidgets.QPushButton("完成本步 ✓")
        self.tp_btn_complete.setStyleSheet(
            "background:#16a34a; color:white; font-weight:bold;"
            " font-size:13px; padding:6px; border-radius:4px;")
        self.tp_btn_complete.clicked.connect(self._on_tp_complete_step)

        brow.addWidget(self.tp_btn_start, 1)
        brow.addWidget(self.tp_btn_complete, 1)
        tl.addWidget(bottom)

    # ════════════════════════════════════════════════════════════════════
    # Widget factories
    # ════════════════════════════════════════════════════════════════════
    def _make_grp(self, title, bg=_SECTION_BG):
        grp = QtWidgets.QGroupBox(title)
        grp.setStyleSheet(_GRP_STYLE.format(bg=bg))
        return grp

    def _make_btn(self, text, bg="#1d4ed8"):
        btn = QtWidgets.QPushButton(text)
        btn.setStyleSheet(f"background:{bg}; color:white; {_BTN}")
        return btn

    def _make_step_list(self, parent_lay, n_steps):
        """Add a checklist widget; return list of QLabel."""
        grp = self._make_grp("测试步骤")
        lay = QtWidgets.QVBoxLayout(grp)
        lay.setSpacing(2)
        labels = []
        for _ in range(n_steps):
            lbl = QtWidgets.QLabel("")
            lbl.setWordWrap(True)
            lbl.setStyleSheet("font-size:11px; color:#94a3b8;")
            lay.addWidget(lbl)
            labels.append(lbl)
        parent_lay.addWidget(grp)
        return labels

    def _make_gen_block(self, parent_lay, step_key, gen_id,
                        mode_options=None, show_pos=False, show_engine=True):
        """
        Add a compact Gen-N control block.

        mode_options : list of (label, val) for mode radio buttons,
                       or None to hide mode row.
        show_pos     : show 脱开/工作 position radio buttons
        show_engine  : show 起机/停机 toggle button
        """
        gen = self.ctrl.sim_state.gen1 if gen_id == 1 else self.ctrl.sim_state.gen2

        inner = QtWidgets.QGroupBox(f"Gen {gen_id}")
        inner.setStyleSheet(_GRP_STYLE.format(bg="#ffffff"))
        ilay = QtWidgets.QVBoxLayout(inner)
        ilay.setSpacing(2)
        ilay.setContentsMargins(4, 4, 4, 4)

        # Status label
        brk_lbl = QtWidgets.QLabel("--")
        brk_lbl.setStyleSheet(
            "color:#64748b; font-size:11px; background:transparent;")
        brk_lbl.setAlignment(QtCore.Qt.AlignCenter)
        ilay.addWidget(brk_lbl)

        # Mode radio buttons (optional)
        mode_rbs: dict = {}
        if mode_options:
            _pcc_lbl = QtWidgets.QLabel("PCC 模式:")
            _pcc_lbl.setStyleSheet("color:#64748b; font-size:10px; background:#f8fafc;")
            ilay.addWidget(_pcc_lbl)
            mr = QtWidgets.QWidget()
            mr.setStyleSheet("background:#f8fafc;")
            mh = QtWidgets.QHBoxLayout(mr)
            mh.setContentsMargins(0, 0, 0, 0)
            mh.setSpacing(4)
            bg_mode = QtWidgets.QButtonGroup(self)
            for txt, val in mode_options:
                rb = QtWidgets.QRadioButton(txt)
                rb.setStyleSheet("color:#334155; background:#f8fafc;")
                rb.setChecked(gen.mode == val)
                rb.toggled.connect(
                    lambda chk, v=val, gid=gen_id: self._on_gen_mode(gid, v, chk))
                bg_mode.addButton(rb)
                mh.addWidget(rb)
                mode_rbs[val] = rb
            ilay.addWidget(mr)

        # Position radio buttons (optional)
        if show_pos:
            _cab_lbl = QtWidgets.QLabel("开关柜位置:")
            _cab_lbl.setStyleSheet("color:#64748b; font-size:10px; background:#f8fafc;")
            ilay.addWidget(_cab_lbl)
            pr = QtWidgets.QWidget()
            pr.setStyleSheet("background:#f8fafc;")
            ph_row = QtWidgets.QHBoxLayout(pr)
            ph_row.setContentsMargins(0, 0, 0, 0)
            ph_row.setSpacing(4)
            bg_pos = QtWidgets.QButtonGroup(self)
            for txt, val in [("脱开", BreakerPosition.DISCONNECTED),
                              ("工作", BreakerPosition.WORKING)]:
                rb = QtWidgets.QRadioButton(txt)
                rb.setStyleSheet("color:#334155; background:#f8fafc;")
                rb.setChecked(gen.breaker_position == val)
                rb.toggled.connect(
                    lambda chk, v=val, gid=gen_id: self._on_brk_pos(gid, v, chk))
                bg_pos.addButton(rb)
                ph_row.addWidget(rb)
            ilay.addWidget(pr)

        # Engine + breaker buttons row
        btn_row = QtWidgets.QWidget()
        btn_row.setStyleSheet("background:#ffffff;")
        br = QtWidgets.QHBoxLayout(btn_row)
        br.setContentsMargins(0, 0, 0, 0)
        br.setSpacing(4)

        eng_btn = None
        if show_engine:
            eng_btn = self._make_btn("起机", "#16a34a")
            eng_btn.clicked.connect(lambda _, gid=gen_id: self.ctrl.toggle_engine(gid))
            br.addWidget(eng_btn)

        brk_btn = self._make_btn("合闸", "#1d4ed8")
        brk_btn.clicked.connect(lambda _, gid=gen_id: self.ctrl.toggle_breaker(gid))
        br.addWidget(brk_btn)

        ilay.addWidget(btn_row)
        parent_lay.addWidget(inner)
        self._tp_gen_refs[(step_key, gen_id)] = (brk_lbl, eng_btn, brk_btn, mode_rbs)

    # ════════════════════════════════════════════════════════════════════
    # Step section builders
    # ════════════════════════════════════════════════════════════════════

    # ── Step 1 ────────────────────────────────────────────────────────
    def _build_step1(self, cl):
        grp = self._make_grp("第一步：回路连通性测试")
        lay = QtWidgets.QVBoxLayout(grp)
        lay.setSpacing(4)

        self.tp_s1_step_lbls = self._make_step_list(lay, 7)

        gnd_lbl = QtWidgets.QLabel("中性点接地:")
        gnd_lbl.setStyleSheet("color:#64748b; font-size:11px;")
        lay.addWidget(gnd_lbl)
        gnd_row = QtWidgets.QWidget()
        gnd_row.setStyleSheet(f"background:{_SECTION_BG};")
        gnd_h = QtWidgets.QHBoxLayout(gnd_row)
        gnd_h.setContentsMargins(0, 0, 0, 0)
        self._tp_gnd_bg = QtWidgets.QButtonGroup(self)
        self._tp_gnd_rbs = {}
        for label, val in [("断开", "断开"), ("小电阻", "小电阻接地"), ("直接", "直接接地")]:
            rb = QtWidgets.QRadioButton(label)
            rb.setStyleSheet(f"color:#334155; background:{_SECTION_BG};")
            rb.setChecked(self.ctrl.sim_state.grounding_mode == val)
            rb.toggled.connect(
                lambda chk, v=val: (
                    setattr(self.ctrl.sim_state, 'grounding_mode', v) if chk else None))
            self._tp_gnd_bg.addButton(rb)
            gnd_h.addWidget(rb)
            self._tp_gnd_rbs[val] = rb
        lay.addWidget(gnd_row)

        no_engine_note = QtWidgets.QLabel("⚠ 回路检查期间勿起机，仅合闸即可")
        no_engine_note.setStyleSheet(
            "color:#d97706; font-size:11px; font-style:italic;")
        lay.addWidget(no_engine_note)

        self._make_gen_block(
            lay, 's1', 1,
            mode_options=[("停机", "stop"), ("手动", "manual")],
            show_pos=True,
            show_engine=False,
        )
        self._make_gen_block(
            lay, 's1', 2,
            mode_options=[("停机", "stop"), ("手动", "manual")],
            show_pos=True,
            show_engine=False,
        )

        rlbl = QtWidgets.QLabel("回路测试快速记录（需先开启万用表）:")
        rlbl.setStyleSheet("color:#64748b; font-size:11px;")
        lay.addWidget(rlbl)
        rrow = QtWidgets.QWidget()
        rrow.setStyleSheet(f"background:{_SECTION_BG};")
        rh = QtWidgets.QHBoxLayout(rrow)
        rh.setContentsMargins(0, 0, 0, 0)
        rh.setSpacing(4)
        self.tp_s1_rec_btns = {}
        for ph in ('A', 'B', 'C'):
            btn = self._make_btn(f"{ph} 相", "#1d4ed8")
            btn.clicked.connect(
                lambda _, p=ph: self.ctrl.record_loop_measurement(p))
            rh.addWidget(btn)
            self.tp_s1_rec_btns[ph] = btn
        lay.addWidget(rrow)

        self.tp_s1_fb_lbl = QtWidgets.QLabel("请按步骤列表操作")
        self.tp_s1_fb_lbl.setWordWrap(True)
        self.tp_s1_fb_lbl.setStyleSheet("color:#15803d; font-size:12px;")
        lay.addWidget(self.tp_s1_fb_lbl)

        cl.addWidget(grp)
        return grp

    # ── Step 2 ────────────────────────────────────────────────────────
    def _build_step2(self, cl):
        grp = self._make_grp("第二步：PT 单体线电压检查")
        lay = QtWidgets.QVBoxLayout(grp)
        lay.setSpacing(4)

        self.tp_s2_step_lbls = self._make_step_list(lay, 9)

        # ── PT 变比设置（停机状态下确认，运行中不可修改）──────────────
        pt_ratio_grp = self._make_grp("PT 变比参数（停机状态下确认）")
        pt_ratio_lay = QtWidgets.QVBoxLayout(pt_ratio_grp)
        pt_ratio_lay.setSpacing(4)
        pt_ratio_lay.setContentsMargins(4, 6, 4, 4)

        # _tp_s2_ratio_rows: { ratio_attr: (pri_spin, sec_spin, ratio_lbl) }
        self._tp_s2_ratio_rows: dict = {}

        for row_label, ratio_attr, pri_default, sec_default in [
            ("PT1/PT3 (机组侧)", "pt_gen_ratio", 11000, 193),
            ("PT2 (母排侧)",     "pt_bus_ratio",  10000, 100),
        ]:
            # 行标题
            hdr = QtWidgets.QLabel(row_label)
            hdr.setStyleSheet("font-size:11px; color:#1d4ed8; font-weight:bold;")
            pt_ratio_lay.addWidget(hdr)

            # 三值行：一次侧 V  :  二次侧 V  =  变比
            rw = QtWidgets.QWidget()
            rw.setStyleSheet("background:#ffffff;")
            rh = QtWidgets.QHBoxLayout(rw)
            rh.setContentsMargins(0, 0, 0, 0)
            rh.setSpacing(4)

            pri_spin = QtWidgets.QSpinBox()
            pri_spin.setRange(100, 100000)
            pri_spin.setValue(pri_default)
            pri_spin.setSuffix(" V")
            pri_spin.setFixedWidth(90)
            pri_spin.setStyleSheet("font-size:11px;")

            colon_lbl = QtWidgets.QLabel(":")
            colon_lbl.setStyleSheet("font-size:12px; color:#64748b; background:#ffffff;")

            sec_spin = QtWidgets.QSpinBox()
            sec_spin.setRange(1, 10000)
            sec_spin.setValue(sec_default)
            sec_spin.setSuffix(" V")
            sec_spin.setFixedWidth(78)
            sec_spin.setStyleSheet("font-size:11px;")

            eq_lbl = QtWidgets.QLabel("=")
            eq_lbl.setStyleSheet("font-size:12px; color:#64748b; background:#ffffff;")

            ratio_lbl = QtWidgets.QLabel(f"{pri_default / sec_default:.2f}")
            ratio_lbl.setFixedWidth(52)
            ratio_lbl.setStyleSheet(
                "font-size:11px; color:#0f172a; font-weight:bold; background:#f1f5f9;"
                " border:1px solid #e2e8f0; border-radius:3px; padding:1px 4px;")
            ratio_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

            def _update_ratio(_val=None, _p=pri_spin, _s=sec_spin, _l=ratio_lbl, _a=ratio_attr):
                pri = _p.value()
                sec = max(1, _s.value())
                ratio = pri / sec
                _l.setText(f"{ratio:.2f}")
                setattr(self.ctrl.sim_state, _a, ratio)

            pri_spin.valueChanged.connect(_update_ratio)
            sec_spin.valueChanged.connect(_update_ratio)

            rh.addWidget(pri_spin)
            rh.addWidget(colon_lbl)
            rh.addWidget(sec_spin)
            rh.addWidget(eq_lbl)
            rh.addWidget(ratio_lbl)
            pt_ratio_lay.addWidget(rw)
            self._tp_s2_ratio_rows[ratio_attr] = (pri_spin, sec_spin, ratio_lbl)

        lay.addWidget(pt_ratio_grp)

        # 中性点接地（第二步需恢复小电阻接地）
        gnd2_lbl = QtWidgets.QLabel("中性点接地（应恢复为小电阻接地）:")
        gnd2_lbl.setStyleSheet("color:#64748b; font-size:11px;")
        lay.addWidget(gnd2_lbl)
        gnd2_row = QtWidgets.QWidget()
        gnd2_row.setStyleSheet(f"background:{_SECTION_BG};")
        gnd2_h = QtWidgets.QHBoxLayout(gnd2_row)
        gnd2_h.setContentsMargins(0, 0, 0, 0)
        self._tp_s2_gnd_bg = QtWidgets.QButtonGroup(self)
        self._tp_s2_gnd_rbs = {}
        for label, val in [("断开", "断开"), ("小电阻", "小电阻接地"), ("直接", "直接接地")]:
            rb = QtWidgets.QRadioButton(label)
            rb.setStyleSheet(f"color:#334155; background:{_SECTION_BG};")
            rb.setChecked(self.ctrl.sim_state.grounding_mode == val)
            rb.toggled.connect(
                lambda chk, v=val: (
                    setattr(self.ctrl.sim_state, 'grounding_mode', v) if chk else None))
            self._tp_s2_gnd_bg.addButton(rb)
            gnd2_h.addWidget(rb)
            self._tp_s2_gnd_rbs[val] = rb
        lay.addWidget(gnd2_row)

        self._make_gen_block(lay, 's2', 1, show_engine=True)

        gen2_note = QtWidgets.QLabel("Gen2 起机后保持断路器断开（提供PT3参考）")
        gen2_note.setStyleSheet("color:#d97706; font-size:11px; font-style:italic;")
        lay.addWidget(gen2_note)
        self._make_gen_block(lay, 's2', 2, show_engine=True)

        self.tp_s2_probe_lbl = QtWidgets.QLabel("当前表笔: 未放置")
        self.tp_s2_probe_lbl.setStyleSheet("color:#854d0e; font-size:12px;")
        lay.addWidget(self.tp_s2_probe_lbl)

        rlbl = QtWidgets.QLabel("按相位快速记录（A→AB，B→BC，C→CA）:")
        rlbl.setStyleSheet("color:#64748b; font-size:11px;")
        lay.addWidget(rlbl)
        rrow = QtWidgets.QWidget()
        rrow.setStyleSheet(f"background:{_SECTION_BG};")
        rh = QtWidgets.QHBoxLayout(rrow)
        rh.setContentsMargins(0, 0, 0, 0)
        rh.setSpacing(4)
        self.tp_s2_rec_btns = {}
        _PHASE_TO_PAIR = {'A': 'AB', 'B': 'BC', 'C': 'CA'}
        for ph in ('A', 'B', 'C'):
            pair = _PHASE_TO_PAIR[ph]
            btn = self._make_btn(f"记录 {pair}", "#1d4ed8")
            btn.clicked.connect(lambda _, p=ph, pa=pair: self._tp_s2_record(p, pa))
            rh.addWidget(btn)
            self.tp_s2_rec_btns[ph] = btn
        lay.addWidget(rrow)

        # ── Gen 频率/幅值/相位调节（让两台发电机电压调到同一水平）──────
        adj_note = QtWidgets.QLabel("调节发电机使各 PT 一次侧线电压均达到 10.5 kV:")
        adj_note.setStyleSheet("color:#1d4ed8; font-size:11px; font-weight:bold;")
        lay.addWidget(adj_note)
        self._tp_s2_fap = {}
        self._make_gen_fap_block(lay, '_tp_s2_fap', 1)
        self._make_gen_fap_block(lay, '_tp_s2_fap', 2)

        self.tp_s2_fb_lbl = QtWidgets.QLabel("请按步骤列表操作")
        self.tp_s2_fb_lbl.setWordWrap(True)
        self.tp_s2_fb_lbl.setStyleSheet("color:#15803d; font-size:12px;")
        lay.addWidget(self.tp_s2_fb_lbl)

        cl.addWidget(grp)
        return grp

    # ── Step 3 ────────────────────────────────────────────────────────
    def _build_step3(self, cl):
        grp = self._make_grp("第三步：PT 相序检查")
        lay = QtWidgets.QVBoxLayout(grp)
        lay.setSpacing(4)

        self.tp_s3_step_lbls = self._make_step_list(lay, 7)

        gen2_note = QtWidgets.QLabel("Gen2 需起机，断路器保持断开")
        gen2_note.setStyleSheet("color:#d97706; font-size:11px; font-style:italic;")
        lay.addWidget(gen2_note)
        self._make_gen_block(lay, 's3', 2, show_engine=True)

        # ── 相序仪接入按钮 ────────────────────────────────────────────
        psm_lbl = QtWidgets.QLabel("相序仪（在母排图右侧查看转盘与指示灯）:")
        psm_lbl.setStyleSheet("color:#64748b; font-size:11px;")
        lay.addWidget(psm_lbl)
        psm_row = QtWidgets.QWidget()
        psm_row.setStyleSheet(f"background:{_SECTION_BG};")
        psm_h = QtWidgets.QHBoxLayout(psm_row)
        psm_h.setContentsMargins(0, 0, 0, 0)
        psm_h.setSpacing(6)
        for pt_name, bg in [("PT1", "#1d4ed8"), ("PT3", "#7c3aed")]:
            btn = self._make_btn(f"📡 接入 {pt_name}", bg)
            btn.clicked.connect(
                lambda _, pt=pt_name: self._on_connect_psm(pt))
            psm_h.addWidget(btn)
        # 断开按钮
        btn_disc = self._make_btn("断开", "#64748b")
        btn_disc.clicked.connect(self._on_disconnect_psm)
        psm_h.addWidget(btn_disc)
        lay.addWidget(psm_row)

        # 相序仪结果记录按钮（接入后方可点击）
        rec_lbl = QtWidgets.QLabel("记录相序结果:")
        rec_lbl.setStyleSheet("color:#64748b; font-size:11px;")
        lay.addWidget(rec_lbl)
        rec_row = QtWidgets.QWidget()
        rec_row.setStyleSheet(f"background:{_SECTION_BG};")
        rec_h = QtWidgets.QHBoxLayout(rec_row)
        rec_h.setContentsMargins(0, 0, 0, 0)
        rec_h.setSpacing(6)
        self._tp_s3_rec_btns: dict = {}
        for pt_name, bg in [("PT1", "#1d4ed8"), ("PT3", "#7c3aed")]:
            btn = self._make_btn(f"记录 {pt_name}", bg)
            btn.setEnabled(False)
            btn.clicked.connect(
                lambda _, pt=pt_name: self._on_record_psm(pt))
            rec_h.addWidget(btn)
            self._tp_s3_rec_btns[pt_name] = btn
        lay.addWidget(rec_row)

        self.tp_s3_fb_lbl = QtWidgets.QLabel("请先接入相序仪查看结果，再点击记录")
        self.tp_s3_fb_lbl.setWordWrap(True)
        self.tp_s3_fb_lbl.setStyleSheet("color:#64748b; font-size:12px;")
        lay.addWidget(self.tp_s3_fb_lbl)

        cl.addWidget(grp)
        return grp

    # ── Step 4 ────────────────────────────────────────────────────────
    def _build_step4(self, cl):
        grp = self._make_grp("第四步：PT 二次端子压差测试")
        lay = QtWidgets.QVBoxLayout(grp)
        lay.setSpacing(4)

        self.tp_s4_step_lbls = self._make_step_list(lay, 7)

        self._make_gen_block(lay, 's4', 1, show_engine=True)
        self._make_gen_block(lay, 's4', 2, show_engine=True)

        adj_note = QtWidgets.QLabel("调节 Gen 2 频率/幅值使 PT 二次压差趋近于零:")
        adj_note.setStyleSheet("color:#1d4ed8; font-size:11px; font-weight:bold;")
        lay.addWidget(adj_note)
        self._tp_s4_fap = {}
        self._make_gen_fap_block(lay, '_tp_s4_fap', 2)

        sel_lbl = QtWidgets.QLabel("测试对象:")
        sel_lbl.setStyleSheet("color:#64748b; font-size:11px;")
        lay.addWidget(sel_lbl)
        sel_row = QtWidgets.QWidget()
        sel_row.setStyleSheet(f"background:{_SECTION_BG};")
        sh = QtWidgets.QHBoxLayout(sel_row)
        sh.setContentsMargins(0, 0, 0, 0)
        self._tp_s4_bg = QtWidgets.QButtonGroup(self)
        for txt, val in [("Gen 1", 1), ("Gen 2", 2)]:
            rb = QtWidgets.QRadioButton(txt)
            rb.setChecked(val == 1)
            rb.setStyleSheet(f"color:#334155; background:{_SECTION_BG};")
            self._tp_s4_bg.addButton(rb, val)
            sh.addWidget(rb)
        lay.addWidget(sel_row)

        rrow = QtWidgets.QWidget()
        rrow.setStyleSheet(f"background:{_SECTION_BG};")
        rh = QtWidgets.QHBoxLayout(rrow)
        rh.setContentsMargins(0, 0, 0, 0)
        rh.setSpacing(4)
        for ph in ('A', 'B', 'C'):
            btn = self._make_btn(f"记录 {ph} 相", "#16a34a")
            btn.clicked.connect(
                lambda _, p=ph: self.ctrl.record_pt_measurement(
                    p, max(1, self._tp_s4_bg.checkedId())))
            rh.addWidget(btn)
        lay.addWidget(rrow)

        self.tp_s4_fb_lbl = QtWidgets.QLabel("请按步骤列表操作")
        self.tp_s4_fb_lbl.setWordWrap(True)
        self.tp_s4_fb_lbl.setStyleSheet("color:#15803d; font-size:12px;")
        lay.addWidget(self.tp_s4_fb_lbl)

        cl.addWidget(grp)
        return grp

    # ── Step 5 ────────────────────────────────────────────────────────
    def _build_step5(self, cl):
        grp = self._make_grp("第五步：同步功能测试")
        lay = QtWidgets.QVBoxLayout(grp)
        lay.setSpacing(4)

        self.tp_s5_step_lbls = self._make_step_list(lay, 12)

        # ── 远程启动信号（自动模式必须打开才能让仲裁器控制发电机）──────
        rs_row = QtWidgets.QWidget()
        rs_row.setStyleSheet(f"background:{_SECTION_BG};")
        rs_h = QtWidgets.QHBoxLayout(rs_row)
        rs_h.setContentsMargins(4, 2, 4, 2)
        rs_lbl = QtWidgets.QLabel("远程启动信号:")
        rs_lbl.setStyleSheet("color:#64748b; font-size:11px;")
        self.tp_s5_remote_btn = QtWidgets.QPushButton("⚡ 开启自动")
        self.tp_s5_remote_btn.setCheckable(True)
        self.tp_s5_remote_btn.setStyleSheet(
            "background:#e2e8f0; color:#475569; font-size:12px;"
            " font-weight:bold; padding:3px 10px; border-radius:3px;")
        self.tp_s5_remote_btn.clicked.connect(self._on_tp_s5_remote_toggle)
        rs_h.addWidget(rs_lbl)
        rs_h.addStretch()
        rs_h.addWidget(self.tp_s5_remote_btn)
        lay.addWidget(rs_row)

        self._make_gen_block(
            lay, 's5', 1,
            mode_options=[("手动", "manual"), ("自动", "auto")],
            show_engine=True,
        )
        self._tp_s5_fap = {}
        self._make_gen_fap_block(lay, '_tp_s5_fap', 1)

        self._make_gen_block(
            lay, 's5', 2,
            mode_options=[("手动", "manual"), ("自动", "auto")],
            show_engine=True,
        )
        self._make_gen_fap_block(lay, '_tp_s5_fap', 2)

        bar_hdr = QtWidgets.QLabel("同步误差监测（越低越好，趋近零可合闸）:")
        bar_hdr.setStyleSheet("color:#475569; font-size:11px; font-weight:bold;")
        lay.addWidget(bar_hdr)

        self.tp_s5_bars: dict = {}
        for key, label, unit, max_val in [
            ('freq',  '频率差', 'Hz',  5.0),
            ('amp',   '幅值差', 'V',   5000.0),
            ('phase', '相位差', '°',   180.0),
        ]:
            rw = QtWidgets.QWidget()
            rw.setStyleSheet(f"background:{_SECTION_BG};")
            rh = QtWidgets.QHBoxLayout(rw)
            rh.setContentsMargins(4, 2, 4, 2)
            rh.setSpacing(4)

            lbl = QtWidgets.QLabel(f"{label}({unit})")
            lbl.setFixedWidth(72)
            lbl.setStyleSheet("color:#64748b; font-size:11px;")

            bar = QtWidgets.QProgressBar()
            bar.setRange(0, 1000)
            bar.setValue(0)
            bar.setTextVisible(False)
            bar.setFixedHeight(14)
            bar.setStyleSheet(
                "QProgressBar{background:#e2e8f0; border-radius:3px;}"
                "QProgressBar::chunk{background:qlineargradient("
                "x1:0,y1:0,x2:1,y2:0,"
                "stop:0 #16a34a,stop:0.5 #d97706,stop:1 #dc2626);"
                "border-radius:3px;}")

            val_lbl = QtWidgets.QLabel("0.0")
            val_lbl.setFixedWidth(46)
            val_lbl.setStyleSheet("color:#1e293b; font-size:11px;")
            val_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

            rh.addWidget(lbl)
            rh.addWidget(bar, 1)
            rh.addWidget(val_lbl)
            lay.addWidget(rw)
            self.tp_s5_bars[key] = (bar, val_lbl, max_val)

        btn_r1 = self._make_btn("记录第一轮（Gen1 基准 → Gen2 同步）", "#16a34a")
        btn_r1.clicked.connect(lambda: self.ctrl.record_sync_round(1))
        lay.addWidget(btn_r1)

        btn_r2 = self._make_btn("记录第二轮（Gen2 基准 → Gen1 同步）", "#16a34a")
        btn_r2.clicked.connect(lambda: self.ctrl.record_sync_round(2))
        lay.addWidget(btn_r2)

        self.tp_s5_fb_lbl = QtWidgets.QLabel("请按步骤列表操作")
        self.tp_s5_fb_lbl.setWordWrap(True)
        self.tp_s5_fb_lbl.setStyleSheet("color:#15803d; font-size:12px;")
        lay.addWidget(self.tp_s5_fb_lbl)

        cl.addWidget(grp)
        return grp

    # ════════════════════════════════════════════════════════════════════
    # Test mode enter / exit
    # ════════════════════════════════════════════════════════════════════
    def enter_test_mode(self):
        self._test_mode_active = True
        self.ctrl_container.setVisible(False)
        self.test_panel.setVisible(True)
        self.tab_widget.setCurrentIndex(1)
        # 进入测试模式即自动开启回路检查，省去用户二次点击
        if not self.ctrl.sim_state.loop_test_mode:
            self.ctrl.enter_loop_test_mode()

    def exit_test_mode(self):
        self._test_mode_active = False
        self.test_panel.setVisible(False)
        self.ctrl_container.setVisible(True)

    # ════════════════════════════════════════════════════════════════════
    # Bottom bar slot functions
    # ════════════════════════════════════════════════════════════════════
    def _on_tp_reset_step(self):
        step = self._current_test_step()
        if step == 1:
            self.ctrl.reset_loop_test()
        elif step == 2:
            self.ctrl.reset_pt_voltage_check()
        elif step == 3:
            self.ctrl.reset_pt_phase_check()
        elif step == 4:
            gen_id = max(1, self._tp_s4_bg.checkedId())
            self.ctrl.reset_pt_exam(gen_id)
        elif step == 5:
            self.ctrl.reset_sync_test()

    def _on_tp_start_step(self):
        step = self._current_test_step()
        if step == 1:
            self._on_toggle_loop_test_mode()
        elif step == 2:
            if self.ctrl.pt_voltage_check_state.started:
                self.ctrl.stop_pt_voltage_check()
            else:
                self.ctrl.start_pt_voltage_check()
        elif step == 3:
            if self.ctrl.pt_phase_check_state.started:
                self.ctrl.stop_pt_phase_check()
            else:
                self.ctrl.start_pt_phase_check()
        elif step == 4:
            both = (self.ctrl.pt_exam_states[1].started and
                    self.ctrl.pt_exam_states[2].started)
            if both:
                self.ctrl.stop_pt_exam(1)
                self.ctrl.stop_pt_exam(2)
            else:
                self.ctrl.start_pt_exam(1)
                self.ctrl.start_pt_exam(2)
        elif step == 5:
            if self.ctrl.sync_test_state.started:
                self.ctrl.stop_sync_test()
            else:
                self.ctrl.start_sync_test()

    def _on_tp_complete_step(self):
        step = self._current_test_step()
        if step == 1:
            self.ctrl.finalize_loop_test()
        elif step == 2:
            self.ctrl.finalize_pt_voltage_check()
            self.multimeter_cb.setChecked(False)  # 步骤二结束后自动关闭万用表
        elif step == 3:
            self.ctrl.finalize_pt_phase_check()
            # 完成后自动关闭相序仪浮层，无需手动断开
            if self.ctrl.pt_phase_check_state.completed:
                try:
                    self.disconnect_phase_seq_meter()
                except Exception:
                    pass
        elif step == 4:
            self.ctrl.finalize_all_pt_exams()
        elif step == 5:
            self.ctrl.finalize_sync_test()

    def _on_tp_s5_remote_toggle(self, checked):
        self.ctrl.sim_state.remote_start_signal = checked
        if checked:
            self.tp_s5_remote_btn.setText("⚡ 关闭自动")
            self.tp_s5_remote_btn.setStyleSheet(
                "background:#16a34a; color:white; font-size:12px;"
                " font-weight:bold; padding:3px 10px; border-radius:3px;")
        else:
            self.tp_s5_remote_btn.setText("⚡ 开启自动")
            self.tp_s5_remote_btn.setStyleSheet(
                "background:#e2e8f0; color:#475569; font-size:12px;"
                " font-weight:bold; padding:3px 10px; border-radius:3px;")

    def _tp_s2_record(self, phase, pair):
        sim = self.ctrl.sim_state
        n1 = sim.probe1_node or ""
        pt_name = n1.split('_')[0] if n1.startswith('PT') else None
        if pt_name:
            self.ctrl.record_pt_voltage_measurement(pt_name, pair)
        else:
            self.ctrl.pt_voltage_check_state.feedback = \
                "请先将表笔放在某一 PT 的两相端子上，再点击记录。"
            self.ctrl.pt_voltage_check_state.feedback_color = "red"

    # ════════════════════════════════════════════════════════════════════
    # Helpers
    # ════════════════════════════════════════════════════════════════════

    @staticmethod
    def _tp_dot_style(state: str) -> str:
        """
        state: 'idle' | 'done' | 'active' | 'admin_idle' | 'admin_active'
        """
        base = "border:none; border-radius:4px; font-size:11px; padding:2px;"
        if state == "done":
            return (f"QPushButton{{{base} color:#16a34a; background:#dcfce7;}}")
        if state == "active":
            return (f"QPushButton{{{base} color:#1d4ed8; background:#dbeafe;"
                    " font-weight:bold; font-size:12px;}")
        if state == "admin_idle":
            return (f"QPushButton{{{base} color:#7c3aed; background:#ede9fe;}}"
                    "QPushButton:hover{background:#c4b5fd;}"
                    "QPushButton:checked{background:#7c3aed; color:white;}")
        if state == "admin_active":
            return (f"QPushButton{{{base} color:white; background:#7c3aed;"
                    " font-weight:bold;}}"
                    "QPushButton:hover{background:#6d28d9;}")
        # idle
        return f"QPushButton{{{base} color:#94a3b8; background:transparent;}}"

    # ── 相序仪回调 ────────────────────────────────────────────────────────
    def _on_connect_psm(self, pt_name: str):
        """接入相序仪到指定 PT，驱动母排图侧栏显示。"""
        try:
            self.connect_phase_seq_meter(pt_name)   # 方法定义在主窗口 mixin 上
        except Exception:
            pass
        # 接入后才允许记录
        if pt_name in self._tp_s3_rec_btns:
            self._tp_s3_rec_btns[pt_name].setEnabled(True)
        self.tp_s3_fb_lbl.setText(
            f"相序仪已接入 {pt_name}，请在母排图右侧查看转盘和指示灯，确认结果后点击「记录 {pt_name}」")

    def _on_disconnect_psm(self):
        """断开相序仪，隐藏侧栏。"""
        try:
            self.disconnect_phase_seq_meter()
        except Exception:
            pass
        for btn in self._tp_s3_rec_btns.values():
            btn.setEnabled(False)
        self.tp_s3_fb_lbl.setText("相序仪已断开，可重新接入")

    def _on_record_psm(self, pt_name: str):
        """根据当前相序仪示数记录相序结果到服务层。"""
        try:
            seq = self.phase_seq_meter._sequence   # phase_seq_meter 在主窗口 mixin 上
        except Exception:
            seq = 'unknown'
        if seq == 'unknown':
            self.tp_s3_fb_lbl.setText("请先接入相序仪，再记录结果。")
            return
        # 把相序仪结果写入 pt_phase_check_state（逐相批量写入）
        state = self.ctrl.pt_phase_check_state
        if not state.started:
            self.tp_s3_fb_lbl.setText("请先点击「开始第三步测试」再记录。")
            return
        # ── 前置条件门禁 ───────────────────────────────────────────────────
        if not self.ctrl.is_loop_test_complete():
            state.feedback = "请先完成第一步【回路连通性测试】，再进行相序检查。"
            state.feedback_color = "red"
            return
        if not self.ctrl.is_pt_voltage_check_complete():
            state.feedback = "请先完成第二步【PT 单体线电压检查】，再进行相序检查。"
            state.feedback_color = "red"
            return
        sim = self.ctrl.sim_state
        from domain.enums import BreakerPosition
        if sim.grounding_mode != "小电阻接地":
            state.feedback = "请先恢复中性点小电阻接地，再进行相序检查。"
            state.feedback_color = "red"
            return
        gen1 = sim.gen1
        if gen1.breaker_position != BreakerPosition.WORKING or not gen1.breaker_closed:
            state.feedback = "请先确认 Gen1 已并入母排，建立 PT1/PT2 参考电压。"
            state.feedback_color = "red"
            return
        if pt_name == 'PT3':
            gen2 = sim.gen2
            if not gen2.running:
                state.feedback = "测量 PT3 相序时，请先启动 Gen2（保持断路器断开）。"
                state.feedback_color = "red"
                return
            if gen2.breaker_closed:
                state.feedback = "测量 PT3 相序时，Gen2 断路器应保持断开状态。"
                state.feedback_color = "red"
                return
        phase_match = (seq == 'ABC')
        for ph in ('A', 'B', 'C'):
            key = f"{pt_name}_{ph}"
            state.records[key] = {
                'phase_match': phase_match,
                'reading': f"相序仪检测: {pt_name} → {seq}",
            }
        result_txt = "正序（ABC）✓" if phase_match else "逆序（ACB）✗"
        color = "#15803d" if phase_match else "#dc2626"
        # 写入 state.feedback，避免下次 refresh 刷新回旧文字
        state.feedback = f"{pt_name} 相序已记录：{result_txt}"
        state.feedback_color = color
        if pt_name in self._tp_s3_rec_btns:
            self._tp_s3_rec_btns[pt_name].setEnabled(False)

    def _on_tp_toggle_admin(self, checked):
        """管理员模式：显示/隐藏步骤详情 Tab 2-6，步骤按钮变为可点击。"""
        self._tp_admin_mode = checked
        self.tp_btn_admin.setText("🔧 管理员 ✓" if checked else "🔧 管理员")
        if not checked:
            # 退出管理员模式：清除强制步骤，恢复正常推算
            self._tp_forced_step = None
            for btn in self.tp_step_btns:
                btn.setChecked(False)
                btn.setCursor(QtCore.Qt.ArrowCursor)
        else:
            for btn in self.tp_step_btns:
                btn.setCursor(QtCore.Qt.PointingHandCursor)
        for i in range(2, 7):
            try:
                self.tab_widget.setTabVisible(i, checked)
            except AttributeError:
                pass

    def _on_tp_step_btn_clicked(self, step_num: int):
        """管理员点击步骤按钮 → 强制跳转到该步骤面板。"""
        if not self._tp_admin_mode:
            return
        if self._tp_forced_step == step_num:
            # 再次点击同一步骤：取消强制，恢复自动
            self._tp_forced_step = None
            for btn in self.tp_step_btns:
                btn.setChecked(False)
        else:
            self._tp_forced_step = step_num
            for i, btn in enumerate(self.tp_step_btns):
                btn.setChecked(i + 1 == step_num)

    def _make_gen_fap_block(self, parent_lay, store_key, gen_id, read_only=False):
        """
        在 parent_lay 中插入 Gen-N 的 频率/幅值/相位 可调控件。
        store_key : 'tp_s2_fap' | 'tp_s5_fap'  — 存到 self.<store_key>[gen_id]
        read_only : True = 只显示，不可调（自动模式下设置）
        返回 entry_map {attr: (slider, entry, read_only_lbl)}
        """
        c = self.ctrl
        gen = c.sim_state.gen1 if gen_id == 1 else c.sim_state.gen2

        grp = QtWidgets.QGroupBox(f"Gen {gen_id} 频率/幅值/相位")
        grp.setStyleSheet(_GRP_STYLE.format(bg="#ffffff"))
        glay = QtWidgets.QVBoxLayout(grp)
        glay.setSpacing(2)
        glay.setContentsMargins(4, 4, 4, 4)

        specs = [
            ("频率(Hz)", 450, 550, int(gen.freq * 10),       10, 'freq',      48.0, 52.0),
            ("幅值(V)",  0, 15000, int(gen.amp),               1, 'amp',       0.0, 15000.0),
            ("相位(°)", -1800, 1800, int(gen.phase_deg * 10), 10, 'phase_deg', -180.0, 180.0),
        ]
        entry_map = {}
        for label, vmin, vmax, init, scale, attr, clo, chi in specs:
            row_w = QtWidgets.QWidget()
            row_w.setStyleSheet("background:#ffffff;")
            rh = QtWidgets.QHBoxLayout(row_w)
            rh.setContentsMargins(0, 0, 0, 0)
            rh.setSpacing(3)

            lbl = QtWidgets.QLabel(label)
            lbl.setFixedWidth(66)
            lbl.setStyleSheet("font-size:11px; color:#64748b; background:#ffffff;")

            sl = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            sl.setRange(vmin, vmax)
            sl.setValue(init)
            sl.setFixedHeight(16)
            sl.setEnabled(not read_only)

            entry = QtWidgets.QLineEdit(f"{getattr(gen, attr):.1f}")
            entry.setFixedWidth(56)
            entry.setStyleSheet("font-size:11px;")
            entry.setEnabled(not read_only)
            entry.setReadOnly(read_only)

            def _sl_ch(val, _a=attr, _sc=scale, _e=entry, _gid=gen_id):
                v = round(val / _sc, 3)
                setattr(c.sim_state.gen1 if _gid == 1 else c.sim_state.gen2, _a, v)
                _e.setText(f"{v:.1f}")

            def _en_ch(_a=attr, _sc=scale, _sl=sl, _gid=gen_id,
                        _clo=clo, _chi=chi, _e=entry):
                try:
                    v = max(_clo, min(_chi, float(_e.text())))
                    setattr(c.sim_state.gen1 if _gid == 1 else c.sim_state.gen2, _a, v)
                    _sl.blockSignals(True)
                    _sl.setValue(int(v * _sc))
                    _sl.blockSignals(False)
                    _e.setText(f"{v:.1f}")
                except ValueError:
                    pass

            if not read_only:
                sl.valueChanged.connect(_sl_ch)
                entry.returnPressed.connect(_en_ch)
                entry.editingFinished.connect(_en_ch)

            rh.addWidget(lbl)
            rh.addWidget(sl, 1)
            rh.addWidget(entry)
            glay.addWidget(row_w)
            entry_map[attr] = (sl, entry)

        parent_lay.addWidget(grp)
        store = getattr(self, store_key, {})
        store[gen_id] = entry_map
        setattr(self, store_key, store)
        return entry_map

    def _current_test_step(self) -> int:
        # 管理员模式强制指定步骤时直接返回
        if self._tp_admin_mode and self._tp_forced_step is not None:
            return self._tp_forced_step
        c = self.ctrl
        if not c.is_loop_test_complete():
            return 1
        if not c.is_pt_voltage_check_complete():
            return 2
        if not c.is_pt_phase_check_complete():
            return 3
        if not (c.pt_exam_states[1].completed and c.pt_exam_states[2].completed):
            return 4
        return 5

    # ════════════════════════════════════════════════════════════════════
    # Render (called every frame from render_visuals)
    # ════════════════════════════════════════════════════════════════════
    def _render_test_panel(self, rs):
        if not self._test_mode_active:
            return

        sim  = self.ctrl.sim_state
        step = self._current_test_step()

        # ── Step dots / admin buttons ──────────────────────────────────
        # 计算自然完成步骤（不受 forced 影响）
        c = self.ctrl
        _auto = (1 if not c.is_loop_test_complete() else
                 2 if not c.is_pt_voltage_check_complete() else
                 3 if not c.is_pt_phase_check_complete() else
                 4 if not (c.pt_exam_states[1].completed and
                           c.pt_exam_states[2].completed) else 5)
        for i, btn in enumerate(self.tp_step_btns):
            s = i + 1
            is_active = (s == step)
            if self._tp_admin_mode:
                style = "admin_active" if is_active else "admin_idle"
            else:
                if s < _auto:
                    style = "done"
                elif s == _auto:
                    style = "active"
                else:
                    style = "idle"
            btn.setStyleSheet(self._tp_dot_style(style))

        # ── Show only current step section ────────────────────────────
        for s, grp in self._tp_step_grps.items():
            grp.setVisible(s == step)

        # ── Bus status ────────────────────────────────────────────────
        msg = getattr(self.ctrl.physics, 'bus_status_msg', '母排: --')
        self.tp_bus_lbl.setText(msg)
        bus_live = getattr(self.ctrl.physics, 'bus_live', False)
        if bus_live:
            self.tp_bus_lbl.setStyleSheet(
                "background:#dcfce7; color:#15803d; font-weight:bold;"
                " font-size:12px; padding:4px; border-radius:4px;"
                " border:1px solid #86efac;")
        else:
            self.tp_bus_lbl.setStyleSheet(
                "background:#fef3c7; color:#92400e; font-weight:bold;"
                " font-size:12px; padding:4px; border-radius:4px;"
                " border:1px solid #fcd34d;")

        # ── Multimeter (hidden on step 3 which uses phase seq meter) ──
        mm_visible = (step != 3)
        self._tp_mm_btn.setVisible(mm_visible)
        self.tp_meter_lbl.setVisible(mm_visible)
        if sim.multimeter_mode:
            reading = getattr(self.ctrl.physics, 'meter_reading', '--')
            self.tp_meter_lbl.setText(f"万用表: {reading}")
            self.tp_meter_lbl.setStyleSheet("color:#854d0e; font-size:12px;")
        else:
            self.tp_meter_lbl.setText("万用表: 关闭")
            self.tp_meter_lbl.setStyleSheet("color:#94a3b8; font-size:12px;")

        # ── Gen control buttons ───────────────────────────────────────
        self._refresh_tp_gen_refs(sim, step)

        # ── Start / Complete button labels ────────────────────────────
        self._refresh_tp_bottom(step, sim)

        # ── Per-step content ──────────────────────────────────────────
        if step == 1:
            self._refresh_tp_step1(sim)
        elif step == 2:
            self._refresh_tp_step2(sim)
        elif step == 3:
            self._refresh_tp_step3()
        elif step == 4:
            self._refresh_tp_step4()
        elif step == 5:
            self._refresh_tp_step5(sim)

    def _refresh_tp_gen_refs(self, sim, step):
        step1_active = (step == 1)
        for (step_key, gen_id), (brk_lbl, eng_btn, brk_btn, mode_rbs) in \
                self._tp_gen_refs.items():
            gen = sim.gen1 if gen_id == 1 else sim.gen2
            pos = gen.breaker_position
            pos_str = {
                BreakerPosition.DISCONNECTED: "脱开",
                BreakerPosition.TEST:         "试验",
                BreakerPosition.WORKING:      "工作",
            }.get(pos, str(pos))

            run_str = "运行" if gen.running else "停机"
            cls_str = "合闸" if gen.breaker_closed else "断路"
            brk_lbl.setText(f"{run_str} | {pos_str} | {cls_str}")
            brk_lbl.setStyleSheet(
                f"color:{'#15803d' if gen.breaker_closed else '#dc2626'};"
                " font-size:11px; background:transparent;")

            if eng_btn is not None:
                eng_btn.setText("停机" if gen.running else "起机")
                if gen.running:
                    eng_btn.setStyleSheet(
                        f"background:#16a34a; color:white; {_BTN}")
                else:
                    eng_btn.setStyleSheet(
                        f"background:#e2e8f0; color:#475569; {_BTN}")

            # 合/分闸按钮
            if gen.breaker_closed:
                close_label = "分闸"
                brk_bg = "#dc2626"
            elif step_key == 's1' and step1_active:
                close_label = "合闸（测试）"
                brk_bg = "#1d4ed8"
            else:
                close_label = "合闸"
                brk_bg = "#1d4ed8"
            brk_btn.setText(close_label)
            brk_btn.setStyleSheet(f"background:{brk_bg}; color:white; {_BTN}")

            # Sync mode radio buttons
            for val, rb in mode_rbs.items():
                rb.blockSignals(True)
                rb.setChecked(gen.mode == val)
                rb.blockSignals(False)

    def _refresh_tp_bottom(self, step, sim):
        names = {1: "回路检查", 2: "线电压检查",
                 3: "相序检查", 4: "压差测试", 5: "同步测试"}
        name = names.get(step, f"第{step}步")

        started = False
        if step == 1:
            started = sim.loop_test_mode
        elif step == 2:
            started = self.ctrl.pt_voltage_check_state.started
        elif step == 3:
            started = self.ctrl.pt_phase_check_state.started
        elif step == 4:
            started = (self.ctrl.pt_exam_states[1].started and
                       self.ctrl.pt_exam_states[2].started)
        elif step == 5:
            started = self.ctrl.sync_test_state.started

        if started:
            self.tp_btn_start.setText(f"退出{name}")
            self.tp_btn_start.setStyleSheet(
                "background:#dc2626; color:white; font-weight:bold;"
                " font-size:13px; padding:6px; border-radius:4px;")
        else:
            self.tp_btn_start.setText(f"开始{name}")
            self.tp_btn_start.setStyleSheet(
                "background:#d97706; color:white; font-weight:bold;"
                " font-size:13px; padding:6px; border-radius:4px;")

    def _refresh_tp_step1(self, sim):
        in_mode = sim.loop_test_mode
        steps = self.ctrl.get_loop_test_steps()
        for lbl, (text, done) in zip(self.tp_s1_step_lbls, steps):
            marker = "✓" if done else "□"
            lbl.setText(f"{marker} {text}")
            lbl.setStyleSheet(
                f"font-size:11px; color:"
                f"{'#15803d' if done else ('#1e293b' if in_mode else '#94a3b8')};")

        for val, rb in self._tp_gnd_rbs.items():
            rb.blockSignals(True)
            rb.setChecked(sim.grounding_mode == val)
            rb.blockSignals(False)

        active = in_mode and sim.multimeter_mode
        for btn in self.tp_s1_rec_btns.values():
            btn.setEnabled(active)

        state = self.ctrl.loop_test_state
        self.tp_s1_fb_lbl.setText(state.feedback)
        self.tp_s1_fb_lbl.setStyleSheet(
            f"color:{state.feedback_color}; font-size:12px;")

    def _refresh_tp_step2(self, sim):
        in_mode = self.ctrl.pt_voltage_check_state.started
        steps = self.ctrl.get_pt_voltage_check_steps()
        for lbl, (text, done) in zip(self.tp_s2_step_lbls, steps):
            marker = "✓" if done else "□"
            lbl.setText(f"{marker} {text}")
            lbl.setStyleSheet(
                f"font-size:11px; color:"
                f"{'#15803d' if done else ('#1e293b' if in_mode else '#94a3b8')};")

        # 同步接地 radio 状态
        for val, rb in self._tp_s2_gnd_rbs.items():
            rb.blockSignals(True)
            rb.setChecked(sim.grounding_mode == val)
            rb.blockSignals(False)

        n1, n2 = sim.probe1_node, sim.probe2_node
        if n1 and n2:
            self.tp_s2_probe_lbl.setText(f"当前表笔: {n1} ↔ {n2}")
        else:
            self.tp_s2_probe_lbl.setText("当前表笔: 未放置")

        # 同步 PT 变比三值行（发电机运行时锁定输入）
        any_running = sim.gen1.running or sim.gen2.running
        for attr, (pri_spin, sec_spin, ratio_lbl) in \
                getattr(self, '_tp_s2_ratio_rows', {}).items():
            pri_spin.setEnabled(not any_running)
            sec_spin.setEnabled(not any_running)
            # 更新比例显示（spinbox 值本身由用户控制，不回写）
            p, s = pri_spin.value(), max(1, sec_spin.value())
            ratio_lbl.setText(f"{p / s:.2f}")

        # 同步 Gen fap 滑块/输入框
        for gid, entry_map in getattr(self, '_tp_s2_fap', {}).items():
            gen = sim.gen1 if gid == 1 else sim.gen2
            for attr, (sl, entry) in entry_map.items():
                scale = 10 if attr in ('freq', 'phase_deg') else 1
                sl.blockSignals(True)
                sl.setValue(int(getattr(gen, attr) * scale))
                sl.blockSignals(False)
                if not entry.hasFocus():
                    entry.setText(f"{getattr(gen, attr):.1f}")

        state = self.ctrl.pt_voltage_check_state
        self.tp_s2_fb_lbl.setText(state.feedback)
        self.tp_s2_fb_lbl.setStyleSheet(
            f"color:{state.feedback_color}; font-size:12px;")

    def _refresh_tp_step3(self):
        in_mode = self.ctrl.pt_phase_check_state.started
        steps = self.ctrl.get_pt_phase_check_steps()
        for lbl, (text, done) in zip(self.tp_s3_step_lbls, steps):
            marker = "✓" if done else "□"
            lbl.setText(f"{marker} {text}")
            lbl.setStyleSheet(
                f"font-size:11px; color:"
                f"{'#15803d' if done else ('#1e293b' if in_mode else '#94a3b8')};")

        state = self.ctrl.pt_phase_check_state
        self.tp_s3_fb_lbl.setText(state.feedback)
        self.tp_s3_fb_lbl.setStyleSheet(
            f"color:{state.feedback_color}; font-size:12px;")

    def _refresh_tp_step4(self):
        sim = self.ctrl.sim_state
        gen_id = max(1, self._tp_s4_bg.checkedId())
        in_mode = (self.ctrl.pt_exam_states[1].started and
                   self.ctrl.pt_exam_states[2].started)
        steps = self.ctrl.get_pt_exam_steps(gen_id)
        for lbl, (text, done) in zip(self.tp_s4_step_lbls, steps):
            marker = "✓" if done else "□"
            lbl.setText(f"{marker} {text}")
            lbl.setStyleSheet(
                f"font-size:11px; color:"
                f"{'#15803d' if done else ('#1e293b' if in_mode else '#94a3b8')};")

        # 同步 Gen2 fap 滑块/输入框
        for gid, entry_map in getattr(self, '_tp_s4_fap', {}).items():
            gen = sim.gen1 if gid == 1 else sim.gen2
            for attr, (sl, entry) in entry_map.items():
                scale = 10 if attr in ('freq', 'phase_deg') else 1
                sl.blockSignals(True)
                sl.setValue(int(getattr(gen, attr) * scale))
                sl.blockSignals(False)
                if not entry.hasFocus():
                    entry.setText(f"{getattr(gen, attr):.1f}")

        state = self.ctrl.pt_exam_states[gen_id]
        self.tp_s4_fb_lbl.setText(state.feedback)
        self.tp_s4_fb_lbl.setStyleSheet(
            f"color:{state.feedback_color}; font-size:12px;")

    def _refresh_tp_step5(self, sim):
        in_mode = self.ctrl.sync_test_state.started
        steps = self.ctrl.get_sync_test_steps()
        for lbl, (text, done) in zip(self.tp_s5_step_lbls, steps):
            marker = "✓" if done else "□"
            lbl.setText(f"{marker} {text}")
            lbl.setStyleSheet(
                f"font-size:11px; color:"
                f"{'#15803d' if done else ('#1e293b' if in_mode else '#94a3b8')};")

        # 同步远程启动按钮状态
        rs = sim.remote_start_signal
        self.tp_s5_remote_btn.blockSignals(True)
        self.tp_s5_remote_btn.setChecked(rs)
        self.tp_s5_remote_btn.blockSignals(False)
        if rs:
            self.tp_s5_remote_btn.setText("⚡ 关闭自动")
            self.tp_s5_remote_btn.setStyleSheet(
                "background:#16a34a; color:white; font-size:12px;"
                " font-weight:bold; padding:3px 10px; border-radius:3px;")
        else:
            self.tp_s5_remote_btn.setText("⚡ 开启自动")
            self.tp_s5_remote_btn.setStyleSheet(
                "background:#e2e8f0; color:#475569; font-size:12px;"
                " font-weight:bold; padding:3px 10px; border-radius:3px;")

        # Gen fap 控件：auto 模式下只显示，不可调
        for gid, entry_map in getattr(self, '_tp_s5_fap', {}).items():
            gen = sim.gen1 if gid == 1 else sim.gen2
            is_auto = (gen.mode == "auto")
            for attr, (sl, entry) in entry_map.items():
                scale = 10 if attr in ('freq', 'phase_deg') else 1
                sl.blockSignals(True)
                sl.setValue(int(getattr(gen, attr) * scale))
                sl.blockSignals(False)
                sl.setEnabled(not is_auto)
                if not entry.hasFocus():
                    entry.setText(f"{getattr(gen, attr):.1f}")
                entry.setReadOnly(is_auto)
                entry.setStyleSheet(
                    f"font-size:11px; background:{'#f1f5f9' if is_auto else '#ffffff'};")

        gen1, gen2 = sim.gen1, sim.gen2
        freq_diff  = abs(gen1.freq - gen2.freq)
        amp_diff   = abs(getattr(gen1, 'actual_amp', gen1.amp) -
                         getattr(gen2, 'actual_amp', gen2.amp))
        pd = abs(gen1.phase_deg - gen2.phase_deg)
        phase_diff = min(pd, 360.0 - pd)

        for key, diff in [('freq', freq_diff), ('amp', amp_diff), ('phase', phase_diff)]:
            bar, val_lbl, max_val = self.tp_s5_bars[key]
            bar.setValue(min(1000, int(1000 * diff / max_val)))
            val_lbl.setText(f"{diff:.1f}")

        self.tp_s5_fb_lbl.setText(state.feedback)
        self.tp_s5_fb_lbl.setStyleSheet(
            f"color:{state.feedback_color}; font-size:12px;")
