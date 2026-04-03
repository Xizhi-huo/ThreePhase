"""
ui/styles.py
三相电并网仿真教学系统 · 全局 QSS 主题

"清新工业教学风" — Light Industrial Theme
  Primary  : #1d4ed8  (蓝)
  Success  : #16a34a  (绿 — 运行/合闸)
  Warning  : #d97706  (琥珀 — 告警)
  Error    : #dc2626  (红 — 跳闸/故障)
  Surface  : #ffffff  (白卡片)
  BG       : #f1f5f9  (浅灰底)
  Border   : #e2e8f0
  Text     : #1e293b  (主文字)
  SubText  : #64748b  (次要文字)
"""

APP_QSS = """
/* ══════════════════════════════════════════════
   全局基础
   ══════════════════════════════════════════════ */
QMainWindow, QWidget {
    background: #f1f5f9;
    color: #1e293b;
    font-size: 12px;
}

QScrollArea {
    border: none;
    background: transparent;
}
QScrollArea > QWidget {
    background: transparent;
}

/* ══════════════════════════════════════════════
   Tab Widget  — 仅显示全局视图标签
   ══════════════════════════════════════════════ */
QTabWidget::pane {
    border: 1px solid #e2e8f0;
    border-top: 2px solid #1d4ed8;
    background: #ffffff;
    border-radius: 0 0 4px 4px;
}
QTabBar {
    background: #f1f5f9;
}
QTabBar::tab {
    background: #e8eef6;
    color: #475569;
    padding: 9px 22px;
    border: 1px solid #d1dbe8;
    border-bottom: none;
    border-radius: 6px 6px 0 0;
    min-width: 150px;
    font-size: 13px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: #ffffff;
    color: #1d4ed8;
    font-weight: bold;
    border-bottom: 2px solid #1d4ed8;
}
QTabBar::tab:hover:!selected {
    background: #dde6f2;
    color: #334155;
}

/* ══════════════════════════════════════════════
   GroupBox
   ══════════════════════════════════════════════ */
QGroupBox {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: bold;
    font-size: 12px;
    color: #334155;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    background: #ffffff;
    color: #334155;
}

/* ══════════════════════════════════════════════
   QPushButton — 三级按钮体系
   ══════════════════════════════════════════════ */

/* 一级：主要操作 (default blue) */
QPushButton {
    background: #1d4ed8;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 5px 14px;
    font-size: 12px;
    font-weight: bold;
}
QPushButton:hover  { background: #1e40af; }
QPushButton:pressed { background: #1e3a8a; }
QPushButton:disabled {
    background: #e2e8f0;
    color: #94a3b8;
}

/* 二级：次要操作（线框样式）*/
QPushButton[secondary="true"] {
    background: transparent;
    color: #475569;
    border: 1px solid #cbd5e1;
}
QPushButton[secondary="true"]:hover {
    background: #f1f5f9;
    border-color: #94a3b8;
}

/* 三级：危险/警告操作 */
QPushButton[danger="true"] {
    background: #dc2626;
}
QPushButton[danger="true"]:hover { background: #b91c1c; }

/* 成功绿 */
QPushButton[success="true"] {
    background: #16a34a;
}
QPushButton[success="true"]:hover { background: #15803d; }

/* 警告琥珀 */
QPushButton[warning="true"] {
    background: #d97706;
}
QPushButton[warning="true"]:hover { background: #b45309; }

/* ══════════════════════════════════════════════
   QLabel
   ══════════════════════════════════════════════ */
QLabel {
    background: transparent;
    color: #1e293b;
}

/* 状态徽章：运行 */
QLabel[status="running"] {
    background: #dcfce7;
    color: #15803d;
    border: 1px solid #86efac;
    border-radius: 3px;
    padding: 2px 6px;
    font-weight: bold;
}
/* 状态徽章：停机 */
QLabel[status="stopped"] {
    background: #f1f5f9;
    color: #64748b;
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    padding: 2px 6px;
}
/* 状态徽章：合闸 */
QLabel[status="closed"] {
    background: #fee2e2;
    color: #dc2626;
    border: 1px solid #fca5a5;
    border-radius: 3px;
    padding: 2px 6px;
    font-weight: bold;
}
/* 状态徽章：分闸 */
QLabel[status="open"] {
    background: #eff6ff;
    color: #1d4ed8;
    border: 1px solid #93c5fd;
    border-radius: 3px;
    padding: 2px 6px;
}

/* ══════════════════════════════════════════════
   QSlider
   ══════════════════════════════════════════════ */
QSlider::groove:horizontal {
    height: 4px;
    background: #e2e8f0;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #1d4ed8;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
QSlider::sub-page:horizontal {
    background: #93c5fd;
    border-radius: 2px;
}

/* ══════════════════════════════════════════════
   QRadioButton / QCheckBox
   ══════════════════════════════════════════════ */
QRadioButton, QCheckBox {
    color: #334155;
    spacing: 6px;
    background: transparent;
}
QRadioButton::indicator:checked,
QCheckBox::indicator:checked {
    background: #1d4ed8;
    border: 2px solid #1d4ed8;
}

/* ══════════════════════════════════════════════
   QLineEdit
   ══════════════════════════════════════════════ */
QLineEdit {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    padding: 3px 6px;
    color: #1e293b;
}
QLineEdit:focus {
    border: 1px solid #1d4ed8;
}

/* ══════════════════════════════════════════════
   QProgressBar
   ══════════════════════════════════════════════ */
QProgressBar {
    background: #e2e8f0;
    border-radius: 4px;
    text-align: center;
    color: #334155;
    font-size: 11px;
}
QProgressBar::chunk {
    background: #1d4ed8;
    border-radius: 4px;
}

/* ══════════════════════════════════════════════
   QScrollBar
   ══════════════════════════════════════════════ */
QScrollBar:vertical {
    background: #f1f5f9;
    width: 8px;
    border-radius: 4px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #94a3b8;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #64748b; }
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical  { height: 0; }

QScrollBar:horizontal {
    height: 8px;
    background: #f1f5f9;
}
QScrollBar::handle:horizontal {
    background: #94a3b8;
    border-radius: 4px;
    min-width: 30px;
}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal { width: 0; }

/* ══════════════════════════════════════════════
   QToolTip
   ══════════════════════════════════════════════ */
QToolTip {
    background: #1e293b;
    color: #f1f5f9;
    border: none;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
}

/* ══════════════════════════════════════════════
   步骤 Tab 内容区底色兼容
   （各步骤 QScrollArea 内 QWidget 的内联样式优先级更高，这里作为回退）
   ══════════════════════════════════════════════ */
QScrollArea > QWidget > QWidget {
    background: #ffffff;
}
"""
