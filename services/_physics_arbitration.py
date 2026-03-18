"""
services/_physics_arbitration.py
母排仲裁与自动同步 Mixin ── PhysicsEngine 的仲裁职责。
"""

import numpy as np

from domain.constants import GRID_FREQ, GRID_AMP
from domain.enums import BreakerPosition, SystemMode


class ArbitrationMixin:
    """母排基准解析、死母线首台投入与并网自动相角捕获。"""

    def auto_adjust_local(self, generator, sim, target_freq, target_amp):
        if generator.breaker_closed:
            return
        speed_factor = self._control_speed_factor(sim)
        err_f = target_freq - generator.freq
        step_f = 0.005 * sim.sync_gain * speed_factor
        if abs(err_f) > step_f:
            generator.freq = round(generator.freq + np.sign(err_f) * step_f, 3)
        elif sim.sync_gain > 3.0:
            generator.freq = round(generator.freq + np.sign(err_f + 0.001) * (0.005 * sim.sync_gain * speed_factor), 3)
        else:
            generator.freq = target_freq

        err_a = target_amp - generator.amp
        step_a = 5.0 * sim.sync_gain * speed_factor
        if abs(err_a) > step_a:
            generator.amp = round(generator.amp + np.sign(err_a) * step_a, 1)
        elif sim.sync_gain > 3.0:
            generator.amp = round(generator.amp + np.sign(err_a + 0.01) * (5.0 * sim.sync_gain * speed_factor), 1)
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
                sim.gen1.amp = ref_amp
                sim.gen1.freq = ref_freq
                sim.gen1.actual_amp = ref_amp
            if mode2 == "auto" and not sim.gen2.running:
                sim.gen2.running = True
                sim.gen2.amp = ref_amp
                sim.gen2.freq = ref_freq
                sim.gen2.actual_amp = ref_amp
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
                if not self.ctrl.is_sync_test_active():
                    self._handle_dead_bus_selection(sim, mode1, mode2, g1_ready, g2_ready)
                else:
                    self.dead_bus_timer = 0.0
                    self.first_ready = None
            else:
                self._handle_live_bus_sync(sim, mode1, mode2)
        else:
            self.arb_msg, self.arb_color = "🛠️ 仲裁器: 待命 (请闭合远程启动信号)", "#00ff00"
            self.dead_bus_timer = 0.0
            self.first_ready = None
