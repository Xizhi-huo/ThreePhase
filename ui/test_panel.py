"""
ui/test_panel.py
合闸前测试模式 — 竖向测试控制条 Mixin

进入测试模式后，右侧控制台隐藏，本 Mixin 提供的竖向测试条替代之。
母排拓扑图自动保持前台，所有测试步骤的必要按钮全部集中在此条内。
"""

from PyQt5 import QtWidgets, QtCore, QtGui
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


# ── 相色常量（黄/绿/红）────────────────────────────────────────────────────
_PC = {'A': '#f59e0b', 'B': '#22c55e', 'C': '#ef4444'}
_PI = {'A': 0, 'B': 1, 'C': 2}


class _GenWiringWidget(QtWidgets.QWidget):
    """发电机端子盒接线图：上方三个内部绕组圆（A/B/C 固定色），
    下方三个输出接线柱方块（U/V/W），连线根据 mapping 动态绘制。
    interactive=True 时支持点击两个节点互换接线。"""

    def __init__(self, mapping, interactive=False, parent=None):
        """mapping: dict {terminal('A'/'B'/'C'): actual_phase}"""
        super().__init__(parent)
        self.mapping = mapping
        self.interactive = interactive
        # _order[i] = 第 i 个接线柱（U/V/W）实际连接的绕组相
        phases = ['A', 'B', 'C']
        self._order = [mapping.get(p, p) for p in phases]
        self._selected = None   # (zone, raw_idx): zone='top'|'bot', raw_idx∈{0,1,2}
        self.setFixedSize(270, 210)
        if interactive:
            self.setCursor(QtCore.Qt.PointingHandCursor)

    def get_order(self):
        """返回当前 [ph_at_U, ph_at_V, ph_at_W] 列表（供修复时写入 pt_phase_orders）。"""
        return list(self._order)

    def _xs(self):
        return [int(self.width() * 0.22), int(self.width() * 0.50), int(self.width() * 0.78)]

    def _hit_test(self, pos):
        """返回 (zone, raw_idx) 或 None。top=绕组圆(idx=相序0-2), bot=接线柱(idx=柱0-2)。"""
        xs = self._xs(); r = 13
        for i in range(3):
            if abs(pos.x() - xs[i]) <= r + 4 and abs(pos.y() - 52) <= r + 4:
                return ('top', i)
        for i in range(3):
            if abs(pos.x() - xs[i]) <= r + 4 and abs(pos.y() - 158) <= r + 4:
                return ('bot', i)
        return None

    def _resolve_j(self, zone, raw_idx):
        """将点击 (zone, raw_idx) 转换为接线柱下标 j（0/1/2 对应 U/V/W）。"""
        if zone == 'bot':
            return raw_idx
        # top: raw_idx 是绕组序号 → 找到该绕组当前连接的接线柱
        ph = ['A', 'B', 'C'][raw_idx]
        return self._order.index(ph)

    def mousePressEvent(self, event):
        if not self.interactive:
            return
        hit = self._hit_test(event.pos())
        if hit is None:
            self._selected = None
            self.update()
            return
        if self._selected is None:
            self._selected = hit
            self.update()
            return
        # 第二次点击：计算两个接线柱下标并互换
        j1 = self._resolve_j(*self._selected)
        j2 = self._resolve_j(*hit)
        if j1 != j2:
            self._order[j1], self._order[j2] = self._order[j2], self._order[j1]
        self._selected = None
        self.update()

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        w = self.width()
        xs = self._xs()
        phases = ['A', 'B', 'C']
        term_labels = ['U', 'V', 'W']
        r = 13          # circle/square half-size
        y_src = 52      # 内部绕组圆心 y
        y_dst = 158     # 输出接线柱中心 y

        # 白色背景
        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(QtGui.QBrush(QtGui.QColor('#ffffff')))
        qp.drawRoundedRect(0, 0, w, self.height(), 6, 6)

        if self.interactive:
            hint = QtWidgets.QLabel()  # 仅借用文字绘制，不显示 widget
            f6 = QtGui.QFont(); f6.setPointSize(6); f6.setItalic(True)
            qp.setFont(f6); qp.setPen(QtGui.QPen(QtGui.QColor('#64748b')))
            qp.drawText(QtCore.QRect(0, self.height() - 28, w, 13),
                        QtCore.Qt.AlignCenter, "点击任意两个节点可互换接线")

        # 区域标签
        f7 = QtGui.QFont(); f7.setPointSize(7)
        qp.setFont(f7); qp.setPen(QtGui.QPen(QtGui.QColor('#94a3b8')))
        qp.drawText(QtCore.QRect(0, 2, w, 14), QtCore.Qt.AlignCenter, "── 内部绕组 ──")
        qp.drawText(QtCore.QRect(0, y_dst + r + 18, w, 13),
                    QtCore.Qt.AlignCenter, "── 输出接线柱 ──")

        # ── 连线（先画，在圆下方）──
        for i in range(3):
            actual = self._order[i]
            sx = xs[_PI[actual]]   # 源：actual 相绕组的固定 x
            dx = xs[i]             # 目标：第 i 个接线柱 x
            c = QtGui.QColor(_PC[actual])
            pen = QtGui.QPen(c, 2.5, QtCore.Qt.SolidLine,
                             QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)
            qp.setPen(pen)
            qp.drawLine(sx, y_src + r + 1, dx, y_dst - r - 1)

        f9b = QtGui.QFont(); f9b.setPointSize(9); f9b.setBold(True)

        # ── 内部绕组圆（A=黄/B=绿/C=红，位置固定）──
        for i, ph in enumerate(phases):
            x = xs[i]; c = QtGui.QColor(_PC[ph])
            # 选中高亮
            sel_top = (self._selected == ('top', i))
            border_c = QtGui.QColor('#1d4ed8') if sel_top else c.darker(130)
            border_w = 3.5 if sel_top else 2
            qp.setPen(QtGui.QPen(border_c, border_w))
            qp.setBrush(QtGui.QBrush(c))
            qp.drawEllipse(x - r, y_src - r, 2 * r, 2 * r)
            qp.setPen(QtGui.QPen(QtGui.QColor('#ffffff')))
            qp.setFont(f9b)
            qp.drawText(QtCore.QRect(x - r, y_src - r, 2 * r, 2 * r),
                        QtCore.Qt.AlignCenter, ph)

        # ── 输出接线柱方块（U/V/W，颜色跟随实际相）──
        for i in range(3):
            x = xs[i]
            actual = self._order[i]
            c = QtGui.QColor(_PC[actual])
            sel_bot = (self._selected == ('bot', i))
            border_c = QtGui.QColor('#1d4ed8') if sel_bot else QtGui.QColor('#475569')
            border_w = 3 if sel_bot else 2
            qp.setPen(QtGui.QPen(border_c, border_w))
            qp.setBrush(QtGui.QBrush(QtGui.QColor('#f0f4f8')))
            qp.drawRect(x - r, y_dst - r, 2 * r, 2 * r)
            qp.setPen(QtGui.QPen(QtGui.QColor('#1e293b')))
            qp.setFont(f9b)
            qp.drawText(QtCore.QRect(x - r, y_dst - r, 2 * r, 2 * r),
                        QtCore.Qt.AlignCenter, term_labels[i])
            # 实际相标注（接线柱下方）
            f8 = QtGui.QFont(); f8.setPointSize(8)
            qp.setFont(f8); qp.setPen(QtGui.QPen(c))
            qp.drawText(QtCore.QRect(x - 18, y_dst + r + 2, 36, 16),
                        QtCore.Qt.AlignCenter, f"({actual})")
        qp.end()


class _PTWiringWidget(QtWidgets.QWidget):
    """PT 接线盒图：按逐级传播后的实际相别显示每一层端子颜色。

    下方输入电缆显示上游实际来相顺序；
    A1/B1/C1 显示一次侧传播后的实际相别；
    A2/B2/C2 显示二次侧传播后的实际相别；
    最上方测量端仅将二次侧当前结果垂直引出，不再额外重排为 ABC。
    """

    _Y_OUT   = 24
    _Y_SEC   = 104
    _Y_BOXT  = 124
    _Y_BOXB  = 202
    _Y_PRI   = 222
    _Y_CABLE = 318

    def __init__(self, pri_order, sec_order, pri_input_order=None,
                 interactive_pri=False, interactive_sec=False, parent=None):
        """pri_order/sec_order 为本级置换，pri_input_order 为上游实际来相顺序。"""
        super().__init__(parent)
        self._pri_order = list(pri_order)
        self._sec_order = list(sec_order)
        self._pri_input_order = list(pri_input_order or ['A', 'B', 'C'])
        self.interactive_pri = interactive_pri
        self.interactive_sec = interactive_sec
        self._sel_sec = None
        self._sel_pri = None
        self.setFixedSize(270, 350)
        if interactive_pri or interactive_sec:
            self.setCursor(QtCore.Qt.PointingHandCursor)

    def get_pri_order(self):
        return list(self._pri_order)

    def get_sec_order(self):
        return list(self._sec_order)

    def _primary_actual_order(self):
        labels = ('A', 'B', 'C')
        return [self._pri_input_order[labels.index(cable_label)] for cable_label in self._pri_order]

    def _secondary_actual_order(self):
        labels = ('A', 'B', 'C')
        primary_actual = self._primary_actual_order()
        return [primary_actual[labels.index(sec_label)] for sec_label in self._sec_order]

    def _xs(self):
        return [int(self.width() * 0.22), int(self.width() * 0.50), int(self.width() * 0.78)]

    def _hit_sec(self, pos):
        """若点击落在二次侧端子圆内，返回下标（0/1/2），否则返回 None。"""
        xs = self._xs(); r = 11
        for i in range(3):
            if abs(pos.x() - xs[i]) <= r + 4 and abs(pos.y() - self._Y_SEC) <= r + 4:
                return i
        return None

    def _hit_pri(self, pos):
        xs = self._xs(); r = 11
        for i in range(3):
            if abs(pos.x() - xs[i]) <= r + 4 and abs(pos.y() - self._Y_PRI) <= r + 4:
                return i
        return None

    def mousePressEvent(self, event):
        if not (self.interactive_pri or self.interactive_sec):
            return
        sec_hit = self._hit_sec(event.pos()) if self.interactive_sec else None
        pri_hit = self._hit_pri(event.pos()) if self.interactive_pri else None
        if sec_hit is not None:
            self._sel_pri = None
            if self._sel_sec is None:
                self._sel_sec = sec_hit
                self.update()
                return
            j1, j2 = self._sel_sec, sec_hit
            if j1 != j2:
                self._sec_order[j1], self._sec_order[j2] = self._sec_order[j2], self._sec_order[j1]
            self._sel_sec = None
            self.update()
            return
        # 第二次点击：互换两个二次侧端子的相
        if pri_hit is not None:
            self._sel_sec = None
            if self._sel_pri is None:
                self._sel_pri = pri_hit
                self.update()
                return
            j1, j2 = self._sel_pri, pri_hit
            if j1 != j2:
                self._pri_order[j1], self._pri_order[j2] = self._pri_order[j2], self._pri_order[j1]
            self._sel_pri = None
            self.update()
            return
        self._sel_sec = None
        self._sel_pri = None
        self.update()

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        w = self.width()
        xs = self._xs()
        pri_input = self._pri_input_order
        pri_actual = self._primary_actual_order()
        sec_actual = self._secondary_actual_order()
        r = 11   # 端子半径

        y_out   = self._Y_OUT
        y_sec   = self._Y_SEC
        y_boxt  = self._Y_BOXT
        y_boxb  = self._Y_BOXB
        y_pri   = self._Y_PRI
        y_cable = self._Y_CABLE

        # 白色背景
        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(QtGui.QBrush(QtGui.QColor('#ffffff')))
        qp.drawRoundedRect(0, 0, w, self.height(), 6, 6)

        if self.interactive_pri or self.interactive_sec:
            f6 = QtGui.QFont(); f6.setPointSize(6); f6.setItalic(True)
            qp.setFont(f6); qp.setPen(QtGui.QPen(QtGui.QColor('#64748b')))
            qp.drawText(QtCore.QRect(0, y_out - 13, w, 11),
                        QtCore.Qt.AlignCenter, "↑ 点击一次侧或二次侧两个端子可互换接线 ↑")

        # 变压器铁芯盒（中间灰色虚线框）
        qp.setPen(QtGui.QPen(QtGui.QColor('#94a3b8'), 1.5, QtCore.Qt.DashLine))
        qp.setBrush(QtGui.QBrush(QtGui.QColor('#f0f9ff')))
        qp.drawRect(10, y_boxt, w - 20, y_boxb - y_boxt)
        f8 = QtGui.QFont(); f8.setPointSize(8)
        qp.setFont(f8); qp.setPen(QtGui.QPen(QtGui.QColor('#64748b')))
        ymid = (y_boxt + y_boxb) // 2
        qp.drawText(QtCore.QRect(0, ymid - 8, w, 16),
                    QtCore.Qt.AlignCenter, "⚡  变压器铁芯（黑盒）")

        f9b = QtGui.QFont(); f9b.setPointSize(9); f9b.setBold(True)
        f7  = QtGui.QFont(); f7.setPointSize(7)

        # ═══════════════════ 二次侧（上半部）═══════════════════

        # 测量端口圆：仅垂直引出二次侧当前实际结果
        qp.setFont(f7); qp.setPen(QtGui.QPen(QtGui.QColor('#94a3b8')))
        qp.drawText(QtCore.QRect(0, y_out + r + 2, w, 12), QtCore.Qt.AlignCenter,
                    "── 二次侧测量端口 ──")
        qp.drawText(QtCore.QRect(0, 8, w, 12), QtCore.Qt.AlignCenter,
                    f"实际输出: {''.join(sec_actual)}")
        for i, ph in enumerate(sec_actual):
            x = xs[i]; c = QtGui.QColor(_PC[ph])
            qp.setPen(QtGui.QPen(c.darker(120), 1.5))
            qp.setBrush(QtGui.QBrush(c.lighter(140)))
            qp.drawEllipse(x - r, y_out - r, 2 * r, 2 * r)
            qp.setPen(QtGui.QPen(c.darker(140)))
            qp.setFont(f9b)
            qp.drawText(QtCore.QRect(x - r, y_out - r, 2 * r, 2 * r),
                        QtCore.Qt.AlignCenter, ph)

        # 二次侧输出：从 A2/B2/C2 垂直引出当前实际相别
        for i, ph_out in enumerate(sec_actual):
            sx = xs[i]
            c  = QtGui.QColor(_PC[ph_out])
            pen = QtGui.QPen(c, 2.2, QtCore.Qt.SolidLine,
                             QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)
            qp.setPen(pen)
            qp.drawLine(sx, y_sec - r - 1, sx, y_out + r + 1)

        # 二次侧端子圆（a2/b2/c2，颜色跟随输出相；选中时蓝边）
        sec_lbl = ['a2', 'b2', 'c2']
        for i, ph_out in enumerate(sec_actual):
            x = xs[i]; c = QtGui.QColor(_PC[ph_out])
            selected = (self._sel_sec == i)
            border_c = QtGui.QColor('#1d4ed8') if selected else c.darker(120)
            border_w = 3.5 if selected else 2
            qp.setPen(QtGui.QPen(border_c, border_w))
            qp.setBrush(QtGui.QBrush(QtGui.QColor('#ffffff')))
            qp.drawEllipse(x - r, y_sec - r, 2 * r, 2 * r)
            f7b = QtGui.QFont(); f7b.setPointSize(7); f7b.setBold(True)
            qp.setFont(f7b); qp.setPen(QtGui.QPen(QtGui.QColor('#1e293b')))
            qp.drawText(QtCore.QRect(x - r, y_sec - r, 2 * r, 2 * r),
                        QtCore.Qt.AlignCenter, sec_lbl[i])
            qp.setFont(f7)
            qp.setPen(QtGui.QPen(c))
            qp.drawText(QtCore.QRect(x + r + 4, y_sec - 8, 28, 16),
                        QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, f"({ph_out})")

        # ═══════════════════ 一次侧（下半部）═══════════════════

        # 一次侧端子圆：显示一次侧端子处的实际相别
        qp.setFont(f7); qp.setPen(QtGui.QPen(QtGui.QColor('#94a3b8')))
        qp.drawText(QtCore.QRect(0, y_pri - r - 18, w, 12), QtCore.Qt.AlignCenter,
                    f"一次侧结果: {''.join(pri_actual)}")
        pri_lbl = ['A1', 'B1', 'C1']
        for i, ph_in in enumerate(pri_actual):
            x = xs[i]; c = QtGui.QColor(_PC[ph_in])
            selected = (self._sel_pri == i)
            border_c = QtGui.QColor('#1d4ed8') if selected else c.darker(120)
            border_w = 3.5 if selected else 2
            qp.setPen(QtGui.QPen(border_c, border_w))
            qp.setBrush(QtGui.QBrush(QtGui.QColor('#ffffff')))
            qp.drawEllipse(x - r, y_pri - r, 2 * r, 2 * r)
            f7b = QtGui.QFont(); f7b.setPointSize(7); f7b.setBold(True)
            qp.setFont(f7b); qp.setPen(QtGui.QPen(QtGui.QColor('#1e293b')))
            qp.drawText(QtCore.QRect(x - r, y_pri - r, 2 * r, 2 * r),
                        QtCore.Qt.AlignCenter, pri_lbl[i])
            qp.setFont(f7)
            qp.setPen(QtGui.QPen(c))
            qp.drawText(QtCore.QRect(x + r + 4, y_pri - 8, 28, 16),
                        QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, f"({ph_in})")

        # 一次侧交叉连线：从下方来相实际位置连到一次侧端子
        for i, ph_in in enumerate(pri_actual):
            src_x = xs[pri_input.index(ph_in)]
            dst_x = xs[i]
            c = QtGui.QColor(_PC[ph_in])
            pen = QtGui.QPen(c, 2.2, QtCore.Qt.SolidLine,
                             QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)
            qp.setPen(pen)
            qp.drawLine(src_x, y_cable - r - 1, dst_x, y_pri + r + 1)

        # 输入电缆圆：继承上游实际来相顺序
        for i, ph in enumerate(pri_input):
            x = xs[i]; c = QtGui.QColor(_PC[ph])
            qp.setPen(QtGui.QPen(c.darker(120), 2))
            qp.setBrush(QtGui.QBrush(c))
            qp.drawEllipse(x - r, y_cable - r, 2 * r, 2 * r)
            qp.setPen(QtGui.QPen(QtGui.QColor('#ffffff')))
            qp.setFont(f9b)
            qp.drawText(QtCore.QRect(x - r, y_cable - r, 2 * r, 2 * r),
                        QtCore.Qt.AlignCenter, ph)

        qp.setFont(f7); qp.setPen(QtGui.QPen(QtGui.QColor('#94a3b8')))
        qp.drawText(QtCore.QRect(0, self.height() - 14, w, 13),
                    QtCore.Qt.AlignCenter, "── 一次侧输入电缆 ──")
        qp.drawText(QtCore.QRect(0, y_cable + r + 14, w, 12), QtCore.Qt.AlignCenter,
                    f"实际来相: {''.join(pri_input)}")
        qp.end()


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

        # 故障训练场景横幅（有故障时显示）
        self._tp_fault_banner = QtWidgets.QLabel("")
        self._tp_fault_banner.setStyleSheet(
            "background:#fef2f2; color:#991b1b; font-weight:bold; font-size:11px;"
            " padding:4px 8px; border-radius:4px; border:1px solid #fca5a5;")
        self._tp_fault_banner.setAlignment(QtCore.Qt.AlignCenter)
        self._tp_fault_banner.setWordWrap(True)
        self._tp_fault_banner.setMinimumHeight(40)
        self._tp_fault_banner.setVisible(False)
        cl.addWidget(self._tp_fault_banner)

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
        self.tp_meter_lbl.setMinimumHeight(36)
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

    def _add_blackbox_section(self, lay):
        """在任意步骤组中插入四个物理接线黑盒检查按钮（可查看 + 交互修复）。"""
        bb_lbl = QtWidgets.QLabel("物理接线检查 / 手动修复 (开盖查线):")
        bb_lbl.setStyleSheet("color:#64748b; font-size:11px; margin-top:4px;")
        lay.addWidget(bb_lbl)
        allow_blackbox = self.ctrl.can_inspect_blackbox()
        bb_row1 = QtWidgets.QWidget()
        bb_row1.setStyleSheet(f"background:{_SECTION_BG};")
        bb_h1 = QtWidgets.QHBoxLayout(bb_row1)
        bb_h1.setContentsMargins(0, 0, 0, 0)
        bb_h1.setSpacing(4)
        btn_g1 = self._make_btn("G1 机端接线", "#92400e")
        btn_g1.setEnabled(allow_blackbox)
        btn_g1.clicked.connect(lambda: self._show_blackbox_dialog('G1'))
        btn_g2 = self._make_btn("G2 机端接线", "#92400e")
        btn_g2.setEnabled(allow_blackbox)
        btn_g2.clicked.connect(lambda: self._show_blackbox_dialog('G2'))
        bb_h1.addWidget(btn_g1)
        bb_h1.addWidget(btn_g2)
        lay.addWidget(bb_row1)
        bb_row2 = QtWidgets.QWidget()
        bb_row2.setStyleSheet(f"background:{_SECTION_BG};")
        bb_h2 = QtWidgets.QHBoxLayout(bb_row2)
        bb_h2.setContentsMargins(0, 0, 0, 0)
        bb_h2.setSpacing(4)
        btn_pt1 = self._make_btn("PT1 接线盒", "#1e40af")
        btn_pt1.setEnabled(allow_blackbox)
        btn_pt1.clicked.connect(lambda: self._show_blackbox_dialog('PT1'))
        btn_pt3 = self._make_btn("PT3 接线盒", "#1e40af")
        btn_pt3.setEnabled(allow_blackbox)
        btn_pt3.clicked.connect(lambda: self._show_blackbox_dialog('PT3'))
        bb_h2.addWidget(btn_pt1)
        bb_h2.addWidget(btn_pt3)
        lay.addWidget(bb_row2)

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

        self._add_blackbox_section(lay)

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
            ("PT1 (Gen1侧)", "pt_gen_ratio", 11000, 193),
            ("PT3 (Gen2侧)", "pt3_ratio",    11000, 193),
            ("PT2 (母排侧)", "pt_bus_ratio", 10500, 105),
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
                self.ctrl.update_pt_ratio(_a, ratio)

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

        self._add_blackbox_section(lay)

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

        self._add_blackbox_section(lay)

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

        self.tp_s4_step_lbls = self._make_step_list(lay, 5)

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
        btn_rec = self._make_btn("记录当前表笔位置", "#16a34a")
        btn_rec.clicked.connect(
            lambda: self.ctrl.record_current_pt_measurement(
                max(1, self._tp_s4_bg.checkedId())))
        rh.addWidget(btn_rec)
        lay.addWidget(rrow)

        # ── 物理接线黑盒检查 ────────────────────────────────────────────────
        self._add_blackbox_section(lay)

        # 第四步快捷记录按钮（管理员模式 / 考核模式可用）
        self._tp_s4_quick_btn = self._make_btn("⚡ 快捷记录全部18组", "#7c3aed")
        self._tp_s4_quick_btn.setToolTip(
            "跳过逐组表笔测量，直接从物理引擎计算 Gen1+Gen2 全部 18 组压差并写入。"
        )
        self._tp_s4_quick_btn.clicked.connect(
            lambda: self.ctrl.record_all_pt_measurements_quick())
        self._tp_s4_quick_btn.setVisible(False)
        lay.addWidget(self._tp_s4_quick_btn)

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
        self.tp_s5_fb_lbl.setMinimumHeight(48)
        self.tp_s5_fb_lbl.setStyleSheet("color:#15803d; font-size:12px;")
        lay.addWidget(self.tp_s5_fb_lbl)

        cl.addWidget(grp)
        return grp

    # ════════════════════════════════════════════════════════════════════
    # Test mode enter / exit
    # ════════════════════════════════════════════════════════════════════
    def enter_test_mode(self):
        # 读取控制面板预设场景并注入（_pre_test_scenario_id 定义在 control_panel.py）
        scenario_id = getattr(self, '_pre_test_scenario_id', '')
        self.ctrl.test_flow_mode = getattr(self, '_pre_test_flow_mode', 'teaching')
        if scenario_id:
            # 有故障：完整重置（停机 + 清空所有测试状态 + 注入故障）
            self.ctrl.reset_for_scenario(scenario_id)
        else:
            # 无故障：仅清除可能残留的故障注入
            self.ctrl.inject_fault('')

        self._test_mode_active = True
        self._assessment_last_logged_step = None
        self._pre_step5_repair_triggered = False   # 重置第五步前修复关卡
        self.ctrl_container.setVisible(False)
        self.test_panel.setVisible(True)
        self.tp_btn_admin.setVisible(self.ctrl.allow_admin_shortcuts())
        if hasattr(self, '_tp_s4_quick_btn'):
            self._tp_s4_quick_btn.setVisible(self.ctrl.can_use_pt_exam_quick_record())
        if not self.ctrl.allow_admin_shortcuts():
            self._tp_admin_mode = False
            self.tp_btn_admin.setChecked(False)
            self._tp_forced_step = None
        self.ctrl.start_assessment_session(scenario_id)
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
        before_complete = self._is_step_complete(step)
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
                except AttributeError:
                    pass
        elif step == 4:
            self.ctrl.finalize_all_pt_exams()
        elif step == 5:
            self.ctrl.finalize_sync_test()
        after_complete = self._is_step_complete(step)
        self.ctrl.append_assessment_event(
            'step_finalize_attempted',
            step=step,
            allowed=after_complete,
            mode=self.ctrl.test_flow_mode,
        )
        if after_complete and not before_complete:
            self.ctrl.append_assessment_event('step_completed', step=step)
        elif not after_complete:
            self.ctrl.append_assessment_event(
                'advance_blocked',
                step=step,
                from_step=step,
                to_step=min(step + 1, 5),
                reason='step_finalize_rejected',
            )

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
                    " font-weight:bold;}"
                    "QPushButton:hover{background:#6d28d9;}")
        # idle
        return f"QPushButton{{{base} color:#94a3b8; background:transparent;}}"

    # ── 相序仪回调 ────────────────────────────────────────────────────────
    def _on_connect_psm(self, pt_name: str):
        """接入相序仪到指定 PT，驱动母排图侧栏显示。"""
        try:
            self.connect_phase_seq_meter(pt_name)   # 方法定义在主窗口 mixin 上
        except AttributeError:
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
        except AttributeError:
            pass
        for btn in self._tp_s3_rec_btns.values():
            btn.setEnabled(False)
        self.tp_s3_fb_lbl.setText("相序仪已断开，可重新接入")

    def _on_record_psm(self, pt_name: str):
        """根据当前相序仪示数记录相序结果到服务层。"""
        seq = getattr(self.phase_seq_meter, '_sequence', 'unknown')
        if seq == 'unknown':
            self.tp_s3_fb_lbl.setText("请先接入相序仪，再记录结果。")
            return
        ok = self.ctrl.record_phase_sequence(pt_name, seq)
        state = self.ctrl.pt_phase_check_state
        self.tp_s3_fb_lbl.setText(state.feedback)
        self.tp_s3_fb_lbl.setStyleSheet(f"color:{state.feedback_color};")
        if ok and pt_name in self._tp_s3_rec_btns:
            self._tp_s3_rec_btns[pt_name].setEnabled(False)

    def _on_tp_toggle_admin(self, checked):
        """管理员模式：显示/隐藏步骤详情 Tab 2-6，步骤按钮变为可点击。"""
        if checked and not self.ctrl.allow_admin_shortcuts():
            self.tp_btn_admin.setChecked(False)
            return
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
        # 第四步快捷记录按钮在管理员模式或考核模式下可见
        if hasattr(self, '_tp_s4_quick_btn'):
            self._tp_s4_quick_btn.setVisible(checked or self.ctrl.is_assessment_mode())

    def _update_fault_banner(self):
        """根据当前故障注入状态更新横幅显示。不向学员透露具体场景信息。"""
        fc = self.ctrl.sim_state.fault_config
        if not self.ctrl.should_show_fault_detected_banner():
            self._tp_fault_banner.setVisible(False)
            return
        if fc.active and fc.scenario_id:
            if fc.repaired:
                text = "✅ 故障已修复，请继续按正常流程完成剩余步骤"
                self._tp_fault_banner.setStyleSheet(
                    "background:#f0fdf4; color:#15803d; font-weight:bold; font-size:11px;"
                    " padding:4px 8px; border-radius:4px; border:1px solid #86efac;")
            elif fc.detected:
                if self.ctrl.can_advance_with_fault():
                    text = ("🔍 已发现异常证据 | 请继续完成所有测试步骤，"
                            "记录全部数据后将在第五步前统一进行检修")
                else:
                    text = ("🔍 已发现异常证据 | 当前流程模式要求先排除故障并复测合格，"
                            "再继续后续步骤")
                self._tp_fault_banner.setStyleSheet(
                    "background:#fffbeb; color:#92400e; font-weight:bold; font-size:11px;"
                    " padding:4px 8px; border-radius:4px; border:1px solid #fcd34d;")
            else:
                text = "⚠ 故障训练模式已启用 | 请按正常流程测试，通过测量数据发现并定位异常"
                self._tp_fault_banner.setStyleSheet(
                    "background:#fef2f2; color:#991b1b; font-weight:bold; font-size:11px;"
                    " padding:4px 8px; border-radius:4px; border:1px solid #fca5a5;")
            self._tp_fault_banner.setText(text)
            self._tp_fault_banner.setVisible(True)
        else:
            self._tp_fault_banner.setVisible(False)

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
        if (c.should_hold_at_step4_when_wiring_fault_unrepaired()
                and c.has_unrepaired_wiring_fault()):
            return 4
        return 5

    def _is_step_complete(self, step: int) -> bool:
        if step == 1:
            return self.ctrl.is_loop_test_complete()
        if step == 2:
            return self.ctrl.is_pt_voltage_check_complete()
        if step == 3:
            return self.ctrl.is_pt_phase_check_complete()
        if step == 4:
            return self.ctrl.pt_exam_states[1].completed and self.ctrl.pt_exam_states[2].completed
        if step == 5:
            return self.ctrl.is_sync_test_complete()
        return False

    def _show_assessment_result_dialog(self, result):
        score_labels = {
            "flow_discipline": "流程纪律",
            "loop_test": "第一步回路测试",
            "pt_voltage_check": "第二步PT电压检查",
            "pt_phase_check": "第三步PT相序检查",
            "pt_exam": "第四步压差考核",
            "anomaly_localization": "异常识别与故障定位",
            "blackbox_repair": "黑盒修复",
            "efficiency": "效率与规范性",
        }
        metric_labels = {
            "step_entered_order": "步骤进入顺序",
            "step_finalize_attempts": "完成本步尝试次数",
            "blocked_advances": "门禁拦截次数",
            "gate_blocks": "闭环门禁触发次数",
            "measurements_recorded": "测量记录总数",
            "invalid_measurements": "无效测量次数",
            "blackboxes_opened": "打开黑盒",
            "blackbox_swap_count": "黑盒交换次数",
            "blackbox_failed_confirms": "错误确认次数",
            "fault_detected_at_step": "首次发现异常步骤",
            "fault_repaired_at": "故障修复时间",
            "serious_misoperations": "严重误操作次数",
        }

        def _table_item(text, align=QtCore.Qt.AlignCenter):
            item = QtWidgets.QTableWidgetItem(text)
            item.setTextAlignment(int(align | QtCore.Qt.AlignVCenter))
            return item

        def _color_row(table, row, bg, fg="#0f172a"):
            for col in range(table.columnCount()):
                item = table.item(row, col)
                if item is not None:
                    item.setBackground(QtGui.QColor(bg))
                    item.setForeground(QtGui.QColor(fg))

        def _status_palette(status_text: str):
            if status_text == "通过":
                return "#ecfdf5", "#166534", "#bbf7d0"
            if status_text == "未通过":
                return "#fef2f2", "#991b1b", "#fecaca"
            return "#fffbeb", "#92400e", "#fde68a"

        def _make_info_card(title_text: str, body_text: str, accent: str = "#cbd5e1", body_size: int = 20):
            card = QtWidgets.QFrame()
            card.setStyleSheet(
                "QFrame{background:white; border:1px solid #dbe4f0; border-radius:14px;}"
            )
            card_lay = QtWidgets.QVBoxLayout(card)
            card_lay.setContentsMargins(14, 12, 14, 12)
            card_lay.setSpacing(6)

            title_lbl = QtWidgets.QLabel(title_text)
            title_lbl.setStyleSheet("font-size:11px; color:#64748b; font-weight:bold; letter-spacing:0.5px;")
            card_lay.addWidget(title_lbl)

            bar = QtWidgets.QFrame()
            bar.setFixedHeight(4)
            bar.setStyleSheet(f"background:{accent}; border:none; border-radius:2px;")
            card_lay.addWidget(bar)

            body_lbl = QtWidgets.QLabel(body_text)
            body_lbl.setStyleSheet(f"font-size:{body_size}px; color:#0f172a; font-weight:bold;")
            body_lbl.setWordWrap(True)
            card_lay.addWidget(body_lbl)
            card_lay.addStretch()
            return card

        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("考核成绩单")
        dlg.resize(760, 720)
        dlg.setStyleSheet(
            "QDialog{background:#f8fafc;}"
            "QLabel{color:#0f172a;}"
            "QHeaderView::section{background:#e2e8f0; color:#0f172a; padding:6px 8px; border:none; font-weight:bold;}"
            "QTableWidget{background:white; border:1px solid #dbe4f0; gridline-color:#eef2f7; border-radius:10px;}"
        )

        lay = QtWidgets.QVBoxLayout(dlg)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(10)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        content = QtWidgets.QWidget()
        content_lay = QtWidgets.QVBoxLayout(content)
        content_lay.setContentsMargins(0, 0, 0, 0)
        content_lay.setSpacing(12)
        scroll.setWidget(content)
        lay.addWidget(scroll, 1)

        result_tag = "通过" if result.passed else "未通过"
        tag_bg = "#dcfce7" if result.passed else "#fee2e2"
        tag_fg = "#166534" if result.passed else "#991b1b"
        overview = QtWidgets.QFrame()
        overview.setStyleSheet("background:#fffdf8; border:1px solid #e2e8f0; border-radius:18px;")
        overview_lay = QtWidgets.QHBoxLayout(overview)
        overview_lay.setContentsMargins(18, 16, 18, 16)
        overview_lay.setSpacing(14)

        hero = QtWidgets.QFrame()
        hero.setStyleSheet("background:transparent; border:none;")
        hero_lay = QtWidgets.QVBoxLayout(hero)
        hero_lay.setContentsMargins(0, 0, 0, 0)
        hero_lay.setSpacing(8)

        kicker = QtWidgets.QLabel("考核结果报告")
        kicker.setStyleSheet("font-size:11px; color:#b45309; font-weight:bold; letter-spacing:1px;")
        hero_lay.addWidget(kicker)

        title = QtWidgets.QLabel("考核成绩单")
        title.setStyleSheet("font-size:28px; font-weight:bold; color:#0f172a;")
        hero_lay.addWidget(title)

        hero_info = QtWidgets.QLabel(
            f"场景：{result.scene_id or '正常模式'}    模式：考核模式\n"
            f"完成时间：{result.finished_at.replace('T', ' ')}"
        )
        hero_info.setStyleSheet("font-size:12px; color:#475569;")
        hero_lay.addWidget(hero_info)

        tag = QtWidgets.QLabel(result_tag)
        tag.setAlignment(QtCore.Qt.AlignCenter)
        tag.setFixedWidth(94)
        tag.setStyleSheet(
            f"background:{tag_bg}; color:{tag_fg}; font-size:15px; "
            "font-weight:bold; border-radius:16px; padding:7px 12px;"
        )
        hero_lay.addWidget(tag, alignment=QtCore.Qt.AlignLeft)
        overview_lay.addWidget(hero, 2)

        side_cards = QtWidgets.QVBoxLayout()
        side_cards.setContentsMargins(0, 0, 0, 0)
        side_cards.setSpacing(10)
        side_cards.addWidget(_make_info_card("总分", f"{result.total_score} / {result.max_score}", "#f59e0b", 30))
        side_cards.addWidget(_make_info_card("总耗时", f"{result.elapsed_seconds}s", "#0ea5e9", 22))
        overview_lay.addLayout(side_cards, 1)
        content_lay.addWidget(overview)

        summary = QtWidgets.QLabel(result.summary)
        summary.setWordWrap(True)
        summary.setStyleSheet(
            "background:white; border:1px solid #dbe4f0; border-radius:14px; "
            "padding:14px; font-size:13px; color:#334155; line-height:1.5;"
        )
        content_lay.addWidget(summary)

        if result.veto_reason:
            veto = QtWidgets.QLabel(f"否决原因：{result.veto_reason}")
            veto.setWordWrap(True)
            veto.setStyleSheet(
                "background:#fff1f2; border:1px solid #fecdd3; border-radius:14px; "
                "padding:12px; font-size:12px; color:#9f1239; font-weight:bold;"
            )
            content_lay.addWidget(veto)

        section1 = QtWidgets.QLabel("分项汇总")
        section1.setStyleSheet("font-size:16px; font-weight:bold; color:#0f172a; padding-top:4px;")
        content_lay.addWidget(section1)

        summary_grid_wrap = QtWidgets.QFrame()
        summary_grid_wrap.setStyleSheet("background:transparent; border:none;")
        summary_grid = QtWidgets.QGridLayout(summary_grid_wrap)
        summary_grid.setContentsMargins(0, 0, 0, 0)
        summary_grid.setHorizontalSpacing(10)
        summary_grid.setVerticalSpacing(10)
        for idx, (key, value) in enumerate(result.step_scores.items()):
            max_value = result.step_max_scores.get(key, 0)
            bg, fg, border = _status_palette(
                "通过" if value == max_value else "未通过" if value == 0 else "部分扣分"
            )
            card = QtWidgets.QFrame()
            card.setStyleSheet(
                f"background:{bg}; border:1px solid {border}; border-radius:14px;"
            )
            card_lay = QtWidgets.QVBoxLayout(card)
            card_lay.setContentsMargins(14, 12, 14, 12)
            card_lay.setSpacing(4)

            name_lbl = QtWidgets.QLabel(score_labels.get(key, key))
            name_lbl.setStyleSheet(f"font-size:12px; color:{fg}; font-weight:bold;")
            card_lay.addWidget(name_lbl)

            score_lbl = QtWidgets.QLabel(f"{value} / {max_value}")
            score_lbl.setStyleSheet("font-size:24px; color:#0f172a; font-weight:bold;")
            card_lay.addWidget(score_lbl)

            if value == max_value:
                note = "表现稳定"
            elif value == 0:
                note = "需要重点关注"
            else:
                note = "存在扣分项"
            note_lbl = QtWidgets.QLabel(note)
            note_lbl.setStyleSheet("font-size:11px; color:#475569;")
            card_lay.addWidget(note_lbl)

            summary_grid.addWidget(card, idx // 2, idx % 2)
        content_lay.addWidget(summary_grid_wrap)

        section2 = QtWidgets.QLabel("详细计分点")
        section2.setStyleSheet("font-size:16px; font-weight:bold; color:#0f172a; padding-top:6px;")
        content_lay.addWidget(section2)

        detail_hint = QtWidgets.QLabel("以下表格列出每个计分点的通过情况、得分与具体说明。")
        detail_hint.setStyleSheet("font-size:11px; color:#64748b;")
        content_lay.addWidget(detail_hint)

        detail_table = QtWidgets.QTableWidget(len(result.score_items), 8)
        detail_table.setHorizontalHeaderLabels(["编号", "计分点", "类别", "结果", "满分", "实得", "步骤", "说明"])
        detail_table.verticalHeader().setVisible(False)
        detail_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        detail_table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        detail_table.setAlternatingRowColors(False)
        detail_table.setShowGrid(False)
        detail_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        detail_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        detail_table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        detail_table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        detail_table.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)
        detail_table.horizontalHeader().setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeToContents)
        detail_table.horizontalHeader().setSectionResizeMode(6, QtWidgets.QHeaderView.ResizeToContents)
        detail_table.horizontalHeader().setSectionResizeMode(7, QtWidgets.QHeaderView.Stretch)
        for row, item in enumerate(result.score_items):
            detail_table.setItem(row, 0, _table_item(item.code))
            detail_table.setItem(row, 1, _table_item(item.title, QtCore.Qt.AlignLeft))
            detail_table.setItem(row, 2, _table_item(item.category))
            detail_table.setItem(row, 3, _table_item(item.status))
            detail_table.setItem(row, 4, _table_item(str(item.max_score)))
            detail_table.setItem(row, 5, _table_item(str(item.earned_score)))
            detail_table.setItem(row, 6, _table_item("-" if item.step <= 0 else str(item.step)))
            detail_table.setItem(row, 7, _table_item(item.detail, QtCore.Qt.AlignLeft))
            if item.status == "通过":
                _color_row(detail_table, row, "#ecfdf5", "#166534")
            elif item.status == "未通过":
                _color_row(detail_table, row, "#fef2f2", "#991b1b")
            else:
                _color_row(detail_table, row, "#fffbeb", "#92400e")
        detail_table.setFixedHeight(
            detail_table.horizontalHeader().height()
            + max(6, detail_table.rowCount()) * 30 + 4
        )
        content_lay.addWidget(detail_table)

        section3 = QtWidgets.QLabel("过程统计")
        section3.setStyleSheet("font-size:16px; font-weight:bold; color:#0f172a; padding-top:6px;")
        content_lay.addWidget(section3)

        metric_rows = []
        for key, value in result.metrics.items():
            if isinstance(value, list):
                value_text = "、".join(str(v) for v in value if v not in (None, "")) or "-"
            else:
                value_text = "-" if value in (None, "", 0) and key == "fault_repaired_at" else str(value)
            metric_rows.append((metric_labels.get(key, key), value_text))

        metrics_wrap = QtWidgets.QFrame()
        metrics_wrap.setStyleSheet("background:transparent; border:none;")
        metrics_grid = QtWidgets.QGridLayout(metrics_wrap)
        metrics_grid.setContentsMargins(0, 0, 0, 0)
        metrics_grid.setHorizontalSpacing(10)
        metrics_grid.setVerticalSpacing(10)
        for idx, (label, value_text) in enumerate(metric_rows):
            card = QtWidgets.QFrame()
            card.setStyleSheet("background:white; border:1px solid #dbe4f0; border-radius:12px;")
            card_lay = QtWidgets.QVBoxLayout(card)
            card_lay.setContentsMargins(12, 10, 12, 10)
            card_lay.setSpacing(4)

            label_lbl = QtWidgets.QLabel(label)
            label_lbl.setStyleSheet("font-size:11px; color:#64748b; font-weight:bold;")
            card_lay.addWidget(label_lbl)

            value_lbl = QtWidgets.QLabel(value_text)
            value_lbl.setWordWrap(True)
            value_lbl.setStyleSheet("font-size:13px; color:#0f172a; font-weight:bold;")
            card_lay.addWidget(value_lbl)
            metrics_grid.addWidget(card, idx // 2, idx % 2)
        content_lay.addWidget(metrics_wrap)
        content_lay.addStretch()

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        btn_close = QtWidgets.QPushButton("关闭")
        btn_close.setStyleSheet(
            "background:#334155; color:white; font-size:12px; font-weight:bold; "
            "padding:6px 18px; border-radius:6px;"
        )
        btn_close.clicked.connect(dlg.accept)
        btn_row.addWidget(btn_close)
        lay.addLayout(btn_row)

        dlg.exec_()

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
        self.tp_btn_admin.setVisible(self.ctrl.allow_admin_shortcuts())
        if hasattr(self, '_tp_s4_quick_btn'):
            self._tp_s4_quick_btn.setVisible(self.ctrl.can_use_pt_exam_quick_record())
        if self._assessment_last_logged_step != step:
            self.ctrl.append_assessment_event('step_entered', step=step)
            self._assessment_last_logged_step = step
        if not self.ctrl.allow_admin_shortcuts():
            self._tp_admin_mode = False
            self.tp_btn_admin.setChecked(False)
            self._tp_forced_step = None
        _auto = (1 if not c.is_loop_test_complete() else
                 2 if not c.is_pt_voltage_check_complete() else
                 3 if not c.is_pt_phase_check_complete() else
                 4 if ((c.should_hold_at_step4_when_wiring_fault_unrepaired()
                        and c.has_unrepaired_wiring_fault()) or not (
                            c.pt_exam_states[1].completed and c.pt_exam_states[2].completed
                        )) else 5)
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

        # ── Fault banner update ───────────────────────────────────────
        self._update_fault_banner()

        # ── 第五步前黑盒修复门禁 ──────────────────────────────────────
        # E01/E02/E03 在 Gen2 实际合闸时触发事故弹窗；黑盒接线类故障需先在步骤1~4修复。
        fc = sim.fault_config
        progress = self.ctrl.get_test_progress_snapshot(
            step,
            getattr(self, '_pre_step5_repair_triggered', False),
        )
        if progress.block_before_step5 and not getattr(self, '_pre_step5_repair_triggered', False):
            self._pre_step5_repair_triggered = True
            if progress.should_emit_assessment_gate_event:
                self.ctrl.append_assessment_event(
                    'assessment_gate_blocked',
                    step=4,
                    scene_id=fc.scenario_id,
                    reason='unrepaired_wiring_before_step5',
                )
            if progress.should_show_blackbox_required_dialog:
                self._show_blackbox_required_dialog(fc)
        elif not self.ctrl.has_unrepaired_wiring_fault():
            self._pre_step5_repair_triggered = False

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

        result = self.ctrl.finish_assessment_session_if_ready(step)
        if result is not None:
            self._show_assessment_result_dialog(result)
            self.ctrl.mark_assessment_result_shown()

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
                allow_engine_toggle = gen.running or gen.mode == "manual"
                eng_btn.setEnabled(allow_engine_toggle)
                eng_btn.setText("停机" if gen.running else "起机")
                if gen.running:
                    eng_btn.setStyleSheet(
                        f"background:#16a34a; color:white; {_BTN}")
                elif allow_engine_toggle:
                    eng_btn.setStyleSheet(
                        f"background:#e2e8f0; color:#475569; {_BTN}")
                else:
                    eng_btn.setStyleSheet(
                        f"background:#f1f5f9; color:#94a3b8; {_BTN}")

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
                if not sl.isSliderDown():
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

    def _show_blackbox_dialog(self, target):
        """打开物理接线黑盒检查对话框（图形化 + 交互修复）。target: 'G1'|'G2'|'PT1'|'PT3'
        G1/G2/PT1/PT3 支持点击互换接线后确认修复。"""
        if not self.ctrl.can_inspect_blackbox():
            return
        self.ctrl.append_assessment_event('blackbox_opened', step=self._current_test_step(), target=target)
        sim = self.ctrl.sim_state
        fc  = sim.fault_config
        allow_repair = self.ctrl.can_repair_in_blackbox()

        # 是否存在活跃未修复故障（影响接线显示）
        blackbox_state = self.ctrl.get_blackbox_runtime_state(target)
        fault_active = blackbox_state['fault_active']

        dlg = QtWidgets.QDialog(self)
        dlg.setStyleSheet("background:#f1f5f9;")
        dlg.setFixedWidth(310)
        vlay = QtWidgets.QVBoxLayout(dlg)
        vlay.setSpacing(6)
        vlay.setContentsMargins(12, 10, 12, 10)

        widget = None          # 引用交互图组件
        repair_target = None   # 'G1'/'PT1'/'PT3' → 标记可修复目标
        initial_order = None
        initial_pri_order = None
        initial_sec_order = None

        if target in ('G1', 'G2'):
            dlg.setWindowTitle(f"发电机 {target} 机端接线检查")
            order = blackbox_state['order']
            mapping = {'A': order[0], 'B': order[1], 'C': order[2]}
            interactive = allow_repair
            repair_target = blackbox_state['repair_target']

            sub_txt = ("上方绕组（A黄/B绿/C红）→ 下方接线柱（U/V/W）"
                       + (" [可交互修复]" if interactive else " [仅查看]"))
            sub = QtWidgets.QLabel(sub_txt)
            sub.setStyleSheet("color:#64748b; font-size:10px;")
            vlay.addWidget(sub)
            widget = _GenWiringWidget(mapping, interactive=interactive)
            initial_order = widget.get_order()
            vlay.addWidget(widget, alignment=QtCore.Qt.AlignHCenter)

        elif target == 'PT1':
            dlg.setWindowTitle(
                "PT1 接线盒检查 [一次/二次侧可交互修复]" if allow_repair
                else "PT1 接线盒检查 [只读]"
            )
            pri_input_order = blackbox_state['pri_input_order']
            pri_order = blackbox_state['pri_order']
            sec_order = blackbox_state['sec_order']
            sub = QtWidgets.QLabel(
                "PT1 接线按当前物理状态绘制：一次侧与二次侧均可点击互换并分别修复。"
                if allow_repair else
                "PT1 接线按当前物理状态绘制：当前流程模式仅允许查看，不允许直接修复。"
            )
            sub.setStyleSheet("color:#64748b; font-size:10px;")
            vlay.addWidget(sub)
            widget = _PTWiringWidget(
                pri_order,
                sec_order,
                pri_input_order=pri_input_order,
                interactive_pri=allow_repair,
                interactive_sec=allow_repair,
            )
            initial_pri_order = widget.get_pri_order()
            initial_sec_order = widget.get_sec_order()
            vlay.addWidget(widget, alignment=QtCore.Qt.AlignHCenter)
            repair_target = blackbox_state['repair_target']

        elif target == 'PT3':
            dlg.setWindowTitle(
                "PT3 接线盒检查 [二次侧可交互修复]" if allow_repair
                else "PT3 接线盒检查 [只读]"
            )
            pri_input_order = blackbox_state['pri_input_order']
            pri_order = blackbox_state['pri_order']
            sec_order = blackbox_state['sec_order']
            sub = QtWidgets.QLabel(
                "上: 二次侧输出→测量端口 [可互换]  |  下: 一次侧输入←Gen2 [只读]"
                if allow_repair else
                "上: 二次侧输出→测量端口 [只读]  |  下: 一次侧输入←Gen2 [只读]"
            )
            sub.setStyleSheet("color:#64748b; font-size:10px;")
            vlay.addWidget(sub)
            widget = _PTWiringWidget(
                pri_order,
                sec_order,
                pri_input_order=pri_input_order,
                interactive_sec=allow_repair,
            )
            initial_pri_order = widget.get_pri_order()
            initial_sec_order = widget.get_sec_order()
            vlay.addWidget(widget, alignment=QtCore.Qt.AlignHCenter)
            repair_target = blackbox_state['repair_target']
            if fault_active and fc.scenario_id == 'E03':
                note = QtWidgets.QLabel("⚠ A 相极性反接：A1 正负极颠倒（a2 输出反相）")
                note.setStyleSheet(
                    "color:#c2410c; font-size:11px; font-weight:bold;"
                    " background:#fff7ed; border-radius:4px; padding:4px 6px;")
                note.setWordWrap(True)
                vlay.addWidget(note)

        # ── 反馈标签 ────────────────────────────────────────────────────
        fb_lbl = QtWidgets.QLabel("")
        fb_lbl.setWordWrap(True)
        fb_lbl.setStyleSheet("font-size:11px;")
        fb_lbl.setVisible(False)
        vlay.addWidget(fb_lbl)

        # ── 底部按钮行 ───────────────────────────────────────────────────
        btn_row = QtWidgets.QWidget()
        btn_row.setStyleSheet("background:transparent;")
        bh = QtWidgets.QHBoxLayout(btn_row)
        bh.setContentsMargins(0, 0, 0, 0)
        bh.setSpacing(6)

        # "确认修复" 按钮（仅对可修复目标显示）
        if repair_target is not None:
            def _on_confirm():
                new_order = widget.get_order() if repair_target in ('G1', 'G2') else None
                new_pri = widget.get_pri_order() if repair_target in ('PT1', 'PT3') else None
                new_sec = widget.get_sec_order() if repair_target in ('PT1', 'PT3') else None
                outcome = self.ctrl.apply_blackbox_repair_attempt(
                    repair_target,
                    step=self._current_test_step(),
                    initial_order=initial_order,
                    new_order=new_order,
                    initial_pri_order=initial_pri_order,
                    new_pri_order=new_pri,
                    initial_sec_order=initial_sec_order,
                    new_sec_order=new_sec,
                )
                fb_lbl.setText(outcome.message)
                fb_lbl.setStyleSheet(
                    f"color:{outcome.message_color}; font-size:11px; font-weight:bold;")
                if outcome.disable_repair_button:
                    btn_repair.setEnabled(False)
                fb_lbl.setVisible(True)

            btn_repair = QtWidgets.QPushButton("确认修复 ✓")
            btn_repair.setStyleSheet(
                "background:#16a34a; color:white; font-weight:bold;"
                " padding:5px 12px; border-radius:4px; font-size:12px;")
            btn_repair.clicked.connect(_on_confirm)
            bh.addWidget(btn_repair, 1)

        btn_ok = QtWidgets.QPushButton("关闭")
        btn_ok.setStyleSheet(
            "background:#334155; color:#f1f5f9; border:none;"
            " padding:5px 18px; border-radius:4px; font-size:12px;")
        btn_ok.clicked.connect(dlg.accept)
        bh.addWidget(btn_ok)
        vlay.addWidget(btn_row)
        dlg.exec_()

    def _refresh_tp_step5(self, sim):
        state   = self.ctrl.sync_test_state
        in_mode = state.started
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
