from PyQt5 import QtCore, QtGui, QtWidgets

from domain.fault_scenarios import SCENARIOS
from domain.enums import BreakerPosition
from ui.tabs._step_style import (
    apply_badge_tone,
    apply_button_tone,
    set_props,
)
from ui.widgets.gen_wiring_widget import _GenWiringWidget
from ui.widgets.pt_wiring_widget import _PTWiringWidget

_SECTION_BG = "#ffffff"
_GRP_STYLE = (
    "QGroupBox{{background:{bg}; color:#0f172a; font-size:13px; font-weight:bold;"
    " border:1px solid #dbe4f0; border-radius:12px; margin-top:12px; padding-top:14px;}}"
    "QGroupBox::title{{subcontrol-origin:margin; left:10px;"
    " background:{bg}; color:#1e293b; padding:0 6px;}}"
    "QGroupBox *{{font-size:12px; color:#334155; font-weight:normal;}}"
)


def make_group(title, bg=_SECTION_BG):
    grp = QtWidgets.QGroupBox(title)
    if bg != _SECTION_BG:
        grp.setStyleSheet(_GRP_STYLE.format(bg=bg))
    return grp


def make_button(owner, text, bg="#1d4ed8"):
    btn = QtWidgets.QPushButton(text)
    if bg == "#64748b":
        apply_button_tone(owner, btn, "primary", secondary=True)
        return btn
    tone = {
        "#16a34a": "success",
        "#dc2626": "danger",
        "#7c3aed": "primary",
    }.get(bg, "warning" if bg in {"#d97706", "#92400e"} else "primary")
    apply_button_tone(owner, btn, tone)
    return btn


def tone_from_color(color) -> str:
    raw = str(color or "").lower()
    if raw in {"#15803d", "#16a34a", "green", "darkgreen"}:
        return "success"
    if raw in {"#dc2626", "#b91c1c", "#991b1b", "red", "darkred"}:
        return "danger"
    if raw in {"#1d4ed8", "#2563eb", "blue"}:
        return "info"
    if raw in {"#d97706", "#b45309", "#92400e", "orange", "yellow"}:
        return "warning"
    return "neutral"


def make_note_label(text, tone="neutral", *, italic=False):
    lbl = QtWidgets.QLabel(text)
    set_props(lbl, noteText=True, tone=tone)
    if italic:
        font = lbl.font()
        font.setItalic(True)
        lbl.setFont(font)
    return lbl


def make_inline_row():
    row = QtWidgets.QWidget()
    set_props(row, inlineRow=True)
    return row


def make_feedback_label(text):
    lbl = QtWidgets.QLabel(text)
    lbl.setWordWrap(True)
    set_props(lbl, feedbackText=True, tone="success")
    return lbl


def set_feedback_label(label, text, color):
    label.setText(text)
    set_props(label, feedbackText=True, tone=tone_from_color(color))


def set_step_list_label(label, text, done, in_mode):
    label.setText(f"{'✓' if done else '□'} {text}")
    tone = "success" if done else ("active" if in_mode else "muted")
    set_props(label, stepListItem=True, tone=tone)


def make_step_list(parent_lay, n_steps):
    grp = make_group("测试步骤")
    lay = QtWidgets.QVBoxLayout(grp)
    lay.setSpacing(2)
    labels = []
    for _ in range(n_steps):
        lbl = QtWidgets.QLabel("")
        lbl.setWordWrap(True)
        set_props(lbl, stepListItem=True)
        lay.addWidget(lbl)
        labels.append(lbl)
    parent_lay.addWidget(grp)
    return labels


def _set_gen_mode(api, gen_id, val, checked):
    if checked:
        gen = api.sim_state.gen1 if gen_id == 1 else api.sim_state.gen2
        gen.mode = val


def _set_breaker_position(api, gen_id, val, checked):
    if checked:
        gen = api.sim_state.gen1 if gen_id == 1 else api.sim_state.gen2
        gen.breaker_position = val


def make_gen_block(parent_lay, *, owner, api, gen_refs, step_key, gen_id,
                   mode_options=None, show_pos=False, show_engine=True):
    gen = api.sim_state.gen1 if gen_id == 1 else api.sim_state.gen2
    inner = QtWidgets.QGroupBox(f"Gen {gen_id}")
    ilay = QtWidgets.QVBoxLayout(inner)
    ilay.setSpacing(2)
    ilay.setContentsMargins(4, 4, 4, 4)

    brk_lbl = QtWidgets.QLabel("--")
    apply_badge_tone(brk_lbl, "neutral")
    brk_lbl.setAlignment(QtCore.Qt.AlignCenter)
    ilay.addWidget(brk_lbl)

    mode_rbs = {}
    if mode_options:
        ilay.addWidget(make_note_label("PCC 模式:"))
        row = make_inline_row()
        hlay = QtWidgets.QHBoxLayout(row)
        hlay.setContentsMargins(0, 0, 0, 0)
        hlay.setSpacing(4)
        bg_mode = QtWidgets.QButtonGroup(owner)
        for txt, val in mode_options:
            rb = QtWidgets.QRadioButton(txt)
            set_props(rb, inlineRadio=True)
            rb.setChecked(gen.mode == val)
            rb.toggled.connect(lambda chk, v=val, gid=gen_id: _set_gen_mode(api, gid, v, chk))
            bg_mode.addButton(rb)
            hlay.addWidget(rb)
            mode_rbs[val] = rb
        ilay.addWidget(row)

    if show_pos:
        ilay.addWidget(make_note_label("开关柜位置:"))
        row = make_inline_row()
        hlay = QtWidgets.QHBoxLayout(row)
        hlay.setContentsMargins(0, 0, 0, 0)
        hlay.setSpacing(4)
        bg_pos = QtWidgets.QButtonGroup(owner)
        for txt, val in [("脱开", BreakerPosition.DISCONNECTED), ("工作", BreakerPosition.WORKING)]:
            rb = QtWidgets.QRadioButton(txt)
            set_props(rb, inlineRadio=True)
            rb.setChecked(gen.breaker_position == val)
            rb.toggled.connect(
                lambda chk, v=val, gid=gen_id: _set_breaker_position(api, gid, v, chk)
            )
            bg_pos.addButton(rb)
            hlay.addWidget(rb)
        ilay.addWidget(row)

    btn_row = QtWidgets.QWidget()
    br = QtWidgets.QHBoxLayout(btn_row)
    br.setContentsMargins(0, 0, 0, 0)
    br.setSpacing(4)

    eng_btn = None
    if show_engine:
        eng_btn = make_button(owner, "起机", "#16a34a")
        eng_btn.clicked.connect(lambda _, gid=gen_id: api.toggle_engine(gid))
        br.addWidget(eng_btn)

    brk_btn = make_button(owner, "合闸", "#1d4ed8")
    brk_btn.clicked.connect(lambda _, gid=gen_id: api.toggle_breaker(gid))
    br.addWidget(brk_btn)
    ilay.addWidget(btn_row)
    parent_lay.addWidget(inner)
    gen_refs[(step_key, gen_id)] = (brk_lbl, eng_btn, brk_btn, mode_rbs)


def make_gen_fap_block(parent_lay, *, api, gen_id, read_only=False):
    gen = api.sim_state.gen1 if gen_id == 1 else api.sim_state.gen2
    grp = QtWidgets.QGroupBox(f"Gen {gen_id} 频率/幅值/相位")
    glay = QtWidgets.QVBoxLayout(grp)
    glay.setSpacing(2)
    glay.setContentsMargins(4, 4, 4, 4)
    specs = [
        ("频率(Hz)", 450, 550, int(gen.freq * 10), 10, "freq", 48.0, 52.0),
        ("幅值(V)", 0, 15000, int(gen.amp), 1, "amp", 0.0, 15000.0),
        ("相位(°)", -1800, 1800, int(gen.phase_deg * 10), 10, "phase_deg", -180.0, 180.0),
    ]
    entry_map = {}
    for label, vmin, vmax, init, scale, attr, clo, chi in specs:
        row_w = make_inline_row()
        rh = QtWidgets.QHBoxLayout(row_w)
        rh.setContentsMargins(0, 0, 0, 0)
        rh.setSpacing(3)
        lbl = QtWidgets.QLabel(label)
        lbl.setFixedWidth(66)
        set_props(lbl, noteText=True)
        sl = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        sl.setRange(vmin, vmax)
        sl.setValue(init)
        sl.setFixedHeight(16)
        sl.setEnabled(not read_only)
        entry = QtWidgets.QLineEdit(f"{getattr(gen, attr):.1f}")
        entry.setFixedWidth(56)
        set_props(entry, compactInput=True)
        entry.setEnabled(not read_only)
        entry.setReadOnly(read_only)
        set_props(entry, compactInput=True, readonlyTone=read_only)

        def _sl_ch(val, _a=attr, _sc=scale, _e=entry, _gid=gen_id):
            v = round(val / _sc, 3)
            setattr(api.sim_state.gen1 if _gid == 1 else api.sim_state.gen2, _a, v)
            _e.setText(f"{v:.1f}")

        def _en_ch(_a=attr, _sc=scale, _sl=sl, _gid=gen_id, _clo=clo, _chi=chi, _e=entry):
            try:
                v = max(_clo, min(_chi, float(_e.text())))
                setattr(api.sim_state.gen1 if _gid == 1 else api.sim_state.gen2, _a, v)
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
    return entry_map


def add_blackbox_section(lay, *, owner, api, show_blackbox_dialog):
    lay.addWidget(make_note_label("物理接线检查 / 手动修复 (开盖查线):"))
    allow_blackbox = api.can_inspect_blackbox()

    row1 = make_inline_row()
    h1 = QtWidgets.QHBoxLayout(row1)
    h1.setContentsMargins(0, 0, 0, 0)
    h1.setSpacing(4)
    btn_g1 = make_button(owner, "G1 机端接线", "#92400e")
    btn_g1.setEnabled(allow_blackbox)
    btn_g1.clicked.connect(lambda: show_blackbox_dialog("G1"))
    btn_g2 = make_button(owner, "G2 机端接线", "#92400e")
    btn_g2.setEnabled(allow_blackbox)
    btn_g2.clicked.connect(lambda: show_blackbox_dialog("G2"))
    h1.addWidget(btn_g1)
    h1.addWidget(btn_g2)
    lay.addWidget(row1)

    row2 = make_inline_row()
    h2 = QtWidgets.QHBoxLayout(row2)
    h2.setContentsMargins(0, 0, 0, 0)
    h2.setSpacing(4)
    btn_pt1 = make_button(owner, "PT1 接线盒", "#1e40af")
    btn_pt1.setEnabled(allow_blackbox)
    btn_pt1.clicked.connect(lambda: show_blackbox_dialog("PT1"))
    btn_pt3 = make_button(owner, "PT3 接线盒", "#1e40af")
    btn_pt3.setEnabled(allow_blackbox)
    btn_pt3.clicked.connect(lambda: show_blackbox_dialog("PT3"))
    h2.addWidget(btn_pt1)
    h2.addWidget(btn_pt3)
    lay.addWidget(row2)


def show_assessment_result_dialog(owner, result):
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
        set_props(card, dialogCard=True)
        card_lay = QtWidgets.QVBoxLayout(card)
        card_lay.setContentsMargins(14, 12, 14, 12)
        card_lay.setSpacing(6)
        title_lbl = QtWidgets.QLabel(title_text)
        set_props(title_lbl, dialogCaption=True)
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

    dlg = QtWidgets.QDialog(owner)
    dlg.setWindowTitle("考核成绩单")
    dlg.resize(760, 720)
    set_props(dlg, themedDialog=True)
    dlg.setStyleSheet(
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
    set_props(overview, dialogCard=True)
    overview_lay = QtWidgets.QHBoxLayout(overview)
    overview_lay.setContentsMargins(18, 16, 18, 16)
    overview_lay.setSpacing(14)
    hero = QtWidgets.QFrame()
    hero_lay = QtWidgets.QVBoxLayout(hero)
    hero_lay.setContentsMargins(0, 0, 0, 0)
    hero_lay.setSpacing(8)
    kicker = QtWidgets.QLabel("考核结果报告")
    set_props(kicker, dialogKicker=True)
    hero_lay.addWidget(kicker)
    title = QtWidgets.QLabel("考核成绩单")
    set_props(title, dialogTitle=True)
    hero_lay.addWidget(title)
    hero_info = QtWidgets.QLabel(
        f"场景：{result.scene_id or '正常模式'}    模式：考核模式\n完成时间：{result.finished_at.replace('T', ' ')}"
    )
    set_props(hero_info, dialogCaption=True)
    hero_lay.addWidget(hero_info)
    tag = QtWidgets.QLabel(result_tag)
    tag.setAlignment(QtCore.Qt.AlignCenter)
    tag.setFixedWidth(94)
    tag.setStyleSheet(
        f"background:{tag_bg}; color:{tag_fg}; font-size:15px; font-weight:bold; border-radius:16px; padding:7px 12px;"
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
    set_props(summary, dialogCard=True)
    summary.setContentsMargins(14, 14, 14, 14)
    content_lay.addWidget(summary)
    if result.veto_reason:
        veto = QtWidgets.QLabel(f"否决原因：{result.veto_reason}")
        veto.setWordWrap(True)
        set_props(veto, stepBanner=True, tone="danger")
        content_lay.addWidget(veto)

    section1 = QtWidgets.QLabel("分项汇总")
    set_props(section1, dialogSection=True)
    content_lay.addWidget(section1)
    summary_grid_wrap = QtWidgets.QFrame()
    summary_grid = QtWidgets.QGridLayout(summary_grid_wrap)
    summary_grid.setContentsMargins(0, 0, 0, 0)
    summary_grid.setHorizontalSpacing(10)
    summary_grid.setVerticalSpacing(10)
    for idx, (key, value) in enumerate(result.step_scores.items()):
        max_value = result.step_max_scores.get(key, 0)
        bg, fg, border = _status_palette("通过" if value == max_value else "未通过" if value == 0 else "部分扣分")
        card = QtWidgets.QFrame()
        card.setStyleSheet(f"background:{bg}; border:1px solid {border}; border-radius:14px;")
        card_lay = QtWidgets.QVBoxLayout(card)
        card_lay.setContentsMargins(14, 12, 14, 12)
        card_lay.setSpacing(4)
        name_lbl = QtWidgets.QLabel(score_labels.get(key, key))
        set_props(name_lbl, dialogCaption=True)
        name_lbl.setStyleSheet(f"color:{fg}; font-weight:bold;")
        card_lay.addWidget(name_lbl)
        score_lbl = QtWidgets.QLabel(f"{value} / {max_value}")
        score_lbl.setStyleSheet("font-size:24px; color:#0f172a; font-weight:bold;")
        card_lay.addWidget(score_lbl)
        note = "表现稳定" if value == max_value else "需要重点关注" if value == 0 else "存在扣分项"
        note_lbl = QtWidgets.QLabel(note)
        set_props(note_lbl, dialogCaption=True)
        card_lay.addWidget(note_lbl)
        summary_grid.addWidget(card, idx // 2, idx % 2)
    content_lay.addWidget(summary_grid_wrap)

    section2 = QtWidgets.QLabel("详细计分点")
    set_props(section2, dialogSection=True)
    content_lay.addWidget(section2)
    detail_hint = QtWidgets.QLabel("以下表格列出每个计分点的通过情况、得分与具体说明。")
    set_props(detail_hint, dialogCaption=True)
    content_lay.addWidget(detail_hint)
    detail_table = QtWidgets.QTableWidget(len(result.score_items), 8)
    detail_table.setHorizontalHeaderLabels(["编号", "计分点", "类别", "结果", "满分", "实得", "步骤", "说明"])
    detail_table.verticalHeader().setVisible(False)
    detail_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
    detail_table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
    detail_table.setAlternatingRowColors(False)
    detail_table.setShowGrid(False)
    for col in range(7):
        detail_table.horizontalHeader().setSectionResizeMode(col, QtWidgets.QHeaderView.ResizeToContents)
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
    detail_table.setFixedHeight(detail_table.horizontalHeader().height() + max(6, detail_table.rowCount()) * 30 + 4)
    content_lay.addWidget(detail_table)

    section3 = QtWidgets.QLabel("过程统计")
    set_props(section3, dialogSection=True)
    content_lay.addWidget(section3)
    extra_penalties = [penalty for penalty in result.penalties if penalty.code in {"X1", "X2"}]
    if extra_penalties:
        section_extra = QtWidgets.QLabel("额外扣分说明")
        set_props(section_extra, dialogSection=True)
        content_lay.addWidget(section_extra)
        extra_wrap = QtWidgets.QFrame()
        extra_wrap.setStyleSheet("background:white; border:1px solid #fecaca; border-radius:12px;")
        extra_lay = QtWidgets.QVBoxLayout(extra_wrap)
        extra_lay.setContentsMargins(14, 12, 14, 12)
        extra_lay.setSpacing(8)
        for penalty in extra_penalties:
            step_text = f"第 {penalty.step} 步" if penalty.step > 0 else "流程外"
            item_lbl = QtWidgets.QLabel(f"{step_text}：{penalty.message}（{penalty.score_delta} 分）")
            item_lbl.setWordWrap(True)
            item_lbl.setStyleSheet("font-size:13px; color:#991b1b; font-weight:bold;")
            extra_lay.addWidget(item_lbl)
        content_lay.addWidget(extra_wrap)

    metric_labels.update({
        "fault_selection_mode": "随机出题方式",
        "fault_guess_scene_id": "学员判定故障",
        "fault_guess_correct": "判定结果",
        "actual_fault_scene_id": "实际故障",
        "early_pt_blackbox_opened": "前两步提前打开 PT 黑盒次数",
        "extra_deduction_total": "额外扣分合计",
    })
    metric_rows = []
    for key, value in result.metrics.items():
        if isinstance(value, list):
            value_text = "、".join(str(v) for v in value if v not in (None, "")) or "-"
        else:
            value_text = "-" if value in (None, "", 0) and key == "fault_repaired_at" else str(value)
        metric_rows.append((metric_labels.get(key, key), value_text))
    metrics_wrap = QtWidgets.QFrame()
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
        set_props(label_lbl, dialogCaption=True)
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
    apply_button_tone(owner, btn_close, "primary")
    btn_close.clicked.connect(dlg.accept)
    btn_row.addWidget(btn_close)
    lay.addLayout(btn_row)
    dlg.adjustSize()
    dlg.resize(max(340, dlg.sizeHint().width()), dlg.sizeHint().height())
    dlg.exec_()


def show_random_fault_identification_dialog(owner, *, submit_guess):
    dlg = QtWidgets.QDialog(owner)
    dlg.setWindowTitle("随机故障判定")
    dlg.resize(520, 260)
    dlg.setModal(True)
    dlg.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint)
    set_props(dlg, themedDialog=True)
    lay = QtWidgets.QVBoxLayout(dlg)
    lay.setContentsMargins(16, 14, 16, 14)
    lay.setSpacing(10)
    title_lbl = QtWidgets.QLabel("请先判断本轮随机故障，再生成第 4 步成绩单")
    set_props(title_lbl, dialogTitle=True)
    lay.addWidget(title_lbl)
    desc_lbl = QtWidgets.QLabel("随机故障考核不会提前公开场景。请根据前四步测量结果，选择你认为最符合当前现象的故障场景。")
    desc_lbl.setWordWrap(True)
    set_props(desc_lbl, dialogCaption=True)
    lay.addWidget(desc_lbl)
    combo = QtWidgets.QComboBox()
    combo.setMinimumHeight(36)
    combo.setStyleSheet(
        "QComboBox{font-size:16px; padding:6px 10px;}"
        "QAbstractItemView{font-size:16px; outline:none;}"
        "QAbstractItemView::item{min-height:30px;}"
    )
    combo.addItem("请选择故障场景", "")
    for scene_id, info in SCENARIOS.items():
        if not scene_id:
            continue
        title_text = info.get("title", scene_id)
        combo.addItem(str(title_text) if str(title_text).startswith(scene_id) else f"{scene_id} - {title_text}", scene_id)
    lay.addWidget(combo)
    hint_lbl = QtWidgets.QLabel("")
    hint_lbl.setWordWrap(True)
    set_props(hint_lbl, feedbackText=True, tone="warning")
    hint_lbl.setVisible(False)
    lay.addWidget(hint_lbl)
    lay.addStretch()
    btn_row = QtWidgets.QHBoxLayout()
    btn_row.addStretch()
    btn_ok = QtWidgets.QPushButton("提交判定并生成成绩单")
    apply_button_tone(owner, btn_ok, "primary")

    def _submit():
        guessed_scene_id = combo.currentData()
        if not guessed_scene_id:
            hint_lbl.setText("请先选择一个故障场景。")
            hint_lbl.setVisible(True)
            return
        submit_guess(guessed_scene_id)
        dlg.accept()

    btn_ok.clicked.connect(_submit)
    btn_row.addWidget(btn_ok)
    lay.addLayout(btn_row)
    dlg.exec_()


def show_blackbox_required_dialog(owner, *, is_assessment, scene_id):
    info = SCENARIOS.get(scene_id, {})
    dlg = QtWidgets.QDialog(owner)
    dlg.setWindowTitle("⚠️ 当前流程尚未闭环" if is_assessment else "⚠️ 仍有接线故障未修复")
    dlg.setModal(True)
    dlg.resize(500, 300)
    lay = QtWidgets.QVBoxLayout(dlg)
    lay.setContentsMargins(14, 12, 14, 12)
    lay.setSpacing(10)
    title_text = "当前考核尚未闭环" if is_assessment else info.get("title", "故障") + " — 需先完成黑盒修复"
    title_lbl = QtWidgets.QLabel(title_text)
    title_lbl.setStyleSheet("font-size:14px; font-weight:bold; color:#991b1b;")
    lay.addWidget(title_lbl)
    if is_assessment:
        hint_text = "当前考核仍未满足结束条件，暂不能继续后续流程。\n\n请根据前四步已获得的测量结果继续排查并完成闭环。如需进一步确认，可进入黑盒检查，但系统不会提供具体故障位置提示。"
    else:
        hint_text = "当前仍存在未恢复的物理接线错误，不能进入第五步【同步功能测试】。\n\n请先回到当前流程中的黑盒检查区，完成相关接线修复。只有当相关接线全部恢复为正确顺序后，系统才会自动允许进入第五步。"
    hint = QtWidgets.QLabel(hint_text)
    hint.setWordWrap(True)
    hint.setStyleSheet("font-size:12px; color:#1f2937; background:#fff7ed; border:1px solid #fdba74; border-radius:4px; padding:8px;")
    lay.addWidget(hint)
    if not is_assessment:
        symptom_lbl = QtWidgets.QLabel("【当前已记录的异常现象】\n" + info.get("symptom", ""))
        symptom_lbl.setWordWrap(True)
        symptom_lbl.setStyleSheet("font-size:11px; color:#374151; background:#fef3c7; padding:6px; border-radius:4px;")
        lay.addWidget(symptom_lbl)
    btn_ok = QtWidgets.QPushButton("知道了")
    btn_ok.setStyleSheet("background:#334155; color:white; font-weight:bold; padding:6px 14px;")
    btn_ok.clicked.connect(dlg.accept)
    lay.addWidget(btn_ok, alignment=QtCore.Qt.AlignRight)
    dlg.exec_()


def show_blackbox_dialog(owner, *, api, step, target):
    if not api.can_inspect_blackbox():
        return
    sim = api.sim_state
    fc = sim.fault_config
    allow_repair = api.can_repair_in_blackbox()
    assessment_mode = api.is_assessment_mode()
    blackbox_state = api.get_blackbox_runtime_state(target)
    fault_active = blackbox_state["fault_active"]
    dlg = QtWidgets.QDialog(owner)
    set_props(dlg, themedDialog=True)
    dlg.setMinimumWidth(340)
    vlay = QtWidgets.QVBoxLayout(dlg)
    vlay.setSpacing(6)
    vlay.setContentsMargins(12, 10, 12, 10)
    widget = None
    repair_target = None
    initial_order = None
    initial_pri_order = None
    initial_sec_order = None

    if target in ("G1", "G2"):
        dlg.setWindowTitle(f"发电机 {target} 机端接线检查")
        order = blackbox_state["order"]
        mapping = {"A": order[0], "B": order[1], "C": order[2]}
        repair_target = blackbox_state["repair_target"]
        sub = QtWidgets.QLabel("上方绕组（A黄/B绿/C红）→ 下方接线柱（U/V/W）" + (" [可交互修复]" if allow_repair else " [仅查看]"))
        set_props(sub, dialogCaption=True)
        vlay.addWidget(sub)
        widget = _GenWiringWidget(mapping, interactive=allow_repair)
        initial_order = widget.get_order()
        vlay.addWidget(widget, alignment=QtCore.Qt.AlignHCenter)
    elif target == "PT1":
        dlg.setWindowTitle("PT1 接线盒检查 [一次/二次侧可交互修复]" if allow_repair else "PT1 接线盒检查 [只读]")
        pri_input_order = blackbox_state["pri_input_order"]
        pri_order = blackbox_state["pri_order"]
        sec_order = blackbox_state["sec_order"]
        sub = QtWidgets.QLabel(
            "PT1 接线按当前物理状态绘制：一次侧与二次侧均可点击互换并分别修复。"
            if allow_repair else "PT1 接线按当前物理状态绘制：当前流程模式仅允许查看，不允许直接修复。"
        )
        set_props(sub, dialogCaption=True)
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
        repair_target = blackbox_state["repair_target"]
    elif target == "PT3":
        dlg.setWindowTitle("PT3 接线盒检查 [二次侧可交互修复]" if allow_repair else "PT3 接线盒检查 [只读]")
        pri_input_order = blackbox_state["pri_input_order"]
        pri_order = blackbox_state["pri_order"]
        sec_order = blackbox_state["sec_order"]
        sub = QtWidgets.QLabel(
            "上: 二次侧输出→测量端口 [可互换]  |  下: 一次侧输入←Gen2 [只读]"
            if allow_repair else "上: 二次侧输出→测量端口 [只读]  |  下: 一次侧输入←Gen2 [只读]"
        )
        set_props(sub, dialogCaption=True)
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
        repair_target = blackbox_state["repair_target"]
        if fault_active and fc.scenario_id == "E03" and not assessment_mode:
            note = QtWidgets.QLabel("⚠ A 相极性反接：A1 正负极颠倒（a2 输出反相）")
            set_props(note, stepBanner=True, tone="warning")
            note.setWordWrap(True)
            vlay.addWidget(note)

    fb_lbl = QtWidgets.QLabel("")
    fb_lbl.setWordWrap(True)
    set_props(fb_lbl, feedbackText=True, tone="neutral")
    fb_lbl.setVisible(False)
    vlay.addWidget(fb_lbl)
    btn_row = QtWidgets.QWidget()
    bh = QtWidgets.QHBoxLayout(btn_row)
    bh.setContentsMargins(0, 0, 0, 0)
    bh.setSpacing(6)

    if repair_target is not None:
        def _on_confirm():
            new_order = widget.get_order() if repair_target in ("G1", "G2") else None
            new_pri = widget.get_pri_order() if repair_target in ("PT1", "PT3") else None
            new_sec = widget.get_sec_order() if repair_target in ("PT1", "PT3") else None
            outcome = api.apply_blackbox_repair_attempt(
                repair_target,
                step=step,
                initial_order=initial_order,
                new_order=new_order,
                initial_pri_order=initial_pri_order,
                new_pri_order=new_pri,
                initial_sec_order=initial_sec_order,
                new_sec_order=new_sec,
            )
            if not assessment_mode:
                fb_lbl.setText(outcome.message)
                set_props(fb_lbl, feedbackText=True, tone=tone_from_color(outcome.message_color))
                fb_lbl.setVisible(True)
            else:
                fb_lbl.setText("接线已保存，请关闭黑盒后返回外部测试流程复测。")
                set_props(fb_lbl, feedbackText=True, tone="info")
                fb_lbl.setVisible(True)
            if outcome.disable_repair_button and not assessment_mode:
                btn_repair.setEnabled(False)

        btn_repair = QtWidgets.QPushButton("保存接线" if assessment_mode else "确认修复 ✓")
        apply_button_tone(owner, btn_repair, "success")
        btn_repair.clicked.connect(_on_confirm)
        bh.addWidget(btn_repair, 1)

    btn_ok = QtWidgets.QPushButton("关闭")
    apply_button_tone(owner, btn_ok, "primary")
    btn_ok.clicked.connect(dlg.accept)
    bh.addWidget(btn_ok)
    vlay.addWidget(btn_row)
    dlg.exec_()
