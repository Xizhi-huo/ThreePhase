import numpy as np

from domain.constants import (CT_RATIO, TRIP_CURRENT, GRID_FREQ, GRID_AMP,
    XS, KP_DROOP, KQ_DROOP, MAX_POINTS, CT_PRIMARY_A, CT_SECONDARY_A,
    NEUTRAL_RESISTOR_OHMS, LOAD_RESISTANCE, PT_RATIO, PRIMARY_AMP)
from domain.enums import BreakerPosition, SystemMode
from domain.node_map import NODES
from adapters.render_state import RenderState


def _heat_color(rms: float) -> str:
    """根据电流 RMS 值返回热力颜色字符串（绿→橙→红）。"""
    ratio = min(rms / TRIP_CURRENT, 1.0)
    r = int(255 * ratio)
    g = int(200 * (1 - ratio))
    return f'#{r:02x}{g:02x}00'


class PhysicsEngine:
    def __init__(self, ctrl):
        self.ctrl = ctrl
        self.animation_time = 0.0
        self.fixed_t = np.linspace(0, 0.06, MAX_POINTS)
        self.fixed_deg = self.fixed_t * 50 * 360
        self.wave_sample_dt = self.fixed_t[1] - self.fixed_t[0]
        self.history_initialized = False

        self.flash_frames1 = 0
        self.flash_frames2 = 0
        self.dead_bus_timer = 0.0
        self.first_ready = None
        self.bus_reference_gen = None

        self.plot_data = {}
        self.relay_msg, self.relay_color = "", "blue"
        self.arb_msg, self.arb_color = "🛠️ 仲裁器: 待机", "#00ff00"
        self.brk1_text, self.brk1_bg, self.brk1_visual = "断路器: OPEN (开路)", "gray", False
        self.brk2_text, self.brk2_bg, self.brk2_visual = "断路器: OPEN (开路)", "gray", False
        self.circ_msg, self.circ_color = "", "gray"
        self.color_sw1, self.color_sw2 = "k", "k"
        self.i1_rms, self.ip1, self.iq1 = 0, 0, 0
        self.i2_rms, self.ip2, self.iq2 = 0, 0, 0
        self.ground_msg, self.ground_color = "N线: 未接地", "gray"

        self.meter_reading = "请用表笔点击两个端子"
        self.meter_color = "black"
        self.meter_voltage = None
        self.meter_status = "idle"
        self.meter_nodes = None
        self.meter_phase_match = None   # PT端子相位一致性（用于PT相序检查）

        self.bus_freq = 0.0
        self.bus_amp = 0.0
        self.bus_phase = 0.0
        self.bus_source = None
        self.bus_live = False
        self.bus_status_msg = "母排: 无电"
        self.bus_reference_msg = "参考基准: 无"

        self.pt1_v = 0.0
        self.pt2_v = 0.0
        self.pt3_v = 0.0

    def _control_speed_factor(self, sim):
        return max(sim.sim_speed, 0.05)

    @staticmethod
    def _three_phase_samples(base_angle, amp, shift_b, shift_c, prefix):
        return {
            f'{prefix}a': amp * np.sin(base_angle),
            f'{prefix}b': amp * np.sin(base_angle + shift_b),
            f'{prefix}c': amp * np.sin(base_angle + shift_c),
        }

    def _build_wave_history(self, w_bus, w_g1, w_g2, p_bus, p_g1, p_g2, bus_a, a1, a2, shift_b, shift_c):
        hist_t = self.animation_time - self.fixed_t[::-1]
        result = {}
        result.update(self._three_phase_samples(
            w_bus * hist_t + p_bus, bus_a, -2*np.pi/3, +2*np.pi/3, 'g'))
        result.update(self._three_phase_samples(
            w_g1  * hist_t + p_g1,  a1,   -2*np.pi/3, +2*np.pi/3, 'g1'))
        result.update(self._three_phase_samples(
            w_g2  * hist_t + p_g2,  a2,    shift_b,    shift_c,    'g2'))
        result['ic1'] = np.zeros(MAX_POINTS)
        result['ic2'] = np.zeros(MAX_POINTS)
        return result

    def _append_history_sample(self, key, value):
        series = self.plot_data[key]
        series[:-1] = series[1:]
        series[-1] = value

    def _get_instant_samples(self, sample_time, w_bus, w_g1, w_g2, p_bus, p_g1, p_g2, bus_a, a1, a2, shift_b, shift_c):
        result = {}
        result.update(self._three_phase_samples(
            w_bus * sample_time + p_bus, bus_a, -2*np.pi/3, +2*np.pi/3, 'g'))
        result.update(self._three_phase_samples(
            w_g1  * sample_time + p_g1,  a1,   -2*np.pi/3, +2*np.pi/3, 'g1'))
        result.update(self._three_phase_samples(
            w_g2  * sample_time + p_g2,  a2,    shift_b,    shift_c,    'g2'))
        return result

    def auto_adjust_local(self, generator, sim, target_freq, target_amp):
        if generator.breaker_closed:
            return
        speed_factor = self._control_speed_factor(sim)
        err_f = target_freq - generator.freq
        step_f = 0.02 * sim.gov_gain * speed_factor
        if abs(err_f) > step_f:
            generator.freq = round(generator.freq + np.sign(err_f) * step_f, 3)
        elif sim.sync_gain > 3.0:
            generator.freq = round(generator.freq + np.sign(err_f + 0.001) * (0.02 * sim.sync_gain * speed_factor), 3)
        else:
            generator.freq = target_freq

        err_a = target_amp - generator.amp
        step_a = 50.0 * sim.gov_gain * speed_factor
        if abs(err_a) > step_a:
            generator.amp = round(generator.amp + np.sign(err_a) * step_a, 1)
        elif sim.sync_gain > 3.0:
            generator.amp = round(generator.amp + np.sign(err_a + 0.01) * (50.0 * sim.sync_gain * speed_factor), 1)
        else:
            generator.amp = target_amp

    def auto_adjust_phase(self, generator, sim, target_phase_deg):
        phase_error = generator.phase_deg - target_phase_deg
        step_p = 0.5 * sim.sync_gain * self._control_speed_factor(sim)
        if abs(phase_error) > step_p:
            generator.phase_deg = round(generator.phase_deg - np.sign(phase_error) * step_p, 1)
        elif sim.sync_gain > 3.0:
            generator.phase_deg = round(generator.phase_deg - np.sign(phase_error + 0.01) * step_p, 1)
        else:
            generator.phase_deg = round(target_phase_deg, 1)

    def _resolve_bus_reference_gen(self, g1_on_bus, g2_on_bus):
        if not g1_on_bus and not g2_on_bus:
            self.bus_reference_gen = None
        elif self.bus_reference_gen == 1 and g1_on_bus:
            pass
        elif self.bus_reference_gen == 2 and g2_on_bus:
            pass
        elif g1_on_bus:
            self.bus_reference_gen = 1
        elif g2_on_bus:
            self.bus_reference_gen = 2
        return self.bus_reference_gen

    def _update_bus_reference(self, sim, is_isolated):
        g1_on_bus = (sim.gen1.breaker_position == BreakerPosition.WORKING) and sim.gen1.breaker_closed
        g2_on_bus = (sim.gen2.breaker_position == BreakerPosition.WORKING) and sim.gen2.breaker_closed

        if is_isolated:
            reference_gen = self._resolve_bus_reference_gen(g1_on_bus, g2_on_bus)
            if reference_gen == 1 and g1_on_bus:
                self.bus_freq = sim.gen1.freq
                self.bus_amp = sim.gen1.actual_amp
                self.bus_phase = np.radians(sim.gen1.phase_deg)
                self.bus_source = 1 if not g2_on_bus else "both"
                self.bus_live = True
                self.bus_reference_msg = "参考基准: Gen 1"
                if g2_on_bus:
                    self.bus_status_msg = f"母排: 以 Gen 1 为基准并联运行 ({self.bus_freq:.1f}Hz, {self.bus_amp:.0f}V)"
                else:
                    self.bus_status_msg = f"母排: Gen 1 独立供电 ({self.bus_freq:.1f}Hz, {self.bus_amp:.0f}V)"
            elif reference_gen == 2 and g2_on_bus:
                self.bus_freq = sim.gen2.freq
                self.bus_amp = sim.gen2.actual_amp
                self.bus_phase = np.radians(sim.gen2.phase_deg)
                self.bus_source = 2 if not g1_on_bus else "both"
                self.bus_live = True
                self.bus_reference_msg = "参考基准: Gen 2"
                if g1_on_bus:
                    self.bus_status_msg = f"母排: 以 Gen 2 为基准并联运行 ({self.bus_freq:.1f}Hz, {self.bus_amp:.0f}V)"
                else:
                    self.bus_status_msg = f"母排: Gen 2 独立供电 ({self.bus_freq:.1f}Hz, {self.bus_amp:.0f}V)"
            else:
                self.bus_freq = 0.0
                self.bus_amp = 0.0
                self.bus_phase = 0.0
                self.bus_source = None
                self.bus_live = False
                self.bus_status_msg = "母排: 无电 (死母线)"
                self.bus_reference_msg = "参考基准: 无"
                self.bus_reference_gen = None
        else:
            self.bus_freq = GRID_FREQ
            self.bus_amp = GRID_AMP
            self.bus_phase = 0.0
            self.bus_source = "grid"
            self.bus_live = True
            self.bus_status_msg = f"母排: 电网供电 ({GRID_FREQ}Hz)"
            self.bus_reference_msg = "参考基准: 外部电网"
            self.bus_reference_gen = None

        return {
            'g1_on_bus': g1_on_bus,
            'g2_on_bus': g2_on_bus,
            'ref_freq': self.bus_freq if self.bus_live else GRID_FREQ,
            'ref_amp': self.bus_amp if self.bus_live else GRID_AMP,
            'reference_gen': self.bus_reference_gen,
        }

    def _handle_dead_bus_selection(self, sim, mode1, mode2, g1_ready, g2_ready):
        if g1_ready and mode1 == "auto" and self.first_ready != 2:
            self.first_ready = 1
        elif g2_ready and mode2 == "auto" and self.first_ready != 1:
            self.first_ready = 2
        else:
            self.first_ready = None
            self.dead_bus_timer = 0.0
            self.arb_msg, self.arb_color = "🔍 仲裁器: 等待机组建立额定电压与频率...", "#00ffff"

        if self.first_ready == 1:
            self.dead_bus_timer += 0.033 * sim.sim_speed
            remaining = sim.first_start_time - self.dead_bus_timer
            if remaining <= 0:
                sim.gen1.phase_deg = 0.0
                sim.gen1.breaker_closed = True
                self.dead_bus_timer = 0.0
                self.first_ready = None
                self.arb_msg, self.arb_color = "🟢 仲裁: Gen 1 首台投入，建立母排基准！", "#00ff00"
            else:
                self.arb_msg, self.arb_color = f"⏳ 仲裁: Gen 1 达标, 准备投入死母线, 延时 {max(0, int(remaining + 1))}s", "#ffcc00"
        elif self.first_ready == 2:
            self.dead_bus_timer += 0.033 * sim.sim_speed
            remaining = sim.first_start_time - self.dead_bus_timer
            if remaining <= 0:
                sim.gen2.phase_deg = 0.0
                sim.gen2.breaker_closed = True
                self.dead_bus_timer = 0.0
                self.first_ready = None
                self.arb_msg, self.arb_color = "🟢 仲裁: Gen 2 首台投入，建立母排基准！", "#00ff00"
            else:
                self.arb_msg, self.arb_color = f"⏳ 仲裁: Gen 2 达标, 准备投入死母线, 延时 {max(0, int(remaining + 1))}s", "#ffcc00"

    def _handle_live_bus_sync(self, sim, mode1, mode2):
        all_synced = True
        target_phase_deg = np.degrees(self.bus_phase)
        if not sim.gen1.breaker_closed and mode1 == "auto" and sim.gen1.running:
            self.auto_adjust_phase(sim.gen1, sim, target_phase_deg)
            self.arb_msg, self.arb_color = "⚙️ 仲裁: 母线带电，Gen 1 正在捕获相角打同期...", "#ffcc00"
            all_synced = False
        if not sim.gen2.breaker_closed and mode2 == "auto" and sim.gen2.running:
            self.auto_adjust_phase(sim.gen2, sim, target_phase_deg)
            if all_synced:
                self.arb_msg, self.arb_color = "⚙️ 仲裁: 母线带电，Gen 2 正在捕获相角打同期...", "#ffcc00"
            all_synced = False
        if all_synced and (sim.gen1.breaker_closed or mode1 != "auto") and (sim.gen2.breaker_closed or mode2 != "auto"):
            self.arb_msg, self.arb_color = "✅ 仲裁器: 全部机组并联运行", "#00ff00"

    def _update_arbitration(self, sim, g1_on_bus, g2_on_bus, ref_freq, ref_amp):
        mode1 = sim.gen1.mode
        mode2 = sim.gen2.mode

        if sim.remote_start_signal and not sim.paused:
            if mode1 == "auto" and not sim.gen1.running:
                sim.gen1.running = True
            if mode2 == "auto" and not sim.gen2.running:
                sim.gen2.running = True
        else:
            if mode1 == "auto" and sim.gen1.running:
                sim.gen1.running = False
                sim.gen1.breaker_closed = False
            if mode2 == "auto" and sim.gen2.running:
                sim.gen2.running = False
                sim.gen2.breaker_closed = False

        if sim.paused:
            return

        if mode1 == "auto" and sim.gen1.running:
            self.auto_adjust_local(sim.gen1, sim, ref_freq, ref_amp)
        if mode2 == "auto" and sim.gen2.running:
            self.auto_adjust_local(sim.gen2, sim, ref_freq, ref_amp)

        g1_ready = (abs(sim.gen1.freq - GRID_FREQ) < 0.2) and (abs(sim.gen1.actual_amp - GRID_AMP) < 150.0)
        g2_ready = (abs(sim.gen2.freq - GRID_FREQ) < 0.2) and (abs(sim.gen2.actual_amp - GRID_AMP) < 150.0)

        if sim.remote_start_signal:
            if not (g1_on_bus or g2_on_bus):
                self._handle_dead_bus_selection(sim, mode1, mode2, g1_ready, g2_ready)
            else:
                self._handle_live_bus_sync(sim, mode1, mode2)
        else:
            self.arb_msg, self.arb_color = "🛠️ 仲裁器: 待命 (请闭合远程启动信号)", "#00ff00"
            self.dead_bus_timer = 0.0
            self.first_ready = None

    def _advance_time(self, sim):
        prev_animation_time = self.animation_time
        if not sim.paused:
            self.animation_time += 0.002 * sim.sim_speed
        return prev_animation_time

    def _update_actual_amplitudes(self, sim):
        speed_factor = self._control_speed_factor(sim)
        for generator in (sim.gen1, sim.gen2):
            target_amp = generator.amp if generator.running else 0.0
            climb_speed = 150.0 * sim.gov_gain * speed_factor
            if generator.actual_amp < target_amp:
                generator.actual_amp = min(target_amp, generator.actual_amp + climb_speed)
            elif generator.actual_amp > target_amp:
                generator.actual_amp = max(target_amp, generator.actual_amp - climb_speed)
        return sim.gen1.actual_amp, sim.gen2.actual_amp

    def _apply_engine_trip_interlocks(self, sim):
        # 任一测试模式激活时：允许不起机机械合闸，跳过失压联锁
        if sim.loop_test_mode or sim.pt_phase_test_mode:
            return
        if sim.gen1.breaker_closed and not sim.gen1.running:
            sim.gen1.breaker_closed = False
            self.relay_msg, self.relay_color = "⚠️ 保护: Gen 1 引擎停机失压，断路器自动脱扣！", "orange"
        if sim.gen2.breaker_closed and not sim.gen2.running:
            sim.gen2.breaker_closed = False
            self.relay_msg, self.relay_color = "⚠️ 保护: Gen 2 引擎停机失压，断路器自动脱扣！", "orange"

    def _compute_wave_state(self, sim, is_isolated, g1_on_bus, g2_on_bus, a1, a2):
        w_g1 = 2 * np.pi * sim.gen1.freq
        w_g2 = 2 * np.pi * sim.gen2.freq
        p_g1 = np.radians(sim.gen1.phase_deg)
        p_g2 = np.radians(sim.gen2.phase_deg)

        if is_isolated:
            if g1_on_bus and g2_on_bus:
                if self.bus_reference_gen == 2:
                    bus_w, bus_p, bus_a = w_g2, p_g2, a2
                else:
                    bus_w, bus_p, bus_a = w_g1, p_g1, a1
            elif g1_on_bus:
                bus_w, bus_p, bus_a = w_g1, p_g1, a1
            elif g2_on_bus:
                bus_w, bus_p, bus_a = w_g2, p_g2, a2
            else:
                bus_w, bus_p, bus_a = 2 * np.pi * GRID_FREQ, 0.0, 0.0
        else:
            bus_w, bus_p, bus_a = 2 * np.pi * GRID_FREQ, 0.0, GRID_AMP

        if sim.rotate_phasor:
            ang_bus = bus_w * self.animation_time + bus_p
            ang_g1 = w_g1 * self.animation_time + p_g1
            ang_g2 = w_g2 * self.animation_time + p_g2
        else:
            ang_bus = bus_p if is_isolated and not self.bus_live else 0.0
            ang_g1 = (w_g1 - bus_w) * self.animation_time + p_g1 - bus_p
            ang_g2 = (w_g2 - bus_w) * self.animation_time + p_g2 - bus_p

        return {
            'w_g1': w_g1, 'w_g2': w_g2,
            'p_g1': p_g1, 'p_g2': p_g2,
            'bus_w': bus_w, 'bus_p': bus_p, 'bus_a': bus_a,
            'ang_bus': ang_bus, 'ang_g1': ang_g1, 'ang_g2': ang_g2,
            'ga_sample': bus_a * np.sin(bus_w * self.animation_time + bus_p),
            'g1a_sample': a1 * np.sin(w_g1 * self.animation_time + p_g1),
            'g2a_sample': a2 * np.sin(w_g2 * self.animation_time + p_g2),
        }

    def _update_protection_state(self, sim, wave_state, a1, a2, g1_connected, g2_connected):
        delta1 = wave_state['ang_g1'] - wave_state['ang_bus']
        delta2 = wave_state['ang_g2'] - wave_state['ang_bus']

        if g1_connected:
            self.i1_rms = abs((wave_state['g1a_sample'] - wave_state['ga_sample']) / XS)
            self.ip1 = (a1 * np.sin(delta1)) / XS
            self.iq1 = (a1 * np.cos(delta1) - wave_state['bus_a']) / XS
        else:
            self.i1_rms = self.ip1 = self.iq1 = 0.0

        if g2_connected:
            self.i2_rms = abs((wave_state['g2a_sample'] - wave_state['ga_sample']) / XS)
            self.ip2 = (a2 * np.sin(delta2)) / XS
            self.iq2 = (a2 * np.cos(delta2) - wave_state['bus_a']) / XS
        else:
            self.i2_rms = self.ip2 = self.iq2 = 0.0

        # ── 继电保护判断 ────────────────────────────────────────────────────────
        self.relay_msg, self.relay_color = (
            f"🛡️ 继电保护监控中 (跳闸阈值: 一次侧 {TRIP_CURRENT}A / CT二次侧 {TRIP_CURRENT/CT_RATIO:.1f}A)",
            "blue"
        )
        # BC相序接反合闸：模拟中无保护器，允许合闸但提示短路电流
        if sim.gen2.breaker_closed and sim.fault_reverse_bc:
            self.relay_msg, self.relay_color = (
                "⚠️ 警告：Gen2 B/C相序接反！合闸后产生短路电流！（模拟中无保护器，实际系统将立即跳闸）",
                "red"
            )
        if self.i1_rms > TRIP_CURRENT:
            sim.gen1.breaker_closed = False
            self.flash_frames1 = 0  # 清除闪烁动画，确保画面同步显示断开状态
            self.relay_msg, self.relay_color = "💥 保护: Gen 1 环流过大，跳闸！", "red"
        if self.i2_rms > TRIP_CURRENT:
            sim.gen2.breaker_closed = False
            sim.auto_sync_active = False
            self.flash_frames2 = 0  # 清除闪烁动画，确保画面同步显示断开状态
            self.relay_msg, self.relay_color = "💥 保护: Gen 2 环流过大，跳闸！", "red"
        return {'delta1': delta1, 'delta2': delta2}

    def _apply_droop_control(self, sim):
        if sim.droop_enabled and not sim.paused:
            if sim.gen1.breaker_closed:
                sim.gen1.freq = max(48.0, min(52.0, sim.gen1.freq - KP_DROOP * self.ip1))
                sim.gen1.amp = max(200.0, min(400.0, sim.gen1.amp - KQ_DROOP * self.iq1))
            if sim.gen2.breaker_closed:
                sim.gen2.freq = max(48.0, min(52.0, sim.gen2.freq - KP_DROOP * self.ip2))
                sim.gen2.amp = max(200.0, min(400.0, sim.gen2.amp - KQ_DROOP * self.iq2))

    def _update_circulating_current(self, sim, a1, a2, delta1, delta2):
        if sim.gen1.breaker_closed and sim.gen2.breaker_closed:
            t = self.animation_time
            w1 = 2 * np.pi * sim.gen1.freq
            w2 = 2 * np.pi * sim.gen2.freq
            p1 = np.radians(sim.gen1.phase_deg)
            p2 = np.radians(sim.gen2.phase_deg)

            ang1 = w1 * t + p1
            ang2 = w2 * t + p2
            e1_r, e1_i = a1 * np.cos(ang1), a1 * np.sin(ang1)
            e2_r, e2_i = a2 * np.cos(ang2), a2 * np.sin(ang2)

            i12_r = (e1_r - e2_r) / (2 * XS)
            i12_i = (e1_i - e2_i) / (2 * XS)
            i12_rms = np.sqrt(i12_r**2 + i12_i**2) / np.sqrt(2)

            freq_diff = sim.gen1.freq - sim.gen2.freq
            amp_diff = a1 - a2

            if abs(freq_diff) > 0.05:
                dir_str = ">>> 有功 >>>" if freq_diff > 0 else "<<< 有功 <<<"
            elif abs(amp_diff) > 50:
                dir_str = ">>> 无功 >>>" if amp_diff > 0 else "<<< 无功 <<<"
            else:
                dir_str = "<-> 平衡 <->"

            self.circ_msg = (f"机组环流: Gen1 {dir_str} Gen2 | "
                             f"CT二次: {i12_rms / CT_RATIO:.3f}A | "
                             f"Δf={freq_diff:+.2f}Hz  ΔU={amp_diff:+.0f}V")
            self.circ_color = _heat_color(i12_rms)
        else:
            self.circ_msg, self.circ_color = "机组间未形成直接环流回路", "gray"

    def _update_wave_history(self, prev_animation_time, wave_state, a1, a2, shift_b, shift_c, g1_connected, g2_connected):
        if not self.history_initialized or not self.plot_data:
            self.plot_data = self._build_wave_history(
                wave_state['bus_w'], wave_state['w_g1'], wave_state['w_g2'],
                wave_state['bus_p'], wave_state['p_g1'], wave_state['p_g2'],
                wave_state['bus_a'], a1, a2, shift_b, shift_c,
            )
            self.history_initialized = True
            return

        interval_dt = max(self.animation_time - prev_animation_time, self.wave_sample_dt)
        sample_count = max(1, int(np.ceil(interval_dt / self.wave_sample_dt)))
        sample_times = np.linspace(prev_animation_time + interval_dt / sample_count, self.animation_time, sample_count)

        for sample_time in sample_times:
            samples = self._get_instant_samples(
                sample_time, wave_state['bus_w'], wave_state['w_g1'], wave_state['w_g2'],
                wave_state['bus_p'], wave_state['p_g1'], wave_state['p_g2'],
                wave_state['bus_a'], a1, a2, shift_b, shift_c,
            )
            self._append_history_sample('ga', samples['ga'])
            self._append_history_sample('gb', samples['gb'])
            self._append_history_sample('gc', samples['gc'])
            self._append_history_sample('g1a', samples['g1a'])
            self._append_history_sample('g1b', samples['g1b'])
            self._append_history_sample('g1c', samples['g1c'])
            self._append_history_sample('g2a', samples['g2a'])
            self._append_history_sample('g2b', samples['g2b'])
            self._append_history_sample('g2c', samples['g2c'])
            self._append_history_sample('ic1', (samples['g1a'] - samples['ga']) / XS if g1_connected else 0.0)
            self._append_history_sample('ic2', (samples['g2a'] - samples['ga']) / XS if g2_connected else 0.0)

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

    def _update_breaker_state(self, generator, gen_id, a_value, delta, ref_freq, ref_amp, is_isolated):
        diff_deg = abs((np.degrees(delta) % 360 + 360) % 360)
        if diff_deg > 180:
            diff_deg -= 360

        text_attr  = 'brk1_text'   if gen_id == 1 else 'brk2_text'
        bg_attr    = 'brk1_bg'     if gen_id == 1 else 'brk2_bg'
        visual_attr = 'brk1_visual' if gen_id == 1 else 'brk2_visual'
        flash_attr  = 'flash_frames1' if gen_id == 1 else 'flash_frames2'

        sync_ok = True if is_isolated and not self.bus_live else (
            abs(generator.freq - ref_freq) <= 0.5 and
            abs(ref_amp - a_value) <= 400.0 and
            abs(diff_deg) <= 15.0
        )

        if generator.mode == "stop":
            generator.breaker_closed = False
            generator.cmd_close = False
        elif generator.mode == "auto":
            if is_isolated and not self.bus_live:
                if abs(generator.freq - GRID_FREQ) < 0.1 and abs(GRID_AMP - a_value) <= 150.0 and not generator.breaker_closed:
                    generator.breaker_closed = True
            else:
                # 第三步同步功能测试期间，Auto 机组只做同步跟踪，不自动真实合闸；
                # 点击"完成第三步测试"后，恢复正常自动合闸逻辑。
                if (self.ctrl.is_sync_test_complete()
                        and abs(generator.freq - ref_freq) < 0.1
                        and abs(ref_amp - a_value) <= 150.0
                        and abs(diff_deg) <= 1.5
                        and not generator.breaker_closed):
                    generator.breaker_closed = True
            generator.cmd_close = False
        elif generator.mode == "manual" and generator.cmd_close:
            generator.cmd_close = False
            if not generator.breaker_closed:
                # 任一测试模式激活时：允许不起机机械合闸，跳过同期检查
                test_mode = (getattr(self.ctrl.sim_state, 'loop_test_mode', False) or
                             getattr(self.ctrl.sim_state, 'pt_phase_test_mode', False))
                if generator.breaker_position != BreakerPosition.WORKING or sync_ok or test_mode:
                    generator.breaker_closed = True
                else:
                    self.relay_msg, self.relay_color = f"非同期合闸爆炸！频差:{abs(generator.freq-ref_freq):.1f}Hz, 压差:{abs(ref_amp-a_value):.0f}V, 角差:{abs(diff_deg):.0f}°", "red"
                    setattr(self, text_attr, "断路器: 炸毁")
                    setattr(self, bg_attr, "red")
                    setattr(self, visual_attr, False)

        if generator.breaker_closed:
            if generator.breaker_position == BreakerPosition.WORKING:
                setattr(self, text_attr, "一次侧: 并网运行 (工作位)")
                setattr(self, bg_attr, "green")
                setattr(self, visual_attr, True)
            elif generator.breaker_position == BreakerPosition.TEST:
                setattr(self, text_attr, "二次侧: 模拟闭合 (试验位)")
                setattr(self, bg_attr, "#ffaa00")
                setattr(self, visual_attr, False)
            else:
                setattr(self, text_attr, "无效: 触头闭合 (脱开位)")
                setattr(self, bg_attr, "gray")
                setattr(self, visual_attr, False)
            setattr(self, flash_attr, 0)
            return

        if self.bus_live and abs(generator.freq - ref_freq) < 0.2 and abs(ref_amp - a_value) <= 150.0 and abs(diff_deg) <= 5.0:
            setattr(self, flash_attr, 15)
        if getattr(self, flash_attr) > 0:
            setattr(self, flash_attr, getattr(self, flash_attr) - 1)
            setattr(self, text_attr, f"Gen{gen_id}: ⚡ 同期条件满足，可合闸")
            setattr(self, bg_attr, "orange")
            setattr(self, visual_attr, False)
        else:
            setattr(self, text_attr, f"断路器: OPEN ({generator.breaker_position})")
            setattr(self, bg_attr, "gray")
            setattr(self, visual_attr, False)

    def _update_breaker_logic(self, sim, delta1, delta2, a1, a2, ref_freq, ref_amp, is_isolated):
        self.color_sw1 = _heat_color(self.i1_rms)
        self.color_sw2 = _heat_color(self.i2_rms)
        self._update_breaker_state(sim.gen1, 1, a1, delta1, ref_freq, ref_amp, is_isolated)
        self._update_breaker_state(sim.gen2, 2, a2, delta2, ref_freq, ref_amp, is_isolated)

    def _update_plot_metadata(self, wave_state, a1, a2, shift_b, shift_c):
        self.plot_data.update({
            'ang_grid': wave_state['ang_bus'],
            'ang_g1':   wave_state['ang_g1'],
            'ang_g2':   wave_state['ang_g2'],
            'a1': a1, 'a2': a2,
            'shift_b': shift_b, 'shift_c': shift_c,
        })

    def _update_pt_measurements(self, bus_a, a1, a2):
        pt_ratio = PT_RATIO
        self.pt1_v = (a1  / np.sqrt(2) * np.sqrt(3)) / pt_ratio
        self.pt2_v = (bus_a / np.sqrt(2) * np.sqrt(3)) / pt_ratio
        # Gen2 不起机但合闸 → 母线反向馈电 → PT3 电压等于母线电压
        gen2 = self.ctrl.sim_state.gen2
        pt3_amp = bus_a if (gen2.breaker_closed and not gen2.running) else a2
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
                if loop_pair:
                    loop_done = self.ctrl.loop_test_state.get('completed', False)
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
                elif frozenset({n1, n2}) in valid_pairs:
                    key1 = self.ctrl.resolve_pt_node_plot_key(n1)
                    key2 = self.ctrl.resolve_pt_node_plot_key(n2)
                    # 相位一致性：从 plot_key 末位提取实际电气相，与端子标签比较
                    actual_ph1 = key1[-1].upper()   # 'g2c'[-1] → 'C'
                    actual_ph2 = key2[-1].upper()
                    labeled1 = n1.split('_')[1]     # 'PT3_B' → 'B'
                    labeled2 = n2.split('_')[1]
                    phases_match = (actual_ph1 == actual_ph2)
                    self.meter_phase_match = phases_match
                    # 相位注释（仅当实际相与标签不一致时显示）
                    ann1 = f"[实际{actual_ph1}相]" if actual_ph1 != labeled1 else ""
                    ann2 = f"[实际{actual_ph2}相]" if actual_ph2 != labeled2 else ""
                    seq_note = "" if phases_match else f" ⚠相序:{actual_ph1}≠{actual_ph2}"
                    # 电压幅值（供 PT压差测试 使用）
                    diff_data = self.plot_data[key1] - self.plot_data[key2]
                    primary_rms_diff = np.sqrt(np.mean(diff_data**2))
                    sec_rms_diff = primary_rms_diff / ((PRIMARY_AMP / np.sqrt(2)) / 100.0)
                    meter_v = np.sqrt(sec_rms_diff**2 + 30.0**2)
                    self.meter_voltage = meter_v
                    self.meter_nodes = (n1, n2)
                    if meter_v < 60.0:
                        status = "同相 (可合闸)"
                        self.meter_color = "green"
                        self.meter_status = "ok"
                    else:
                        status = "异相 (危险!)"
                        self.meter_color = "red"
                        self.meter_status = "danger"
                    # 相序状态作为主信息，电压作为次要参考
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

    def update_physics(self):
        sim = self.ctrl.sim_state
        is_isolated = sim.system_mode == SystemMode.ISOLATED_BUS

        bus_state = self._update_bus_reference(sim, is_isolated)
        self._update_arbitration(
            sim,
            bus_state['g1_on_bus'],
            bus_state['g2_on_bus'],
            bus_state['ref_freq'],
            bus_state['ref_amp'],
        )
        bus_state = self._update_bus_reference(sim, is_isolated)

        prev_animation_time = self._advance_time(sim)
        a1, a2 = self._update_actual_amplitudes(sim)
        self._apply_engine_trip_interlocks(sim)

        wave_state = self._compute_wave_state(sim, is_isolated, bus_state['g1_on_bus'], bus_state['g2_on_bus'], a1, a2)
        deltas = self._update_protection_state(sim, wave_state, a1, a2, bus_state['g1_on_bus'], bus_state['g2_on_bus'])
        self._apply_droop_control(sim)
        self._update_circulating_current(sim, a1, a2, deltas['delta1'], deltas['delta2'])

        shift_b = 2 * np.pi / 3 if sim.fault_reverse_bc else -2 * np.pi / 3
        shift_c = -2 * np.pi / 3 if sim.fault_reverse_bc else 2 * np.pi / 3
        self._update_wave_history(
            prev_animation_time, wave_state, a1, a2, shift_b, shift_c,
            bus_state['g1_on_bus'], bus_state['g2_on_bus'],
        )
        self._update_grounding(sim)
        self._update_breaker_logic(
            sim, deltas['delta1'], deltas['delta2'], a1, a2,
            bus_state['ref_freq'], bus_state['ref_amp'], is_isolated,
        )
        self._update_plot_metadata(wave_state, a1, a2, shift_b, shift_c)
        self._update_pt_measurements(wave_state['bus_a'], a1, a2)
        self._update_multimeter(sim)

    def build_render_state(self):
        """将物理引擎当前帧的所有渲染属性打包为 RenderState 快照，供 UI 消费。"""
        from adapters.render_state import RenderState
        return RenderState(
            plot_data         = self.plot_data,
            fixed_deg         = self.fixed_deg,
            bus_live          = self.bus_live,
            bus_amp           = self.bus_amp,
            bus_source        = self.bus_source,
            bus_reference_gen = self.bus_reference_gen,
            bus_status_msg    = self.bus_status_msg,
            bus_reference_msg = self.bus_reference_msg,
            brk1_text         = self.brk1_text,
            brk1_bg           = self.brk1_bg,
            brk1_visual       = self.brk1_visual,
            color_sw1         = self.color_sw1,
            brk2_text         = self.brk2_text,
            brk2_bg           = self.brk2_bg,
            brk2_visual       = self.brk2_visual,
            color_sw2         = self.color_sw2,
            arb_msg           = self.arb_msg,
            arb_color         = self.arb_color,
            relay_msg         = self.relay_msg,
            relay_color       = self.relay_color,
            i1_rms            = self.i1_rms,
            ip1               = self.ip1,
            iq1               = self.iq1,
            i2_rms            = self.i2_rms,
            ip2               = self.ip2,
            iq2               = self.iq2,
            circ_msg          = self.circ_msg,
            circ_color        = self.circ_color,
            ground_msg        = self.ground_msg,
            ground_color      = self.ground_color,
            pt1_v             = self.pt1_v,
            pt2_v             = self.pt2_v,
            pt3_v             = self.pt3_v,
            meter_reading     = self.meter_reading,
            meter_color       = self.meter_color,
            meter_voltage     = self.meter_voltage,
            meter_status      = self.meter_status,
            meter_nodes       = self.meter_nodes,
            meter_phase_match = self.meter_phase_match,
        )
