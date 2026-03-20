"""
app/main.py  ──  PyQt5 版本
三相电并网仿真教学系统 · 控制器层 + 程序入口

架构说明
────────
PowerSyncController   唯一数据源 (SimulationState) + 编排层
  ├─ LoopTestService          第一步：回路连通性测试业务逻辑
  ├─ PtVoltageCheckService    第二步：PT 单体线电压检查业务逻辑
  ├─ PtPhaseCheckService      第三步：PT 相序检查业务逻辑
  ├─ PtExamService            第四步：PT 二次端子压差考核业务逻辑
  └─ SyncTestService          第五步：同步功能测试业务逻辑
PhysicsEngine         物理计算，通过 ctrl.sim_state 读写，build_render_state() 输出快照
PowerSyncUI           视图，通过 ctrl 引用读写状态，render_visuals(rs) 消费 RenderState
QTimer                每 33ms 驱动主循环
"""

import sys
import os
import math
import random

# 将项目根目录加入 sys.path，确保 domain/services/ui 包可以被找到
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5 import QtWidgets, QtCore

from domain.constants import GRID_FREQ, GRID_AMP
from domain.enums import BreakerPosition, SystemMode
from domain.models import GeneratorState, SimulationState
from services.physics_engine import PhysicsEngine
from services.loop_test_service import LoopTestService
from services.pt_voltage_check_service import PtVoltageCheckService
from services.pt_phase_check_service import PtPhaseCheckService
from services.pt_exam_service import PtExamService
from services.sync_test_service import SyncTestService
from ui.main_window import PowerSyncUI


class PowerSyncController:
    """
    编排层控制器。
    持有 sim_state（唯一数据源）、四个业务服务、physics 和 ui。
    所有测试业务逻辑委托给对应 Service；控制器只保留：
      · 状态字典的所有权（供 UI 直接读取）
      · PT 节点解析辅助（physics_engine 通过 ctrl 调用）
      · 硬件控制动作（toggle_engine / toggle_breaker 等）
      · loop_test_mode 开关（跨步骤共用）
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

        # PT 相序（黑盒考核时随机打乱）
        self.pt_phase_orders = {
            'PT1': ['A', 'B', 'C'],
            'PT2': ['A', 'B', 'C'],
            'PT3': ['A', 'B', 'C'],
        }
        self.pt_blackbox_mode_val: bool = False

        # ── 业务服务（各服务通过 self._ctrl 回写状态 dataclass）─────────
        self._loop_svc            = LoopTestService(self)
        self._pt_voltage_svc      = PtVoltageCheckService(self)
        self._pt_phase_svc        = PtPhaseCheckService(self)
        self._pt_exam_svc         = PtExamService(self)
        self._sync_svc            = SyncTestService(self)

        # ── 状态 dataclass（UI 直接读取属性，服务通过 ctrl 写入）────────
        self.loop_test_state         = self._loop_svc.create_loop_test_state()
        self.pt_voltage_check_state  = self._pt_voltage_svc.create_pt_voltage_check_state()
        self.pt_phase_check_state    = self._pt_phase_svc.create_pt_phase_check_state()
        self.pt_exam_states          = {
            1: self._pt_exam_svc.create_pt_exam_state(),
            2: self._pt_exam_svc.create_pt_exam_state(),
        }
        self.sync_test_state         = self._sync_svc.create_sync_test_state()

        # ── 物理引擎 ──────────────────────────────────────────────────────
        self.physics = PhysicsEngine(self)

        # ── UI 窗口 ───────────────────────────────────────────────────────
        self.ui = PowerSyncUI(self)

        # ── 主循环定时器（33ms ≈ 30fps）──────────────────────────────────
        self._timer = QtCore.QTimer()
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    # ════════════════════════════════════════════════════════════════════════
    # pt_blackbox_mode 兼容接口（circuit_tab.py 调用 ctrl.pt_blackbox_mode.get()）
    # ════════════════════════════════════════════════════════════════════════
    class _BoolProxy:
        """轻量代理，让 ui 中的 ctrl.pt_blackbox_mode.get() 调用不报错。"""
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
    # PT 节点解析辅助（physics_engine.py 通过 self.ctrl 调用）
    # ════════════════════════════════════════════════════════════════════════
    def resolve_pt_node_plot_key(self, node_name):
        pt_name, terminal = node_name.split('_', 1)
        terminal_index = ('A', 'B', 'C').index(terminal)
        actual_phase = self.pt_phase_orders[pt_name][terminal_index]
        if pt_name == 'PT3':
            # PT3 始终读 Gen2 自身的发电电压（Gen2 起机不合闸时提供相序参考）
            prefix = 'g2'
        else:
            prefix = {'PT1': 'g1', 'PT2': 'g'}[pt_name]
        return f"{prefix}{actual_phase.lower()}"

    def get_pt_phase_sequence(self, pt_name: str) -> str:
        """
        返回 pt_name（'PT1' 或 'PT3'）的三相实际相序。

        原理：通过 resolve_pt_node_plot_key 获取三个端子对应的实际物理波形
        （'a'/'b'/'c'），判断 A-B-C 端子标注是否构成 ABC（正序）或 ACB（逆序）。

        Returns: 'ABC' | 'ACB'
        """
        phase_map = {}
        for ph in ('A', 'B', 'C'):
            node = f"{pt_name}_{ph}"
            key = self.resolve_pt_node_plot_key(node)
            phase_map[ph] = key[-1]   # 'a', 'b', or 'c'

        order = (phase_map['A'], phase_map['B'], phase_map['C'])
        # 合法性校验：三端子必须对应三个不同物理相，否则为缺相/短接故障
        if len(set(order)) < 3:
            return 'FAULT'
        # 顺序组合为 ABC（任意循环位移均视为正序）
        abc_orders = {('a', 'b', 'c'), ('b', 'c', 'a'), ('c', 'a', 'b')}
        return 'ABC' if order in abc_orders else 'ACB'

    def resolve_loop_node_phase(self, node_name):
        _, gen_name, terminal = node_name.split('_', 2)
        if gen_name == 'G2' and self.sim_state.fault_reverse_bc:
            return {'A': 'A', 'B': 'C', 'C': 'B'}[terminal]
        return terminal

    # ════════════════════════════════════════════════════════════════════════
    # 小型辅助（被 UI 或多个服务直接调用）
    # ════════════════════════════════════════════════════════════════════════
    def _get_generator_state(self, gen_id):
        return self.sim_state.gen1 if gen_id == 1 else self.sim_state.gen2

    def _expected_pt_probe_pair(self, gen_id, phase):
        return self._pt_exam_svc._expected_pt_probe_pair(gen_id, phase)

    def _get_current_pt_phase_match(self, gen_id):
        return self._pt_exam_svc._get_current_pt_phase_match(gen_id)

    def _get_current_loop_phase_match(self):
        return self._loop_svc._get_current_loop_phase_match()

    def _is_gen_synced(self, follower, master, freq_tol=0.5, amp_tol=500.0):
        return self._sync_svc._is_gen_synced(follower, master, freq_tol, amp_tol)

    # ════════════════════════════════════════════════════════════════════════
    # 第一步：回路连通性测试 — 委托给 LoopTestService
    # ════════════════════════════════════════════════════════════════════════
    def get_loop_test_steps(self):
        return self._loop_svc.get_loop_test_steps()

    def record_loop_measurement(self, phase):
        self._loop_svc.record_loop_measurement(phase)

    def is_loop_test_complete(self):
        return self._loop_svc.is_loop_test_complete()

    def finalize_loop_test(self):
        self._loop_svc.finalize_loop_test()

    def reset_loop_test(self):
        self._loop_svc.reset_loop_test()
        self.exit_loop_test_mode()

    def get_loop_test_blockers(self):
        return self._loop_svc.get_loop_test_blockers()

    def enter_loop_test_mode(self):
        """进入第一步回路检查模式：跳过失压联锁，允许不起机合闸。"""
        self.sim_state.loop_test_mode = True

    def exit_loop_test_mode(self):
        """退出第一步回路检查模式：恢复失压联锁保护，未起机或未建压的断路器自动断开。"""
        self.sim_state.loop_test_mode = False
        # 失压联锁：未起机 或 电压幅值低于 20% 额定（仿真中未励磁/未起机均满足此条件）
        _voltage_threshold = GRID_AMP * 0.2
        for gen in (self.sim_state.gen1, self.sim_state.gen2):
            if gen.breaker_closed and (not gen.running or gen.amp < _voltage_threshold):
                gen.breaker_closed = False
    # ════════════════════════════════════════════════════════════════════════
    # 第二步：PT 单体线电压检查 — 委托给 PtVoltageCheckService
    # ════════════════════════════════════════════════════════════════════════
    def get_pt_voltage_check_steps(self):
        return self._pt_voltage_svc.get_pt_voltage_check_steps()

    def record_pt_voltage_measurement(self, pt_name, phase_pair):
        self._pt_voltage_svc.record_pt_voltage_measurement(pt_name, phase_pair)

    def is_pt_voltage_check_complete(self):
        return self._pt_voltage_svc.is_pt_voltage_check_complete()

    def finalize_pt_voltage_check(self):
        self._pt_voltage_svc.finalize_pt_voltage_check()

    def reset_pt_voltage_check(self):
        self._pt_voltage_svc.reset_pt_voltage_check()

    def start_pt_voltage_check(self):
        self._pt_voltage_svc.start_pt_voltage_check()

    def stop_pt_voltage_check(self):
        self._pt_voltage_svc.stop_pt_voltage_check()

    def get_pt_voltage_check_blockers(self):
        return self._pt_voltage_svc.get_pt_voltage_check_blockers()

    # ════════════════════════════════════════════════════════════════════════
    # 第三步：PT 相序检查 — 委托给 PtPhaseCheckService
    # ════════════════════════════════════════════════════════════════════════
    def get_pt_phase_check_steps(self):
        return self._pt_phase_svc.get_pt_phase_check_steps()

    def record_pt_phase_check(self, pt_name, phase):
        self._pt_phase_svc.record_pt_phase_check(pt_name, phase)

    def is_pt_phase_check_complete(self):
        return self._pt_phase_svc.is_pt_phase_check_complete()

    def finalize_pt_phase_check(self):
        self._pt_phase_svc.finalize_pt_phase_check()

    def start_pt_phase_check(self):
        self._pt_phase_svc.start_pt_phase_check()

    def stop_pt_phase_check(self):
        self._pt_phase_svc.stop_pt_phase_check()

    def reset_pt_phase_check(self):
        self._pt_phase_svc.reset_pt_phase_check()

    # ════════════════════════════════════════════════════════════════════════
    # 第四步：PT 二次端子压差考核 — 委托给 PtExamService
    # ════════════════════════════════════════════════════════════════════════
    def _is_pt_exam_setup_ready(self, gen_id):
        return self._pt_exam_svc._is_pt_exam_setup_ready(gen_id)

    def reset_pt_exam(self, gen_id=None):
        self._pt_exam_svc.reset_pt_exam(gen_id)

    def record_pt_measurement(self, phase, gen_id):
        self._pt_exam_svc.record_pt_measurement(phase, gen_id)

    def get_pt_exam_steps(self, gen_id):
        return self._pt_exam_svc.get_pt_exam_steps(gen_id)

    def get_pt_exam_close_blockers(self, gen_id):
        return self._pt_exam_svc.get_pt_exam_close_blockers(gen_id)

    def is_pt_exam_recorded(self, gen_id):
        return self._pt_exam_svc.is_pt_exam_recorded(gen_id)

    def is_pt_exam_ready(self, gen_id):
        return self._pt_exam_svc.is_pt_exam_ready(gen_id)

    def finalize_pt_exam(self, gen_id):
        self._pt_exam_svc.finalize_pt_exam(gen_id)

    def finalize_all_pt_exams(self):
        self._pt_exam_svc.finalize_all_pt_exams()

    def start_pt_exam(self, gen_id):
        self._pt_exam_svc.start_pt_exam(gen_id)

    def stop_pt_exam(self, gen_id):
        self._pt_exam_svc.stop_pt_exam(gen_id)

    # ════════════════════════════════════════════════════════════════════════
    # 第五步：同步功能测试 — 委托给 SyncTestService
    # ════════════════════════════════════════════════════════════════════════
    def get_sync_test_steps(self):
        return self._sync_svc.get_sync_test_steps()

    def record_sync_round(self, round_num):
        self._sync_svc.record_sync_round(round_num)

    def is_sync_test_complete(self):
        return self._sync_svc.is_sync_test_complete()

    def is_sync_test_active(self):
        """同步测试已开始但尚未最终完成——此期间屏蔽自动合闸。"""
        return self.sync_test_state.started and not self.sync_test_state.completed

    def is_sync_test_rounds_done(self):
        return self._sync_svc.is_sync_test_rounds_done()

    def finalize_sync_test(self):
        self._sync_svc.finalize_sync_test()

    def reset_sync_test(self):
        self._sync_svc.reset_sync_test()

    def start_sync_test(self):
        self._sync_svc.start_sync_test()

    def stop_sync_test(self):
        self._sync_svc.stop_sync_test()

    def get_sync_test_blockers(self):
        return self._sync_svc.get_sync_test_blockers()

    # ════════════════════════════════════════════════════════════════════════
    # 合闸前置流程检查
    # ════════════════════════════════════════════════════════════════════════
    def get_preclose_flow_blockers(self, gen_id):
        sections = []
        loop_done = self.is_loop_test_complete()

        if not loop_done:
            # 第一步未完成：同时列出所有后续步骤，让用户一次看到全部要求
            sections.append(("第一步：回路连通性测试", ["三相回路连通性测试尚未完成"]))
            if not self.is_pt_voltage_check_complete():
                sections.append(("第二步：PT 单体线电压检查", ["PT1/PT2/PT3 线电压检查尚未完成"]))
            if not self.is_pt_phase_check_complete():
                sections.append(("第三步：PT 相序检查", ["PT1/PT3 相序检查尚未完成"]))
            if not self.is_pt_exam_recorded(2):
                sections.append(("第四步：PT 二次端子压差考核（Gen 2）",
                                 ["Gen 2 三相 PT 二次端子压差尚未全部记录"]))
            if not self.is_sync_test_complete() and not self.is_sync_test_active():
                sections.append(("第五步：同步功能测试",
                                 ["同步功能测试尚未完成（需完成两轮同步跟踪记录）"]))
        elif gen_id == 1:
            # Gen1 合闸：若母排已由 Gen2 供电，Gen1 也必须先完成同期测试
            bus_live = getattr(self.physics, 'bus_live', False)
            bus_ref  = getattr(self.physics, 'bus_reference_gen', None)
            if bus_live and bus_ref == 2:
                if not self.is_sync_test_complete() and not self.is_sync_test_active():
                    sections.append(("第五步：同步功能测试",
                                     ["母排当前由 Gen 2 供电，Gen 1 合闸前需完成同步功能测试"]))
        elif gen_id == 2:
            # 第一步已完成；Gen1 已建立母排参考，Gen2 需完成第二至五步
            if not self.is_pt_voltage_check_complete():
                sections.append(("第二步：PT 单体线电压检查", ["PT1/PT2/PT3 线电压检查尚未完成"]))
            if not self.is_pt_phase_check_complete():
                sections.append(("第三步：PT 相序检查", ["PT1/PT3 相序检查尚未完成"]))
            if not self.is_pt_exam_recorded(2):
                sections.append(("第四步：PT 二次端子压差考核（Gen 2）",
                                 ["Gen 2 三相 PT 二次端子压差尚未全部记录"]))
            # 同步测试进行中（Gen2 需合闸作第二轮基准）不拦截
            if not self.is_sync_test_complete() and not self.is_sync_test_active():
                sections.append(("第五步：同步功能测试",
                                 ["同步功能测试尚未完成（需完成两轮同步跟踪记录）"]))
        return sections

    def _should_enforce_pt_exam_before_close(self):
        return self.sim_state.grounding_mode != "断开"

    def _should_limit_close_to_selected_pt_target(self):
        sim = self.sim_state
        return (
            sim.grounding_mode == "小电阻接地" and
            sim.gen1.mode == "manual" and
            sim.gen2.mode == "manual" and
            not self.is_sync_test_complete() and
            self.pt_exam_states[1].started
        )

    # ════════════════════════════════════════════════════════════════════════
    # 控制动作（直接操作 sim_state，不经过服务）
    # ════════════════════════════════════════════════════════════════════════
    def instant_sync(self):
        # 若母排已带电，相位必须跟随母排当前动态相角，不能强行清零
        # （bus_phase 由物理引擎实时维护，单位为弧度）
        if getattr(self.physics, 'bus_live', False):
            target_phase_deg = math.degrees(self.physics.bus_phase)
        else:
            target_phase_deg = 0.0   # 母排无电时建立参考，0° 合法
        for gen in (self.sim_state.gen1, self.sim_state.gen2):
            gen.freq      = GRID_FREQ
            gen.amp       = GRID_AMP
            gen.phase_deg = target_phase_deg

    def toggle_engine(self, gen_id: int):
        gen = self._get_generator_state(gen_id)
        gen.running = not gen.running

    def _on_breaker_blocked(self, gen_id: int, title: str, message: str):
        """合闸被拦截时的 UI 响应钩子。由 UI 层覆写以控制弹窗和 Tab 跳转。
        控制器本身只负责状态，不直接操作视图。"""
        self.ui.tab_widget.setCurrentIndex(5)
        self.ui.show_warning(title, message)

    def toggle_breaker(self, gen_id: int):
        generator = self._get_generator_state(gen_id)
        if generator.breaker_closed:
            generator.breaker_closed = False
            return
        # ── 拦截：Gen1 考核期间禁止 Gen2 合闸 ─────────────────────────────
        if gen_id == 2 and self._should_limit_close_to_selected_pt_target():
            self._pt_exam_svc._set_pt_exam_feedback(
                1,
                "当前第四步正在测试 Gen 1，请先完成 Gen 1 的 PT 二次端子压差测试，再合闸 Gen 2。",
                "red"
            )
            self._on_breaker_blocked(
                gen_id,
                "当前机组不允许合闸",
                "第四步 PT 测试当前锁定在 Gen 1。\n请先完成 Gen 1 的测试，再合闸 Gen 2。"
            )
            return
        # ── 拦截：工作位合闸前置流程检查 ──────────────────────────────────
        if (generator.breaker_position == BreakerPosition.WORKING
                and self._should_enforce_pt_exam_before_close()):
            blocker_sections = self.get_preclose_flow_blockers(gen_id)
            if blocker_sections:
                msg_lines = ["隔离母排模式下合闸前流程尚未完成，当前不能合闸："]
                for section_title, items in blocker_sections:
                    msg_lines.append(f"\n{section_title}")
                    msg_lines.extend(f"{i}. {item}" for i, item in enumerate(items, 1))
                warn_msg = "\n".join(msg_lines)
                self._pt_exam_svc._set_pt_exam_feedback(
                    gen_id, warn_msg.replace("\n", "；"), "red")
                self._on_breaker_blocked(gen_id, "合闸前步骤未完成", warn_msg)
                return
        generator.cmd_close = True

    def toggle_feeder(self):
        self.sim_state.feeder_closed = not self.sim_state.feeder_closed

    def toggle_pause(self):
        self.sim_state.paused = not self.sim_state.paused
        self.ui.pause_btn.setText(
            "▶ 恢复物理时空" if self.sim_state.paused else "⏸ 暂停整个物理空间"
        )
        self.ui.pause_btn.setStyleSheet(
            f"background:{'#99ff99' if self.sim_state.paused else '#ffcc00'}; "
            f"font-weight:bold; font-size:13px; padding:7px;"
        )

    def reshuffle_pt_phase_orders(self):
        # 不强制排除正序结果，允许随机到 ABC（真实排故训练包含"本就正确"的场景）
        base = ['A', 'B', 'C']
        for pt_name in self.pt_phase_orders:
            new_order = base[:]
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
            rs = self.physics.build_render_state()
            self.ui.render_visuals(rs)
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
    app.setStyle("Fusion")

    ctrl = PowerSyncController()
    ctrl.ui.showMaximized()

    sys.exit(app.exec_())
