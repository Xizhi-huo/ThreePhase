"""
ui_plots.py  ──  matplotlib 图形模块
三相电并网仿真教学系统 · 绘图层

职责：
  - Tab1（波形与相量图）的 Figure / Axes 初始化
  - Tab2（母排拓扑图）的静态图形绘制与动态元素初始化
  - 每帧渲染：_render_waveforms / _render_phasors / _render_ct_readings
            _render_bus_status / _render_breakers / _render_grounding_and_pt
            _render_multimeter / _render_pt_exam
  - MplCanvas 封装类

不含任何 QWidget 控件搭建逻辑；通过 self.ctrl 访问控制器。
"""

import numpy as np
from PyQt5 import QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.gridspec as gridspec
import matplotlib.patheffects as pe
from matplotlib.ticker import MultipleLocator
from matplotlib.patches import Circle, FancyBboxPatch

from config_qt5 import CT_RATIO, TRIP_CURRENT
from ui_nodes import NODES


# ── 热力颜色工具 ─────────────────────────────────────────────────────────────
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


# ════════════════════════════════════════════════════════════════════════════
# MplCanvas  —  单张 matplotlib Figure 嵌入 Qt
# ════════════════════════════════════════════════════════════════════════════
class MplCanvas(FigureCanvas):
    def __init__(self, fig: Figure):
        super().__init__(fig)
        self.setMinimumSize(400, 300)
        FigureCanvas.setSizePolicy(
            self,
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding,
        )
        FigureCanvas.updateGeometry(self)


# ════════════════════════════════════════════════════════════════════════════
# Mixin：图形搭建 + 渲染
# ════════════════════════════════════════════════════════════════════════════
class PlotBuilderMixin:
    """
    混入类，为 PowerSyncUI 提供所有 matplotlib 相关方法。
    """

    # ── Tab1：波形与相量 ─────────────────────────────────────────────────────
    def _setup_tab_waveforms(self):
        tab = QtWidgets.QWidget()
        self.tab_widget.addTab(tab, " 📊 实时波形与同期表 ")
        lay = QtWidgets.QVBoxLayout(tab)
        lay.setContentsMargins(0, 0, 0, 0)

        self.fig1 = Figure(figsize=(8, 6), dpi=100)
        gs1 = gridspec.GridSpec(3, 2, width_ratios=[1.2, 1.0], figure=self.fig1)
        self.ax_a   = self.fig1.add_subplot(gs1[0, 0])
        self.ax_b   = self.fig1.add_subplot(gs1[1, 0])
        self.ax_c   = self.fig1.add_subplot(gs1[2, 0])
        self.ax_p   = self.fig1.add_subplot(gs1[0:2, 1], projection='polar')
        self.ax_all = self.fig1.add_subplot(gs1[2, 1])

        deg_end = self.ctrl.physics.fixed_deg[-1]
        for ax, ph in zip([self.ax_a, self.ax_b, self.ax_c],
                          ["Phase A", "Phase B", "Phase C"]):
            ax.set_title(ph, fontsize=10)
            ax.set_ylabel("Voltage(V)", fontsize=8)
            ax.set_ylim(-10000, 10000)
            ax.set_xlim(0, deg_end)
            ax.grid(True, linestyle='--', alpha=0.5)
            ax.xaxis.set_major_locator(MultipleLocator(90))
            if ax != self.ax_c:
                ax.set_xticklabels([])
            else:
                ax.tick_params(axis='x', labelrotation=45, labelsize=8)
        self.ax_c.set_xlabel("Recent Window (°)", fontsize=9)

        self.ax_p.set_title("Phasor Diagram", pad=28, fontsize=11, weight='bold')
        self.ax_p.set_rmax(10000)
        self.ax_p.set_rticks([3000, 6000, 9000])
        self.ax_p.set_rlabel_position(22)
        self.ax_p.set_thetagrids(
            np.arange(0, 360, 45),
            labels=["0°", "45°", "90°", "135°", "180°", "225°", "270°", "315°"],
        )
        self.ax_p.tick_params(axis='x', pad=2)
        self.ax_p.tick_params(axis='y', labelsize=8)

        self.ax_all.set_title("Main Grid Busbar", fontsize=10, weight='bold')
        self.ax_all.set_ylim(-10000, 10000)
        self.ax_all.set_xlim(0, deg_end)
        self.ax_all.grid(True, linestyle='-', alpha=0.6)
        self.ax_all.xaxis.set_major_locator(MultipleLocator(90))
        self.ax_all.tick_params(axis='x', labelrotation=45, labelsize=8)

        self.fig1.tight_layout(pad=1.2)
        self.canvas1 = MplCanvas(self.fig1)
        lay.addWidget(self.canvas1)

    # ── Tab2：母排拓扑 ───────────────────────────────────────────────────────
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

        # 鼠标点击（万用表）
        self.canvas2.mpl_connect('button_press_event', self._on_circuit_click)
        self._draw_circuit_content()

    # ── 波形线 / 相量线初始化 ────────────────────────────────────────────────
    def _init_lines(self):
        self._init_waveform_lines()
        self._init_phasor_lines()

    def _init_waveform_lines(self):
        self.line_ga,     = self.ax_a.plot([], [], color='#d4aa00', lw=2,   label='Busbar')
        self.line_gen1_a, = self.ax_a.plot([], [], color='#d4aa00', ls='--', lw=1.5, alpha=0.7, label='Gen1')
        self.line_gen2_a, = self.ax_a.plot([], [], color='#d4aa00', ls='-.', lw=1.5, alpha=0.7, label='Gen2')

        self.line_gb,     = self.ax_b.plot([], [], color='#1a9c3c', lw=2,   label='Busbar')
        self.line_gen1_b, = self.ax_b.plot([], [], color='#1a9c3c', ls='--', lw=1.5, alpha=0.7, label='Gen1')
        self.line_gen2_b, = self.ax_b.plot([], [], color='#1a9c3c', ls='-.', lw=1.5, alpha=0.7, label='Gen2')

        self.line_gc,     = self.ax_c.plot([], [], color='#d62828', lw=2,   label='Busbar')
        self.line_gen1_c, = self.ax_c.plot([], [], color='#d62828', ls='--', lw=1.5, alpha=0.7, label='Gen1')
        self.line_gen2_c, = self.ax_c.plot([], [], color='#d62828', ls='-.', lw=1.5, alpha=0.7, label='Gen2')

        self.line_all_a,  = self.ax_all.plot([], [], color='#d4aa00', lw=2.5, label='Phase A')
        self.line_all_b,  = self.ax_all.plot([], [], color='#1a9c3c', lw=2.5, label='Phase B')
        self.line_all_c,  = self.ax_all.plot([], [], color='#d62828', lw=2.5, label='Phase C')

        for ax in [self.ax_a, self.ax_b, self.ax_c]:
            ax.legend(loc='upper right', fontsize=7, ncol=3)

    def _init_phasor_lines(self):
        self.p_ga,  = self.ax_p.plot([], [], color='#d4aa00', lw=3,   alpha=0.6, marker='o', markersize=8)
        self.p_g1a, = self.ax_p.plot([], [], color='#d4aa00', ls='--', lw=1.5, marker='X', markersize=5)
        self.p_g2a, = self.ax_p.plot([], [], color='#d4aa00', ls='-.', lw=1.5, marker='*', markersize=6)
        self.p_gb,  = self.ax_p.plot([], [], color='#1a9c3c', lw=3,   alpha=0.6, marker='o', markersize=8)
        self.p_g1b, = self.ax_p.plot([], [], color='#1a9c3c', ls='--', lw=1.5, marker='X', markersize=5)
        self.p_g2b, = self.ax_p.plot([], [], color='#1a9c3c', ls='-.', lw=1.5, marker='*', markersize=6)
        self.p_gc,  = self.ax_p.plot([], [], color='#d62828', lw=3,   alpha=0.6, marker='o', markersize=8)
        self.p_g1c, = self.ax_p.plot([], [], color='#d62828', ls='--', lw=1.5, marker='X', markersize=5)
        self.p_g2c, = self.ax_p.plot([], [], color='#d62828', ls='-.', lw=1.5, marker='*', markersize=6)

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
        BUS_COLORS = ['#d4aa00', '#1a9c3c', '#d62828']
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
        def draw_pt_y_symbol(cx, cy, size, color='#cc6600'):
            arm_a   = (cx - size*0.90, cy + size*0.85)
            arm_b   = (cx,             cy + size)
            arm_c   = (cx + size*0.90, cy + size*0.85)
            neutral = (cx,             cy - size)
            for tip in (arm_a, arm_b, arm_c):
                ax.plot([cx, tip[0]], [cy, tip[1]], color=color, lw=2.0)
            ax.plot([cx, neutral[0]], [cy, neutral[1]], color=color, lw=1.6, ls='--')
            ax.plot(*neutral, 'o', color=color, markersize=3)
            ax.text(neutral[0]+0.012, neutral[1], "Yn", fontsize=6, color='#888', va='center')
            return {'A': arm_a, 'B': arm_b, 'C': arm_c, 'N': neutral, 'C_xy': (cx, cy)}

        def draw_pt_blackbox_symbol(cx, cy, size, color='#cc6600'):
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
                         lbl_y, phase_order, ls='-', side='center'):
            if pt_blackbox_mode:
                sym       = draw_pt_blackbox_symbol(cx, cy, PT_SIZE)
                terminals = sym['terms']
            else:
                sym       = draw_pt_y_symbol(cx, cy, PT_SIZE)
                terminals = [sym['A'], sym['B'], sym['C']]
            for sx, sy, ph, color in zip(src_xs, src_ys, BUS_PHASES, BUS_COLORS):
                draw_pt_wired(sx, sy, terminals[phase_order.index(ph)],
                              channels[ph], color, ls=ls)
            ax.text(cx, lbl_y,       label,     fontsize=7, ha='center', color='#cc6600', weight='bold')
            ax.text(cx, lbl_y-0.03,  sub_label, fontsize=6, ha='center', color='#666')
            if pt_blackbox_mode:
                ax.text(cx, lbl_y-0.055, "黑盒教学模式", fontsize=5.5, ha='center', color='#555')
            # "PT本体" / "一次侧" 标注在 Y 型图案旁边（黑盒模式下不显示）
            if not pt_blackbox_mode:
                if side == 'left':
                    lbl_x, lbl_ha = cx - PT_SIZE*1.1, 'right'
                elif side == 'right':
                    lbl_x, lbl_ha = cx + PT_SIZE*1.1, 'left'
                else:
                    lbl_x, lbl_ha = cx, 'center'
                ax.text(lbl_x, cy + PT_SIZE*0.15, "PT本体", fontsize=10, ha=lbl_ha, color='#555')
                ax.text(lbl_x, cy - PT_SIZE*0.35, "一次侧", fontsize=10, ha=lbl_ha, color='#666')
            return sym

        def draw_pt_secondary_terminal_strip(cx, cy, prefix, section_y, line_y, color='#cc6600'):
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
            ax.text(cx, box_bottom+box_h+0.015, f"{prefix}二次端子", fontsize=5.5, ha='center', color='#444')
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
            for fx in fan_xs:
                ax.plot([fx, fx], [GND_BOT_Y, fan_y], color='k', lw=1.4)
            ax.plot([fan_xs[0], fan_xs[-1]], [fan_y, fan_y], color='k', lw=1.4)
            ax.plot(cx, fan_y, 'ko', markersize=4)
            ax.plot([cx, cx], [fan_y, GND_RES_Y1], 'k-', lw=1.4)
            ry = np.linspace(GND_RES_Y1, GND_RES_Y2, 13)
            rx = [cx + (0.012 if i % 2 == 1 else -0.012) for i in range(len(ry))]
            rx[0] = rx[-1] = cx
            ax.plot(rx, ry, 'k-', lw=1.4)
            ax.text(cx+0.030, (GND_RES_Y1+GND_RES_Y2)/2, "Rn", fontsize=7, color='#555', va='center')
            ax.plot([cx, cx], [GND_RES_Y2, GND_EARTH_Y], 'k-', lw=1.4)
            for i, half in enumerate([0.022, 0.015, 0.008]):
                ey = GND_EARTH_Y + i*0.013
                ax.plot([cx-half, cx+half], [ey, ey], 'k-', lw=2.0-i*0.4)

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
            0.50, -0.035, "Dead Bus (无电)", weight='bold', ha='center', fontsize=10, color='#333')

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
            lbl  = "G1" if side == -1 else "G2"
            ax.text(xpos, GEN_CY+0.02, lbl,   fontsize=11, ha=ha, va='center',
                    weight='bold', color='#111', path_effects=_side_stroke)
            ax.text(xpos, GEN_CY-0.02, "机端", fontsize=9,  ha=ha, va='center',
                    weight='bold', color='#444', path_effects=_side_stroke)

        for node_name in ('LOOP_G1_A', 'LOOP_G1_B', 'LOOP_G1_C',
                          'LOOP_G2_A', 'LOOP_G2_B', 'LOOP_G2_C'):
            x, y, _, phase, _ = NODES[node_name]
            phase_color = {'A': '#d4aa00', 'B': '#1a9c3c', 'C': '#d62828'}[phase]
            ax.plot(x, y, 'o', color='k', markersize=4.5, zorder=6)
            ax.text(x, y+0.018, phase, fontsize=6, ha='center', color=phase_color, weight='bold')
        ax.text(0.50, 0.438, "三相回路连通测点", fontsize=7, ha='center', color='#444')
        ax.text(0.50, 0.423, "断开接地并闭合两台开关后，用于演示相序对应", fontsize=6, ha='center', color='#666')

        # ── 3. 中性点接地 ─────────────────────────────────────────────────
        draw_generator_neutral_ground(G1_CX)
        draw_generator_neutral_ground(G2_CX)

        # ── 4. PT ─────────────────────────────────────────────────────────
        PT_GEN_CHANNELS = {'A': CB_BOT-0.015, 'B': CB_BOT-0.030, 'C': CB_BOT-0.045}

        draw_pt_full(cx=PT1_CX, cy=PT_GEN_CY, src_xs=G1_X, src_ys=[CB_BOT]*3,
                     channels=PT_GEN_CHANNELS, label="PT1", sub_label="G1机端",
                     phase_order=pt_orders['PT1'], lbl_y=PT_LBL_Y, ls='--', side='left')
        draw_pt_secondary_terminal_strip(PT1_CX, PT_GEN_CY, "PT1", section_y=0.512, line_y=0.500)

        if pt_blackbox_mode:
            sym2  = draw_pt_blackbox_symbol(PT2_CX, PT2_CY, PT_SIZE)
            arms2 = sym2['terms']
        else:
            sym2  = draw_pt_y_symbol(PT2_CX, PT2_CY, PT_SIZE)
            arms2 = [sym2['A'], sym2['B'], sym2['C']]

        for ph, bus_y_val, color in zip(BUS_PHASES, BUS_YL, BUS_COLORS):
            arm_tx, arm_ty = arms2[pt_orders['PT2'].index(ph)]
            ax.plot(arm_tx, bus_y_val, 'o', color='k', markersize=3)
            ax.plot([arm_tx, arm_tx], [bus_y_val, arm_ty], color=color, lw=1.2, alpha=0.85)
        ax.text(PT2_CX, PT2_LBL_Y,       "PT2", fontsize=7, ha='center', color='#cc6600', weight='bold')
        ax.text(PT2_CX, PT2_LBL_Y-0.03,  "母排", fontsize=6, ha='center', color='#666')
        if pt_blackbox_mode:
            ax.text(PT2_CX, PT2_LBL_Y-0.055, "黑盒教学模式", fontsize=5.5, ha='center', color='#555')
        draw_pt_secondary_terminal_strip(PT2_CX, PT2_CY, "PT2", section_y=0.372, line_y=0.360)

        draw_pt_full(cx=PT3_CX, cy=PT_GEN_CY, src_xs=G2_X, src_ys=[CB_BOT]*3,
                     channels=PT_GEN_CHANNELS, label="PT3", sub_label="G2机端",
                     phase_order=pt_orders['PT3'], lbl_y=PT_LBL_Y, ls='-.', side='right')
        draw_pt_secondary_terminal_strip(PT3_CX, PT_GEN_CY, "PT3", section_y=0.512, line_y=0.500)

        ax.text(0.50, 0.415, "仅允许在 PT 二次端子排上进行测量", fontsize=7, ha='center', color='#444')

        # PT 电压读数文字
        PT_V_LBL_Y  = PT_GEN_CY + PT_SIZE + 0.245
        PT2_V_LBL_Y = PT2_CY   + PT_SIZE + 0.245
        bbox_pt = dict(facecolor='#ffffee', edgecolor='#cc6600',
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
            0.50, CT_Y_TOP, "N线: 未接地", color='gray', ha='center', fontsize=8,
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
    # 主渲染入口（每帧由 QTimer 驱动）
    # ════════════════════════════════════════════════════════════════════════
    def render_visuals(self):
        p   = self.ctrl.physics
        deg = p.fixed_deg
        d   = p.plot_data
        bus_a_display = p.bus_amp if p.bus_live else 0.0

        self._render_waveforms(d, deg, bus_a_display)
        self._render_phasors(d, bus_a_display)
        self._render_ct_readings(p)
        self._render_bus_status(p)
        self._render_breakers(p)
        self._render_grounding_and_pt(p)
        self._render_multimeter(p)
        self._render_pt_exam(p)
        self._update_generator_buttons()

        idx = self.tab_widget.currentIndex()
        if idx == 0:
            self.canvas1.draw_idle()
        elif idx == 1:
            self.canvas2.draw_idle()

    # ── 各子渲染方法 ─────────────────────────────────────────────────────────
    def _render_waveforms(self, d, deg, bus_a_display):
        self.line_ga.set_data(deg, d['ga'])
        self.line_gb.set_data(deg, d['gb'])
        self.line_gc.set_data(deg, d['gc'])
        self.line_gen1_a.set_data(deg, d['g1a'])
        self.line_gen1_b.set_data(deg, d['g1b'])
        self.line_gen1_c.set_data(deg, d['g1c'])
        self.line_gen2_a.set_data(deg, d['g2a'])
        self.line_gen2_b.set_data(deg, d['g2b'])
        self.line_gen2_c.set_data(deg, d['g2c'])
        self.line_all_a.set_data(deg, d['ga'])
        self.line_all_b.set_data(deg, d['gb'])
        self.line_all_c.set_data(deg, d['gc'])

    def _render_phasors(self, d, bus_a_display):
        self.p_ga.set_data([0, d['ang_grid']], [0, bus_a_display])
        self.p_g1a.set_data([0, d['ang_g1']], [0, d['a1']])
        self.p_g2a.set_data([0, d['ang_g2']], [0, d['a2']])
        self.p_gb.set_data([0, d['ang_grid'] - 2*np.pi/3], [0, bus_a_display])
        self.p_g1b.set_data([0, d['ang_g1']  - 2*np.pi/3], [0, d['a1']])
        self.p_g2b.set_data([0, d['ang_g2']  + d['shift_b']], [0, d['a2']])
        self.p_gc.set_data([0, d['ang_grid'] + 2*np.pi/3], [0, bus_a_display])
        self.p_g1c.set_data([0, d['ang_g1']  + 2*np.pi/3], [0, d['a1']])
        self.p_g2c.set_data([0, d['ang_g2']  + d['shift_c']], [0, d['a2']])

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

    def _render_bus_status(self, p):
        self.bus_status_lbl.setText(p.bus_status_msg)
        self.bus_status_lbl.setStyleSheet(
            f"background:#1a1a2e; color:{'#00ff00' if p.bus_live else '#ff6600'}; "
            f"font-weight:bold; padding:5px; font-size:12px;")
        self.bus_reference_lbl.setText(p.bus_reference_msg)
        self.bus_reference_lbl.setStyleSheet(
            f"background:#f4f4f4; color:{'#006600' if p.bus_live else '#666666'}; "
            f"font-weight:bold; padding:4px; font-size:12px;")
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
            f"background:black; color:{p.arb_color}; font-weight:bold; padding:6px; font-size:12px;")
        self.relay_lbl.setText(p.relay_msg)
        self.relay_lbl.setStyleSheet(f"color:{_qs(p.relay_color)}; font-size:12px; padding:3px;")

        for lbl_attr, text, bg in [
            ('status1_lbl', p.brk1_text, p.brk1_bg),
            ('status2_lbl', p.brk2_text, p.brk2_bg),
        ]:
            lbl = getattr(self, lbl_attr)
            lbl.setText(text)
            tc = 'white' if _qs(bg) not in ('#ffaa00', '#ffcc00') else 'black'
            lbl.setStyleSheet(
                f"background:{_qs(bg)}; color:{tc}; font-weight:bold; padding:3px; font-size:12px;")

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
        for txt, label, v in [
            (self.txt_pt1_v, "PT1", p.pt1_v),
            (self.txt_pt2_v, "PT2", p.pt2_v),
            (self.txt_pt3_v, "PT3", p.pt3_v),
        ]:
            txt.set_text(f"{label}: {v:.1f}V")
            txt.set_color('#006600' if v > 90.0 else '#cc6600' if v > 10.0 else '#999999')

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

    def _render_pt_exam(self, p):
        gen_id = self._pt_target_bg.checkedId()
        if gen_id <= 0:
            gen_id = 1
        records   = self.ctrl.pt_exam_states[gen_id]['records']
        feedback  = self.ctrl.pt_exam_states[gen_id]['feedback']
        fb_color  = self.ctrl.pt_exam_states[gen_id]['feedback_color']
        generator = self.ctrl._get_generator_state(gen_id)
        current_phase = self.ctrl._get_current_pt_phase_match(gen_id)

        if self.ctrl.is_pt_exam_ready(gen_id):
            summary = f"Gen {gen_id} 已完成 PT 二次端子压差考核，允许执行工作位合闸。"
            sc = '#006400'
        elif all(records[ph] is not None for ph in ('A', 'B', 'C')):
            summary = (f"Gen {gen_id} 三相 PT 二次端子压差已记录，"
                       f"当前开关柜位置：{generator.breaker_position}。")
            sc = '#cc6600'
        else:
            summary = f"Gen {gen_id} 当前开关柜位置：{generator.breaker_position}。"
            sc = '#264653'
        self.pt_exam_summary_lbl.setText(summary)
        self.pt_exam_summary_lbl.setStyleSheet(f"font-weight:bold; font-size:12px; color:{sc};")

        meter_text = p.meter_reading
        if current_phase:
            meter_text = f"当前表笔对准 Gen {gen_id} {current_phase} 相。{meter_text}"
        self.pt_exam_meter_lbl.setText(f"实时测量：{meter_text}")
        self.pt_exam_meter_lbl.setStyleSheet(
            f"font-size:12px; color:{_qs(getattr(p, 'meter_color', 'black'))};")
        self.pt_exam_feedback_lbl.setText(f"考核提示：{feedback}")
        self.pt_exam_feedback_lbl.setStyleSheet(f"font-size:12px; color:{_qs(fb_color)};")

        for lbl, (text, done) in zip(self.pt_exam_step_labels,
                                     self.ctrl.get_pt_exam_steps(gen_id)):
            lbl.setText(("√ " if done else "□ ") + text)
            lbl.setStyleSheet(f"font-size:12px; color:{'#006400' if done else '#666666'};")

        for phase, lbl in self.pt_exam_record_labels.items():
            record = records[phase]
            if record is None:
                lbl.setText("未记录")
                lbl.setStyleSheet("font-size:12px; color:#999999;")
            else:
                lbl.setText(f"{record['voltage']:.1f} V  [可合闸]")
                lbl.setStyleSheet("font-size:12px; color:#006400;")

    def _update_generator_buttons(self):
        for gen_id in (1, 2):
            sim = self.ctrl.sim_state
            gen = sim.gen1 if gen_id == 1 else sim.gen2
            is_manual  = gen.mode == "manual"
            is_running = gen.running
            brk_closed = gen.breaker_closed
            engine_btn  = getattr(self, f'btn_engine{gen_id}')
            breaker_btn = getattr(self, f'btn_breaker{gen_id}')

            engine_btn.setEnabled(is_manual)
            engine_btn.setText("停机 (Stop)" if is_running else "起机 (Start)")
            engine_btn.setStyleSheet(
                f"background:{'#ff9999' if is_running else '#99ff99'};")
            breaker_btn.setEnabled(is_manual)
            breaker_btn.setText("控分 (Open)" if brk_closed else "控合 (Close)")
            breaker_btn.setStyleSheet(
                f"background:{'#ff9999' if brk_closed else '#99ff99'};")

            # 同步滑块 / 输入框（物理引擎可能修改数值）
            em = getattr(self, f'_gen{gen_id}_entry_map', {})
            for attr, (sl, entry) in em.items():
                val   = getattr(gen, attr)
                scale = 10 if attr in ('freq', 'phase_deg') else 1
                sl.blockSignals(True)
                sl.setValue(int(val * scale))
                sl.blockSignals(False)
                if not entry.hasFocus():
                    entry.setText(f"{val:.1f}")