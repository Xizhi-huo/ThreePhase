"""
app/main.py  ──  PyQt5 版本
三相电并网仿真教学系统 · 控制器层 + 程序入口

架构说明
────────
PowerSyncController   唯一数据源 (SimulationState) + 业务逻辑
PowerSyncUI           视图（ui/main_window.py），通过 ctrl 引用读写状态
PhysicsEngine         物理计算（services/physics_engine.py），通过 ctrl.sim_state 读写
QTimer                替代 tkinter after()，每 33ms 驱动主循环
"""

import sys
import os
import random

# 将项目根目录加入 sys.path，确保 domain/services/ui 包可以被找到
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5 import QtWidgets, QtCore

from domain.constants import GRID_FREQ, GRID_AMP, AVAILABLE_MODES
from domain.enums import BreakerPosition, SystemMode
from domain.models import GeneratorState, SimulationState
from services.physics_engine import PhysicsEngine
from ui.main_window import PowerSyncUI


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

        # PT 相序检查状态（第二步）
        self.pt_phase_check_state = self._create_pt_phase_check_state()

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
        if pt_name == 'PT3':
            gen2 = self.sim_state.gen2
            # Gen2 合闸但未起机 → 母线反向馈电 → PT3 读母线电压（经自身接线映射）
            prefix = 'g' if (gen2.breaker_closed and not gen2.running) else 'g2'
        else:
            prefix = {'PT1': 'g1', 'PT2': 'g'}[pt_name]
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
        gen1, gen2 = self.sim_state.gen1, self.sim_state.gen2
        gnd_ok     = self.sim_state.grounding_mode == "小电阻接地"
        gen1_on    = gen1.breaker_position == BreakerPosition.WORKING and gen1.breaker_closed
        if gen_id == 1:
            return gnd_ok and gen1_on and not gen2.breaker_closed
        else:
            return gnd_ok and gen1_on and gen2.running and not gen2.breaker_closed

    # ════════════════════════════════════════════════════════════════════════
    # 回路连通性测试辅助
    # ════════════════════════════════════════════════════════════════════════
    def _create_loop_test_state(self):
        return {
            'records': {'A': None, 'B': None, 'C': None},
            'completed': False,
            'feedback': "请先断开中性点小电阻，将两台发电机切至手动模式并合闸（不要起机），再用万用表测量三相回路连通性。",
            'feedback_color': '#444444',
        }

    # ════════════════════════════════════════════════════════════════════════
    # PT 相序检查辅助（第二步）
    # ════════════════════════════════════════════════════════════════════════
    def _create_pt_phase_check_state(self):
        return {
            'completed': False,
            # 6组测量：PT1_A/B/C 和 PT3_A/B/C，各自对 PT2 同相端子
            'records': {
                'PT1_A': None, 'PT1_B': None, 'PT1_C': None,
                'PT3_A': None, 'PT3_B': None, 'PT3_C': None,
            },
            'result': None,      # None | 'pass' | 'fail'
            'feedback': (
                "请先完成第一步回路检查，然后恢复小电阻接地，将 Gen1 并入母排，"
                "进入测试模式后合闸 Gen2（不起机，母线反向馈入 PT3），"
                "开启万用表，分别测量 PT1/PT2 和 PT3/PT2 各相端子相序。"
            ),
            'feedback_color': '#444444',
        }

    def _set_pt_phase_check_feedback(self, message, color='#444444'):
        self.pt_phase_check_state['feedback'] = message
        self.pt_phase_check_state['feedback_color'] = color

    def get_pt_phase_check_steps(self):
        sim = self.sim_state
        gen1, gen2 = sim.gen1, sim.gen2
        state = self.pt_phase_check_state
        loop_done = self.is_loop_test_complete()
        gnd_ok = sim.grounding_mode == "小电阻接地"
        gen1_on_bus = (gen1.breaker_position == BreakerPosition.WORKING and gen1.breaker_closed)
        # Gen2：不起机 + 合闸（母线反向馈入 PT3）
        gen2_backfeed = not gen2.running and gen2.breaker_closed
        test_mode = sim.loop_test_mode
        rec = state['records']
        steps = [
            ("1. 前提：第一步回路连通性测试已完成", loop_done),
            ("2. 恢复中性点小电阻接地", gnd_ok),
            ("3. 确认 Gen1 在母排上（运行+合闸，提供 PT1/PT2 参考）", gen1_on_bus),
            ("4. 进入测试模式，合闸 Gen2（不起机，母线反向馈入 PT3）", gen2_backfeed and test_mode),
            ("5. 开启万用表，在母排拓扑页测量同相端子", sim.multimeter_mode),
            ("6. 记录 PT1 A 相相序（PT1_A ↔ PT2_A）", rec['PT1_A'] is not None),
            ("7. 记录 PT1 B 相相序（PT1_B ↔ PT2_B）", rec['PT1_B'] is not None),
            ("8. 记录 PT1 C 相相序（PT1_C ↔ PT2_C）", rec['PT1_C'] is not None),
            ("9. 记录 PT3 A 相相序（PT3_A ↔ PT2_A）", rec['PT3_A'] is not None),
            ("10. 记录 PT3 B 相相序（PT3_B ↔ PT2_B）", rec['PT3_B'] is not None),
            ("11. 记录 PT3 C 相相序（PT3_C ↔ PT2_C）", rec['PT3_C'] is not None),
        ]
        if state.get('completed'):
            return [(text, True) for text, _ in steps]
        return steps

    def record_pt_phase_check(self, pt_name, phase):
        """逐相手动测量记录 PT 相序。
        pt_name: 'PT1' 或 'PT3'
        phase:   'A' / 'B' / 'C'
        PT1：Gen1 并网即可；PT3：Gen2 不起机+合闸（母线反向馈入）。
        """
        pt_name = pt_name.upper()
        phase = phase.upper()
        key = f"{pt_name}_{phase}"
        sim = self.sim_state
        gen1, gen2 = sim.gen1, sim.gen2
        state = self.pt_phase_check_state

        if not self.is_loop_test_complete():
            self._set_pt_phase_check_feedback(
                "请先完成第一步【回路连通性测试】，再进行 PT 相序检查。", "red")
            return
        if sim.grounding_mode != "小电阻接地":
            self._set_pt_phase_check_feedback(
                "请先恢复中性点小电阻接地，再进行 PT 相序检查。", "red")
            return
        if gen1.breaker_position != BreakerPosition.WORKING or not gen1.breaker_closed:
            self._set_pt_phase_check_feedback(
                "请先确认 Gen1 已并入母排（工作位置+合闸），建立 PT1/PT2 参考电压。", "red")
            return

        # PT3 额外要求：Gen2 不起机 + 合闸（母线反向馈入），且须在测试模式下
        if pt_name == 'PT3':
            if gen2.running:
                self._set_pt_phase_check_feedback(
                    "测量 PT3 相序时 Gen2 应保持停机（不起机），利用母线反向馈电。", "red")
                return
            if not gen2.breaker_closed:
                self._set_pt_phase_check_feedback(
                    "请先进入测试模式并合闸 Gen2（不起机），使母线电压反向馈入 PT3 端子。", "red")
                return
            if not sim.loop_test_mode:
                self._set_pt_phase_check_feedback(
                    "请先点击\u201c进入测试模式\u201d，再合闸 Gen2 进行 PT3 相序测量。", "red")
                return

        if not sim.multimeter_mode:
            self._set_pt_phase_check_feedback("请先开启万用表。", "red")
            return

        # 同一 PT 内强制 A→B→C 顺序
        phase_order = ('A', 'B', 'C')
        for prev in phase_order[:phase_order.index(phase)]:
            prev_key = f"{pt_name}_{prev}"
            if state['records'][prev_key] is None:
                self._set_pt_phase_check_feedback(
                    f"请先完成 {pt_name} {prev} 相的测量记录，再记录 {phase} 相。", "red")
                return

        # 验证表笔位置：必须在 {pt_name}_{phase} 与 PT2_{phase} 上
        expected_pair = {key, f"PT2_{phase}"}
        actual_pair = (
            {sim.probe1_node, sim.probe2_node}
            if sim.probe1_node and sim.probe2_node else set()
        )
        if actual_pair != expected_pair:
            self._set_pt_phase_check_feedback(
                f"请在母排拓扑页将表笔放在 {key} 和 PT2_{phase} 端子上，再点击记录。",
                "red")
            return

        # 从物理引擎读取相位一致性
        phase_match = getattr(self.physics, 'meter_phase_match', None)
        if phase_match is None:
            self._set_pt_phase_check_feedback(
                "当前测量结果无效，请确认表笔接在 PT 和 PT2 同相端子上。", "red")
            return

        state['records'][key] = {
            'phase_match': phase_match,
            'reading': self.physics.meter_reading,
        }

        all_six_keys = ('PT1_A', 'PT1_B', 'PT1_C', 'PT3_A', 'PT3_B', 'PT3_C')
        all_rec = all(state['records'][k] is not None for k in all_six_keys)
        any_fail = any(
            r is not None and not r['phase_match'] for r in state['records'].values()
        )

        if any_fail:
            state['result'] = 'fail'
            self._set_pt_phase_check_feedback(
                f"⚠️ 相序异常！{key} 检测到端子接线错误，请检查对应侧 B/C 接线。", "red")
        elif all_rec:
            state['result'] = 'pass'
            self._set_pt_phase_check_feedback(
                "PT 相序检查通过：PT1/PT3 各相连线均正确，可点击\u201c完成第二步测试\u201d继续。",
                "#006600")
        elif phase_match:
            self._set_pt_phase_check_feedback(
                f"{key} 相序正确，请继续测量其余项目。", "#006600")
        else:
            state['result'] = 'fail'
            self._set_pt_phase_check_feedback(
                f"⚠️ {key} 相序异常！请检查对应侧接线。", "red")

    def reset_pt_phase_check(self):
        self.pt_phase_check_state = self._create_pt_phase_check_state()

    def is_pt_phase_check_complete(self):
        records = self.pt_phase_check_state.get('records', {})
        all_six_keys = ('PT1_A', 'PT1_B', 'PT1_C', 'PT3_A', 'PT3_B', 'PT3_C')
        return all(
            records.get(k) is not None and records[k]['phase_match']
            for k in all_six_keys
        )

    def finalize_pt_phase_check(self):
        state = self.pt_phase_check_state
        if not self.is_pt_phase_check_complete():
            self._set_pt_phase_check_feedback(
                '请先完成 PT1/PT3 全部六相相序测量（且全部通过），再点击\u201c完成第二步测试\u201d。',
                "red")
            return
        state['completed'] = True
        self.exit_loop_test_mode()   # 退出测试模式，Gen2 未起机的断路器自动断开
        self._set_pt_phase_check_feedback(
            "第二步【PT 相序检查】已确认完成，测试模式已退出，后续操作将不再影响该步骤状态。",
            "#006600")

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
            ("2. 将 Gen 1 切至手动模式并切至工作位置",
             gen1.mode == "manual" and gen1.breaker_position == BreakerPosition.WORKING),
            ("3. 将 Gen 2 切至手动模式并切至工作位置",
             gen2.mode == "manual" and gen2.breaker_position == BreakerPosition.WORKING),
            ("4. 合闸 Gen 1（不要起机，仅闭合开关）",
             gen1.breaker_position == BreakerPosition.WORKING and gen1.breaker_closed),
            ("5. 合闸 Gen 2（不要起机，仅闭合开关）",
             gen2.breaker_position == BreakerPosition.WORKING and gen2.breaker_closed),
            ("6. 开启万用表，在母排拓扑页测量三相回路",
             sim.multimeter_mode),
            ("7. 记录 A/B/C 三相回路连通性结果",
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
        if gen1.running or gen2.running:
            self._set_loop_test_feedback(
                "回路测试期间发电机不应起机！合闸但不起机，处于高压侧断路状态。", "red")
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
        all_rec = all(self.loop_test_state['records'][ph] is not None for ph in ('A', 'B', 'C'))
        if all_rec:
            self._set_loop_test_feedback(
                "三相回路连通性测试全部完成，电路连通正常，可进行第二步 PT 相序检查。", "#006600")
        else:
            self._set_loop_test_feedback(f"{phase} 相回路连通正常，请继续测量其余相别。", "#006600")

    def enter_loop_test_mode(self):
        """进入回路检查模式：跳过失压联锁，允许不起机合闸。"""
        self.sim_state.loop_test_mode = True

    def exit_loop_test_mode(self):
        """退出回路检查模式：恢复失压联锁保护，未起机的断路器自动断开。"""
        self.sim_state.loop_test_mode = False
        for gen in (self.sim_state.gen1, self.sim_state.gen2):
            if gen.breaker_closed and not gen.running:
                gen.breaker_closed = False

    def reset_loop_test(self):
        self.loop_test_state = self._create_loop_test_state()
        self.exit_loop_test_mode()

    def is_loop_test_complete(self):
        records = self.loop_test_state['records']
        return all(records[ph] is not None for ph in ('A', 'B', 'C'))

    def finalize_loop_test(self):
        records = self.loop_test_state['records']
        if not all(records[ph] is not None for ph in ('A', 'B', 'C')):
            self._set_loop_test_feedback('请先完成 A/B/C 三相回路连通性记录，再点击"完成第一步测试"。', "red")
            return
        self.loop_test_state['completed'] = True
        self.exit_loop_test_mode()   # 完成后自动退出回路检查模式
        self._set_loop_test_feedback("第一步【回路连通性测试】已确认完成，后续操作将不再影响该步骤状态。", "#006600")

    # ════════════════════════════════════════════════════════════════════════
    # 同步功能测试辅助
    # ════════════════════════════════════════════════════════════════════════
    def _create_sync_test_state(self):
        return {
            'round1_done': False,   # Gen1基准 → Gen2同步
            'round2_done': False,   # Gen2基准 → Gen1同步
            'completed': False,
            'feedback': "请先完成第一步（回路测试）、第二步（PT相序检查）和第三步（PT压差测试），再进行同步功能测试。",
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

        loop_done       = self.is_loop_test_complete()
        phase_chk_done  = self.is_pt_phase_check_complete()
        pt_done         = self.is_pt_exam_recorded(1) and self.is_pt_exam_recorded(2)

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
            ("2. 前提：第二步 PT 相序检查已完成",
             phase_chk_done),
            ("3. 前提：第三步 PT 二次端子压差测试已完成（Gen1 & Gen2）",
             pt_done),
            ("4. [第一轮] 将 Gen 1 切至手动模式并在工作位置合闸（建立母排电压）",
             r1_master_ok or state['round1_done']),
            ("5. [第一轮] 将 Gen 2 切至自动（Auto）同步模式",
             r1_follower_ok or state['round1_done']),
            ("6. [第一轮] 确认 Gen 2 已同步完成（频率/幅值与 Gen 1 匹配）",
             r1_synced or state['round1_done']),
            ("7. [第一轮] 记录结果：Gen 1 基准 → Gen 2 同步完成",
             state['round1_done']),
            ("8. [第二轮] 断开 Gen 1，将 Gen 2 切至手动模式并合闸（互换基准）",
             r2_master_ok or state['round2_done']),
            ("9. [第二轮] 将 Gen 1 切至自动（Auto）同步模式",
             r2_follower_ok or state['round2_done']),
            ("10. [第二轮] 确认 Gen 1 已同步完成（频率/幅值与 Gen 2 匹配）",
             r2_synced or state['round2_done']),
            ("11. [第二轮] 记录结果：Gen 2 基准 → Gen 1 同步完成",
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

        # 前提：第一、二、三步必须已完成
        if not self.is_loop_test_complete():
            self._set_sync_test_feedback("请先完成第一步【回路连通性测试】。", "red")
            return
        if not self.is_pt_phase_check_complete():
            self._set_sync_test_feedback("请先完成第二步【PT 相序检查】。", "red")
            return
        if not (self.is_pt_exam_recorded(1) and self.is_pt_exam_recorded(2)):
            self._set_sync_test_feedback(
                "请先完成第三步【PT二次端子压差测试】（Gen1 和 Gen2 均需完成）。", "red")
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
            self._set_sync_test_feedback(
                "第二轮记录成功：Gen 2 作基准，Gen 1 同步功能正常。两台发电机同步功能测试全部完成！",
                "#006600")

    def reset_sync_test(self):
        self.sync_test_state = self._create_sync_test_state()

    def is_sync_test_complete(self):
        return (self.sync_test_state['round1_done'] and
                self.sync_test_state['round2_done'])

    def is_sync_test_rounds_done(self):
        return (self.sync_test_state['round1_done'] and
                self.sync_test_state['round2_done'])

    def finalize_sync_test(self):
        if not self.is_sync_test_rounds_done():
            self._set_sync_test_feedback("请先完成并记录两轮同步测试，再点击[完成第四步测试]。", "red")
            return
        self.sync_test_state['completed'] = True
        self._set_sync_test_feedback("第四步【同步功能测试】已确认完成，系统恢复正常自动合闸逻辑。", "#006600")

    def record_pt_measurement(self, phase):
        gen_id    = self.ui._pt_target_bg.checkedId()
        if gen_id <= 0:
            gen_id = 1
        phase = phase.upper()
        gen1, gen2 = self.sim_state.gen1, self.sim_state.gen2

        # 第一步（回路连通性测试）必须先完成
        if not self.is_loop_test_complete():
            self._set_pt_exam_feedback(
                gen_id,
                "请先完成第一步【回路连通性测试】，再进行 PT 二次端子压差测量。",
                "red")
            return
        # 第二步（PT 相序检查）必须先完成
        if not self.is_pt_phase_check_complete():
            self._set_pt_exam_feedback(
                gen_id,
                "请先完成第二步【PT 相序检查】，确认 ABC 相序正确后再进行 PT 二次端子压差测量。",
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

        if gen_id == 1:
            # 测 Gen1：Gen1 必须合闸建立母排，Gen2 不允许合闸
            if gen1.breaker_position != BreakerPosition.WORKING or not gen1.breaker_closed:
                self._set_pt_exam_feedback(1, "请将 Gen1 切至工作位置并合闸，建立母排参考电压。", "red")
                return
            if gen2.breaker_closed:
                self._set_pt_exam_feedback(1, "测试 Gen1 时请先断开 Gen2 断路器，Gen2 不应并入母排。", "red")
                return
        else:
            # 测 Gen2：Gen1 必须合闸作为母排参考，Gen2 运行但不合闸
            if gen1.breaker_position != BreakerPosition.WORKING or not gen1.breaker_closed:
                self._set_pt_exam_feedback(2, "请先确保 Gen1 已并入母排，作为母排参考电压来源。", "red")
                return
            if not gen2.running:
                self._set_pt_exam_feedback(2, "请先启动 Gen2，再进行 PT 二次端子压差测量。", "red")
                return
            if gen2.breaker_closed:
                self._set_pt_exam_feedback(2, "Gen2 断路器应保持断开，并入前才能测量有效压差。", "red")
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
        all_rec = all(self.pt_exam_states[gen_id]['records'][ph] is not None for ph in ('A', 'B', 'C'))
        if all_rec:
            msg = f"Gen {gen_id} 三相 PT 二次端子压差已全部记录完成。"
        else:
            msg = f"Gen {gen_id} {phase} 相 PT 二次端子压差记录完成：{meter_v:.1f} V。"
        self._set_pt_exam_feedback(gen_id, msg, "#006600")

    def get_pt_exam_steps(self, gen_id):
        state   = self.pt_exam_states[gen_id]
        records = state['records']
        has_any = any(records[ph] is not None for ph in ('A', 'B', 'C'))
        gen1, gen2 = self.sim_state.gen1, self.sim_state.gen2
        gnd_ok = self.sim_state.grounding_mode == "小电阻接地"
        gen1_on_bus = (gen1.breaker_position == BreakerPosition.WORKING and gen1.breaker_closed)

        if gen_id == 1:
            steps = [
                ("1. 恢复中性点小电阻接地",
                 gnd_ok or has_any),
                ("2. 将 Gen1 切至工作位置并合闸（建立母排参考）",
                 gen1_on_bus or has_any),
                ("3. 确认 Gen2 断路器处于断开状态",
                 (not gen2.breaker_closed) or has_any),
                ("4. 开启万用表并连接 PT1 与 PT2 同相端子",
                 self.sim_state.multimeter_mode or has_any),
                ("5. 记录 A 相 PT 二次端子压差", records['A'] is not None),
                ("6. 记录 B 相 PT 二次端子压差", records['B'] is not None),
                ("7. 记录 C 相 PT 二次端子压差", records['C'] is not None),
            ]
        else:
            gen2_running_not_closed = gen2.running and not gen2.breaker_closed
            steps = [
                ("1. 恢复中性点小电阻接地",
                 gnd_ok or has_any),
                ("2. 确认 Gen1 已并入母排（作为母排参考）",
                 gen1_on_bus or has_any),
                ("3. 启动 Gen2，保持断路器断开",
                 gen2_running_not_closed or has_any),
                ("4. 开启万用表并连接 PT3 与 PT2 同相端子",
                 self.sim_state.multimeter_mode or has_any),
                ("5. 记录 A 相 PT 二次端子压差", records['A'] is not None),
                ("6. 记录 B 相 PT 二次端子压差", records['B'] is not None),
                ("7. 记录 C 相 PT 二次端子压差", records['C'] is not None),
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
            self._set_pt_exam_feedback(gen_id, '请先完成 A/B/C 三相 PT 二次端子压差记录，再点击"完成第三步测试"。', "red")
            return
        state['completed'] = True
        self._set_pt_exam_feedback(gen_id, f"第三步【Gen {gen_id} PT 二次端子压差测试】已确认完成，后续操作将不再影响该步骤状态。", "#006600")

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
