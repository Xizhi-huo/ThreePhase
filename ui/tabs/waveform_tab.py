"""
ui/tabs/waveform_tab.py
波形与相量图 Tab (Tab 0)
"""

import numpy as np
from PyQt5 import QtWidgets, QtCore
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.gridspec as gridspec
from matplotlib.ticker import MultipleLocator

from domain.constants import CT_RATIO


# MplCanvas  —  单张 matplotlib Figure 嵌入 Qt
class MplCanvas(FigureCanvas):
    def __init__(self, fig: Figure):
        super().__init__(fig)
        self.setMinimumSize(400, 300)
        # Expanding：canvas 填满布局分配的空间；sizeHint() 已被覆盖为 (400,300)，
        # updateGeometry() 已移除，不再向上撑大窗口
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding,
        )

    def minimumSizeHint(self):
        return QtCore.QSize(400, 300)

    def sizeHint(self):
        return QtCore.QSize(400, 300)


class WaveformTabMixin:
    """
    混入类，提供波形与相量图 Tab 的构建和渲染方法。
    """

    # ── Tab0：波形与相量 ─────────────────────────────────────────────────────
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
        self.ax_p.set_rmax(13000)
        self.ax_p.set_rticks([3500, 7000, 10500])
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

    # ── 渲染方法 ─────────────────────────────────────────────────────────────
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
