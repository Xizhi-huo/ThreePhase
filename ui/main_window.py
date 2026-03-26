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
        self._render_pt_record_tables(p)
        self._render_pt_phase_check(p)
        self._render_sync_test(p)
        self._render_pt_exam(p)
        self._update_generator_buttons()
        self._render_test_panel(p)
        self._check_fault_detection()

        # resize/全屏动画期间跳过 canvas 重绘，防止卡死
        if self._is_resizing:
            return

        idx = self.tab_widget.currentIndex()
        if idx == 0:
            self.canvas1.draw_idle()
        elif idx == 1:
            self.canvas2.draw_idle()

    # ── 故障检测轮询（每帧 render_visuals 末尾调用）──────────────────────────
    def _check_fault_detection(self):
        """
        轮询 fault_config.detected 标志。

        策略（方案B — 延迟修复）：
          · E06 事故：立即弹出事故报告对话框（紧急处置，不能延后）
          · E01-E05 渐进故障：不弹窗，仅通过横幅提示学员继续测试；
            修复统一延迟到第五步前，由 _render_test_panel 的关卡逻辑触发。
        """
        fc = self.ctrl.sim_state.fault_config
        if not (fc.active and fc.detected and not fc.repaired):
            self._fault_dialog_open = False
            return
        if getattr(self, '_fault_dialog_open', False):
            return
        from domain.fault_scenarios import SCENARIOS
        info = SCENARIOS.get(fc.scenario_id, {})
        if info.get('danger_level') == 'accident':
            # E06 事故：立即弹出
            self._fault_dialog_open = True
            self._show_fault_repair_dialog(fc)
        # 其他故障：横幅已更新，等待步骤五关卡触发修复

    def _show_fault_repair_dialog(self, fc):
        """显示故障定位确认对话框，学员确认修复后调用 ctrl.repair_fault()。"""
        from domain.fault_scenarios import SCENARIOS
        info = SCENARIOS.get(fc.scenario_id, {})
        is_accident = (info.get('danger_level') == 'accident')

        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("⚠️ 检测到故障" if not is_accident else "💥 事故模拟")
        dlg.setModal(True)
        dlg.resize(520, 380)

        lay = QtWidgets.QVBoxLayout(dlg)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(10)

        # 标题
        title_color = "#991b1b" if not is_accident else "#7f1d1d"
        title_lbl = QtWidgets.QLabel(
            info.get('title', '故障') + (" — 事故报告" if is_accident else " — 故障定位"))
        title_lbl.setStyleSheet(
            f"font-size:14px; font-weight:bold; color:{title_color};")
        lay.addWidget(title_lbl)

        # 内容区（滚动）
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:1px solid #fca5a5; background:white;}")
        inner = QtWidgets.QWidget()
        inner_lay = QtWidgets.QVBoxLayout(inner)
        inner_lay.setContentsMargins(10, 10, 10, 10)

        # E06 事故：加入冲击电流信息
        prompt = info.get('repair_prompt', '已检测到故障，请检查并修复。')
        if is_accident and 'surge_current_kA' in fc.params:
            surge_info = (
                f"\n\n📊 事故数据：\n"
                f"  合闸相位差 = {fc.params.get('phase_diff_deg', '?')}°\n"
                f"  冲击电流峰值 ≈ {fc.params.get('surge_current_kA', '?')} kA（一次侧）\n"
                f"  （额定持续电流约 0.6A，冲击电流超出数百倍）"
            )
            prompt = prompt + surge_info

        body = QtWidgets.QLabel(prompt)
        body.setWordWrap(True)
        body.setStyleSheet("font-size:12px; color:#222;")
        body.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        inner_lay.addWidget(body)
        inner_lay.addStretch()
        scroll.setWidget(inner)
        lay.addWidget(scroll, 1)

        # 现象说明
        symptom_lbl = QtWidgets.QLabel("【学员可见异常现象】\n" + info.get('symptom', ''))
        symptom_lbl.setWordWrap(True)
        symptom_lbl.setStyleSheet(
            "font-size:11px; color:#374151; background:#fef3c7;"
            " padding:6px; border-radius:4px;")
        lay.addWidget(symptom_lbl)

        # 按钮
        btn_row = QtWidgets.QHBoxLayout()
        if not is_accident:
            btn_repair = QtWidgets.QPushButton("✅ 确认修复，继续测试")
            btn_repair.setStyleSheet(
                "background:#16a34a; color:white; font-weight:bold; padding:6px 14px;")
            btn_repair.clicked.connect(lambda: (self.ctrl.repair_fault(), dlg.accept()))
            btn_row.addWidget(btn_repair)
        else:
            btn_ok = QtWidgets.QPushButton("确认（事故已记录）")
            btn_ok.setStyleSheet(
                "background:#dc2626; color:white; font-weight:bold; padding:6px 14px;")
            btn_ok.clicked.connect(lambda: (self.ctrl.repair_fault(), dlg.accept()))
            btn_row.addWidget(btn_ok)
        lay.addLayout(btn_row)

        dlg.exec_()
        self._fault_dialog_open = False

    def show_e01_accident_dialog(self):
        """
        E01 专用致命事故弹窗：Gen2 在 Gen1 A/B 相错接未修复时尝试合闸，
        触发非同期并网事故。最高优先级模态对话框，阻断所有其他操作。
        内置修复功能，修复后可继续完成第五步。
        """
        from PyQt5.QtCore import Qt

        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("⚡ [致命事故] 非同期并网跳闸！")
        dlg.setModal(True)
        dlg.setWindowModality(Qt.ApplicationModal)
        dlg.setWindowFlags(
            Qt.Dialog
            | Qt.CustomizeWindowHint
            | Qt.WindowTitleHint
            | Qt.WindowStaysOnTopHint
        )
        dlg.resize(620, 520)

        lay = QtWidgets.QVBoxLayout(dlg)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(12)

        # ── 顶部警告横幅 ──────────────────────────────────────────────────
        banner = QtWidgets.QLabel("🚨  致命事故  🚨")
        banner.setAlignment(Qt.AlignCenter)
        banner.setStyleSheet(
            "background:#7f1d1d; color:#fef2f2; font-size:20px;"
            " font-weight:bold; padding:10px; border-radius:6px;"
        )
        lay.addWidget(banner)

        # ── 主提示文本 ────────────────────────────────────────────────────
        main_lbl = QtWidgets.QLabel(
            "发电机 Gen2 发生非同期合闸，相间短路！\n机组已紧急停机！"
        )
        main_lbl.setAlignment(Qt.AlignCenter)
        main_lbl.setWordWrap(True)
        main_lbl.setStyleSheet(
            "font-size:16px; font-weight:bold; color:#991b1b; padding:6px;"
        )
        lay.addWidget(main_lbl)

        # ── 详细事故分析（滚动区）────────────────────────────────────────
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea{border:2px solid #fca5a5; border-radius:4px; background:white;}"
        )
        inner = QtWidgets.QWidget()
        inner_lay = QtWidgets.QVBoxLayout(inner)
        inner_lay.setContentsMargins(12, 12, 12, 12)
        inner_lay.setSpacing(10)

        detail_title = QtWidgets.QLabel("【详细事故分析】")
        detail_title.setStyleSheet(
            "font-size:13px; font-weight:bold; color:#7f1d1d;"
        )
        inner_lay.addWidget(detail_title)

        fault_loc = QtWidgets.QLabel(
            "<b>故障定位：</b>Gen1 出线 A、B 相序反接。"
        )
        fault_loc.setWordWrap(True)
        fault_loc.setStyleSheet("font-size:12px; color:#1e293b;")
        inner_lay.addWidget(fault_loc)

        consequence = QtWidgets.QLabel(
            "<b>动作后果：</b>同期装置单相（C 相）条件满足误发合闸指令，"
            "导致 A、B 错相 120° 短路，产生巨大非同期冲击电流，"
            "定子绕组及大轴严重受损。"
        )
        consequence.setWordWrap(True)
        consequence.setStyleSheet("font-size:12px; color:#1e293b;")
        inner_lay.addWidget(consequence)

        symptom_box = QtWidgets.QLabel(
            "【学员可见异常现象】\n"
            "第一步：AA 回路 ∞Ω（断路），BB 回路 ∞Ω（断路），CC 回路正常。\n"
            "第三步：PT1 相序仪显示 ACB（逆序）。\n"
            "第四步：PT1_A↔PT2_B 压差 ≈ 0V，PT1_A↔PT2_A 压差 ≈ 146V。"
        )
        symptom_box.setWordWrap(True)
        symptom_box.setStyleSheet(
            "font-size:11px; color:#374151; background:#fef3c7;"
            " padding:8px; border-radius:4px;"
        )
        inner_lay.addWidget(symptom_box)

        repair_hint = QtWidgets.QLabel(
            "<b>修复方法：</b>将 Gen1 接线盒内 A 相与 B 相端子重新对调接回原位，"
            "然后重新执行同步并网操作。"
        )
        repair_hint.setWordWrap(True)
        repair_hint.setStyleSheet(
            "font-size:12px; color:#14532d; background:#dcfce7;"
            " padding:8px; border-radius:4px;"
        )
        inner_lay.addWidget(repair_hint)
        inner_lay.addStretch()

        scroll.setWidget(inner)
        lay.addWidget(scroll, 1)

        # ── 按钮区 ────────────────────────────────────────────────────────
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setSpacing(10)

        btn_repair = QtWidgets.QPushButton("🔧  修复故障，继续第五步测试")
        btn_repair.setStyleSheet(
            "background:#15803d; color:white; font-size:14px;"
            " font-weight:bold; padding:8px 20px; border-radius:4px;"
        )
        btn_repair.clicked.connect(lambda: (self.ctrl.repair_fault(), dlg.accept()))

        btn_record = QtWidgets.QPushButton("📋  确认事故已记录")
        btn_record.setStyleSheet(
            "background:#dc2626; color:white; font-size:13px;"
            " padding:8px 16px; border-radius:4px;"
        )
        btn_record.clicked.connect(dlg.accept)

        btn_row.addWidget(btn_repair)
        btn_row.addWidget(btn_record)
        lay.addLayout(btn_row)

        dlg.exec_()

    def show_e02_accident_dialog(self):
        """
        E02 专用致命事故弹窗：Gen2 在 B/C 相接线对调未修复时合闸并入带电母线，
        触发跨相短路事故。最高优先级模态对话框，阻断所有其他操作。
        内置修复功能，修复后可继续完成第五步。
        """
        from PyQt5.QtCore import Qt

        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("⚡ [致命事故] 跨相短路跳闸！")
        dlg.setModal(True)
        dlg.setWindowModality(Qt.ApplicationModal)
        dlg.setWindowFlags(
            Qt.Dialog
            | Qt.CustomizeWindowHint
            | Qt.WindowTitleHint
            | Qt.WindowStaysOnTopHint
        )
        dlg.resize(620, 520)

        lay = QtWidgets.QVBoxLayout(dlg)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(12)

        # ── 顶部警告横幅 ──────────────────────────────────────────────────
        banner = QtWidgets.QLabel("🚨  致命事故  🚨")
        banner.setAlignment(Qt.AlignCenter)
        banner.setStyleSheet(
            "background:#7f1d1d; color:#fef2f2; font-size:20px;"
            " font-weight:bold; padding:10px; border-radius:6px;"
        )
        lay.addWidget(banner)

        # ── 主提示文本 ────────────────────────────────────────────────────
        main_lbl = QtWidgets.QLabel(
            "发电机 Gen2 合闸瞬间发生跨相短路！\n机组已紧急停机！"
        )
        main_lbl.setAlignment(Qt.AlignCenter)
        main_lbl.setWordWrap(True)
        main_lbl.setStyleSheet(
            "font-size:16px; font-weight:bold; color:#991b1b; padding:6px;"
        )
        lay.addWidget(main_lbl)

        # ── 详细事故分析（滚动区）────────────────────────────────────────
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea{border:2px solid #fca5a5; border-radius:4px; background:white;}"
        )
        inner = QtWidgets.QWidget()
        inner_lay = QtWidgets.QVBoxLayout(inner)
        inner_lay.setContentsMargins(12, 12, 12, 12)
        inner_lay.setSpacing(10)

        detail_title = QtWidgets.QLabel("【详细事故分析】")
        detail_title.setStyleSheet(
            "font-size:13px; font-weight:bold; color:#7f1d1d;"
        )
        inner_lay.addWidget(detail_title)

        fault_loc = QtWidgets.QLabel(
            "<b>故障定位：</b>Gen2 出线 B、C 相序反接。"
        )
        fault_loc.setWordWrap(True)
        fault_loc.setStyleSheet("font-size:12px; color:#1e293b;")
        inner_lay.addWidget(fault_loc)

        consequence = QtWidgets.QLabel(
            "<b>动作后果：</b>同期装置以 A 相为基准判定条件满足并发出合闸指令，"
            "但 Gen2 B 端子实接 C 相绕组、C 端子实接 B 相绕组，"
            "合闸瞬间 B/C 两相与母线形成 120° 跨相短路，"
            "产生巨大冲击电流，定子绕组及大轴严重受损。"
        )
        consequence.setWordWrap(True)
        consequence.setStyleSheet("font-size:12px; color:#1e293b;")
        inner_lay.addWidget(consequence)

        symptom_box = QtWidgets.QLabel(
            "【学员可见异常现象（合闸前已有预警）】\n"
            "第一步：BB 回路 ∞Ω（断路），CC 回路 ∞Ω（断路），AA 回路正常。\n"
            "第三步：PT3 相序仪显示 ACB（逆序）。\n"
            "第四步：PT3_B↔PT2_C 压差 ≈ 0V，PT3_B↔PT2_B 压差 ≈ 146V。"
        )
        symptom_box.setWordWrap(True)
        symptom_box.setStyleSheet(
            "font-size:11px; color:#374151; background:#fef3c7;"
            " padding:8px; border-radius:4px;"
        )
        inner_lay.addWidget(symptom_box)

        repair_hint = QtWidgets.QLabel(
            "<b>修复方法：</b>将 Gen2 接线盒内 B 相与 C 相端子重新对调接回原位，"
            "然后重新执行同步并网操作。"
        )
        repair_hint.setWordWrap(True)
        repair_hint.setStyleSheet(
            "font-size:12px; color:#14532d; background:#dcfce7;"
            " padding:8px; border-radius:4px;"
        )
        inner_lay.addWidget(repair_hint)
        inner_lay.addStretch()

        scroll.setWidget(inner)
        lay.addWidget(scroll, 1)

        # ── 按钮区 ────────────────────────────────────────────────────────
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setSpacing(10)

        btn_repair = QtWidgets.QPushButton("🔧  修复故障，继续第五步测试")
        btn_repair.setStyleSheet(
            "background:#15803d; color:white; font-size:14px;"
            " font-weight:bold; padding:8px 20px; border-radius:4px;"
        )
        btn_repair.clicked.connect(lambda: (self.ctrl.repair_fault(), dlg.accept()))

        btn_record = QtWidgets.QPushButton("📋  确认事故已记录")
        btn_record.setStyleSheet(
            "background:#dc2626; color:white; font-size:13px;"
            " padding:8px 16px; border-radius:4px;"
        )
        btn_record.clicked.connect(dlg.accept)

        btn_row.addWidget(btn_repair)
        btn_row.addWidget(btn_record)
        lay.addLayout(btn_row)

        dlg.exec_()

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
