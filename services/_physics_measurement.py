"""
services/_physics_measurement.py
接地、PT 测量与万用表仿真 Mixin ── PhysicsEngine 的测量职责。
"""

import numpy as np

from domain.constants import NEUTRAL_RESISTOR_OHMS, PT_RATIO, PRIMARY_AMP
from domain.enums import BreakerPosition
from domain.node_map import NODES


class MeasurementMixin:
    """中性点接地状态、PT 二次电压计算与万用表交互仿真。"""

    def _update_grounding(self, sim):
        ga_data = self.plot_data['ga']
        gb_data = self.plot_data['gb']
        gc_data = self.plot_data['gc']
        v_sum_rms = np.sqrt(np.mean((ga_data + gb_data + gc_data) ** 2))

        if sim.grounding_mode == "断开":
            self.ground_msg = "N线: 悬浮脱开 (Vn = 漂移电位)"
            self.ground_color = "red"
        elif sim.grounding_mode == "直接接地":
            self.ground_msg = "N线: 直接接地 (Vn = 0V, 存在短路隐患)"
            self.ground_color = "orange"
        else:
            i0_rms = v_sum_rms / (3 * NEUTRAL_RESISTOR_OHMS + 0.001)
            vn_rms = i0_rms * NEUTRAL_RESISTOR_OHMS
            self.ground_msg = f"N线: 10Ω小电阻接地 (Vn={vn_rms:.1f}V)"
            self.ground_color = "green"

    def _update_pt_measurements(self, bus_a, a1, a2):
        pt_ratio = PT_RATIO
        self.pt1_v = (a1  / np.sqrt(2) * np.sqrt(3)) / pt_ratio
        self.pt2_v = (bus_a / np.sqrt(2) * np.sqrt(3)) / pt_ratio
        # PT3 始终读 Gen2 自身的发电电压（Gen2 起机不合闸时提供相序参考）
        pt3_amp = a2
        self.pt3_v = (pt3_amp / np.sqrt(2) * np.sqrt(3)) / pt_ratio

    def _update_multimeter(self, sim):
        _UI_NODES = NODES

        self.meter_color = "black"
        self.meter_voltage = None
        self.meter_status = "idle"
        self.meter_nodes = None
        self.meter_phase_match = None
        if sim.multimeter_mode:
            n1, n2 = sim.probe1_node, sim.probe2_node
            if n1 and n2:
                info1, info2 = _UI_NODES[n1], _UI_NODES[n2]
                loop_pair = info1[2].startswith('Loop') and info2[2].startswith('Loop')
                valid_pairs = {
                    frozenset({'PT1_A', 'PT2_A'}), frozenset({'PT1_B', 'PT2_B'}), frozenset({'PT1_C', 'PT2_C'}),
                    frozenset({'PT3_A', 'PT2_A'}), frozenset({'PT3_B', 'PT2_B'}), frozenset({'PT3_C', 'PT2_C'}),
                }
                # 检查是否为同一 PT 内的线电压测量（如 PT1_A ↔ PT1_B）
                _pt1 = n1.rsplit('_', 1)[0] if '_' in n1 else ''
                _pt2 = n2.rsplit('_', 1)[0] if '_' in n2 else ''
                _ph1 = n1.rsplit('_', 1)[1] if '_' in n1 else ''
                _ph2 = n2.rsplit('_', 1)[1] if '_' in n2 else ''
                intra_pt_pair = (
                    _pt1 == _pt2 and
                    _pt1 in ('PT1', 'PT2', 'PT3') and
                    _ph1 in ('A', 'B', 'C') and
                    _ph2 in ('A', 'B', 'C') and
                    _ph1 != _ph2
                )
                if loop_pair:
                    loop_done = self.ctrl.loop_test_state.completed
                    if sim.grounding_mode != "断开" and not loop_done:
                        self.meter_status = "invalid"
                        self.meter_color = "red"
                        self.meter_reading = "回路演示前请先断开中性点接地"
                    elif not (sim.gen1.breaker_closed and sim.gen2.breaker_closed):
                        self.meter_status = "invalid"
                        self.meter_color = "red"
                        self.meter_reading = "回路演示前请先闭合 Gen1 和 Gen2 开关"
                    elif info1[2] == info2[2]:
                        self.meter_status = "invalid"
                        self.meter_reading = "请分别选择 G1 与 G2 的三相回路测点进行比较"
                    else:
                        phase1 = self.ctrl.resolve_loop_node_phase(n1)
                        phase2 = self.ctrl.resolve_loop_node_phase(n2)
                        self.meter_nodes = (n1, n2)
                        if phase1 == phase2:
                            self.meter_status = "ok"
                            self.meter_color = "green"
                            self.meter_reading = f"回路连通: {info1[4]} ↔ {info2[4]} 为同一相回路 [导通/同相]"
                        else:
                            self.meter_status = "danger"
                            self.meter_color = "red"
                            self.meter_reading = f"相序不对应: {info1[4]} ↔ {info2[4]} 不属于同一相回路 [不导通]"
                elif intra_pt_pair:
                    # 同一 PT 内两相线电压测量（第二步 PT 单体线电压检查）
                    key1 = self.ctrl.resolve_pt_node_plot_key(n1)
                    key2 = self.ctrl.resolve_pt_node_plot_key(n2)
                    wave_diff = self.plot_data[key1] - self.plot_data[key2]
                    primary_rms = np.sqrt(np.mean(wave_diff ** 2))
                    meter_v = primary_rms / PT_RATIO
                    self.meter_voltage = meter_v
                    self.meter_nodes = (n1, n2)
                    # ±15% 容差判断（二次侧额定线电压 100V）
                    if 85.0 <= meter_v <= 115.0:
                        self.meter_status = "ok"
                        self.meter_color = "green"
                    elif meter_v < 1.0:
                        self.meter_status = "idle"
                        self.meter_color = "black"
                    else:
                        self.meter_status = "danger"
                        self.meter_color = "red"
                    self.meter_reading = (
                        f"线电压: {info1[4]} ↔ {info2[4]} | "
                        f"测量值={meter_v:.1f}V"
                        + ("  [正常]" if self.meter_status == "ok" else
                           "  [异常]" if self.meter_status == "danger" else "  [无电压]")
                    )
                elif frozenset({n1, n2}) in valid_pairs:
                    key1 = self.ctrl.resolve_pt_node_plot_key(n1)
                    key2 = self.ctrl.resolve_pt_node_plot_key(n2)
                    actual_ph1 = key1[-1].upper()
                    actual_ph2 = key2[-1].upper()
                    labeled1 = n1.split('_')[1]
                    labeled2 = n2.split('_')[1]
                    phases_match = (actual_ph1 == actual_ph2)
                    self.meter_phase_match = phases_match
                    ann1 = f"[实际{actual_ph1}相]" if actual_ph1 != labeled1 else ""
                    ann2 = f"[实际{actual_ph2}相]" if actual_ph2 != labeled2 else ""
                    rms1 = np.sqrt(np.mean(self.plot_data[key1]**2))
                    rms2 = np.sqrt(np.mean(self.plot_data[key2]**2))
                    primary_rms_diff = abs(rms1 - rms2)
                    sec_rms_diff = primary_rms_diff / ((PRIMARY_AMP / np.sqrt(2)) / 100.0)
                    meter_v = sec_rms_diff
                    self.meter_voltage = meter_v
                    self.meter_nodes = (n1, n2)
                    if phases_match:
                        self.meter_color = "green"
                        self.meter_status = "ok"
                    else:
                        self.meter_color = "red"
                        self.meter_status = "danger"
                    if phases_match:
                        seq_status = f"相序✓ ({actual_ph1}相匹配)"
                    else:
                        seq_status = (
                            f"相序✗ (端子标{labeled1}/实际{actual_ph1}相"
                            f" ≠ 端子标{labeled2}/实际{actual_ph2}相)"
                        )
                    self.meter_reading = (
                        f"PT端子: {info1[4]}{ann1} ↔ {info2[4]}{ann2}"
                        f" | {seq_status} | 压差={meter_v:.1f}V"
                    )
                else:
                    self.meter_status = "invalid"
                    self.meter_reading = "测量无效: PT压差请测 PT 二次端子；回路演示请测 G1/G2 三相回路测点"
            elif n1:
                self.meter_status = "waiting"
                self.meter_reading = f"已连接 {_UI_NODES[n1][4]}, 等待放置黑表笔..."
            else:
                self.meter_status = "waiting"
                self.meter_reading = "请用鼠标点击 PT 二次端子或 G1/G2 三相回路测点进行测量"
        else:
            sim.probe1_node = None
            sim.probe2_node = None
            self.meter_reading = "万用表未开启"
