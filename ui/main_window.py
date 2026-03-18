"""
ui/main_window.py  ──  PyQt5 主窗口（组装入口）
三相电并网仿真教学系统 · 视图层

架构
────
PowerSyncUI 通过多重继承组合各个 Mixin：

  WidgetBuilderMixin  (ui/panels/control_panel.py)
    └── 右侧控制面板的所有 QWidget 构建 + 槽函数

  WaveformTabMixin    (ui/tabs/waveform_tab.py)
    └── Tab0(波形/相量) 的 matplotlib Figure 初始化 + 渲染

  CircuitTabMixin     (ui/tabs/circuit_tab.py)
    └── Tab1(母排拓扑) 的 matplotlib Figure 初始化 + 渲染

  LoopTestTabMixin      (ui/tabs/loop_test_tab.py)
    └── Tab2(回路测试) 的 QWidget 构建 + 渲染

  PtVoltageCheckTabMixin (ui/tabs/pt_voltage_check_tab.py)
    └── Tab3(PT线电压检查) 的 QWidget 构建 + 渲染

  PtPhaseCheckTabMixin (ui/tabs/pt_phase_check_tab.py)
    └── Tab4(PT相序检查) 的 QWidget 构建 + 渲染

  PtExamTabMixin      (ui/tabs/pt_exam_tab.py)
    └── Tab5(PT考核) 的 QWidget 构建 + 渲染

  SyncTestTabMixin    (ui/tabs/sync_test_tab.py)
    └── Tab6(同步测试) 的 QWidget 构建 + 渲染

本文件只负责：
  - 窗口框架（QMainWindow）
  - 中央布局（Tab 区 + 控制面板滚动区）
  - 调用各 Mixin 的构建入口
  - show_warning 等少量顶层接口
"""

from PyQt5 import QtWidgets, QtCore, QtGui

from ui.styles import APP_QSS
from ui.panels.control_panel import WidgetBuilderMixin
from ui.tabs.waveform_tab import WaveformTabMixin
from ui.tabs.circuit_tab import CircuitTabMixin
from ui.tabs.loop_test_tab import LoopTestTabMixin
from ui.tabs.pt_voltage_check_tab import PtVoltageCheckTabMixin
from ui.tabs.pt_phase_check_tab import PtPhaseCheckTabMixin
from ui.tabs.pt_exam_tab import PtExamTabMixin
from ui.tabs.sync_test_tab import SyncTestTabMixin
from ui.test_panel import TestPanelMixin


class PowerSyncUI(
    WidgetBuilderMixin,
    WaveformTabMixin,
    CircuitTabMixin,
    LoopTestTabMixin,
    PtVoltageCheckTabMixin,
    PtPhaseCheckTabMixin,
    PtExamTabMixin,
    SyncTestTabMixin,
    TestPanelMixin,
    QtWidgets.QMainWindow,
):
    """
    主窗口，组合所有 Mixin。
    实例化后调用 showMaximized() 即可运行。
    """

    def __init__(self, ctrl):
        super().__init__()
        self.ctrl = ctrl
        self.setWindowTitle("三相电并网仿真教学系统 (PyQt5)")

        # 全屏/resize 防抖：resize 期间暂停 canvas 重绘，避免卡死
        self._resize_timer = QtCore.QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(150)
        self._resize_timer.timeout.connect(self._on_resize_done)
        self._is_resizing = False

        # ── 中央 Widget + 水平主布局 ──────────────────────────────────────
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        h_layout = QtWidgets.QHBoxLayout(central)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)

        # ── 左侧：Tab 区 ──────────────────────────────────────────────────
        self.tab_widget = QtWidgets.QTabWidget()
        h_layout.addWidget(self.tab_widget, stretch=1)

        # ── 右侧：控制面板（固定宽度 + 垂直滚动）─────────────────────────
        ctrl_container = QtWidgets.QScrollArea()
        ctrl_container.setFixedWidth(520)
        ctrl_container.setWidgetResizable(True)
        ctrl_container.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        ctrl_container.setStyleSheet("QScrollArea { border: none; background: #f1f5f9; }")
        self.ctrl_inner = QtWidgets.QWidget()
        self.ctrl_inner.setStyleSheet("background: #f1f5f9;")
        ctrl_container.setWidget(self.ctrl_inner)
        h_layout.addWidget(ctrl_container)
        self.ctrl_container = ctrl_container  # 保存引用，供 test_panel 切换显示

        self.ctrl_layout = QtWidgets.QVBoxLayout(self.ctrl_inner)
        self.ctrl_layout.setAlignment(QtCore.Qt.AlignTop)
        self.ctrl_layout.setContentsMargins(8, 6, 8, 6)
        self.ctrl_layout.setSpacing(4)

        # ── 构建各区域 ────────────────────────────────────────────────────
        self._build_control_panel()           # ← WidgetBuilderMixin
        self._setup_tab_waveforms()           # ← WaveformTabMixin          Tab 0
        self._setup_tab_circuit()             # ← CircuitTabMixin           Tab 1
        self._setup_tab_loop_test()           # ← LoopTestTabMixin          Tab 2
        self._setup_tab_pt_voltage_check()    # ← PtVoltageCheckTabMixin    Tab 3
        self._setup_tab_pt_phase_check()      # ← PtPhaseCheckTabMixin      Tab 4
        self._setup_tab_pt_exam()             # ← PtExamTabMixin            Tab 5
        self._setup_tab_sync_test()           # ← SyncTestTabMixin          Tab 6
        self._init_lines()                    # ← WaveformTabMixin

        # ── 全局主题 + Tab 整理 ───────────────────────────────────────────
        QtWidgets.QApplication.instance().setStyleSheet(APP_QSS)
        self.tab_widget.setTabText(0, "📊 实时波形与同期表")
        # 步骤 Tab 2-6 由测试模式按需显示，初始隐藏
        for _i in range(2, 7):
            try:
                self.tab_widget.setTabVisible(_i, False)
            except AttributeError:
                pass  # Qt < 5.15 fallback: 无 setTabVisible

        # ── 竖向测试控制条（测试模式时替换右侧控制台）───────────────────
        self._setup_test_panel()              # ← TestPanelMixin
        h_layout.addWidget(self.test_panel)   # 加入主布局（初始隐藏）

    # ── resize 防抖回调 ─────────────────────────────────────────────────────
    def resizeEvent(self, event: QtGui.QResizeEvent):
        self._is_resizing = True
        self._resize_timer.start()
        super().resizeEvent(event)

    def _on_resize_done(self):
        self._is_resizing = False

    # ── 渲染主入口（每帧由 QTimer 驱动）────────────────────────────────────
    def render_visuals(self, rs):
        p   = rs
        deg = rs.fixed_deg
        d   = rs.plot_data
        bus_a_display = rs.bus_amp if rs.bus_live else 0.0

        self._render_waveforms(d, deg, bus_a_display)
        self._render_phasors(d, bus_a_display)
        self._render_ct_readings(p)
        self._render_bus_status(p)
        self._render_breakers(p)
        self._render_grounding_and_pt(p)
        self._render_multimeter(p)
        # _render_circuit_quick_record 已移除（记录功能集中在右侧测试条）
        self._render_loop_test(p)
        self._render_pt_voltage_check(p)
        self._render_pt_phase_check(p)
        self._render_sync_test(p)
        self._render_pt_exam(p)
        self._update_generator_buttons()
        self._render_test_panel(p)

        # resize/全屏动画期间跳过 canvas 重绘，防止卡死
        if self._is_resizing:
            return

        idx = self.tab_widget.currentIndex()
        if idx == 0:
            self.canvas1.draw_idle()
        elif idx == 1:
            self.canvas2.draw_idle()

    # ── 对外接口（ctrl 调用）────────────────────────────────────────────────
    def show_warning(self, title: str, message: str):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setModal(True)
        dialog.resize(560, 360)

        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        title_lbl = QtWidgets.QLabel(title)
        title_lbl.setStyleSheet("font-size:14px; font-weight:bold; color:#8b0000;")
        layout.addWidget(title_lbl)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #cccccc; background: white; }")

        content = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(10, 10, 10, 10)

        msg_lbl = QtWidgets.QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        msg_lbl.setStyleSheet("font-size:12px; color:#222222;")
        msg_lbl.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        content_layout.addWidget(msg_lbl)
        content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok)
        btn_box.accepted.connect(dialog.accept)
        layout.addWidget(btn_box)

        dialog.exec_()
