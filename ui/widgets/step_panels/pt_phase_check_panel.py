from typing import Callable, Optional, TYPE_CHECKING

from PyQt5 import QtCore, QtWidgets

from ui.widgets.step_panels._panel_builders import (
    add_blackbox_section,
    make_button,
    make_feedback_label,
    make_gen_block,
    make_inline_row,
    make_note_label,
    make_step_list,
    set_feedback_label,
    set_props,
    set_step_list_label,
)

if TYPE_CHECKING:
    from ui.test_panel import TestPanelAPI


class PtPhaseCheckPanel(QtWidgets.QGroupBox):
    def __init__(
        self,
        api: "TestPanelAPI",
        *,
        get_current_test_step: Callable[[], int],
        is_step_complete: Callable[[int], bool],
        on_connect_phase_seq_meter: Optional[Callable[[str], None]] = None,
        on_disconnect_phase_seq_meter: Optional[Callable[[], None]] = None,
        get_phase_seq_meter_sequence: Optional[Callable[[], str]] = None,
        on_force_multimeter_off: Optional[Callable[[], None]] = None,
        show_blackbox_dialog: Optional[Callable[[str], None]] = None,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__("第三步：PT 相序检查", parent)
        self._api = api
        self._get_current_test_step = get_current_test_step
        self._is_step_complete = is_step_complete
        self._on_connect_phase_seq_meter = on_connect_phase_seq_meter
        self._on_disconnect_phase_seq_meter = on_disconnect_phase_seq_meter
        self._get_phase_seq_meter_sequence = get_phase_seq_meter_sequence
        self._on_force_multimeter_off = on_force_multimeter_off
        self._show_blackbox_dialog = show_blackbox_dialog
        self.gen_refs = {}
        self._build()

    def _build(self):
        lay = QtWidgets.QVBoxLayout(self)
        lay.setSpacing(4)
        self.tp_s3_step_lbls = make_step_list(lay, 7)
        lay.addWidget(make_note_label("Gen2 需起机，断路器保持断开", "warning", italic=True))
        make_gen_block(lay, owner=self, api=self._api, gen_refs=self.gen_refs, step_key="s3", gen_id=2)

        lay.addWidget(make_note_label("相序仪（在母排图右侧查看转盘与指示灯）:"))
        psm_row = make_inline_row()
        psm_h = QtWidgets.QHBoxLayout(psm_row)
        psm_h.setContentsMargins(0, 0, 0, 0)
        psm_h.setSpacing(6)
        for pt_name, bg in [("PT1", "#1d4ed8"), ("PT3", "#7c3aed")]:
            btn = make_button(self, f"📡 接入 {pt_name}", bg)
            btn.clicked.connect(lambda _, pt=pt_name: self._on_connect_psm(pt))
            psm_h.addWidget(btn)
        btn_disc = make_button(self, "断开", "#64748b")
        btn_disc.clicked.connect(self._on_disconnect_psm)
        psm_h.addWidget(btn_disc)
        lay.addWidget(psm_row)

        lay.addWidget(make_note_label("记录相序结果:"))
        rec_row = make_inline_row()
        rec_h = QtWidgets.QHBoxLayout(rec_row)
        rec_h.setContentsMargins(0, 0, 0, 0)
        rec_h.setSpacing(6)
        self._tp_s3_rec_btns = {}
        for pt_name, bg in [("PT1", "#1d4ed8"), ("PT3", "#7c3aed")]:
            btn = make_button(self, f"记录 {pt_name}", bg)
            btn.setEnabled(False)
            btn.clicked.connect(lambda _, pt=pt_name: self._on_record_psm(pt))
            rec_h.addWidget(btn)
            self._tp_s3_rec_btns[pt_name] = btn
        lay.addWidget(rec_row)

        if self._show_blackbox_dialog is not None:
            add_blackbox_section(
                lay,
                owner=self,
                api=self._api,
                show_blackbox_dialog=self._show_blackbox_dialog,
            )

        self.tp_s3_fb_lbl = make_feedback_label("请先接入相序仪查看结果，再点击记录")
        set_props(self.tp_s3_fb_lbl, feedbackText=True, tone="neutral")
        lay.addWidget(self.tp_s3_fb_lbl)

    def on_enter(self) -> None:
        if self._on_force_multimeter_off is not None:
            self._on_force_multimeter_off()

    def reset(self) -> None:
        self._on_disconnect_psm()

    def _on_connect_psm(self, pt_name: str):
        if self._on_connect_phase_seq_meter is not None:
            self._on_connect_phase_seq_meter(pt_name)
        if pt_name in self._tp_s3_rec_btns:
            self._tp_s3_rec_btns[pt_name].setEnabled(True)
        self.tp_s3_fb_lbl.setText(
            f"相序仪已接入 {pt_name}，请在母排图右侧查看转盘和指示灯，确认结果后点击「记录 {pt_name}」"
        )

    def _on_disconnect_psm(self):
        if self._on_disconnect_phase_seq_meter is not None:
            self._on_disconnect_phase_seq_meter()
        for btn in self._tp_s3_rec_btns.values():
            btn.setEnabled(False)
        self.tp_s3_fb_lbl.setText("相序仪已断开，可重新接入")
        set_props(self.tp_s3_fb_lbl, feedbackText=True, tone="neutral")

    def _on_record_psm(self, pt_name: str):
        seq = self._get_phase_seq_meter_sequence() if self._get_phase_seq_meter_sequence else "unknown"
        if seq == "unknown":
            set_feedback_label(self.tp_s3_fb_lbl, "请先接入相序仪，再记录结果。", "orange")
            return
        ok = self._api.record_phase_sequence(pt_name, seq)
        state = self._api.pt_phase_check_state
        set_feedback_label(self.tp_s3_fb_lbl, state.feedback, state.feedback_color)
        if ok and pt_name in self._tp_s3_rec_btns:
            self._tp_s3_rec_btns[pt_name].setEnabled(False)

    def refresh(self, rs, step: int) -> None:
        in_mode = self._api.pt_phase_check_state.started
        for lbl, (text, done) in zip(self.tp_s3_step_lbls, self._api.get_pt_phase_check_steps()):
            set_step_list_label(lbl, text, done, in_mode)
        state = self._api.pt_phase_check_state
        set_feedback_label(self.tp_s3_fb_lbl, state.feedback, state.feedback_color)
