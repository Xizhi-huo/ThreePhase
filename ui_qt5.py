"""
ui_qt5.py  ──  PyQt5 主窗口（组装入口）
三相电并网仿真教学系统 · 视图层

架构
────
PowerSyncUI 通过多重继承组合两个 Mixin：

  WidgetBuilderMixin  (ui_widgets.py)
    └── 右侧控制面板、Tab3(回路测试)、Tab4(同步测试)、Tab5(PT考核) 的所有 QWidget 构建 + 槽函数

  PlotBuilderMixin    (ui_plots.py)
    └── Tab1(波形/相量) / Tab2(母排拓扑) 的 matplotlib Figure 初始化
        + 每帧渲染逻辑 (render_visuals 及各子方法)
        + MplCanvas 封装

本文件只负责：
  - 窗口框架（QMainWindow）
  - 中央布局（Tab 区 + 控制面板滚动区）
  - 调用各 Mixin 的构建入口
  - show_warning 等少量顶层接口

新增功能时：
  - 纯 Qt 控件    → 在 ui_widgets.py 中新增方法
  - 新图表/新 Tab → 在 ui_plots.py   中新增方法
  - 不需要改动本文件
"""

from PyQt5 import QtWidgets, QtCore

from ui_widgets_qt5 import WidgetBuilderMixin
from ui_plots_qt5   import PlotBuilderMixin


class PowerSyncUI(WidgetBuilderMixin, PlotBuilderMixin, QtWidgets.QMainWindow):
    """
    主窗口，组合 WidgetBuilderMixin 与 PlotBuilderMixin。
    实例化后调用 showMaximized() 即可运行。
    """

    def __init__(self, ctrl):
        super().__init__()
        self.ctrl = ctrl
        self.setWindowTitle("三相电并网仿真教学系统 (PyQt5)")
        self.resize(1400, 860)

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
        ctrl_container.setStyleSheet("QScrollArea { border: none; background: #ececec; }")
        self.ctrl_inner = QtWidgets.QWidget()
        self.ctrl_inner.setStyleSheet("background: #ececec;")
        ctrl_container.setWidget(self.ctrl_inner)
        h_layout.addWidget(ctrl_container)

        self.ctrl_layout = QtWidgets.QVBoxLayout(self.ctrl_inner)
        self.ctrl_layout.setAlignment(QtCore.Qt.AlignTop)
        self.ctrl_layout.setContentsMargins(8, 6, 8, 6)
        self.ctrl_layout.setSpacing(4)

        # ── 构建各区域 ────────────────────────────────────────────────────
        self._build_control_panel()   # ← WidgetBuilderMixin
        self._setup_tab_waveforms()   # ← PlotBuilderMixin   Tab 0
        self._setup_tab_circuit()     # ← PlotBuilderMixin   Tab 1
        self._setup_tab_loop_test()   # ← WidgetBuilderMixin Tab 2
        self._setup_tab_pt_exam()     # ← WidgetBuilderMixin Tab 3
        self._setup_tab_sync_test()   # ← WidgetBuilderMixin Tab 4
        self._init_lines()            # ← PlotBuilderMixin

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