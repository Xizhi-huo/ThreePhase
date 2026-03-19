"""
ui/tabs/circuit_tab.py
母排拓扑图 Tab (Tab 1)
"""

import numpy as np
from PyQt5 import QtCore, QtWidgets
from matplotlib.figure import Figure
import matplotlib.patheffects as pe
from matplotlib.patches import Circle, FancyBboxPatch

from domain.constants import CT_RATIO, TRIP_CURRENT
from domain.node_map import NODES
from ui.tabs.waveform_tab import MplCanvas
from ui.widgets.phase_seq_meter import PhaseSeqMeterWidget

# 第二步快速记录辅助映射
_PHASE_PAIR_LABEL = {
    frozenset({'A', 'B'}): 'AB',
    frozenset({'B', 'C'}): 'BC',
    frozenset({'C', 'A'}): 'CA',
}
_PHASE_TO_PAIR = {'A': 'AB', 'B': 'BC', 'C': 'CA'}


# 热力颜色工具
def rms_to_heat_color(rms: float) -> str:
    ratio = min(rms / TRIP_CURRENT, 1.0)
    r = int(255 * ratio)
    g = int(200 * (1 - ratio))
    return f'#{r:02x}{g:02x}00'


# ── matplotlib 颜色名 → Qt stylesheet hex ────────────────────────────────────
def _qs(color: str) -> str:
    _MAP = {
        'gray': '#808080', 'grey': '#808080',
        'green': '#008000', 'red': '#cc0000',
        'orange': '#ff8800', 'blue': '#0000cc',
        'black': '#000000', 'white': '#ffffff',
        'k': '#000000',
    }
    return _MAP.get(color, color)


class CircuitTabMixin:
    """
    混入类，提供母排拓扑图 Tab 的构建和渲染方法。
    """

    # ── Tab1：母排拓扑 ───────────────────────────────────────────────────────
    def _setup_tab_circuit(self):
        tab = QtWidgets.QWidget()
        self.tab_widget.addTab(tab, " ⚡ 母排拓扑与环流监测 ")
        lay = QtWidgets.QVBoxLayout(tab)
        lay.setContentsMargins(0, 0, 0, 0)

        self.fig2 = Figure(figsize=(8, 6), dpi=100)
        self.ax_circuit = self.fig2.add_subplot(111)
        self.fig2.tight_layout(pad=1.2)
        self.canvas2 = MplCanvas(self.fig2)
        lay.addWidget(self.canvas2)

        # 相序仪：浮动覆盖在 canvas 上，两台发电机正中间
        # 以 canvas2 为父控件，用绝对定位 move() 放置
        self.phase_seq_meter = PhaseSeqMeterWidget(self.canvas2)
        self.phase_seq_meter.setVisible(False)

        # 结果小标签，紧贴在仪器下方
        self._psm_result_lbl = QtWidgets.QLabel("", self.canvas2)
        self._psm_result_lbl.setAlignment(QtCore.Qt.AlignCenter)
        self._psm_result_lbl.setWordWrap(True)
        self._psm_result_lbl.setStyleSheet(
            "color:#ecf0f1; font-size:10px; background:rgba(30,39,46,200);"
            " border-radius:4px; padding:2px 6px;")
        self._psm_result_lbl.setVisible(False)

        # 鼠标点击（万用表）
        self.canvas2.mpl_connect('button_press_event', self._on_circuit_click)
        self._draw_circuit_content()

        # 快速记录栏已移至右侧测试控制条，此处不再重复显示

    # ════════════════════════════════════════════════════════════════════════
    # 母排拓扑静态绘制
    # ════════════════════════════════════════════════════════════════════════
    def _draw_circuit_content(self):
        ax = self.ax_circuit
        ax.cla()

        pt_blackbox_mode = self.ctrl.pt_blackbox_mode_val \
            if hasattr(self.ctrl, 'pt_blackbox_mode_val') \
            else self.ctrl.pt_blackbox_mode.get()
        pt_orders = self.ctrl.pt_phase_orders

        ax.axis('off')
        ax.set_xlim(0.0, 1.0)
        ax.set_ylim(-0.10, 1.02)
        ax.set_title("Switchgear Bus Topology", pad=8, weight='bold', fontsize=12)

        # ── 布局常量 ──────────────────────────────────────────────────────
        BUS_Y      = {'A': 0.115, 'B': 0.090, 'C': 0.065, 'N': 0.040}
        BUS_YL     = [BUS_Y['A'], BUS_Y['B'], BUS_Y['C']]
        BUS_PHASES = ['A', 'B', 'C']
        BUS_COLORS = ['#b45309', '#1a9c3c', '#d62828']
        NEUTRAL_COLOR = '#111111'

        G1_CX, G2_CX = 0.28, 0.72
        PHASE_DX = 0.04
        G1_X = [G1_CX - PHASE_DX, G1_CX, G1_CX + PHASE_DX]
        G2_X = [G2_CX - PHASE_DX, G2_CX, G2_CX + PHASE_DX]

        CB_BOT, CB_TOP = 0.24, 0.31
        CB_LBL_Y = 0.195

        GEN_CY, GEN_R = 0.52, 0.065

        GND_BOT_Y   = GEN_CY + GEN_R
        GND_MERGE_Y = GND_BOT_Y + 0.05
        GND_RES_Y1  = GND_MERGE_Y + 0.025
        GND_RES_Y2  = GND_RES_Y1  + 0.075
        GND_EARTH_Y = GND_RES_Y2  + 0.015

        PT_SIZE   = 0.030
        PT2_CX    = 0.50;  PT2_CY   = 0.205
        PT1_CX    = 0.10;  PT3_CX   = 0.90
        PT_GEN_CY = 0.355

        PT_LBL_Y  = PT_GEN_CY - PT_SIZE - 0.045
        PT2_LBL_Y = PT2_CY    - PT_SIZE - 0.045

        CT_X_LEFT  = 0.02;  CT_X_RIGHT = 0.78
        CT_Y_TOP   = 0.88;  CT_DY = 0.055

        # ── 内部绘图辅助函数 ──────────────────────────────────────────────
        def draw_pt_y_symbol(cx, cy, size, color='#9a3412', yn_side='right'):
            arm_a   = (cx - size*0.90, cy + size*0.85)
            arm_b   = (cx,             cy + size)
            arm_c   = (cx + size*0.90, cy + size*0.85)
            neutral = (cx,             cy - size)
            for tip in (arm_a, arm_b, arm_c):
                ax.plot([cx, tip[0]], [cy, tip[1]], color=color, lw=2.0)
            ax.plot([cx, neutral[0]], [cy, neutral[1]], color=color, lw=1.6, ls='--')
            ax.plot(*neutral, 'o', color=color, markersize=3)
            yn_x  = neutral[0] + (0.012 if yn_side == 'right' else -0.012)
            yn_ha = 'left'     if yn_side == 'right' else 'right'
            ax.text(yn_x, neutral[1], "Yn", fontsize=6, color='#888', va='center', ha=yn_ha)
            return {'A': arm_a, 'B': arm_b, 'C': arm_c, 'N': neutral, 'C_xy': (cx, cy)}

        def draw_pt_blackbox_symbol(cx, cy, size, color='#9a3412'):
            box_w = size*2.2;  box_h = size*1.7
            left  = cx - box_w/2;  bottom = cy - box_h/2
            ax.add_patch(FancyBboxPatch(
                (left, bottom), box_w, box_h,
                boxstyle="round,pad=0.01,rounding_size=0.01",
                fill=False, ec=color, lw=1.8))
            top_y = bottom + box_h + size*0.55
            terms = [(cx - size*0.90, top_y), (cx, top_y), (cx + size*0.90, top_y)]
            for idx, (tx, ty) in enumerate(terms, 1):
                ax.plot([tx, tx], [bottom+box_h, ty], color=color, lw=1.5)
                ax.plot(tx, ty, 'o', color=color, markersize=3)
                ax.text(tx, ty+0.012, f"T{idx}", fontsize=6, color='#666', ha='center')
            neutral = (cx, bottom - size*0.65)
            ax.plot([cx, cx], [bottom, neutral[1]], color=color, lw=1.4, ls='--')
            ax.plot(*neutral, 'o', color=color, markersize=3)
            ax.text(cx, cy, "PT", fontsize=8, color=color, ha='center', va='center', weight='bold')
            ax.text(neutral[0]+0.012, neutral[1], "N", fontsize=6, color='#888', va='center')
            return {'terms': terms, 'N': neutral, 'C_xy': (cx, cy)}

        def draw_pt_wired(src_x, src_y, arm_tip, h_channel_y, color, ls='-'):
            tx, ty = arm_tip
            ax.plot([src_x, src_x], [src_y, h_channel_y],       color=color, lw=1.2, alpha=0.85, ls=ls)
            ax.plot([src_x, tx],    [h_channel_y, h_channel_y], color=color, lw=1.2, alpha=0.85, ls=ls)
            ax.plot([tx, tx],       [h_channel_y, ty],           color=color, lw=1.2, alpha=0.85, ls=ls)
            ax.plot(src_x, src_y, 'o', color='k', markersize=3)

        def draw_pt_full(cx, cy, src_xs, src_ys, channels, label, sub_label,
                         lbl_y, phase_order, ls='-', side='right'):
            # side controls where Yn + PT label appear: 'right' or 'left'
            yn_side = side if side in ('left', 'right') else 'right'
            if pt_blackbox_mode:
                sym       = draw_pt_blackbox_symbol(cx, cy, PT_SIZE)
                terminals = sym['terms']
            else:
                sym       = draw_pt_y_symbol(cx, cy, PT_SIZE, yn_side=yn_side)
                terminals = [sym['A'], sym['B'], sym['C']]
            for sx, sy, ph, color in zip(src_xs, src_ys, BUS_PHASES, BUS_COLORS):
                draw_pt_wired(sx, sy, terminals[phase_order.index(ph)],
                              channels[ph], color, ls=ls)
            offset = PT_SIZE * 1.5
            if side == 'right':
                lbl_x, lbl_ha = cx + offset, 'left'
            elif side == 'left':
                lbl_x, lbl_ha = cx - offset, 'right'
            else:
                lbl_x, lbl_ha = cx, 'center'
            ax.text(lbl_x, cy + PT_SIZE*0.4,  label,    fontsize=7, ha=lbl_ha, color='#9a3412', weight='bold')
            ax.text(lbl_x, cy - PT_SIZE*0.4,  "PT本体", fontsize=6, ha=lbl_ha, color='#555')
            ax.text(lbl_x, cy - PT_SIZE*1.1,  "一次侧", fontsize=6, ha=lbl_ha, color='#666')
            if pt_blackbox_mode:
                ax.text(lbl_x, cy - PT_SIZE*1.8, "黑盒教学模式", fontsize=5.5, ha=lbl_ha, color='#555')
            return sym

        def draw_pt_secondary_terminal_strip(cx, cy, prefix, section_y, line_y, color='#9a3412'):
            node_keys = [f"{prefix}_{ph}" for ph in ('A', 'B', 'C')]
            xs = [NODES[key][0] for key in node_keys]
            y  = NODES[node_keys[0]][1]
            box_left   = min(xs) - 0.020
            box_bottom = y - 0.018
            box_w = (max(xs) - min(xs)) + 0.040
            box_h = 0.040
            ax.add_patch(FancyBboxPatch(
                (box_left, box_bottom), box_w, box_h,
                boxstyle="round,pad=0.004,rounding_size=0.006",
                facecolor='#fffdf5', edgecolor=color, lw=1.2, linestyle='--', alpha=0.95))
            ax.plot([box_left, box_left+box_w], [line_y, line_y], color='#888', lw=1.0, ls=':')
            ax.text(cx, line_y+0.045, "二次端子排", fontsize=6, ha='center', color=color, weight='bold')
            source_y = cy + PT_SIZE*0.75
            for phase, x in zip(('A', 'B', 'C'), xs):
                ax.plot([cx, x], [source_y, section_y], color=color, lw=1.0, alpha=0.9)
                ax.plot([x, x], [section_y, y],         color=color, lw=1.0, alpha=0.9)
                ax.plot(x, y, 'o', color='k', markersize=4, zorder=6)
                ax.text(x, y-0.017, phase, fontsize=6, ha='center', color=color)

        def draw_gen_cabinet(gx_list, ls):
            for ph_idx, (x, color) in enumerate(zip(gx_list, BUS_COLORS)):
                bus_y_ph = BUS_YL[ph_idx]
                ax.plot([x, x], [bus_y_ph, CB_BOT], color=color, lw=2, ls=ls)
                ax.plot(x, bus_y_ph, 'o', color='k', markersize=5)
                ax.plot(x, CB_BOT,   'o', color='k', markersize=4)
                ax.plot(x, CB_TOP,   'o', color='k', markersize=4)
                ax.plot([x, x], [CB_TOP, GEN_CY-GEN_R], color=color, lw=2, ls=ls)

        def draw_generator_neutral_ground(cx):
            fan_xs = [cx-0.030, cx, cx+0.030]
            fan_y  = GND_BOT_Y + 0.02
            # ── 发电机→中性点连接线（断开时隐藏）──────────────────────────
            conn_lines = []
            for fx in fan_xs:
                ln, = ax.plot([fx, fx], [GND_BOT_Y, fan_y], color='k', lw=1.4)
                conn_lines.append(ln)
            ln, = ax.plot([fan_xs[0], fan_xs[-1]], [fan_y, fan_y], color='k', lw=1.4)
            conn_lines.append(ln)
            dot, = ax.plot([cx], [fan_y], 'ko', markersize=4)
            conn_lines.append(dot)
            ln, = ax.plot([cx, cx], [fan_y, GND_RES_Y1], 'k-', lw=1.4)
            conn_lines.append(ln)
            # ── 直接接地旁路线（仅直接接地时显示）────────────────────────
            bypass_ln, = ax.plot([cx, cx], [fan_y, GND_EARTH_Y], 'k-', lw=1.4, visible=False)
            # ── 小电阻符号（直接接地时隐藏）──────────────────────────────
            ry = np.linspace(GND_RES_Y1, GND_RES_Y2, 13)
            rx = [cx + (0.012 if i % 2 == 1 else -0.012) for i in range(len(ry))]
            rx[0] = rx[-1] = cx
            res_zigzag, = ax.plot(rx, ry, 'k-', lw=1.4)
            rn_text = ax.text(cx+0.030, (GND_RES_Y1+GND_RES_Y2)/2, "Rn",
                              fontsize=7, color='#555', va='center')
            post_res_ln, = ax.plot([cx, cx], [GND_RES_Y2, GND_EARTH_Y], 'k-', lw=1.4)
            # ── 接地符号（始终显示）───────────────────────────────────────
            for i, half in enumerate([0.022, 0.015, 0.008]):
                ey = GND_EARTH_Y + i*0.013
                ax.plot([cx-half, cx+half], [ey, ey], 'k-', lw=2.0-i*0.4)
            return {
                'conn':     conn_lines,
                'bypass':   bypass_ln,
                'resistor': [res_zigzag, rn_text, post_res_ln],
            }

        # ── 1. 三相四线母排 ───────────────────────────────────────────────
        BUS_X_L, BUS_X_R = 0.02, 0.98
        _stroke = [pe.withStroke(linewidth=2.5, foreground='black')]
        for ph, color in zip(BUS_PHASES, BUS_COLORS):
            y = BUS_Y[ph]
            ax.plot([BUS_X_L, BUS_X_R], [y, y], color=color, lw=5, solid_capstyle='round')
            for xpos, ha in [(BUS_X_L-0.018, 'center'), (BUS_X_R+0.018, 'center')]:
                ax.text(xpos, y, ph, fontsize=13, ha=ha, va='center',
                        weight='bold', color=color, path_effects=_stroke)
        neutral_y = BUS_Y['N']
        ax.plot([BUS_X_L, BUS_X_R], [neutral_y, neutral_y],
                color=NEUTRAL_COLOR, lw=4, solid_capstyle='round')
        for xpos in [BUS_X_L-0.018, BUS_X_R+0.018]:
            ax.text(xpos, neutral_y, 'N', fontsize=12, ha='center', va='center',
                    weight='bold', color=NEUTRAL_COLOR, path_effects=_stroke)
        self.txt_bus_source = ax.text(
            0.50, -0.035, "Dead Bus (无电)", weight='bold', ha='center', fontsize=10,
            color='#1e293b',
            bbox=dict(facecolor='#f8fafc', edgecolor='#cbd5e1',
                      boxstyle='round,pad=0.3', alpha=0.92))

        # ── 2. 发电机柜 ───────────────────────────────────────────────────
        draw_gen_cabinet(G1_X, '--')
        draw_gen_cabinet(G2_X, '-.')

        self.sw1_pack = [ax.plot([], [], 'k-', lw=4)[0] for _ in range(3)]
        self.sw2_pack = [ax.plot([], [], 'k-', lw=4)[0] for _ in range(3)]

        for cx, label in [(G1_CX, "Gen1 CB"), (G2_CX, "Gen2 CB")]:
            ax.text(cx, CB_LBL_Y, label, fontsize=8, ha='center', color='#222', weight='bold')

        _gen_stroke  = [pe.withStroke(linewidth=3, foreground='white')]
        _side_stroke = [pe.withStroke(linewidth=2, foreground='white')]
        for cx, label in [(G1_CX, "G1"), (G2_CX, "G2")]:
            ax.add_patch(Circle((cx, GEN_CY), GEN_R, fill=False, ec='#111', lw=2.5))
            ax.text(cx, GEN_CY, label, fontsize=13, ha='center', va='center',
                    weight='bold', color='#111', path_effects=_gen_stroke)
        for cx, side, ha in [(G1_CX, -1, 'right'), (G2_CX, 1, 'left')]:
            xpos = cx + side * (GEN_R + 0.025)
            ax.text(xpos, GEN_CY, "机端", fontsize=9, ha=ha, va='center',
                    weight='bold', color='#444', path_effects=_side_stroke)

        for node_name in ('LOOP_G1_A', 'LOOP_G1_B', 'LOOP_G1_C',
                          'LOOP_G2_A', 'LOOP_G2_B', 'LOOP_G2_C'):
            x, y, _, phase, _ = NODES[node_name]
            phase_color = {'A': '#b45309', 'B': '#1a9c3c', 'C': '#d62828'}[phase]
            ax.plot(x, y, 'o', color='k', markersize=4.5, zorder=6)
            ax.text(x, y+0.018, phase, fontsize=6, ha='center', color=phase_color, weight='bold')
        ax.text(0.50, 0.438, "三相回路连通测点", fontsize=7, ha='center', color='#444')

        # ── 3. 中性点接地 ─────────────────────────────────────────────────
        self.gnd_data1 = draw_generator_neutral_ground(G1_CX)
        self.gnd_data2 = draw_generator_neutral_ground(G2_CX)

        # ── 4. PT ─────────────────────────────────────────────────────────
        PT_GEN_CHANNELS = {'A': CB_BOT-0.015, 'B': CB_BOT-0.030, 'C': CB_BOT-0.045}

        draw_pt_full(cx=PT1_CX, cy=PT_GEN_CY, src_xs=G1_X, src_ys=[CB_TOP]*3,
                     channels=PT_GEN_CHANNELS, label="PT1", sub_label="G1机端",
                     phase_order=pt_orders['PT1'], lbl_y=PT_LBL_Y, ls='--', side='right')
        draw_pt_secondary_terminal_strip(PT1_CX, PT_GEN_CY, "PT1", section_y=0.512, line_y=0.500)

        if pt_blackbox_mode:
            sym2  = draw_pt_blackbox_symbol(PT2_CX, PT2_CY, PT_SIZE)
            arms2 = sym2['terms']
        else:
            sym2  = draw_pt_y_symbol(PT2_CX, PT2_CY, PT_SIZE, yn_side='right')
            arms2 = [sym2['A'], sym2['B'], sym2['C']]

        for ph, bus_y_val, color in zip(BUS_PHASES, BUS_YL, BUS_COLORS):
            arm_tx, arm_ty = arms2[pt_orders['PT2'].index(ph)]
            ax.plot(arm_tx, bus_y_val, 'o', color='k', markersize=3)
            ax.plot([arm_tx, arm_tx], [bus_y_val, arm_ty], color=color, lw=1.2, alpha=0.85)
        _pt2_lbl_x = PT2_CX + PT_SIZE * 1.5
        ax.text(_pt2_lbl_x, PT2_CY + PT_SIZE*0.4,  "PT2", fontsize=7, ha='left', color='#9a3412', weight='bold')
        ax.text(_pt2_lbl_x, PT2_CY - PT_SIZE*0.4,  "母排", fontsize=6, ha='left', color='#666')
        if pt_blackbox_mode:
            ax.text(_pt2_lbl_x, PT2_CY - PT_SIZE*1.1, "黑盒教学模式", fontsize=5.5, ha='left', color='#555')
        draw_pt_secondary_terminal_strip(PT2_CX, PT2_CY, "PT2", section_y=0.372, line_y=0.360)

        draw_pt_full(cx=PT3_CX, cy=PT_GEN_CY, src_xs=G2_X, src_ys=[CB_TOP]*3,
                     channels=PT_GEN_CHANNELS, label="PT3", sub_label="G2机端",
                     phase_order=pt_orders['PT3'], lbl_y=PT_LBL_Y, ls='-.', side='left')
        draw_pt_secondary_terminal_strip(PT3_CX, PT_GEN_CY, "PT3", section_y=0.512, line_y=0.500)


        # PT 电压读数文字
        PT_V_LBL_Y  = PT_GEN_CY + PT_SIZE + 0.245
        PT2_V_LBL_Y = PT2_CY   + PT_SIZE + 0.245
        bbox_pt = dict(facecolor='#f8fafc', edgecolor='#9a3412',
                       boxstyle='round,pad=0.25', alpha=0.90)
        self.txt_pt1_v = ax.text(PT1_CX, PT_V_LBL_Y,  "PT1: -- V", fontsize=7,
                                  ha='center', color='#0066cc', bbox=bbox_pt)
        self.txt_pt2_v = ax.text(PT2_CX, PT2_V_LBL_Y, "PT2: -- V", fontsize=7,
                                  ha='center', color='#0066cc', bbox=bbox_pt)
        self.txt_pt3_v = ax.text(PT3_CX, PT_V_LBL_Y,  "PT3: -- V", fontsize=7,
                                  ha='center', color='#0066cc', bbox=bbox_pt)

        # ── 5. 文字信息区 ─────────────────────────────────────────────────
        self.txt_i1  = ax.text(CT_X_LEFT, CT_Y_TOP,         "Gen1  CT: 0.00 A",
                                color='#cc2200', ha='left', weight='bold', fontsize=8)
        self.txt_ip1 = ax.text(CT_X_LEFT, CT_Y_TOP-CT_DY,   "  Ip = 0.00 A  (有功)",
                                color='#0055aa', ha='left', fontsize=7)
        self.txt_iq1 = ax.text(CT_X_LEFT, CT_Y_TOP-2*CT_DY, "  Iq = 0.00 A  (无功)",
                                color='#aa00aa', ha='left', fontsize=7)

        self.txt_grounding = ax.text(
            0.50, 0.97, "N线: 未接地", color='gray', ha='center', fontsize=8,
            bbox=dict(facecolor='#f5f5f5', edgecolor='gray', boxstyle='round,pad=0.3', alpha=0.9))

        self.txt_i2  = ax.text(CT_X_RIGHT, CT_Y_TOP,         "Gen2  CT: 0.00 A",
                                color='#cc2200', ha='left', weight='bold', fontsize=8)
        self.txt_ip2 = ax.text(CT_X_RIGHT, CT_Y_TOP-CT_DY,   "  Ip = 0.00 A  (有功)",
                                color='#0055aa', ha='left', fontsize=7)
        self.txt_iq2 = ax.text(CT_X_RIGHT, CT_Y_TOP-2*CT_DY, "  Iq = 0.00 A  (无功)",
                                color='#aa00aa', ha='left', fontsize=7)

        self.txt_circ_flow = ax.text(
            0.30, -0.06, "机组间无环流", color='gray', ha='center', weight='bold', fontsize=9,
            bbox=dict(facecolor='#ffffff', edgecolor='gray', alpha=0.9, boxstyle='round,pad=0.3'))
        self.txt_meter = ax.text(
            0.70, -0.06, "万用表未开启", color='black', ha='center', weight='bold', fontsize=9,
            bbox=dict(facecolor='#ffffcc', edgecolor='black', boxstyle='round,pad=0.4'),
            clip_on=False)

        self.probe1_plot, = ax.plot([], [], 'ro', markersize=12, alpha=0.8)
        self.probe2_plot, = ax.plot([], [], 'ko', markersize=12, alpha=0.8)

    def rebuild_circuit_diagram(self):
        """PT 黑盒模式切换时重绘拓扑图（由 ctrl 调用）。"""
        self._draw_circuit_content()
        self.canvas2.draw()

    # ════════════════════════════════════════════════════════════════════════
    # 渲染方法
    # ════════════════════════════════════════════════════════════════════════
    def _render_ct_readings(self, p):
        self.txt_i1.set_text(f"Gen1  CT: {p.i1_rms/CT_RATIO:.2f} A")
        self.txt_ip1.set_text(f"  Ip = {p.ip1/CT_RATIO:.2f} A  (有功)")
        self.txt_iq1.set_text(f"  Iq = {p.iq1/CT_RATIO:.2f} A  (无功)")
        self.txt_i2.set_text(f"Gen2  CT: {p.i2_rms/CT_RATIO:.2f} A")
        self.txt_ip2.set_text(f"  Ip = {p.ip2/CT_RATIO:.2f} A  (有功)")
        self.txt_iq2.set_text(f"  Iq = {p.iq2/CT_RATIO:.2f} A  (无功)")
        self.txt_circ_flow.set_text(p.circ_msg)
        self.txt_circ_flow.set_color(p.circ_color)
        self.txt_circ_flow.get_bbox_patch().set_edgecolor(p.circ_color)

    # ── 相序仪 Public API ─────────────────────────────────────────────────
    def connect_phase_seq_meter(self, pt_name: str):
        """接入相序仪到指定 PT，浮动显示在 canvas 中央两台发电机之间。"""
        seq = self.ctrl.get_pt_phase_sequence(pt_name)
        self.phase_seq_meter.connect_pt(pt_name, seq)
        sim = self.ctrl.sim_state
        freq = sim.gen1.freq if pt_name in ('PT1', 'PT2') else sim.gen2.freq
        self.phase_seq_meter.set_freq(freq)

        # 用 axes 边界框将数据坐标 (G1/G2 中点) 转换为 canvas 像素坐标
        # G1_CX=0.28, G2_CX=0.72, GEN_CY=0.52；xlim=(0,1), ylim=(-0.10,1.02)
        mw, mh = self.phase_seq_meter.width(), self.phase_seq_meter.height()
        try:
            bbox   = self.ax_circuit.get_position()  # axes bbox 占图比例 (y 从底部)
            xlim   = self.ax_circuit.get_xlim()       # (0.0, 1.0)
            ylim   = self.ax_circuit.get_ylim()       # (-0.10, 1.02)
            ax_fx  = (0.50 - xlim[0]) / (xlim[1] - xlim[0])   # 0.50 → 0.50
            ax_fy  = (0.72 - ylim[0]) / (ylim[1] - ylim[0])   # 0.72 → 发电机上方空白区
            fig_fx = bbox.x0 + ax_fx * (bbox.x1 - bbox.x0)    # 图比例 x
            fig_fy = bbox.y0 + ax_fy * (bbox.y1 - bbox.y0)    # 图比例 y (从底)
            cw     = self.canvas2.width()
            ch     = self.canvas2.height()
            px     = int(fig_fx * cw)
            py     = int((1.0 - fig_fy) * ch)                 # 翻转：Qt y 从顶
        except Exception:
            cw, ch = self.canvas2.width(), self.canvas2.height()
            px, py = cw // 2, ch // 2
        mx = px - mw // 2
        my = py - mh // 2
        self.phase_seq_meter.move(mx, my)
        self.phase_seq_meter.setVisible(True)
        self.phase_seq_meter.raise_()

        # 结果标签紧贴仪器下方
        color = '#2ecc71' if seq == 'ABC' else '#e74c3c'
        self._psm_result_lbl.setText(
            f"{pt_name} → {seq}  "
            f"{'✓ 正序' if seq == 'ABC' else '✗ 逆序'}")
        self._psm_result_lbl.setStyleSheet(
            f"color:{color}; font-size:10px;"
            " background:rgba(30,39,46,200);"
            " border-radius:4px; padding:2px 6px;")
        self._psm_result_lbl.adjustSize()
        lw = self._psm_result_lbl.width()
        self._psm_result_lbl.move(max(0, px - lw // 2), my + mh + 4)
        self._psm_result_lbl.setVisible(True)
        self._psm_result_lbl.raise_()

    def disconnect_phase_seq_meter(self):
        """断开相序仪，隐藏浮层。"""
        self.phase_seq_meter.disconnect()
        self.phase_seq_meter.setVisible(False)
        self._psm_result_lbl.setVisible(False)

    def _render_bus_status(self, p):
        self.bus_status_lbl.setText(p.bus_status_msg)
        if p.bus_live:
            self.bus_status_lbl.setStyleSheet(
                "background:#dcfce7; color:#15803d; font-weight:bold;"
                " padding:5px; font-size:12px; border-radius:4px;"
                " border:1px solid #86efac;")
        else:
            self.bus_status_lbl.setStyleSheet(
                "background:#fef3c7; color:#92400e; font-weight:bold;"
                " padding:5px; font-size:12px; border-radius:4px;"
                " border:1px solid #fcd34d;")
        self.bus_reference_lbl.setText(p.bus_reference_msg)
        self.bus_reference_lbl.setStyleSheet(
            f"background:#f8fafc; color:{'#15803d' if p.bus_live else '#64748b'}; "
            f"font-weight:bold; padding:4px; font-size:12px; border-radius:4px;"
            f" border:1px solid #e2e8f0;")
        src_map = {
            1:      "Bus ← Gen 1",
            2:      "Bus ← Gen 2",
            "both": p.bus_reference_msg.replace("参考基准: ", "Bus Ref ← "),
            "grid": "Grid Source",
        }
        self.txt_bus_source.set_text(src_map.get(p.bus_source, "Dead Bus (无电)"))

    def _render_breakers(self, p):
        self.arbitrator_lbl.setText(p.arb_msg)
        self.arbitrator_lbl.setStyleSheet(
            f"background:#eff6ff; color:#1d4ed8; font-weight:bold; padding:6px; font-size:12px;"
            f" border-radius:4px; border:1px solid #bfdbfe;")
        self.relay_lbl.setText(p.relay_msg)
        self.relay_lbl.setStyleSheet(f"color:{_qs(p.relay_color)}; font-size:12px; padding:3px;")

        for lbl_attr, text, bg in [
            ('status1_lbl', p.brk1_text, p.brk1_bg),
            ('status2_lbl', p.brk2_text, p.brk2_bg),
        ]:
            lbl = getattr(self, lbl_attr)
            lbl.setText(text)
            bg_str = _qs(bg)
            # Map legacy dark colors to new theme palette
            if bg_str in ('#00cc00', '#009900', '#006600', '#00ff00'):
                style = ("background:#dcfce7; color:#15803d; font-weight:bold;"
                         " padding:3px; font-size:12px; border-radius:3px;"
                         " border:1px solid #86efac;")
            elif bg_str in ('#cc0000', '#ff0000', '#990000', '#ff3333'):
                style = ("background:#fee2e2; color:#dc2626; font-weight:bold;"
                         " padding:3px; font-size:12px; border-radius:3px;"
                         " border:1px solid #fca5a5;")
            elif bg_str in ('#ffaa00', '#ffcc00', '#ff9900', '#d97706'):
                style = ("background:#fef3c7; color:#92400e; font-weight:bold;"
                         " padding:3px; font-size:12px; border-radius:3px;"
                         " border:1px solid #fcd34d;")
            elif bg_str in ('#333399', '#0000ff', '#1d4ed8'):
                style = ("background:#eff6ff; color:#1d4ed8; font-weight:bold;"
                         " padding:3px; font-size:12px; border-radius:3px;"
                         " border:1px solid #93c5fd;")
            else:
                tc = 'white' if bg_str not in ('#ffaa00', '#ffcc00') else 'black'
                style = (f"background:{bg_str}; color:{tc}; font-weight:bold;"
                         f" padding:3px; font-size:12px; border-radius:3px;")
            lbl.setStyleSheet(style)

        for lines, xs, y_bot, y_top, is_closed in [
            (self.sw1_pack, [0.24, 0.28, 0.32], 0.24, 0.31, p.brk1_visual),
            (self.sw2_pack, [0.68, 0.72, 0.76], 0.24, 0.31, p.brk2_visual),
        ]:
            color1 = p.color_sw1 if lines is self.sw1_pack else p.color_sw2
            for line, x in zip(lines, xs):
                line.set_color(color1)
                if is_closed:
                    line.set_data([x, x], [y_bot, y_top])
                else:
                    line.set_data([x, x+0.02], [y_bot, y_top-0.02])

    def _render_grounding_and_pt(self, p):
        self.txt_grounding.set_text(p.ground_msg)
        self.txt_grounding.set_color(p.ground_color)
        self.txt_grounding.get_bbox_patch().set_edgecolor(p.ground_color)
        # 根据接地模式动态更新中性点连接线和电阻符号
        gnd_mode = self.ctrl.sim_state.grounding_mode
        disconnected = (gnd_mode == "断开")
        direct       = (gnd_mode == "直接接地")
        for gnd in (self.gnd_data1, self.gnd_data2):
            for ln in gnd['conn']:
                ln.set_visible(not disconnected)
            gnd['bypass'].set_visible(not disconnected and direct)
            for art in gnd['resistor']:
                art.set_visible(not direct)
        for txt, label, v in [
            (self.txt_pt1_v, "PT1", p.pt1_v),
            (self.txt_pt2_v, "PT2", p.pt2_v),
            (self.txt_pt3_v, "PT3", p.pt3_v),
        ]:
            txt.set_text(f"{label}: {v:.1f}V")
            txt.set_color('#15803d' if v > 90.0 else '#9a3412' if v > 10.0 else '#94a3b8')

    def _render_multimeter(self, p):
        if self.ctrl.sim_state.multimeter_mode:
            self.txt_meter.set_text(p.meter_reading)
            self.txt_meter.set_color(getattr(p, 'meter_color', 'black'))
            self.txt_meter.set_visible(True)
            if self.ctrl.sim_state.probe1_node:
                nx, ny = NODES[self.ctrl.sim_state.probe1_node][:2]
                self.probe1_plot.set_data([nx], [ny])
            else:
                self.probe1_plot.set_data([], [])
            if self.ctrl.sim_state.probe2_node:
                nx, ny = NODES[self.ctrl.sim_state.probe2_node][:2]
                self.probe2_plot.set_data([nx], [ny])
            else:
                self.probe2_plot.set_data([], [])
        else:
            self.txt_meter.set_visible(False)
            self.probe1_plot.set_data([], [])
            self.probe2_plot.set_data([], [])

    def _render_circuit_quick_record(self, p):
        """更新母排拓扑页底部快速记录栏的按钮状态与提示文字。"""
        sim = self.ctrl.sim_state
        if not sim.multimeter_mode or not (sim.probe1_node and sim.probe2_node):
            self.circuit_mode_lbl.setText("万用表未开启或表笔未放置")
            for ph in ('A', 'B', 'C'):
                btn = getattr(self, f'circuit_rec_btn_{ph}')
                btn.setEnabled(False)
                btn.setStyleSheet("font-size:13px;")
            return

        info1 = NODES[sim.probe1_node]
        loop_pair = info1[2].startswith('Loop')

        if loop_pair:
            state = self.ctrl.loop_test_state
            if state.completed:
                self.circuit_mode_lbl.setText("第一步已完成，数据已锁定")
                for ph in ('A', 'B', 'C'):
                    getattr(self, f'circuit_rec_btn_{ph}').setEnabled(False)
                return
            self.circuit_mode_lbl.setText("第一步：回路连通性 — 快速记录")
            for ph in ('A', 'B', 'C'):
                recorded = state.records[ph] is not None
                btn = getattr(self, f'circuit_rec_btn_{ph}')
                btn.setEnabled(not recorded)
                btn.setStyleSheet(
                    f"font-size:13px; background:{'#c8f0c8' if recorded else '#ffffff'};")
        elif not self.ctrl.is_pt_voltage_check_complete():
            # ── 第二步：PT 单体线电压检查 ──────────────────────────────────────
            n1, n2 = sim.probe1_node, sim.probe2_node
            _pt1 = n1.rsplit('_', 1)[0] if n1 and '_' in n1 else ''
            _pt2 = n2.rsplit('_', 1)[0] if n2 and '_' in n2 else ''
            _ph1 = n1.rsplit('_', 1)[1] if n1 and '_' in n1 else ''
            _ph2 = n2.rsplit('_', 1)[1] if n2 and '_' in n2 else ''
            intra_pt = (_pt1 == _pt2 and _pt1 in ('PT1', 'PT2', 'PT3') and
                        _ph1 in ('A', 'B', 'C') and _ph2 in ('A', 'B', 'C') and _ph1 != _ph2)
            if not intra_pt:
                self.circuit_mode_lbl.setText("第二步：请将两支表笔放在同一 PT 的两相端子上")
                for ph in ('A', 'B', 'C'):
                    btn = getattr(self, f'circuit_rec_btn_{ph}')
                    btn.setEnabled(False)
                    btn.setStyleSheet("font-size:13px;")
                return
            state2 = self.ctrl.pt_voltage_check_state
            pair_key = _PHASE_PAIR_LABEL.get(frozenset({_ph1, _ph2}), '')
            self.circuit_mode_lbl.setText(f"第二步：{_pt1} {pair_key}线电压 — 快速记录")
            for ph in ('A', 'B', 'C'):
                btn = getattr(self, f'circuit_rec_btn_{ph}')
                this_pair = _PHASE_TO_PAIR[ph]
                rec_key = f"{_pt1}_{this_pair}"
                already_rec = state2.records.get(rec_key) is not None
                is_current = (this_pair == pair_key)
                btn.setEnabled(is_current and not already_rec)
                btn.setStyleSheet(
                    f"font-size:13px; background:{'#c8f0c8' if already_rec else '#ffffff'};")
        elif not self.ctrl.is_pt_phase_check_complete():
            # ── 第三步：PT 相序检查 ────────────────────────────────────────────
            pt_name = None
            for node in (sim.probe1_node, sim.probe2_node):
                if node and node.startswith('PT') and not node.startswith('PT2'):
                    pt_name = node.split('_')[0]  # 'PT1' or 'PT3'
                    break
            if pt_name is None:
                self.circuit_mode_lbl.setText("第三步：请将表笔放在 PT1_X 或 PT3_X 与 PT2_X 上")
                for ph in ('A', 'B', 'C'):
                    getattr(self, f'circuit_rec_btn_{ph}').setEnabled(False)
                return
            state = self.ctrl.pt_phase_check_state
            if state.completed:
                self.circuit_mode_lbl.setText("第三步 PT相序已完成，数据已锁定")
                for ph in ('A', 'B', 'C'):
                    getattr(self, f'circuit_rec_btn_{ph}').setEnabled(False)
                return
            self.circuit_mode_lbl.setText(f"第三步：{pt_name}/PT2 相序 — 快速记录")
            records = state.records
            for ph in ('A', 'B', 'C'):
                key = f"{pt_name}_{ph}"
                recorded = records.get(key) is not None
                btn = getattr(self, f'circuit_rec_btn_{ph}')
                btn.setEnabled(not recorded)
                btn.setStyleSheet(
                    f"font-size:13px; background:{'#c8f0c8' if recorded else '#ffffff'};")
        else:
            # ── 第四步：PT 压差测试 ────────────────────────────────────────────
            gen_id = getattr(self, '_pt_target_bg').checkedId()
            if gen_id <= 0:
                gen_id = 1
            state = self.ctrl.pt_exam_states[gen_id]
            if state.completed:
                self.circuit_mode_lbl.setText(f"第四步 Gen {gen_id} 已完成，数据已锁定")
                for ph in ('A', 'B', 'C'):
                    getattr(self, f'circuit_rec_btn_{ph}').setEnabled(False)
                return
            if not state.started:
                self.circuit_mode_lbl.setText("第四步尚未开始 — 请在第四步标签页点击「开始第四步测试」")
                for ph in ('A', 'B', 'C'):
                    getattr(self, f'circuit_rec_btn_{ph}').setEnabled(False)
                return
            self.circuit_mode_lbl.setText(f"第四步：Gen {gen_id} PT 二次压差 — 快速记录")
            for ph in ('A', 'B', 'C'):
                recorded = state.records[ph] is not None
                btn = getattr(self, f'circuit_rec_btn_{ph}')
                btn.setEnabled(not recorded)
                btn.setStyleSheet(
                    f"font-size:13px; background:{'#c8f0c8' if recorded else '#ffffff'};")

    def _on_quick_record(self, phase):
        """母排拓扑页快速记录按钮回调。"""
        sim = self.ctrl.sim_state
        if not (sim.probe1_node and sim.probe2_node):
            return
        info1 = NODES[sim.probe1_node]
        loop_pair = info1[2].startswith('Loop')
        if loop_pair:
            self.ctrl.record_loop_measurement(phase)
            st = self.ctrl.loop_test_state
            self.circuit_rec_feedback.setText(st.feedback)
            self.circuit_rec_feedback.setStyleSheet(
                f"font-size:13px; color:{_qs(st.feedback_color)}; min-width:220px;")
        elif not self.ctrl.is_pt_voltage_check_complete():
            # 第二步：PT 单体线电压 — 直接记录同一 PT 内两相端子的线电压
            n1, n2 = sim.probe1_node, sim.probe2_node
            _pt1 = n1.rsplit('_', 1)[0] if n1 and '_' in n1 else ''
            _pt2 = n2.rsplit('_', 1)[0] if n2 and '_' in n2 else ''
            _ph1 = n1.rsplit('_', 1)[1] if n1 and '_' in n1 else ''
            _ph2 = n2.rsplit('_', 1)[1] if n2 and '_' in n2 else ''
            intra_pt = (_pt1 == _pt2 and _pt1 in ('PT1', 'PT2', 'PT3') and
                        _ph1 in ('A', 'B', 'C') and _ph2 in ('A', 'B', 'C') and _ph1 != _ph2)
            if not intra_pt:
                return
            pair_key = _PHASE_PAIR_LABEL.get(frozenset({_ph1, _ph2}), '')
            if _PHASE_TO_PAIR.get(phase) != pair_key:
                return  # 按下的按钮与当前表笔所在线对不对应
            self.ctrl.record_pt_voltage_measurement(_pt1, pair_key)
            st = self.ctrl.pt_voltage_check_state
            self.circuit_rec_feedback.setText(st.feedback)
            self.circuit_rec_feedback.setStyleSheet(
                f"font-size:13px; color:{_qs(st.feedback_color)}; min-width:220px;")
        elif not self.ctrl.is_pt_phase_check_complete():
            # 第三步：PT 相序检查快速记录
            pt_name = None
            for node in (sim.probe1_node, sim.probe2_node):
                if node and node.startswith('PT') and not node.startswith('PT2'):
                    pt_name = node.split('_')[0]
                    break
            if pt_name is None:
                return
            self.ctrl.record_pt_phase_check(pt_name, phase)
            st = self.ctrl.pt_phase_check_state
            self.circuit_rec_feedback.setText(st.feedback)
            self.circuit_rec_feedback.setStyleSheet(
                f"font-size:13px; color:{_qs(st.feedback_color)}; min-width:220px;")
        else:
            # 第四步：PT 压差测试（只有已开始才记录）
            gen_id = getattr(self, '_pt_target_bg').checkedId()
            if gen_id <= 0:
                gen_id = 1
            if not self.ctrl.pt_exam_states[gen_id].started:
                return
            self.ctrl.record_pt_measurement(phase, gen_id)
            st = self.ctrl.pt_exam_states[gen_id]
            self.circuit_rec_feedback.setText(st.feedback)
            self.circuit_rec_feedback.setStyleSheet(
                f"font-size:13px; color:{_qs(st.feedback_color)}; min-width:220px;")
