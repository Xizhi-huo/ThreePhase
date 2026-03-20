"""
services/_physics_measurement.py
接地、PT 测量与万用表仿真 Mixin ── PhysicsEngine 的测量职责。
"""

import numpy as np

from domain.constants import NEUTRAL_RESISTOR_OHMS, PT_GEN_RATIO, PT_BUS_RATIO
from domain.enums import BreakerPosition
from domain.node_map import NODES


class MeasurementMixin:
    """中性点接地状态、PT 二次电压计算与万用表交互仿真。"""

    def _whole_cycle_rms_raw(self, wave: np.ndarray, freq_hz: float,
                             n_cycles: int = 3) -> float:
        """整周期截断后的纯 RMS，不修改任何 EMA 状态。"""
        freq_hz = max(freq_hz, 1.0)
        spc = 1.0 / (freq_hz * self.wave_sample_dt)
        n_use = max(1, round(min(n_cycles, len(wave) / spc) * spc))
        n_use = min(n_use, len(wave))
        return float(np.sqrt(np.mean(wave[-n_use:] ** 2)))

    def _ema_update(self, key: str, raw_value: float) -> float:
        """
        对指定 key 独立维护 EMA，各测量路径互不串扰。
        key 示例: 'intra_diff', 'cross_rms1', 'cross_rms2'
        """
        if not hasattr(self, '_meter_ema_dict'):
            self._meter_ema_dict: dict = {}
        if key not in self._meter_ema_dict:
            self._meter_ema_dict[key] = raw_value
        else:
            a = self._meter_ema_alpha
            self._meter_ema_dict[key] = a * raw_value + (1.0 - a) * self._meter_ema_dict[key]
        return self._meter_ema_dict[key]

    def _ema_reset(self, *keys):
        """探针切换时清除指定 key 的历史，避免拖尾。"""
        if hasattr(self, '_meter_ema_dict'):
            for k in keys:
                self._meter_ema_dict.pop(k, None)

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
        self.pt1_v = (a1  / np.sqrt(2) * np.sqrt(3)) / PT_GEN_RATIO
        self.pt2_v = (bus_a / np.sqrt(2) * np.sqrt(3)) / PT_BUS_RATIO
        # PT3 始终读 Gen2 自身的发电电压（Gen2 起机不合闸时提供相序参考）
        pt3_amp = a2
        self.pt3_v = (pt3_amp / np.sqrt(2) * np.sqrt(3)) / PT_GEN_RATIO

    def _update_multimeter(self, sim):
        _UI_NODES = NODES

        self.meter_color = "black"
        self.meter_voltage = None
        self.meter_status = "idle"
        self.meter_nodes = None
        self.meter_phase_match = None

        # 当探针位置变化时重置 EMA，避免切换测点后示值拖尾
        _cur_probes = (sim.probe1_node, sim.probe2_node)
        if not hasattr(self, '_meter_last_probes'):
            self._meter_last_probes = _cur_probes
        if _cur_probes != self._meter_last_probes:
            self._ema_reset('intra_diff', 'cross_rms1', 'cross_rms2')
            self._meter_last_probes = _cur_probes

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
                    # 根据所属 PT 取对应实时频率，做整周期截断 + EMA
                    _pt_name = _pt1   # 两探针同 PT
                    sim_ref = self.ctrl.sim_state
                    if _pt_name == 'PT1':
                        _freq = sim_ref.gen1.freq
                    elif _pt_name == 'PT3':
                        _freq = sim_ref.gen2.freq
                    else:
                        _freq = self.bus_freq or 50.0
                    raw_rms = self._whole_cycle_rms_raw(wave_diff, _freq)
                    primary_rms = self._ema_update('intra_diff', raw_rms)
                    # 按所属 PT 使用对应变比：机组侧≈57.02，母排侧=100
                    _pt_ratio = PT_GEN_RATIO if _pt_name in ('PT1', 'PT3') else PT_BUS_RATIO
                    meter_v = primary_rms / _pt_ratio
                    self.meter_voltage = meter_v
                    self.meter_nodes = (n1, n2)
                    # ±15% 容差：均以一次侧 [8925V, 12075V] 为基准折算到各 PT 二次侧
                    _ok_lo = 8925.0 / _pt_ratio
                    _ok_hi = 12075.0 / _pt_ratio
                    if _ok_lo <= meter_v <= _ok_hi:
                        self.meter_status = "ok"
                        self.meter_color = "green"
                    elif meter_v < 1.0:
                        self.meter_status = "idle"
                        self.meter_color = "black"
                    else:
                        self.meter_status = "danger"
                        self.meter_color = "red"
                    primary_display = meter_v * _pt_ratio   # 换算回一次侧
                    self.meter_reading = (
                        f"线电压: {info1[4]} ↔ {info2[4]} | "
                        f"一次侧={primary_display/1000:.2f} kV"
                        f"（二次侧={meter_v:.1f} V）"
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
                    # 整周期截断 + EMA（分别对两路做平滑，差值也就稳定）
                    _sim2 = self.ctrl.sim_state
                    _f1 = (_sim2.gen1.freq if key1.startswith('g1')
                           else _sim2.gen2.freq if key1.startswith('g2')
                           else self.bus_freq or 50.0)
                    _f2 = (_sim2.gen1.freq if key2.startswith('g1')
                           else _sim2.gen2.freq if key2.startswith('g2')
                           else self.bus_freq or 50.0)
                    rms1 = self._ema_update('cross_rms1',
                               self._whole_cycle_rms_raw(self.plot_data[key1], _f1))
                    rms2 = self._ema_update('cross_rms2',
                               self._whole_cycle_rms_raw(self.plot_data[key2], _f2))
                    primary_rms_diff = abs(rms1 - rms2)
                    # 各侧用自己变比折算二次侧电压（用于显示）
                    gen_sec  = rms1 / PT_GEN_RATIO   # 机组侧 PT 二次侧相电压
                    bus_sec  = rms2 / PT_BUS_RATIO   # 母排侧 PT 二次侧相电压
                    # meter_voltage 以机组侧变比折算，供 pt_exam_service 逆算一次侧
                    meter_v = primary_rms_diff / PT_GEN_RATIO
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
                        f" | {seq_status}"
                        f" | 一次侧压差={primary_rms_diff:.0f} V"
                        f"（机组侧二次={gen_sec:.1f} V，母排侧二次={bus_sec:.1f} V）"
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
