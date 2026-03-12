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

        # 回路连通性测试状态
        self.loop_test_state = self._create_loop_test_state()

        # 同步功能测试状态
        self.sync_test_state = self._create_sync_test_state()

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
            'completed': False,
            'feedback': "请先恢复小电阻接地，并将机组并入母排后，在母排拓扑页完成三相 PT 二次端子压差测量。",
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

    def _is_pt_exam_setup_ready(self, gen_id):
        generator = self._get_generator_state(gen_id)
        return (
            self.sim_state.grounding_mode == "小电阻接地" and
            generator.breaker_position == BreakerPosition.WORKING and
            generator.breaker_closed
        )

    # ════════════════════════════════════════════════════════════════════════
    # 回路连通性测试辅助
    # ════════════════════════════════════════════════════════════════════════
    def _create_loop_test_state(self):
        return {
            'records': {'A': None, 'B': None, 'C': None},
            'completed': False,
            'feedback': "请先断开中性点小电阻，将两台发电机切至手动模式，起机并合闸后，用万用表测量三相回路连通性。",
            'feedback_color': '#444444',
        }

    def _set_loop_test_feedback(self, message, color='#444444'):
        self.loop_test_state['feedback'] = message
        self.loop_test_state['feedback_color'] = color

    def _get_current_loop_phase_match(self):
        sim = self.sim_state
        n1, n2 = sim.probe1_node, sim.probe2_node
        if not n1 or not n2:
            return None
        if not (n1.startswith('LOOP_G') and n2.startswith('LOOP_G')):
            return None
        parts1 = n1.split('_')   # ['LOOP', 'G1', 'A']
        parts2 = n2.split('_')   # ['LOOP', 'G2', 'A']
        if parts1[1] == parts2[1]:
            return None          # 同一台发电机，无效
        if parts1[2] == parts2[2]:
            return parts1[2]     # 同相，返回相别
        return None              # 异相

    def get_loop_test_steps(self):
        sim = self.sim_state
        gen1, gen2 = sim.gen1, sim.gen2
        state = self.loop_test_state
        records = state['records']
        all_rec = all(records[ph] is not None for ph in ('A', 'B', 'C'))
        steps = [
            ("1. 断开中性点小电阻连接",
             sim.grounding_mode == "断开"),
            ("2. 将 Gen 1 切至手动工作模式",
             gen1.mode == "manual"),
            ("3. 将 Gen 2 切至手动工作模式",
             gen2.mode == "manual"),
            ("4. 设置频率/幅值/相位并起机运行",
             gen1.running and gen2.running),
            ("5. 依次合闸 Gen 1（切至工作位置后合闸）",
             gen1.breaker_position == BreakerPosition.WORKING and gen1.breaker_closed),
            ("6. 依次合闸 Gen 2（切至工作位置后合闸）",
             gen2.breaker_position == BreakerPosition.WORKING and gen2.breaker_closed),
            ("7. 开启万用表，在母排拓扑页测量三相回路",
             sim.multimeter_mode),
            ("8. 记录 A/B/C 三相回路连通性结果",
             all_rec),
        ]
        if state.get('completed'):
            return [(text, True) for text, _ in steps]
        return steps

    def record_loop_measurement(self, phase):
        sim = self.sim_state
        gen1, gen2 = sim.gen1, sim.gen2
        phase = phase.upper()

        if sim.grounding_mode != "断开":
            self._set_loop_test_feedback('请先断开中性点小电阻连接（接地系统选"断开"）。', "red")
            return
        if gen1.mode != "manual" or gen2.mode != "manual":
            self._set_loop_test_feedback("请先将两台发电机都切至手动（Manual）模式。", "red")
            return
        if not (gen1.running and gen2.running):
            self._set_loop_test_feedback("请先起动两台发电机。", "red")
            return
        if not (gen1.breaker_closed and gen1.breaker_position == BreakerPosition.WORKING):
            self._set_loop_test_feedback("请先将 Gen 1 切至工作位置并合闸。", "red")
            return
        if not (gen2.breaker_closed and gen2.breaker_position == BreakerPosition.WORKING):
            self._set_loop_test_feedback("请先将 Gen 2 切至工作位置并合闸。", "red")
            return
        if not sim.multimeter_mode:
            self._set_loop_test_feedback("请先开启万用表。", "red")
            return

        # 强制 A→B→C 顺序，不允许跳跃录入
        phase_order = ('A', 'B', 'C')
        for prev in phase_order[:phase_order.index(phase)]:
            if self.loop_test_state['records'][prev] is None:
                self._set_loop_test_feedback(
                    f"请先完成 {prev} 相的测量记录，再记录 {phase} 相。", "red")
                return

        current_phase = self._get_current_loop_phase_match()
        if current_phase != phase:
            if current_phase is None:
                msg = (f"当前表笔未正确对准 {phase} 相回路，"
                       f"请在母排拓扑页将表笔分别放在 G1 与 G2 的 {phase} 相回路测点。")
            else:
                msg = f"当前表笔对准的是 {current_phase} 相，请记录对应相别或重新放置表笔。"
            self._set_loop_test_feedback(msg, "red")
            return

        meter_status = getattr(self.physics, 'meter_status', 'idle')
        if meter_status not in ('ok', 'danger'):
            self._set_loop_test_feedback("测量结果无效，请确认表笔放在 G1 与 G2 的同相回路测点上。", "red")
            return
        if meter_status != 'ok':
            self._set_loop_test_feedback(f"{phase} 相回路测量显示相序不对应，请检查接线后重试。", "red")
            return

        self.loop_test_state['records'][phase] = {
            'status': meter_status,
            'reading': self.physics.meter_reading,
        }
        self.loop_test_state['completed'] = False
        all_rec = all(self.loop_test_state['records'][ph] is not None for ph in ('A', 'B', 'C'))
        if all_rec:
            self._set_loop_test_feedback(
                "三相回路连通性测试全部完成，电路连通正常，可进行第二步 PT 二次端子压差测试。", "#006600")
        else:
            self._set_loop_test_feedback(f"{phase} 相回路连通正常，请继续测量其余相别。", "#006600")

    def reset_loop_test(self):
        self.loop_test_state = self._create_loop_test_state()

    def is_loop_test_complete(self):
        return self.loop_test_state.get('completed', False)

    def finalize_loop_test(self):
        records = self.loop_test_state['records']
        if not all(records[ph] is not None for ph in ('A', 'B', 'C')):
            self._set_loop_test_feedback("请先完成 A/B/C 三相回路连通性记录，再点击“完成第一步测试”。", "red")
            return
        self.loop_test_state['completed'] = True
        self._set_loop_test_feedback("第一步【回路连通性测试】已确认完成，后续操作将不再影响该步骤状态。", "#006600")

    # ════════════════════════════════════════════════════════════════════════
    # 同步功能测试辅助
    # ════════════════════════════════════════════════════════════════════════
    def _create_sync_test_state(self):
        return {
            'round1_done': False,   # Gen1基准 → Gen2同步
            'round2_done': False,   # Gen2基准 → Gen1同步
            'completed': False,
            'feedback': "请先完成第一步（回路测试）和第二步（PT测试），再进行同步功能测试。",
            'feedback_color': '#444444',
        }

    def _set_sync_test_feedback(self, message, color='#444444'):
        self.sync_test_state['feedback'] = message
        self.sync_test_state['feedback_color'] = color

    def is_pt_exam_recorded(self, gen_id):
        """仅检查三相是否已记录，不要求当前开关柜位置（用于后续步骤前提判断）。"""
        records = self.pt_exam_states[gen_id]['records']
        return all(records[ph] is not None for ph in ('A', 'B', 'C'))

    def _is_gen_synced(self, follower, master, freq_tol=0.5, amp_tol=500.0):
        """判断 follower 是否已同步到 master 的频率和幅值。"""
        return (abs(follower.freq - master.freq) < freq_tol and
                abs(follower.amp - master.amp) < amp_tol)

    def get_sync_test_steps(self):
        sim = self.sim_state
        gen1, gen2 = sim.gen1, sim.gen2
        p = self.physics
        state = self.sync_test_state

        loop_done = self.is_loop_test_complete()
        pt_done   = self.is_pt_exam_recorded(1) and self.is_pt_exam_recorded(2)

        # 第一轮实时状态
        r1_master_ok    = (gen1.breaker_closed and
                           gen1.breaker_position == BreakerPosition.WORKING and
                           gen1.mode == "manual")
        r1_follower_ok  = gen2.mode == "auto"
        r1_synced       = (r1_master_ok and r1_follower_ok and
                           self._is_gen_synced(gen2, gen1))

        # 第二轮实时状态
        r2_master_ok    = (gen2.breaker_closed and
                           gen2.breaker_position == BreakerPosition.WORKING and
                           gen2.mode == "manual" and
                           getattr(p, 'bus_reference_gen', None) == 2)
        r2_follower_ok  = gen1.mode == "auto"
        r2_synced       = (r2_master_ok and r2_follower_ok and
                           self._is_gen_synced(gen1, gen2))

        steps = [
            ("1. 前提：第一步回路连通性测试已完成",
             loop_done),
            ("2. 前提：第二步 PT 二次端子压差测试已完成（Gen1 & Gen2）",
             pt_done),
            ("3. [第一轮] 将 Gen 1 切至手动模式并在工作位置合闸（建立母排电压）",
             r1_master_ok or state['round1_done']),
            ("4. [第一轮] 将 Gen 2 切至自动（Auto）同步模式",
             r1_follower_ok or state['round1_done']),
            ("5. [第一轮] 确认 Gen 2 已同步完成（频率/幅值与 Gen 1 匹配）",
             r1_synced or state['round1_done']),
            ("6. [第一轮] 记录结果：Gen 1 基准 → Gen 2 同步完成",
             state['round1_done']),
            ("7. [第二轮] 断开 Gen 1，将 Gen 2 切至手动模式并合闸（互换基准）",
             r2_master_ok or state['round2_done']),
            ("8. [第二轮] 将 Gen 1 切至自动（Auto）同步模式",
             r2_follower_ok or state['round2_done']),
            ("9. [第二轮] 确认 Gen 1 已同步完成（频率/幅值与 Gen 2 匹配）",
             r2_synced or state['round2_done']),
            ("10. [第二轮] 记录结果：Gen 2 基准 → Gen 1 同步完成",
             state['round2_done']),
        ]
        if state.get('completed'):
            return [(text, True) for text, _ in steps]
        return steps

    def record_sync_round(self, round_num):
        sim = self.sim_state
        gen1, gen2 = sim.gen1, sim.gen2
        p = self.physics
        state = self.sync_test_state

        # 前提：第一步、第二步必须已完成
        if not self.is_loop_test_complete():
            self._set_sync_test_feedback("请先完成第一步【回路连通性测试】。", "red")
            return
        if not (self.is_pt_exam_recorded(1) and self.is_pt_exam_recorded(2)):
            self._set_sync_test_feedback(
                "请先完成第二步【PT二次端子压差测试】（Gen1 和 Gen2 均需完成）。", "red")
            return

        if round_num == 1:
            if not (gen1.breaker_closed and
                    gen1.breaker_position == BreakerPosition.WORKING and
                    gen1.mode == "manual"):
                self._set_sync_test_feedback(
                    "请先将 Gen 1 切至手动模式并在工作位置合闸，建立母排电压。", "red")
                return
            if gen2.mode != "auto":
                self._set_sync_test_feedback(
                    "请先将 Gen 2 切至自动（Auto）同步模式。", "red")
                return
            if not self._is_gen_synced(gen2, gen1):
                df = abs(gen2.freq - gen1.freq)
                dv = abs(gen2.amp - gen1.amp)
                self._set_sync_test_feedback(
                    f"Gen 2 尚未同步完成（Δf={df:.2f} Hz，ΔV={dv:.0f} V），请等待同步后再记录。",
                    "red")
                return
            state['round1_done'] = True
            state['completed'] = False
            self._set_sync_test_feedback(
                "第一轮记录成功：Gen 1 作基准，Gen 2 同步功能正常。"
                "请断开 Gen 1，互换角色进行第二轮测试。", "#006600")

        elif round_num == 2:
            if not state['round1_done']:
                self._set_sync_test_feedback(
                    "请先完成第一轮测试并记录，再进行第二轮。", "red")
                return
            if not (gen2.breaker_closed and
                    gen2.breaker_position == BreakerPosition.WORKING and
                    gen2.mode == "manual" and
                    getattr(p, 'bus_reference_gen', None) == 2):
                self._set_sync_test_feedback(
                    "请先断开 Gen 1，将 Gen 2 切至手动模式并在工作位置合闸作为新基准。", "red")
                return
            if gen1.mode != "auto":
                self._set_sync_test_feedback(
                    "请先将 Gen 1 切至自动（Auto）同步模式。", "red")
                return
            if not self._is_gen_synced(gen1, gen2):
                df = abs(gen1.freq - gen2.freq)
                dv = abs(gen1.amp - gen2.amp)
                self._set_sync_test_feedback(
                    f"Gen 1 尚未同步完成（Δf={df:.2f} Hz，ΔV={dv:.0f} V），请等待同步后再记录。",
                    "red")
                return
            state['round2_done'] = True
            state['completed'] = False
            self._set_sync_test_feedback(
                "第二轮记录成功：Gen 2 作基准，Gen 1 同步功能正常。两台发电机同步功能测试全部完成！",
                "#006600")

    def reset_sync_test(self):
        self.sync_test_state = self._create_sync_test_state()

    def is_sync_test_complete(self):
        return self.sync_test_state.get('completed', False)

    def is_sync_test_rounds_done(self):
        return (self.sync_test_state['round1_done'] and
                self.sync_test_state['round2_done'])

    def finalize_sync_test(self):
        if not self.is_sync_test_rounds_done():
            self._set_sync_test_feedback("请先完成并记录两轮同步测试，再点击“完成第三步测试”。", "red")
            return
        self.sync_test_state['completed'] = True
        self._set_sync_test_feedback("第三步【同步功能测试】已确认完成，系统恢复正常自动合闸逻辑。", "#006600")

    def record_pt_measurement(self, phase):
        gen_id    = self.ui._pt_target_bg.checkedId()
        if gen_id <= 0:
            gen_id = 1
        generator = self._get_generator_state(gen_id)
        phase     = phase.upper()

        # 第一步（回路连通性测试）必须先完成
        if not self.is_loop_test_complete():
            self._set_pt_exam_feedback(
                gen_id,
                "请先完成第一步【回路连通性测试】，再进行 PT 二次端子压差测量。",
                "red")
            return

        # 强制 A→B→C 顺序录入
        phase_order = ('A', 'B', 'C')
        records = self.pt_exam_states[gen_id]['records']
        for prev in phase_order[:phase_order.index(phase)]:
            if records[prev] is None:
                self._set_pt_exam_feedback(
                    gen_id,
                    f"请先完成 {prev} 相的测量记录，再记录 {phase} 相。",
                    "red")
                return

        if self.sim_state.grounding_mode != "小电阻接地":
            self._set_pt_exam_feedback(gen_id, "请先恢复中性点小电阻接地，再进行 PT 二次端子压差测量。", "red")
            return
        if generator.breaker_position != BreakerPosition.WORKING or not generator.breaker_closed:
            self._set_pt_exam_feedback(gen_id, "请先将机组切至工作位置并完成并网合闸，再记录 PT 二次端子压差。", "red")
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
        self.pt_exam_states[gen_id]['completed'] = False
        if self.is_pt_exam_ready(gen_id):
            msg = f"Gen {gen_id} 三相 PT 二次端子压差已完成记录，可执行合闸。"
        elif all(self.pt_exam_states[gen_id]['records'][ph] is not None for ph in ('A', 'B', 'C')):
            msg = f"Gen {gen_id} 三相 PT 二次端子压差已记录，请切回工作位置后合闸。"
        else:
            msg = f"Gen {gen_id} {phase} 相 PT 二次端子压差记录完成：{meter_v:.1f} V。"
        self._set_pt_exam_feedback(gen_id, msg, "#006600")

    def get_pt_exam_steps(self, gen_id):
        generator = self._get_generator_state(gen_id)
        state     = self.pt_exam_states[gen_id]
        records   = state['records']
        has_any   = any(records[ph] is not None for ph in ('A', 'B', 'C'))
        steps = [
            ("1. 恢复中性点小电阻接地",
             self.sim_state.grounding_mode == "小电阻接地" or has_any),
            (f"2. 将 Gen {gen_id} 切至工作位置并并入母排",
             self._is_pt_exam_setup_ready(gen_id) or has_any),
            ("3. 开启万用表并在母排拓扑页连接 PT 二次端子排上的同相端子",
             self.sim_state.multimeter_mode or has_any),
            ("4. 记录 A 相 PT 二次端子压差", records['A'] is not None),
            ("5. 记录 B 相 PT 二次端子压差", records['B'] is not None),
            ("6. 记录 C 相 PT 二次端子压差", records['C'] is not None),
        ]
        if state.get('completed'):
            return [(text, True) for text, _ in steps]
        return steps

    def get_pt_exam_close_blockers(self, gen_id):
        generator = self._get_generator_state(gen_id)
        records   = self.pt_exam_states[gen_id]['records']
        blockers  = []
        if not any(records[ph] is not None for ph in ('A', 'B', 'C')):
            if self.sim_state.grounding_mode != "小电阻接地":
                blockers.append("未恢复中性点小电阻接地")
            if generator.breaker_position != BreakerPosition.WORKING or not generator.breaker_closed:
                blockers.append("未在工作位置并入母排完成 PT 二次端子测量")
            if not self.sim_state.multimeter_mode:
                blockers.append("未开启万用表")
        for phase in ('A', 'B', 'C'):
            if records[phase] is None:
                blockers.append(f"未记录 {phase} 相 PT 二次端子压差")
        return blockers

    def get_loop_test_blockers(self):
        return [text for text, done in self.get_loop_test_steps() if not done]

    def get_sync_test_blockers(self):
        return [text for text, done in self.get_sync_test_steps() if not done]

    def get_preclose_flow_blockers(self, gen_id):
        sections = []

        loop_blockers = self.get_loop_test_blockers()
        if loop_blockers:
            sections.append(("第一步：回路连通性测试", loop_blockers))

        return sections

    def is_pt_exam_ready(self, gen_id):
        return self.pt_exam_states[gen_id].get('completed', False)

    def finalize_pt_exam(self, gen_id):
        state = self.pt_exam_states[gen_id]
        records = state['records']
        if not all(records[ph] is not None for ph in ('A', 'B', 'C')):
            self._set_pt_exam_feedback(gen_id, "请先完成 A/B/C 三相 PT 二次端子压差记录，再点击“完成第二步测试”。", "red")
            return
        state['completed'] = True
        self._set_pt_exam_feedback(gen_id, f"第二步【Gen {gen_id} PT 二次端子压差测试】已确认完成，后续操作将不再影响该步骤状态。", "#006600")

    def _should_enforce_pt_exam_before_close(self):
        return self.sim_state.grounding_mode != "断开"

    def _should_limit_close_to_selected_pt_target(self):
        sim = self.sim_state
        return (
            sim.grounding_mode == "小电阻接地" and
            sim.gen1.mode == "manual" and
            sim.gen2.mode == "manual" and
            not self.is_sync_test_complete()
        )

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
            if self._should_limit_close_to_selected_pt_target():
                target_gen_id = self.ui._pt_target_bg.checkedId()
                if target_gen_id in (1, 2) and gen_id != target_gen_id:
                    self._set_pt_exam_feedback(
                        target_gen_id,
                        f"当前第二步正在测试 Gen {target_gen_id}，请先完成该机组的 PT 二次端子压差测试；"
                        f"若需合闸 Gen {gen_id}，请先在第二步页面切换测试对象。",
                        "red"
                    )
                    self.ui.tab_widget.setCurrentIndex(3)
                    self.ui.show_warning(
                        "当前机组不允许合闸",
                        f"第二步 PT 测试当前锁定在 Gen {target_gen_id}。\n"
                        f"请先完成 Gen {target_gen_id} 的测试，或先切换测试对象后再合闸 Gen {gen_id}。"
                    )
                    return
            if (generator.breaker_position == BreakerPosition.WORKING
                    and self._should_enforce_pt_exam_before_close()):
                blocker_sections = self.get_preclose_flow_blockers(gen_id)
                if blocker_sections:
                    msg_lines = ["隔离母排模式下合闸前流程尚未完成，当前不能合闸："]
                    for section_title, items in blocker_sections:
                        msg_lines.append(f"\n{section_title}")
                        msg_lines.extend(f"{i}. {item}" for i, item in enumerate(items, 1))
                    warn_msg = "\n".join(msg_lines)
                    self._set_pt_exam_feedback(gen_id, warn_msg.replace("\n", "；"), "red")
                    self.ui.tab_widget.setCurrentIndex(2)   # 跳到第一步流程页
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