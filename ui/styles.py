"""
ui/styles.py
浅色主题的全局样式入口。

策略：
1. 以自定义 QSS 为主，确保当前项目可控演进。
2. 若运行环境安装了 qdarkstyle，则尝试加载其 light 基底后叠加本项目样式；
   若不可用，自动回退为纯自定义主题，不影响运行。
"""

LIGHT_THEME = {
    "bg_app": "#f4f7fb",
    "bg_panel": "#eef3f9",
    "bg_surface": "#ffffff",
    "bg_surface_alt": "#f8fbff",
    "bg_hover": "#f1f6fd",
    "bg_selected": "#e6f0ff",
    "text_main": "#0f172a",
    "text_body": "#1e293b",
    "text_muted": "#64748b",
    "text_soft": "#94a3b8",
    "border": "#dbe4f0",
    "border_strong": "#c7d4e5",
    "primary": "#1d4ed8",
    "primary_hover": "#1e40af",
    "primary_soft": "#dbeafe",
    "success": "#15803d",
    "success_soft": "#dcfce7",
    "warning": "#b45309",
    "warning_soft": "#fff7ed",
    "danger": "#dc2626",
    "danger_soft": "#fef2f2",
    "info": "#2563eb",
    "info_soft": "#eff6ff",
    "shadow": "rgba(15, 23, 42, 0.08)",
}

_QSS_TEMPLATE = """
QMainWindow {{
    background: {bg_app};
    color: {text_body};
}}

QWidget#appRoot,
QWidget[panelSurface="true"] {{
    background: {bg_app};
    color: {text_body};
    font-size: 13px;
}}

QWidget#controlSidebar,
QWidget#controlPage0,
QWidget#controlPage1 {{
    background: {bg_panel};
    color: {text_body};
    font-size: 13px;
}}

QWidget {{
    color: {text_body};
    selection-background-color: {primary};
    selection-color: #ffffff;
}}

QScrollArea,
QStackedWidget,
QFrame {{
    border: none;
    background: transparent;
}}

QScrollArea#controlSidebarScroll {{
    background: {bg_panel};
}}

QWidget#panelSwitcher,
QWidget[toolbarStrip="true"] {{
    background: transparent;
}}

QLabel {{
    background: transparent;
    color: {text_body};
}}

QLabel[sidebarTitle="true"] {{
    background: {bg_surface};
    border: 1px solid {border};
    border-radius: 12px;
    padding: 12px 14px;
    color: {text_main};
    font-size: 16px;
    font-weight: 700;
}}

QLabel[mutedText="true"] {{
    color: {text_muted};
}}

QWidget[waveformPage="true"] {{
    background: {bg_app};
}}

QLabel[sectionTitle="true"] {{
    color: {text_main};
    font-size: 17px;
    font-weight: 800;
}}

QLabel[sectionCaption="true"] {{
    color: {text_muted};
    font-size: 12px;
}}

QFrame[metricCard="true"],
QFrame[plotCard="true"],
QFrame[wavePanelCard="true"] {{
    background: {bg_surface};
    border: 1px solid {border};
    border-radius: 14px;
}}

QFrame[metricCard="true"][tone="success"] {{
    border-color: #bbf7d0;
    background: #f8fdf9;
}}

QFrame[metricCard="true"][tone="warning"] {{
    border-color: #fed7aa;
    background: #fffdf8;
}}

QFrame[metricCard="true"][tone="danger"] {{
    border-color: #fecaca;
    background: #fff9f9;
}}

QFrame[metricCard="true"][tone="primary"],
QFrame[metricCard="true"][tone="info"] {{
    border-color: #d7e4ff;
    background: #fbfdff;
}}

QFrame[criteriaRow="true"] {{
    background: {bg_surface_alt};
    border: 1px solid {border};
    border-radius: 12px;
}}

QLabel[metricTitle="true"] {{
    color: {text_muted};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.2px;
}}

QLabel[metricValue="true"] {{
    color: {text_main};
    font-size: 22px;
    font-weight: 800;
    min-height: 30px;
    padding: 2px 0;
}}

QLabel[metricValue="true"][tone="neutral"] {{
    color: {text_main};
}}

QLabel[metricValue="true"][tone="primary"],
QLabel[metricValue="true"][tone="info"] {{
    color: {primary};
}}

QLabel[metricValue="true"][tone="success"] {{
    color: {success};
}}

QLabel[metricValue="true"][tone="warning"] {{
    color: {warning};
}}

QLabel[metricValue="true"][tone="danger"] {{
    color: {danger};
}}

QLabel[metricCaption="true"] {{
    color: {text_muted};
    font-size: 10px;
}}

QLabel[syncStateHero="true"] {{
    background: {bg_surface_alt};
    border: 1px solid {border};
    border-radius: 12px;
    padding: 10px 12px;
    color: {text_main};
    font-size: 18px;
    font-weight: 800;
    min-height: 52px;
}}

QLabel[syncStateHero="true"][tone="neutral"] {{
    background: {bg_surface_alt};
    border-color: {border};
    color: {text_muted};
}}

QLabel[syncStateHero="true"][tone="info"] {{
    background: {info_soft};
    border-color: #bfdbfe;
    color: {info};
}}

QLabel[syncStateHero="true"][tone="primary"] {{
    background: {primary_soft};
    border-color: #bfdbfe;
    color: {primary};
}}

QLabel[syncStateHero="true"][tone="success"] {{
    background: {success_soft};
    border-color: #bbf7d0;
    color: {success};
}}

QLabel[syncStateHero="true"][tone="warning"] {{
    background: {warning_soft};
    border-color: #fed7aa;
    color: {warning};
}}

QLabel[syncStateHero="true"][tone="danger"] {{
    background: {danger_soft};
    border-color: #fecaca;
    color: {danger};
}}

QLabel[stepHeader="true"] {{
    color: {text_main};
    font-size: 20px;
    font-weight: 800;
    padding: 2px 0 4px 0;
}}

QLabel[stepDescription="true"] {{
    color: {text_muted};
    font-size: 13px;
    padding: 0 0 4px 0;
}}

QLabel[badge="true"] {{
    background: {bg_surface};
    border: 1px solid {border};
    border-radius: 10px;
    padding: 8px 12px;
    color: {text_body};
    font-size: 12px;
    font-weight: 700;
}}

QLabel[badge="true"][tone="neutral"] {{
    background: {bg_surface_alt};
    color: {text_muted};
    border-color: {border};
}}

QLabel[badge="true"][tone="primary"] {{
    background: {primary_soft};
    color: {primary};
    border-color: #bfdbfe;
}}

QLabel[badge="true"][tone="info"] {{
    background: {info_soft};
    color: {info};
    border-color: #bfdbfe;
}}

QLabel[badge="true"][tone="success"] {{
    background: {success_soft};
    color: {success};
    border-color: #bbf7d0;
}}

QLabel[badge="true"][tone="warning"] {{
    background: {warning_soft};
    color: {warning};
    border-color: #fed7aa;
}}

QLabel[badge="true"][tone="danger"] {{
    background: {danger_soft};
    color: {danger};
    border-color: #fecaca;
}}

QLabel[badge="true"][criteriaBadge="true"] {{
    border-radius: 9px;
    padding: 4px 10px;
    font-size: 10px;
    font-weight: 600;
    min-height: 22px;
}}

QLabel[stepBanner="true"] {{
    background: {bg_surface_alt};
    border: 1px solid {border};
    border-radius: 12px;
    padding: 10px 12px;
    color: {text_body};
    font-size: 13px;
    font-weight: 700;
}}

QLabel[stepBanner="true"][tone="neutral"] {{
    background: {bg_surface_alt};
    color: {text_muted};
    border-color: {border};
}}

QLabel[stepBanner="true"][tone="primary"] {{
    background: {primary_soft};
    color: {primary};
    border-color: #bfdbfe;
}}

QLabel[stepBanner="true"][tone="info"] {{
    background: {info_soft};
    color: {info};
    border-color: #bfdbfe;
}}

QLabel[stepBanner="true"][tone="success"] {{
    background: {success_soft};
    color: {success};
    border-color: #bbf7d0;
}}

QLabel[stepBanner="true"][tone="warning"] {{
    background: {warning_soft};
    color: {warning};
    border-color: #fed7aa;
}}

QLabel[stepBanner="true"][tone="danger"] {{
    background: {danger_soft};
    color: {danger};
    border-color: #fecaca;
}}

QLabel[stepListItem="true"] {{
    color: {text_muted};
    font-size: 12px;
    padding: 1px 0;
}}

QLabel[stepListItem="true"][tone="success"] {{
    color: {success};
}}

QLabel[stepListItem="true"][tone="active"] {{
    color: {text_body};
}}

QLabel[stepListItem="true"][tone="muted"] {{
    color: {text_soft};
}}

QLabel[stepHint="true"] {{
    color: {text_muted};
    font-size: 12px;
}}

QLabel[stepStatus="true"] {{
    color: {text_body};
    font-size: 13px;
}}

QLabel[noteText="true"] {{
    color: {text_muted};
    font-size: 11px;
    padding: 1px 0;
}}

QLabel[noteText="true"][tone="warning"] {{
    color: {warning};
    font-weight: 700;
}}

QLabel[noteText="true"][tone="primary"] {{
    color: {primary};
    font-weight: 700;
}}

QLabel[noteText="true"][tone="danger"] {{
    color: {danger};
    font-weight: 700;
}}

QLabel[feedbackText="true"] {{
    color: {text_body};
    font-size: 12px;
    font-weight: 700;
    padding: 2px 0;
}}

QLabel[feedbackText="true"][tone="neutral"] {{
    color: {text_muted};
}}

QLabel[feedbackText="true"][tone="success"] {{
    color: {success};
}}

QLabel[feedbackText="true"][tone="warning"] {{
    color: {warning};
}}

QLabel[feedbackText="true"][tone="danger"] {{
    color: {danger};
}}

QLabel[feedbackText="true"][tone="info"] {{
    color: {info};
}}

QLabel[liveText="true"] {{
    color: {text_body};
    font-size: 15px;
}}

QLabel[liveText="true"][tone="neutral"] {{
    color: #444444;
}}

QLabel[liveText="true"][tone="muted"] {{
    color: #999999;
}}

QLabel[liveText="true"][tone="success"] {{
    color: {success};
}}

QLabel[liveText="true"][tone="warning"] {{
    color: {warning};
}}

QLabel[liveText="true"][tone="danger"] {{
    color: {danger};
}}

QLabel[liveText="true"][tone="info"] {{
    color: {info};
}}

QLabel[recordValue="true"] {{
    color: {text_muted};
    font-size: 14px;
}}

QLabel[recordValue="true"][tone="neutral"] {{
    color: {text_soft};
}}

QLabel[recordValue="true"][tone="success"] {{
    color: {success};
}}

QLabel[recordValue="true"][tone="warning"] {{
    color: {warning};
}}

QLabel[recordValue="true"][tone="danger"] {{
    color: {danger};
}}

QLabel[testPanelTitle="true"] {{
    color: {text_main};
    font-size: 16px;
    font-weight: 800;
}}

QWidget[testPanelRoot="true"] {{
    background: {bg_panel};
}}

QWidget[testPanelBar="true"] {{
    background: {bg_surface};
    border-bottom: 1px solid {border};
}}

QWidget[testPanelBar="true"][barRole="footer"] {{
    border-top: 1px solid {border};
    border-bottom: none;
}}

QWidget[stepPage="true"] {{
    background: {bg_app};
}}

QWidget[actionRow="true"] {{
    background: transparent;
}}

QWidget[inlineRow="true"] {{
    background: {bg_surface_alt};
    border: 1px solid {border};
    border-radius: 10px;
}}

QWidget[recordRow="true"] {{
    background: {bg_surface};
    border: 1px solid {border};
    border-radius: 10px;
}}

QLabel[valueChip="true"] {{
    background: {bg_hover};
    border: 1px solid {border};
    border-radius: 8px;
    color: {text_main};
    font-size: 11px;
    font-weight: 700;
    padding: 2px 6px;
}}

QDialog[themedDialog="true"] {{
    background: {bg_panel};
}}

QFrame[dialogCard="true"],
QWidget[dialogCard="true"] {{
    background: {bg_surface};
    border: 1px solid {border};
    border-radius: 14px;
}}

QLabel[dialogKicker="true"] {{
    color: {warning};
    font-size: 11px;
    font-weight: 700;
}}

QLabel[dialogTitle="true"] {{
    color: {text_main};
    font-size: 26px;
    font-weight: 800;
}}

QLabel[dialogSection="true"] {{
    color: {text_main};
    font-size: 16px;
    font-weight: 700;
    padding-top: 4px;
}}

QLabel[dialogCaption="true"] {{
    color: {text_muted};
    font-size: 11px;
}}

QTabWidget::pane {{
    border: 1px solid {border};
    background: {bg_surface};
    border-radius: 12px;
    top: -1px;
}}

QTabBar::tab {{
    background: {bg_surface_alt};
    color: {text_muted};
    border: 1px solid transparent;
    border-radius: 10px;
    padding: 10px 18px;
    margin-right: 6px;
    min-width: 148px;
    font-size: 13px;
    font-weight: 600;
}}

QTabBar::tab:hover:!selected {{
    background: {bg_hover};
    color: {text_body};
}}

QTabBar::tab:selected {{
    background: {bg_surface};
    color: {primary};
    border-color: {border};
}}

QGroupBox {{
    background: {bg_surface};
    border: 1px solid {border};
    border-radius: 12px;
    margin-top: 12px;
    padding-top: 14px;
    color: {text_body};
    font-size: 13px;
    font-weight: 700;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    background: {bg_surface};
    color: {text_body};
}}

QGroupBox[cardTone="warning"] {{
    background: #fffdf7;
    border-color: #f6d7a5;
    color: {warning};
}}

QGroupBox[cardTone="warning"]::title {{
    background: #fffdf7;
    color: {warning};
}}

QGroupBox[cardTone="info"] {{
    background: #f8fbff;
    border-color: #d5e5ff;
}}

QPushButton {{
    background: {primary};
    color: #ffffff;
    border: 1px solid {primary};
    border-radius: 8px;
    padding: 7px 14px;
    min-height: 18px;
    font-size: 13px;
    font-weight: 700;
}}

QPushButton:hover {{
    background: {primary_hover};
    border-color: {primary_hover};
}}

QPushButton:pressed {{
    background: #1e3a8a;
    border-color: #1e3a8a;
}}

QPushButton:disabled {{
    background: #e8eef6;
    color: {text_soft};
    border-color: {border};
}}

QPushButton[hero="true"] {{
    min-height: 24px;
    font-size: 14px;
    border-radius: 10px;
    padding: 10px 16px;
}}

QPushButton[secondary="true"] {{
    background: {bg_surface};
    color: {text_body};
    border: 1px solid {border_strong};
}}

QPushButton[secondary="true"]:hover {{
    background: {bg_hover};
    border-color: #b6c5d9;
}}

QPushButton[success="true"] {{
    background: {success};
    border-color: {success};
}}

QPushButton[success="true"]:hover {{
    background: #166534;
    border-color: #166534;
}}

QPushButton[warning="true"] {{
    background: {warning};
    border-color: {warning};
}}

QPushButton[warning="true"]:hover {{
    background: #92400e;
    border-color: #92400e;
}}

QPushButton[danger="true"] {{
    background: {danger};
    border-color: {danger};
}}

QPushButton[danger="true"]:hover {{
    background: #b91c1c;
    border-color: #b91c1c;
}}

QPushButton[muted="true"] {{
    background: #e8eef6;
    color: {text_muted};
    border-color: {border};
}}

QPushButton[adminButton="true"] {{
    background: #7c3aed;
    color: #ffffff;
    border-color: #7c3aed;
}}

QPushButton[adminButton="true"]:hover {{
    background: #6d28d9;
    border-color: #6d28d9;
}}

QPushButton[adminButton="true"]:checked {{
    background: #4c1d95;
    border-color: #4c1d95;
}}

QRadioButton[inlineRadio="true"] {{
    background: transparent;
    color: {text_body};
    font-size: 12px;
}}

QLineEdit[compactInput="true"],
QSpinBox[compactInput="true"] {{
    min-height: 18px;
    font-size: 11px;
    padding: 3px 6px;
    border-radius: 8px;
}}

QLineEdit[compactInput="true"][readonlyTone="true"] {{
    background: #eef2f7;
    color: {text_muted};
}}

QProgressBar[metricBar="true"] {{
    background: #e2e8f0;
    border: none;
    border-radius: 6px;
}}

QProgressBar[metricBar="true"]::chunk {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #16a34a,
        stop:0.5 #d97706,
        stop:1 #dc2626
    );
    border-radius: 6px;
}}

QPushButton[segment="true"] {{
    background: {bg_surface_alt};
    color: {text_muted};
    border: 1px solid {border};
    border-radius: 10px;
    padding: 6px 10px;
}}

QPushButton[segment="true"]:hover {{
    background: {bg_hover};
    border-color: {border_strong};
    color: {text_body};
}}

QPushButton[segment="true"]:checked {{
    background: {primary};
    color: #ffffff;
    border-color: {primary};
}}

QPushButton[segment="true"][segmentTone="warning"]:checked {{
    background: {warning};
    border-color: {warning};
}}

QPushButton[segment="true"][segmentTone="danger"]:checked {{
    background: {danger};
    border-color: {danger};
}}

QCheckBox,
QRadioButton {{
    color: {text_body};
    spacing: 8px;
    font-size: 13px;
}}

QCheckBox::indicator,
QRadioButton::indicator {{
    width: 18px;
    height: 18px;
}}

QCheckBox::indicator {{
    border-radius: 5px;
    border: 1px solid {border_strong};
    background: {bg_surface};
}}

QRadioButton::indicator {{
    border-radius: 9px;
    border: 1px solid {border_strong};
    background: {bg_surface};
}}

QCheckBox::indicator:checked,
QRadioButton::indicator:checked {{
    background: {primary};
    border-color: {primary};
}}

QCheckBox[cardToggle="true"] {{
    background: {bg_surface};
    border: 1px solid {border};
    border-radius: 12px;
    padding: 10px 12px;
    font-weight: 700;
}}

QCheckBox[cardToggle="true"][tone="success"] {{
    background: #f4fbf6;
    color: {success};
    border-color: #ccebd8;
}}

QCheckBox[cardToggle="true"][tone="warning"] {{
    background: #fffaf2;
    color: {warning};
    border-color: #f8dfbf;
}}

QCheckBox[cardToggle="true"][tone="info"] {{
    background: #f6faff;
    color: #0369a1;
    border-color: #cfe7f5;
}}

QCheckBox[cardToggle="true"][tone="primary"] {{
    background: #f7faff;
    color: {primary};
    border-color: #d8e3f4;
}}

QLineEdit,
QComboBox,
QAbstractSpinBox {{
    background: {bg_surface};
    color: {text_main};
    border: 1px solid {border_strong};
    border-radius: 8px;
    padding: 6px 8px;
    selection-background-color: {primary};
}}

QLineEdit:focus,
QComboBox:focus,
QAbstractSpinBox:focus {{
    border-color: {primary};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background: {bg_surface};
    color: {text_body};
    border: 1px solid {border};
    selection-background-color: {primary_soft};
    selection-color: {primary};
}}

QSlider::groove:horizontal {{
    height: 6px;
    background: #dbe4f0;
    border-radius: 3px;
}}

QSlider::sub-page:horizontal {{
    background: #93c5fd;
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
    border: 2px solid {bg_surface};
    background: {primary};
}}

QProgressBar {{
    min-height: 10px;
    background: #e7edf5;
    color: {text_muted};
    border: 1px solid {border};
    border-radius: 6px;
    text-align: center;
}}

QProgressBar::chunk {{
    background: {primary};
    border-radius: 5px;
}}

QScrollBar:vertical {{
    width: 10px;
    background: transparent;
    margin: 2px;
}}

QScrollBar::handle:vertical {{
    background: #b4c2d4;
    border-radius: 5px;
    min-height: 28px;
}}

QScrollBar::handle:vertical:hover {{
    background: #90a4ba;
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    height: 10px;
    background: transparent;
    margin: 2px;
}}

QScrollBar::handle:horizontal {{
    background: #b4c2d4;
    border-radius: 5px;
    min-width: 28px;
}}

QScrollBar::handle:horizontal:hover {{
    background: #90a4ba;
}}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0;
}}

QToolTip {{
    background: {bg_surface};
    color: {text_body};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 6px 8px;
}}

QMenu {{
    background: {bg_surface};
    color: {text_body};
    border: 1px solid {border};
    border-radius: 10px;
    padding: 6px;
}}

QMenu::item {{
    padding: 8px 14px;
    border-radius: 8px;
}}

QMenu::item:selected {{
    background: {bg_hover};
    color: {text_main};
}}
"""

APP_QSS = _QSS_TEMPLATE.format(**LIGHT_THEME)


def _load_qdarkstyle_base() -> str:
    try:
        import qdarkstyle
    except Exception:
        return ""

    try:
        from qdarkstyle.light.palette import LightPalette
        return qdarkstyle.load_stylesheet(qt_api="pyqt5", palette=LightPalette)
    except Exception:
        return ""


def build_app_stylesheet() -> str:
    base = _load_qdarkstyle_base()
    return f"{base}\n{APP_QSS}" if base else APP_QSS


def apply_app_theme(app) -> None:
    app.setStyleSheet(build_app_stylesheet())
