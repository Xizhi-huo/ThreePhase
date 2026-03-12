"""
main.py  ──  PyQt5 版本
三相电并网仿真教学系统 · 控制器层 + 程序入口

架构说明
────────
PowerSyncController   唯一数据源 (SimulationState) + 业务逻辑
PowerSyncUI           视图（ui.py），通过 ctrl 引用读写状态
PhysicsEngine         物理计算（physics.py），通过 ctrl.sim_state 读写
QTimer                替代 tkinter after()，每 33ms 驱动主循环
"""

import sys
import random

from PyQt5 import QtWidgets, QtCore

from config_qt5 import (
    GRID_FREQ, GRID_AMP, BreakerPosition, SystemMode
)
from models_qt5 import GeneratorState, SimulationState
from physics_qt5 import PhysicsEngine
from ui_qt5 import PowerSyncUI


class PowerSyncController:
    """
    业务控制器。
    不继承任何 Qt 类，持有 sim_state（唯一数据源）、physics、ui 三个对象。
    UI 事件通过 ui 的槽函数调用 ctrl 方法；物理引擎通过 ctrl 访问 sim_state。
    """

    def __init__(self):
        # ── 随机初始状态 ──────────────────────────────────────────────────
        init_amp1   = round(random.uniform(8000.0, 9000.0), 1)
        init_phase1 = round(random.uniform(-180.0, 180.0), 1)
        init_freq1  = round(random.uniform(48.0, 49.0), 1)
        init_amp2   = round(random.uniform(8000.0, 9000.0), 1)
        init_phase2 = round(random.uniform(-180.0, 180.0), 1)
        init_freq2  = round(random.uniform(51.0, 52.0), 1)

        # ── 唯一数据源 ────────────────────────────────────────────────────
        self.sim_state = SimulationState(
            gen1=GeneratorState(freq=init_freq1, amp=init_amp1, phase_deg=init_phase1),
            gen2=GeneratorState(freq=init_freq2, amp=init_amp2, phase_deg=init_phase2),
        )

        # PT 相序 & 考核状态
        self.pt_phase_orders = {
            'PT1': ['A', 'B', 'C'],
            'PT2': ['A', 'B', 'C'],
            'PT3': ['A', 'B', 'C'],
        }
        self.pt_exam_states = {
            1: self._create_pt_exam_state(),
            2: self._create_pt_exam_state(),
        }

        # PT 黑盒模式（纯 Python bool，不再依赖 tk.BooleanVar）
        self.pt_blackbox_mode_val: bool = False

        # ── 物理引擎 ──────────────────────────────────────────────────────
        self.physics = PhysicsEngine(self)

        # ── UI 窗口 ───────────────────────────────────────────────────────
        self.ui = PowerSyncUI(self)

        # ── 主循环定时器（33ms ≈ 30fps）──────────────────────────────────
        self._timer = QtCore.QTimer()
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    # ── pt_blackbox_mode 兼容接口（ui.py 调用 ctrl.pt_blackbox_mode.get()）
    class _BoolProxy:
        """轻量代理，让 ui.py 中的 ctrl.pt_blackbox_mode.get() 调用不报错。"""
        def __init__(self, ctrl):
            self._ctrl = ctrl
        def get(self):
            return self._ctrl.pt_blackbox_mode_val
        def set(self, v):
            self._ctrl.pt_blackbox_mode_val = bool(v)

    @property
    def pt_blackbox_mode(self):
        return self._BoolProxy(self)

    # ════════════════════════════════════════════════════════════════════════
    # 属性代理（与原版保持完全相同的访问接口）
    # ════════════════════════════════════════════════════════════════════════
    @property
    def gen1_running(self): return self.sim_state.gen1.running
    @gen1_running.setter
    def gen1_running(self, v): self.sim_state.gen1.running = v

    @property
    def gen2_running(self): return self.sim_state.gen2.running
    @gen2_running.setter
    def gen2_running(self, v): self.sim_state.gen2.running = v

    @property
    def breaker1_closed(self): return self.sim_state.gen1.breaker_closed
    @breaker1_closed.setter
    def breaker1_closed(self, v): self.sim_state.gen1.breaker_closed = v

    @property
    def breaker2_closed(self): return self.sim_state.gen2.breaker_closed
    @breaker2_closed.setter
    def breaker2_closed(self, v): self.sim_state.gen2.breaker_closed = v

    @property
    def cmd_close_g1(self): return self.sim_state.gen1.cmd_close
    @cmd_close_g1.setter
    def cmd_close_g1(self, v): self.sim_state.gen1.cmd_close = v

    @property
    def cmd_close_g2(self): return self.sim_state.gen2.cmd_close
    @cmd_close_g2.setter
    def cmd_close_g2(self, v): self.sim_state.gen2.cmd_close = v

    @property
    def feeder_closed(self): return self.sim_state.feeder_closed
    @feeder_closed.setter
    def feeder_closed(self, v): self.sim_state.feeder_closed = v

    @property
    def is_paused(self): return self.sim_state.paused
    @is_paused.setter
    def is_paused(self, v): self.sim_state.paused = v

    @property
    def auto_sync_active(self): return self.sim_state.auto_sync_active
    @auto_sync_active.setter
    def auto_sync_active(self, v): self.sim_state.auto_sync_active = v

    @property
    def sync_target(self): return self.sim_state.sync_target
    @sync_target.setter
    def sync_target(self, v): self.sim_state.sync_target = v

    @property
    def probe1_node(self): return self.sim_state.probe1_node
    @probe1_node.setter
    def probe1_node(self, v): self.sim_state.probe1_node = v

    @property
    def probe2_node(self): return self.sim_state.probe2_node
    @probe2_node.setter
    def probe2_node(self, v): self.sim_state.probe2_node = v

    # ════════════════════════════════════════════════════════════════════════
    # PT 考核辅助
    # ════════════════════════════════════════════════════════════════════════
    def _create_pt_exam_state(self):
        return {
            'records': {'A': None, 'B': None, 'C': None},
            'feedback': "请先切到试验位置，并在母排拓扑页完成三相 PT 二次端子压差测量。",
            'feedback_color': '#444444',
        }

    def _get_generator_state(self, gen_id):
        return self.sim_state.gen1 if gen_id == 1 else self.sim_state.gen2

    def _set_pt_exam_feedback(self, gen_id, message, color='#444444'):
        self.pt_exam_states[gen_id]['feedback'] = message
        self.pt_exam_states[gen_id]['feedback_color'] = color

    def _expected_pt_probe_pair(self, gen_id, phase):
        bus_node = f"PT2_{phase}"
        gen_node = f"PT1_{phase}" if gen_id == 1 else f"PT3_{phase}"
        return {bus_node, gen_node}

    def resolve_pt_node_plot_key(self, node_name):
        pt_name, terminal = node_name.split('_', 1)
        terminal_index = ('A', 'B', 'C').index(terminal)
        actual_phase = self.pt_phase_orders[pt_name][terminal_index]
        prefix = {'PT1': 'g1', 'PT2': 'g', 'PT3': 'g2'}[pt_name]
        return f"{prefix}{actual_phase.lower()}"

    def resolve_loop_node_phase(self, node_name):
        _, gen_name, terminal = node_name.split('_', 2)
        if gen_name == 'G2' and self.sim_state.fault_reverse_bc:
            return {'A': 'A', 'B': 'C', 'C': 'B'}[terminal]
        return terminal

    def _get_current_pt_phase_match(self, gen_id):
        sim = self.sim_state
        if not sim.probe1_node or not sim.probe2_node:
            return None
        pair = {sim.probe1_node, sim.probe2_node}
        for phase in ('A', 'B', 'C'):
            if pair == self._expected_pt_probe_pair(gen_id, phase):
                return phase
        return None

    def reset_pt_exam(self, gen_id=None):
        target_ids = (gen_id,) if gen_id in (1, 2) else (1, 2)
        for gid in target_ids:
            self.pt_exam_states[gid] = self._create_pt_exam_state()

    def record_pt_measurement(self, phase):
        gen_id    = self.ui._pt_target_bg.checkedId()
        if gen_id <= 0:
            gen_id = 1
        generator = self._get_generator_state(gen_id)
        phase     = phase.upper()

        if generator.breaker_position != BreakerPosition.TEST:
            self._set_pt_exam_feedback(gen_id, "请先将开关柜切到试验位置，再记录 PT 二次端子压差。", "red")
            return
        if not self.sim_state.multimeter_mode:
            self._set_pt_exam_feedback(gen_id, "请先开启万用表，再到母排拓扑页放置表笔。", "red")
            return
        if not self.sim_state.probe1_node or not self.sim_state.probe2_node:
            self._set_pt_exam_feedback(gen_id, "表笔尚未放置完成，请在母排拓扑页连接 PT 二次端子排上的同相端子。", "red")
            return

        matched_phase = self._get_current_pt_phase_match(gen_id)
        if matched_phase != phase:
            if matched_phase is None:
                msg = f"当前表笔不在 Gen {gen_id} {phase} 相 PT 二次端子与 PT2 同相端子之间，请重新放置。"
            else:
                msg = f"当前表笔落在 {matched_phase} 相，请记录对应相别或重新放置表笔。"
            self._set_pt_exam_feedback(gen_id, msg, "red")
            return

        meter_v      = getattr(self.physics, 'meter_voltage', None)
        meter_status = getattr(self.physics, 'meter_status', 'idle')
        if meter_v is None or meter_status not in ('ok', 'danger'):
            self._set_pt_exam_feedback(gen_id, "当前测量结果无效，请确认表笔接在 PT 二次端子排对应端子上。", "red")
            return
        if meter_status != 'ok':
            self._set_pt_exam_feedback(gen_id, f"{phase} 相 PT 二次端子压差为 {meter_v:.1f} V，暂不满足合闸条件，请继续调整。", "red")
            return

        self.pt_exam_states[gen_id]['records'][phase] = {
            'voltage': meter_v,
            'reading': self.physics.meter_reading,
        }
        if self.is_pt_exam_ready(gen_id):
            msg = f"Gen {gen_id} 三相 PT 二次端子压差已完成记录，可执行合闸。"
        elif all(self.pt_exam_states[gen_id]['records'][ph] is not None for ph in ('A', 'B', 'C')):
            msg = f"Gen {gen_id} 三相 PT 二次端子压差已记录，请切回工作位置后合闸。"
        else:
            msg = f"Gen {gen_id} {phase} 相 PT 二次端子压差记录完成：{meter_v:.1f} V。"
        self._set_pt_exam_feedback(gen_id, msg, "#006600")

    def get_pt_exam_steps(self, gen_id):
        generator = self._get_generator_state(gen_id)
        records   = self.pt_exam_states[gen_id]['records']
        has_any   = any(records[ph] is not None for ph in ('A', 'B', 'C'))
        all_rec   = all(records[ph] is not None for ph in ('A', 'B', 'C'))
        return [
            (f"1. 将 Gen {gen_id} 开关柜切到试验位置",
             generator.breaker_position == BreakerPosition.TEST or has_any),
            ("2. 开启万用表并在母排拓扑页连接 PT 二次端子排上的同相端子",
             self.sim_state.multimeter_mode or has_any),
            ("3. 记录 A 相 PT 二次端子压差", records['A'] is not None),
            ("4. 记录 B 相 PT 二次端子压差", records['B'] is not None),
            ("5. 记录 C 相 PT 二次端子压差", records['C'] is not None),
            (f"6. 切回 Gen {gen_id} 工作位置并准备合闸",
             all_rec and generator.breaker_position == BreakerPosition.WORKING),
        ]

    def get_pt_exam_close_blockers(self, gen_id):
        generator = self._get_generator_state(gen_id)
        records   = self.pt_exam_states[gen_id]['records']
        blockers  = []
        if not any(records[ph] is not None for ph in ('A', 'B', 'C')):
            if generator.breaker_position != BreakerPosition.TEST:
                blockers.append("未切至试验位置完成 PT 二次端子测量")
            if not self.sim_state.multimeter_mode:
                blockers.append("未开启万用表")
        for phase in ('A', 'B', 'C'):
            if records[phase] is None:
                blockers.append(f"未记录 {phase} 相 PT 二次端子压差")
        return blockers

    def is_pt_exam_ready(self, gen_id):
        generator = self._get_generator_state(gen_id)
        records   = self.pt_exam_states[gen_id]['records']
        return (
            generator.breaker_position == BreakerPosition.WORKING and
            all(records[ph] is not None for ph in ('A', 'B', 'C'))
        )

    def _should_enforce_pt_exam_before_close(self):
        return self.sim_state.grounding_mode != "断开"

    # ════════════════════════════════════════════════════════════════════════
    # 控制动作
    # ════════════════════════════════════════════════════════════════════════
    def instant_sync(self):
        for gen in (self.sim_state.gen1, self.sim_state.gen2):
            gen.freq      = GRID_FREQ
            gen.amp       = GRID_AMP
            gen.phase_deg = 0.0

    def toggle_engine(self, gen_id: int):
        if gen_id == 1:
            self.gen1_running = not self.gen1_running
        elif gen_id == 2:
            self.gen2_running = not self.gen2_running

    def toggle_breaker(self, gen_id: int):
        generator = self._get_generator_state(gen_id)
        attr_closed  = f'breaker{gen_id}_closed'
        attr_cmd     = f'cmd_close_g{gen_id}'

        if getattr(self, attr_closed):
            setattr(self, attr_closed, False)
        else:
            if (generator.breaker_position == BreakerPosition.WORKING
                    and self._should_enforce_pt_exam_before_close()):
                blockers = self.get_pt_exam_close_blockers(gen_id)
                if blockers:
                    warn_msg = "PT 二次端子压差考核未完成，当前不能合闸：\n" + "\n".join(
                        f"{i}. {item}" for i, item in enumerate(blockers, 1)
                    )
                    self._set_pt_exam_feedback(gen_id, warn_msg.replace("\n", "；"), "red")
                    self.ui.tab_widget.setCurrentIndex(2)   # 跳到 PT 考核 Tab
                    self.ui.show_warning("合闸前步骤未完成", warn_msg)
                    return
            setattr(self, attr_cmd, True)

    def toggle_feeder(self):
        self.feeder_closed = not self.feeder_closed

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        self.ui.pause_btn.setText(
            "▶ 恢复物理时空" if self.is_paused else "⏸ 暂停整个物理空间"
        )
        self.ui.pause_btn.setStyleSheet(
            f"background:{'#99ff99' if self.is_paused else '#ffcc00'}; "
            f"font-weight:bold; font-size:13px; padding:7px;"
        )

    def reshuffle_pt_phase_orders(self):
        base = ['A', 'B', 'C']
        for pt_name in self.pt_phase_orders:
            new_order = base[:]
            while new_order == base:
                random.shuffle(new_order)
            self.pt_phase_orders[pt_name] = new_order[:]
        self.rebuild_circuit_view()

    def reset_pt_phase_orders(self):
        self.pt_phase_orders = {
            'PT1': ['A', 'B', 'C'],
            'PT2': ['A', 'B', 'C'],
            'PT3': ['A', 'B', 'C'],
        }
        self.rebuild_circuit_view()

    def on_pt_blackbox_toggle(self, checked: bool):
        self.pt_blackbox_mode_val = checked
        if not checked:
            self.reset_pt_phase_orders()
        else:
            self.reshuffle_pt_phase_orders()

    def rebuild_circuit_view(self):
        self.ui.rebuild_circuit_diagram()

    # ════════════════════════════════════════════════════════════════════════
    # 主循环（QTimer 每 33ms 触发）
    # ════════════════════════════════════════════════════════════════════════
    def _tick(self):
        try:
            self.physics.update_physics()
            self.ui.render_visuals()
        except Exception as e:
            print(f"[Runtime Warning] {e}")


# ════════════════════════════════════════════════════════════════════════════
# 程序入口
# ════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    # Windows HiDPI
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")  # 跨平台一致外观

    ctrl = PowerSyncController()
    ctrl.ui.showMaximized()

    sys.exit(app.exec_())