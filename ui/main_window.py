"""
ui/main_window.py  â”€â”€  PyQt5 ä¸»çª—å£ï¼ˆç»„è£…å…¥å£ï¼‰
ä¸‰ç›¸ç”µå¹¶ç½‘ä»¿çœŸæ•™å­¦ç³»ç»Ÿ Â· è§†å›¾å±‚

æž¶æž„
â”€â”€â”€â”€
PowerSyncUI é€šè¿‡å¤šé‡ç»§æ‰¿ç»„åˆå„ä¸ª Mixinï¼š

  WidgetBuilderMixin  (ui/panels/control_panel.py)
    â””â”€â”€ å³ä¾§æŽ§åˆ¶é¢æ¿çš„æ‰€æœ‰ QWidget æž„å»º + æ§½å‡½æ•°

  WaveformTabMixin    (ui/tabs/waveform_tab.py)
    â””â”€â”€ Tab0(æ³¢å½¢/ç›¸é‡) çš„ matplotlib Figure åˆå§‹åŒ– + æ¸²æŸ“

  CircuitTabMixin     (ui/tabs/circuit_tab.py)
    â””â”€â”€ Tab1(æ¯æŽ’æ‹“æ‰‘) çš„ matplotlib Figure åˆå§‹åŒ– + æ¸²æŸ“

  LoopTestTabMixin      (ui/tabs/loop_test_tab.py)
    â””â”€â”€ Tab2(å›žè·¯æµ‹è¯•) çš„ QWidget æž„å»º + æ¸²æŸ“

  PtVoltageCheckTabMixin (ui/tabs/pt_voltage_check_tab.py)
    â””â”€â”€ Tab3(PTçº¿ç”µåŽ‹æ£€æŸ¥) çš„ QWidget æž„å»º + æ¸²æŸ“

  PtPhaseCheckTabMixin (ui/tabs/pt_phase_check_tab.py)
    â””â”€â”€ Tab4(PTç›¸åºæ£€æŸ¥) çš„ QWidget æž„å»º + æ¸²æŸ“

  PtExamTabMixin      (ui/tabs/pt_exam_tab.py)
    â””â”€â”€ Tab5(PTè€ƒæ ¸) çš„ QWidget æž„å»º + æ¸²æŸ“

  SyncTestTabMixin    (ui/tabs/sync_test_tab.py)
    â””â”€â”€ Tab6(åŒæ­¥æµ‹è¯•) çš„ QWidget æž„å»º + æ¸²æŸ“

æœ¬æ–‡ä»¶åªè´Ÿè´£ï¼š
  - çª—å£æ¡†æž¶ï¼ˆQMainWindowï¼‰
  - ä¸­å¤®å¸ƒå±€ï¼ˆTab åŒº + æŽ§åˆ¶é¢æ¿æ»šåŠ¨åŒºï¼‰
  - è°ƒç”¨å„ Mixin çš„æž„å»ºå…¥å£
  - show_warning ç­‰å°‘é‡é¡¶å±‚æŽ¥å£
"""

from PyQt5 import QtWidgets, QtCore, QtGui

from ui.styles import apply_app_theme
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
    ä¸»çª—å£ï¼Œç»„åˆæ‰€æœ‰ Mixinã€‚
    å®žä¾‹åŒ–åŽè°ƒç”¨ showMaximized() å³å¯è¿è¡Œã€‚
    """

    def __init__(self, ctrl):
        super().__init__()
        self.ctrl = ctrl
        self.setWindowTitle("ä¸‰ç›¸ç”µå¹¶ç½‘ä»¿çœŸæ•™å­¦ç³»ç»Ÿ (PyQt5)")

        # å…¨å±/resize é˜²æŠ–ï¼šresize æœŸé—´æš‚åœ canvas é‡ç»˜ï¼Œé¿å…å¡æ­»
        self._resize_timer = QtCore.QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(150)
        self._resize_timer.timeout.connect(self._on_resize_done)
        self._is_resizing = False

        # â”€â”€ ä¸­å¤® Widget + æ°´å¹³ä¸»å¸ƒå±€ â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        central = QtWidgets.QWidget()
        central.setObjectName("appRoot")
        self.setCentralWidget(central)
        h_layout = QtWidgets.QHBoxLayout(central)
        h_layout.setContentsMargins(12, 12, 12, 12)
        h_layout.setSpacing(12)

        # â”€â”€ å·¦ä¾§ï¼šTab åŒº â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self.tab_widget = QtWidgets.QTabWidget()
        self.tab_widget.setObjectName("mainTabWidget")
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.tabBar().setExpanding(False)
        self.tab_widget.tabBar().setElideMode(QtCore.Qt.ElideRight)
        h_layout.addWidget(self.tab_widget, stretch=1)

        # â”€â”€ å³ä¾§ï¼šæŽ§åˆ¶é¢æ¿ï¼ˆå›ºå®šå®½åº¦ + åž‚ç›´æ»šåŠ¨ï¼‰â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        ctrl_container = QtWidgets.QScrollArea()
        ctrl_container.setObjectName("controlSidebarScroll")
        ctrl_container.setFixedWidth(520)
        ctrl_container.setWidgetResizable(True)
        ctrl_container.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.ctrl_inner = QtWidgets.QWidget()
        self.ctrl_inner.setObjectName("controlSidebar")
        self.ctrl_inner.setProperty("panelSurface", True)
        ctrl_container.setWidget(self.ctrl_inner)
        h_layout.addWidget(ctrl_container)
        self.ctrl_container = ctrl_container  # ä¿å­˜å¼•ç”¨ï¼Œä¾› test_panel åˆ‡æ¢æ˜¾ç¤º

        self.ctrl_layout = QtWidgets.QVBoxLayout(self.ctrl_inner)
        self.ctrl_layout.setAlignment(QtCore.Qt.AlignTop)
        self.ctrl_layout.setContentsMargins(0, 0, 0, 0)
        self.ctrl_layout.setSpacing(8)

        # â”€â”€ æž„å»ºå„åŒºåŸŸ â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self._build_control_panel()           # â† WidgetBuilderMixin
        self._setup_tab_waveforms()           # â† WaveformTabMixin          Tab 0
        self._setup_tab_circuit()             # â† CircuitTabMixin           Tab 1
        self._setup_tab_loop_test()           # â† LoopTestTabMixin          Tab 2
        self._setup_tab_pt_voltage_check()    # â† PtVoltageCheckTabMixin    Tab 3
        self._setup_tab_pt_phase_check()      # â† PtPhaseCheckTabMixin      Tab 4
        self._setup_tab_pt_exam()             # â† PtExamTabMixin            Tab 5
        self._setup_tab_sync_test()           # â† SyncTestTabMixin          Tab 6
        self._init_lines()                    # â† WaveformTabMixin

        # â”€â”€ å…¨å±€ä¸»é¢˜ + Tab æ•´ç† â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        apply_app_theme(QtWidgets.QApplication.instance())
        self.tab_widget.setTabText(0, "ðŸ“Š å®žæ—¶æ³¢å½¢ä¸ŽåŒæœŸè¡¨")
        # æ­¥éª¤ Tab 2-6 ç”±æµ‹è¯•æ¨¡å¼æŒ‰éœ€æ˜¾ç¤ºï¼Œåˆå§‹éšè—
        for _i in range(2, 7):
            try:
                self.tab_widget.setTabVisible(_i, False)
            except AttributeError:
                pass  # Qt < 5.15 fallback: æ—  setTabVisible

        # â”€â”€ ç«–å‘æµ‹è¯•æŽ§åˆ¶æ¡ï¼ˆæµ‹è¯•æ¨¡å¼æ—¶æ›¿æ¢å³ä¾§æŽ§åˆ¶å°ï¼‰â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self._setup_test_panel()              # â† TestPanelMixin
        h_layout.addWidget(self.test_panel)   # åŠ å…¥ä¸»å¸ƒå±€ï¼ˆåˆå§‹éšè—ï¼‰

    # â”€â”€ resize é˜²æŠ–å›žè°ƒ â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def resizeEvent(self, event: QtGui.QResizeEvent):
        self._is_resizing = True
        self._resize_timer.start()
        super().resizeEvent(event)

    def _on_resize_done(self):
        self._is_resizing = False

    def _consume_controller_ui_requests(self):
        tab_index = self.ctrl.consume_requested_ui_tab()
        if tab_index is not None:
            self.tab_widget.setCurrentIndex(tab_index)

        ratio_updates = self.ctrl.consume_requested_pt_ratio_row_updates()
        if not ratio_updates:
            return

        rows = getattr(self, '_tp_s2_ratio_rows', {})
        for ratio_attr, (pri_value, sec_value) in ratio_updates.items():
            row = rows.get(ratio_attr)
            if not row:
                continue
            pri_spin, sec_spin, ratio_lbl = row
            pri_spin.blockSignals(True)
            sec_spin.blockSignals(True)
            pri_spin.setValue(pri_value)
            sec_spin.setValue(sec_value)
            pri_spin.blockSignals(False)
            sec_spin.blockSignals(False)
            ratio_lbl.setText(f"{pri_value / max(1, sec_value):.2f}")

    # â”€â”€ æ¸²æŸ“ä¸»å…¥å£ï¼ˆæ¯å¸§ç”± QTimer é©±åŠ¨ï¼‰â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def render_visuals(self, rs):
        self._consume_controller_ui_requests()
        p   = rs
        deg = rs.fixed_deg
        d   = rs.plot_data
        bus_a_display = rs.bus_amp if rs.bus_live else 0.0

        self._render_waveforms(d, deg, bus_a_display)
        self._render_phasors(d, bus_a_display)
        self._render_waveform_dashboard(rs)
        self._render_ct_readings(p)
        self._render_bus_status(p)
        self._render_breakers(p)
        self._render_gen_wire_visibility()
        self._render_grounding_and_pt(p)
        self._render_multimeter(p)
        # _render_circuit_quick_record å·²ç§»é™¤ï¼ˆè®°å½•åŠŸèƒ½é›†ä¸­åœ¨å³ä¾§æµ‹è¯•æ¡ï¼‰
        self._render_loop_test(p)
        self._render_pt_voltage_check(p)
        self._render_pt_record_tables(p)
        self._render_pt_phase_check(p)
        self._render_sync_test(p)
        self._render_pt_exam(p)
        self._update_generator_buttons()
        self._render_test_panel(p)
        self._check_fault_detection()

        # resize/å…¨å±åŠ¨ç”»æœŸé—´è·³è¿‡ canvas é‡ç»˜ï¼Œé˜²æ­¢å¡æ­»
        if self._is_resizing:
            return

        idx = self.tab_widget.currentIndex()
        if idx == 0:
            self._draw_waveform_canvases()
        elif idx == 1:
            self.canvas2.draw_idle()

    # â”€â”€ æ•…éšœæ£€æµ‹è½®è¯¢ï¼ˆæ¯å¸§ render_visuals æœ«å°¾è°ƒç”¨ï¼‰â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _check_fault_detection(self):
        """
        è½®è¯¢ fault_config.detected æ ‡å¿—ã€‚

        ç­–ç•¥ï¼š
          Â· accident åœºæ™¯ï¼šä¸åœ¨æ£€æµ‹é˜¶æ®µæå‰å¼¹çª—ï¼Œç»Ÿä¸€ä¿ç•™åˆ°æ­¥éª¤äº”çœŸå®žåˆé—¸äº‹æ•…é€šé“
          Â· recoverable åœºæ™¯ï¼šä»…é€šè¿‡æ¨ªå¹…æç¤ºå­¦å‘˜ç»§ç»­æµ‹è¯•ï¼›
            ä¿®å¤ç»Ÿä¸€å»¶è¿Ÿåˆ°ç¬¬äº”æ­¥å‰ï¼Œç”±æµ‹è¯•é¢æ¿é—¨ç¦é€»è¾‘è§¦å‘ã€‚
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
            return
        # å…¶ä»–æ•…éšœï¼šæ¨ªå¹…å·²æ›´æ–°ï¼Œç­‰å¾…æ­¥éª¤äº”å…³å¡è§¦å‘ä¿®å¤

    def _show_blackbox_required_dialog(self, fc):
        """æ­¥éª¤äº”å‰å‘çŽ°é»‘ç›’æŽ¥çº¿æœªä¿®å¤æ—¶ï¼Œæç¤ºå­¦å‘˜å…ˆå›žåˆ°é»‘ç›’ä¸­å®Œæˆç‰©ç†ä¿®å¤ã€‚"""
        from domain.fault_scenarios import SCENARIOS

        info = SCENARIOS.get(fc.scenario_id, {})
        dlg = QtWidgets.QDialog(self)
        is_assessment = getattr(self.ctrl, "is_assessment_mode", lambda: False)()
        dlg.setWindowTitle("âš ï¸ å½“å‰æµç¨‹å°šæœªé—­çŽ¯" if is_assessment else "âš ï¸ ä»æœ‰æŽ¥çº¿æ•…éšœæœªä¿®å¤")
        dlg.setModal(True)
        dlg.resize(500, 300)

        lay = QtWidgets.QVBoxLayout(dlg)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(10)

        if is_assessment:
            title_text = "å½“å‰è€ƒæ ¸å°šæœªé—­çŽ¯"
        else:
            title_text = info.get('title', 'æ•…éšœ') + " â€” éœ€å…ˆå®Œæˆé»‘ç›’ä¿®å¤"
        title_lbl = QtWidgets.QLabel(title_text)
        title_lbl.setStyleSheet("font-size:14px; font-weight:bold; color:#991b1b;")
        lay.addWidget(title_lbl)

        if is_assessment:
            hint_text = (
                "å½“å‰è€ƒæ ¸ä»æœªæ»¡è¶³ç»“æŸæ¡ä»¶ï¼Œæš‚ä¸èƒ½ç»§ç»­åŽç»­æµç¨‹ã€‚\n\n"
                "è¯·æ ¹æ®å‰å››æ­¥å·²èŽ·å¾—çš„æµ‹é‡ç»“æžœç»§ç»­æŽ’æŸ¥å¹¶å®Œæˆé—­çŽ¯ã€‚"
                "å¦‚éœ€è¿›ä¸€æ­¥ç¡®è®¤ï¼Œå¯è¿›å…¥é»‘ç›’æ£€æŸ¥ï¼Œä½†ç³»ç»Ÿä¸ä¼šæä¾›å…·ä½“æ•…éšœä½ç½®æç¤ºã€‚"
            )
        else:
            hint_text = (
                "å½“å‰ä»å­˜åœ¨æœªæ¢å¤çš„ç‰©ç†æŽ¥çº¿é”™è¯¯ï¼Œä¸èƒ½è¿›å…¥ç¬¬äº”æ­¥ã€åŒæ­¥åŠŸèƒ½æµ‹è¯•ã€‘ã€‚\n\n"
                "è¯·å…ˆå›žåˆ°å½“å‰æµç¨‹ä¸­çš„é»‘ç›’æ£€æŸ¥åŒºï¼Œå®Œæˆç›¸å…³æŽ¥çº¿ä¿®å¤ã€‚"
                "åªæœ‰å½“ç›¸å…³æŽ¥çº¿å…¨éƒ¨æ¢å¤ä¸ºæ­£ç¡®é¡ºåºåŽï¼Œç³»ç»Ÿæ‰ä¼šè‡ªåŠ¨å…è®¸è¿›å…¥ç¬¬äº”æ­¥ã€‚"
            )
        hint = QtWidgets.QLabel(hint_text)
        hint.setWordWrap(True)
        hint.setStyleSheet(
            "font-size:12px; color:#1f2937; background:#fff7ed;"
            " border:1px solid #fdba74; border-radius:4px; padding:8px;")
        lay.addWidget(hint)

        if not is_assessment:
            symptom_lbl = QtWidgets.QLabel("ã€å½“å‰å·²è®°å½•çš„å¼‚å¸¸çŽ°è±¡ã€‘\n" + info.get('symptom', ''))
            symptom_lbl.setWordWrap(True)
            symptom_lbl.setStyleSheet(
                "font-size:11px; color:#374151; background:#fef3c7;"
                " padding:6px; border-radius:4px;")
            lay.addWidget(symptom_lbl)

        btn_ok = QtWidgets.QPushButton("çŸ¥é“äº†")
        btn_ok.setStyleSheet(
            "background:#334155; color:white; font-weight:bold; padding:6px 14px;")
        btn_ok.clicked.connect(dlg.accept)
        lay.addWidget(btn_ok, alignment=QtCore.Qt.AlignRight)

        dlg.exec_()

    def _show_accident_dialog(
        self,
        *,
        window_title: str,
        main_text: str,
        fault_loc_html: str,
        consequence_html: str,
        symptom_text: str,
        repair_hint_html: str,
        repair_source: str,
        dialog_height: int = 520,
    ):
        from PyQt5.QtCore import Qt

        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle(window_title)
        dlg.setModal(True)
        dlg.setWindowModality(Qt.ApplicationModal)
        dlg.setWindowFlags(
            Qt.Dialog
            | Qt.CustomizeWindowHint
            | Qt.WindowTitleHint
            | Qt.WindowStaysOnTopHint
        )
        dlg.resize(620, dialog_height)

        lay = QtWidgets.QVBoxLayout(dlg)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(12)

        banner = QtWidgets.QLabel("ðŸš¨  è‡´å‘½äº‹æ•…  ðŸš¨")
        banner.setAlignment(Qt.AlignCenter)
        banner.setStyleSheet(
            "background:#7f1d1d; color:#fef2f2; font-size:20px;"
            " font-weight:bold; padding:10px; border-radius:6px;"
        )
        lay.addWidget(banner)

        main_lbl = QtWidgets.QLabel(main_text)
        main_lbl.setAlignment(Qt.AlignCenter)
        main_lbl.setWordWrap(True)
        main_lbl.setStyleSheet(
            "font-size:16px; font-weight:bold; color:#991b1b; padding:6px;"
        )
        lay.addWidget(main_lbl)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea{border:2px solid #fca5a5; border-radius:4px; background:white;}"
        )
        inner = QtWidgets.QWidget()
        inner_lay = QtWidgets.QVBoxLayout(inner)
        inner_lay.setContentsMargins(12, 12, 12, 12)
        inner_lay.setSpacing(10)

        detail_title = QtWidgets.QLabel("ã€è¯¦ç»†äº‹æ•…åˆ†æžã€‘")
        detail_title.setStyleSheet(
            "font-size:13px; font-weight:bold; color:#7f1d1d;"
        )
        inner_lay.addWidget(detail_title)

        fault_loc = QtWidgets.QLabel(fault_loc_html)
        fault_loc.setWordWrap(True)
        fault_loc.setStyleSheet("font-size:12px; color:#1e293b;")
        inner_lay.addWidget(fault_loc)

        consequence = QtWidgets.QLabel(consequence_html)
        consequence.setWordWrap(True)
        consequence.setStyleSheet("font-size:12px; color:#1e293b;")
        inner_lay.addWidget(consequence)

        symptom_box = QtWidgets.QLabel(symptom_text)
        symptom_box.setWordWrap(True)
        symptom_box.setStyleSheet(
            "font-size:11px; color:#374151; background:#fef3c7;"
            " padding:8px; border-radius:4px;"
        )
        inner_lay.addWidget(symptom_box)

        repair_hint = QtWidgets.QLabel(repair_hint_html)
        repair_hint.setWordWrap(True)
        repair_hint.setStyleSheet(
            "font-size:12px; color:#14532d; background:#dcfce7;"
            " padding:8px; border-radius:4px;"
        )
        inner_lay.addWidget(repair_hint)
        inner_lay.addStretch()

        scroll.setWidget(inner)
        lay.addWidget(scroll, 1)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setSpacing(10)

        btn_repair = QtWidgets.QPushButton("ðŸ”§  ä¿®å¤æ•…éšœï¼Œç»§ç»­ç¬¬äº”æ­¥æµ‹è¯•")
        btn_repair.setStyleSheet(
            "background:#15803d; color:white; font-size:14px;"
            " font-weight:bold; padding:8px 20px; border-radius:4px;"
        )
        btn_repair.clicked.connect(
            lambda: (self.ctrl.repair_fault(step=5, source=repair_source), dlg.accept())
        )

        btn_record = QtWidgets.QPushButton("ðŸ“‹  ç¡®è®¤äº‹æ•…å·²è®°å½•")
        btn_record.setStyleSheet(
            "background:#dc2626; color:white; font-size:13px;"
            " padding:8px 16px; border-radius:4px;"
        )
        btn_record.clicked.connect(dlg.accept)

        btn_row.addWidget(btn_repair)
        btn_row.addWidget(btn_record)
        lay.addLayout(btn_row)

        dlg.exec_()

    def show_e01_accident_dialog(self):
        self._show_accident_dialog(
            window_title="âš¡ [è‡´å‘½äº‹æ•…] éžåŒæœŸå¹¶ç½‘è·³é—¸ï¼",
            main_text="å‘ç”µæœº Gen2 å‘ç”ŸéžåŒæœŸåˆé—¸ï¼Œç›¸é—´çŸ­è·¯ï¼\næœºç»„å·²ç´§æ€¥åœæœºï¼",
            fault_loc_html="<b>æ•…éšœå®šä½ï¼š</b>Gen1 å‡ºçº¿ Aã€B ç›¸åºåæŽ¥ã€‚",
            consequence_html=(
                "<b>åŠ¨ä½œåŽæžœï¼š</b>åŒæœŸè£…ç½®å•ç›¸ï¼ˆC ç›¸ï¼‰æ¡ä»¶æ»¡è¶³è¯¯å‘åˆé—¸æŒ‡ä»¤ï¼Œ"
                "å¯¼è‡´ Aã€B é”™ç›¸ 120Â° çŸ­è·¯ï¼Œäº§ç”Ÿå·¨å¤§éžåŒæœŸå†²å‡»ç”µæµï¼Œ"
                "å®šå­ç»•ç»„åŠå¤§è½´ä¸¥é‡å—æŸã€‚"
            ),
            symptom_text=(
                "ã€å­¦å‘˜å¯è§å¼‚å¸¸çŽ°è±¡ã€‘\n"
                "ç¬¬ä¸€æ­¥ï¼šAA å›žè·¯ âˆžÎ©ï¼ˆæ–­è·¯ï¼‰ï¼ŒBB å›žè·¯ âˆžÎ©ï¼ˆæ–­è·¯ï¼‰ï¼ŒCC å›žè·¯æ­£å¸¸ã€‚\n"
                "ç¬¬ä¸‰æ­¥ï¼šPT1 ç›¸åºä»ªæ˜¾ç¤ºååºã€‚\n"
                "ç¬¬å››æ­¥ï¼šPT1_Aâ†”PT2_B åŽ‹å·® â‰ˆ 0Vï¼ŒPT1_Aâ†”PT2_A åŽ‹å·® â‰ˆ 146Vã€‚"
            ),
            repair_hint_html=(
                "<b>ä¿®å¤æ–¹æ³•ï¼š</b>å°† Gen1 æŽ¥çº¿ç›’å†… A ç›¸ä¸Ž B ç›¸ç«¯å­é‡æ–°å¯¹è°ƒæŽ¥å›žåŽŸä½ï¼Œ"
                "ç„¶åŽé‡æ–°æ‰§è¡ŒåŒæ­¥å¹¶ç½‘æ“ä½œã€‚"
            ),
            repair_source="E01_accident_dialog",
        )

    def show_e02_accident_dialog(self):
        self._show_accident_dialog(
            window_title="âš¡ [è‡´å‘½äº‹æ•…] è·¨ç›¸çŸ­è·¯è·³é—¸ï¼",
            main_text="å‘ç”µæœº Gen2 åˆé—¸çž¬é—´å‘ç”Ÿè·¨ç›¸çŸ­è·¯ï¼\næœºç»„å·²ç´§æ€¥åœæœºï¼",
            fault_loc_html="<b>æ•…éšœå®šä½ï¼š</b>Gen2 å‡ºçº¿ Bã€C ç›¸åºåæŽ¥ã€‚",
            consequence_html=(
                "<b>åŠ¨ä½œåŽæžœï¼š</b>åŒæœŸè£…ç½®ä»¥ A ç›¸ä¸ºåŸºå‡†åˆ¤å®šæ¡ä»¶æ»¡è¶³å¹¶å‘å‡ºåˆé—¸æŒ‡ä»¤ï¼Œ"
                "ä½† Gen2 B ç«¯å­å®žæŽ¥ C ç›¸ç»•ç»„ã€C ç«¯å­å®žæŽ¥ B ç›¸ç»•ç»„ï¼Œ"
                "åˆé—¸çž¬é—´ B/C ä¸¤ç›¸ä¸Žæ¯çº¿å½¢æˆ 120Â° è·¨ç›¸çŸ­è·¯ï¼Œ"
                "äº§ç”Ÿå·¨å¤§å†²å‡»ç”µæµï¼Œå®šå­ç»•ç»„åŠå¤§è½´ä¸¥é‡å—æŸã€‚"
            ),
            symptom_text=(
                "ã€å­¦å‘˜å¯è§å¼‚å¸¸çŽ°è±¡ï¼ˆåˆé—¸å‰å·²æœ‰é¢„è­¦ï¼‰ã€‘\n"
                "ç¬¬ä¸€æ­¥ï¼šBB å›žè·¯ âˆžÎ©ï¼ˆæ–­è·¯ï¼‰ï¼ŒCC å›žè·¯ âˆžÎ©ï¼ˆæ–­è·¯ï¼‰ï¼ŒAA å›žè·¯æ­£å¸¸ã€‚\n"
                "ç¬¬ä¸‰æ­¥ï¼šPT3 ç›¸åºä»ªæ˜¾ç¤ºååºã€‚\n"
                "ç¬¬å››æ­¥ï¼šPT3_Bâ†”PT2_C åŽ‹å·® â‰ˆ 0Vï¼ŒPT3_Bâ†”PT2_B åŽ‹å·® â‰ˆ 146Vã€‚"
            ),
            repair_hint_html=(
                "<b>ä¿®å¤æ–¹æ³•ï¼š</b>å°† Gen2 æŽ¥çº¿ç›’å†… B ç›¸ä¸Ž C ç›¸ç«¯å­é‡æ–°å¯¹è°ƒæŽ¥å›žåŽŸä½ï¼Œ"
                "ç„¶åŽé‡æ–°æ‰§è¡ŒåŒæ­¥å¹¶ç½‘æ“ä½œã€‚"
            ),
            repair_source="E02_accident_dialog",
        )

    def show_e03_accident_dialog(self):
        self._show_accident_dialog(
            window_title="âš¡ [è‡´å‘½äº‹æ•…] PT3æžæ€§é”™è¯¯å¯¼è‡´éžåŒæœŸåˆé—¸ï¼",
            main_text=(
                "PT3 A ç›¸æžæ€§åæŽ¥å¯¼è‡´åŒæœŸè£…ç½®ç›¸è§’åŸºå‡†é”™è¯¯ï¼\n"
                "Gen2 ä»¥ 180Â° åç›¸ä½ç½®åˆé—¸ï¼Œå‘ç”ŸéžåŒæœŸå†²å‡»ï¼æœºç»„å·²ç´§æ€¥åœæœºï¼"
            ),
            fault_loc_html=(
                "<b>æ•…éšœå®šä½ï¼š</b>PT3 A ç›¸äºŒæ¬¡ç«¯å­ K/k æžæ€§åæŽ¥ï¼Œå®žé™…è¾“å‡º âˆ’V<sub>A</sub>ã€‚"
            ),
            consequence_html=(
                "<b>åŠ¨ä½œåŽæžœï¼š</b>åŒæœŸè£…ç½®ä»¥ PT3 A ç›¸ä½œä¸ºç›¸è§’å‚è€ƒï¼Œæžæ€§åæŽ¥ä½¿å‚è€ƒè§’åå·® 180Â°ã€‚"
                "è‡ªåŠ¨åŒæœŸå°† Gen2 é©±å‘åç›¸ä½ç½®åŽè¯¯åˆ¤ã€Œç›¸è§’å·® = 0Â°ã€å‘å‡ºåˆé—¸æŒ‡ä»¤ï¼Œ"
                "åˆé—¸çž¬é—´ Gen2 ä¸Žæ¯çº¿å®žé™…ç›¸ä½å·®çº¦ 180Â°ï¼Œäº§ç”Ÿå·¨å¤§éžåŒæœŸå†²å‡»ç”µæµï¼Œ"
                "å®šå­ç»•ç»„åŠå¤§è½´ä¸¥é‡å—æŸã€‚"
            ),
            symptom_text=(
                "ã€å­¦å‘˜å¯è§å¼‚å¸¸çŽ°è±¡ï¼ˆåˆé—¸å‰å·²æœ‰é¢„è­¦ï¼‰ã€‘\n"
                "ç¬¬äºŒæ­¥ï¼šPT3_AB â‰ˆ 106Vï¼ˆåº”â‰ˆ184Vï¼Œæ ‡çº¢å¼‚å¸¸ï¼‰ï¼›PT3_CA â‰ˆ 106Vï¼ˆæ ‡çº¢å¼‚å¸¸ï¼‰ã€‚\n"
                "ç¬¬ä¸‰æ­¥ï¼šPT3 ç›¸åºä»ªæ˜¾ç¤ºã€Œæ•…éšœ/ä¸å¹³è¡¡ã€ï¼ˆA ç›¸æžæ€§åç›¸ï¼‰ã€‚\n"
                "ç¬¬å››æ­¥ï¼šPT3_Aâ†”PT2_A â‰ˆ 166Vï¼ˆåº”â‰ˆ0Vï¼‰ï¼ŒPT3_Aâ†”PT2_B/C â‰ˆ 92Vï¼ˆåº”â‰ˆ146Vï¼‰ã€‚\n"
                "ç¬¬äº”æ­¥ï¼šåŒæ­¥ä»ªç›¸ä½å·®æŒç»­æ˜¾ç¤ºçº¦ 180Â°ï¼Œä»²è£å™¨æŠ¥ PT3 Aç›¸æžæ€§å¼‚å¸¸ã€‚"
            ),
            repair_hint_html=(
                "<b>ä¿®å¤æ–¹æ³•ï¼š</b>å°† PT3 A ç›¸äºŒæ¬¡ç«¯å­ K/k å¯¹è°ƒï¼Œæ¢å¤æ­£ç¡®æžæ€§åŽ"
                "é‡æ–°æ‰§è¡ŒåŒæ­¥å¹¶ç½‘æ“ä½œã€‚"
            ),
            repair_source="E03_accident_dialog",
            dialog_height=540,
        )


    # â”€â”€ å¯¹å¤–æŽ¥å£ï¼ˆctrl è°ƒç”¨ï¼‰â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def show_warning(self, title: str, message: str):
        self._consume_controller_ui_requests()
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
