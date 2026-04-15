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
import random
import traceback
import time
from typing import Any, Dict, Optional

# 将项目根目录加入 sys.path，确保 domain/services/ui 包可以被找到
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5 import QtWidgets, QtCore

from domain.constants import GRID_AMP
from domain.enums import SystemMode
from domain.models import GeneratorState, SimulationState, FaultConfig
from services.assessment_service import AssessmentService
from services.assessment_coordinator import AssessmentCoordinator, StepProgressSnapshot
from services.blackbox_repair_handler import BlackboxRepairHandler, BlackboxRepairOutcome
from services.fault_manager import FaultManager
from services.hardware_actions import HardwareActions
from services.physics_engine import PhysicsEngine
from services.loop_test_service import LoopTestService
from services.pt_voltage_check_service import PtVoltageCheckService
from services.pt_phase_check_service import PtPhaseCheckService
from services.pt_exam_service import PtExamService
from services.sync_test_service import SyncTestService
from services.flow_mode_manager import FlowModeManager, FlowModePolicy
from services.phase_order_resolver import PhaseOrderResolver
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
        init_amp1   = round(random.uniform(9500.0, 11500.0), 1)
        init_phase1 = round(random.uniform(-180.0, 180.0), 1)
        init_freq1  = round(random.uniform(48.0, 49.0), 1)
        init_amp2   = round(random.uniform(9500.0, 11500.0), 1)
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
        self.g1_blackbox_order = ['A', 'B', 'C']
        self.g2_blackbox_order = ['A', 'B', 'C']
        self.pt1_pri_blackbox_order = ['A', 'B', 'C']
        self.pt1_sec_blackbox_order = ['A', 'B', 'C']
        self.flow_mgr = FlowModeManager()
        self.test_flow_mode = 'teaching'
        self.pt_blackbox_mode_val: bool = False
        self._pt_blackbox_mode_proxy = self._BoolProxy(self)
        self.assessment_session = None
        self._last_fault_detected = False
        self._pending_accident_scene_id = None
        self._pending_ui_tab_index = None
        self._pending_pt_ratio_row_updates = {}
        self._consecutive_tick_failures = 0
        self._tick_error_notified = False
        self._last_tick_perf = time.perf_counter()

        # ── 业务服务（各服务通过 self._ctrl 回写状态 dataclass）─────────
        self.assessment_svc       = AssessmentService()
        self.assessment_coord     = AssessmentCoordinator(self)
        self.blackbox_handler     = BlackboxRepairHandler(self)
        self.phase_resolver       = PhaseOrderResolver(self)
        self.hw                   = HardwareActions(self)
        self.fault_mgr            = FaultManager(self)
        self.loop_svc             = LoopTestService(self)
        self.pt_voltage_svc       = PtVoltageCheckService(self)
        self.pt_phase_svc         = PtPhaseCheckService(self)
        self.pt_exam_svc          = PtExamService(self)
        self.sync_svc             = SyncTestService(self)

        # ── 状态 dataclass（UI 直接读取属性，服务通过 ctrl 写入）────────
        self.loop_test_state         = self.loop_svc.create_loop_test_state()
        self.pt_voltage_check_state  = self.pt_voltage_svc.create_pt_voltage_check_state()
        self.pt_phase_check_state    = self.pt_phase_svc.create_pt_phase_check_state()
        self.pt_exam_states          = {
            1: self.pt_exam_svc.create_pt_exam_state(),
            2: self.pt_exam_svc.create_pt_exam_state(),
        }
        self.sync_test_state         = self.sync_svc.create_sync_test_state()

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
        return self._pt_blackbox_mode_proxy

    @property
    def test_flow_mode(self):
        return self.flow_mgr.test_flow_mode

    @test_flow_mode.setter
    def test_flow_mode(self, value: str):
        self.flow_mgr.test_flow_mode = value

    def update_pt_ratio(self, ratio_attr: str, ratio: float):
        if ratio_attr not in {'pt_gen_ratio', 'pt3_ratio', 'pt_bus_ratio'}:
            raise ValueError(f"Unsupported PT ratio attribute: {ratio_attr}")
        setattr(self.sim_state, ratio_attr, ratio)

    def request_ui_tab(self, tab_index: int):
        self._pending_ui_tab_index = tab_index

    def consume_requested_ui_tab(self):
        tab_index = self._pending_ui_tab_index
        self._pending_ui_tab_index = None
        return tab_index

    def request_pt_ratio_row_update(self, ratio_attr: str, pri_value: int, sec_value: int):
        self._pending_pt_ratio_row_updates[ratio_attr] = (pri_value, sec_value)

    def consume_requested_pt_ratio_row_updates(self):
        updates = dict(self._pending_pt_ratio_row_updates)
        self._pending_pt_ratio_row_updates.clear()
        return updates

    # ════════════════════════════════════════════════════════════════════════
    # PT 节点解析辅助（physics_engine.py 通过 self.ctrl 调用）
    # ════════════════════════════════════════════════════════════════════════
    # ════════════════════════════════════════════════════════════════════════
    # 小型辅助（被 UI 或多个服务直接调用）
    # ════════════════════════════════════════════════════════════════════════
    def _get_generator_state(self, gen_id):
        return self.sim_state.gen1 if gen_id == 1 else self.sim_state.gen2

    def set_loop_test_feedback(self, message, color='#444444'):
        self.loop_test_state.feedback = message
        self.loop_test_state.feedback_color = color

    def record_loop_test_result(self, phase, status, reading):
        self.loop_test_state.records[phase] = {
            'status': status,
            'reading': reading,
        }

    def mark_loop_test_completed(self):
        self.loop_test_state.completed = True

    def set_pt_phase_check_feedback(self, message, color='#444444'):
        self.pt_phase_check_state.feedback = message
        self.pt_phase_check_state.feedback_color = color

    def record_pt_phase_check_result(self, key, phase_match, reading, actual_phase=None):
        self.pt_phase_check_state.records[key] = {
            'phase_match': phase_match,
            'reading': reading,
        }
        if actual_phase is not None:
            self.pt_phase_check_state.records[key]['actual_phase'] = actual_phase

    def mark_pt_phase_check_completed(self):
        self.pt_phase_check_state.completed = True

    # ════════════════════════════════════════════════════════════════════════
    # 第一步：回路连通性测试 — 委托给 LoopTestService
    # ════════════════════════════════════════════════════════════════════════
    def record_loop_measurement(self, phase):
        self.loop_svc.record_loop_measurement(phase)

    def finalize_loop_test(self):
        self.loop_svc.finalize_loop_test()

    def reset_loop_test(self):
        self.loop_svc.reset_loop_test()
        self.exit_loop_test_mode()

    def enter_loop_test_mode(self):
        """进入第一步回路检查模式：跳过失压联锁，允许不起机合闸。"""
        self.sim_state.loop_test_mode = True

    def get_loop_test_steps(self):
        return self.loop_svc.get_loop_test_steps()

    def get_current_loop_phase_match(self):
        return self.loop_svc._get_current_loop_phase_match()

    def is_loop_test_complete(self):
        return self.loop_svc.is_loop_test_complete()

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
    def record_pt_voltage_measurement(self, pt_name, phase_pair):
        self.pt_voltage_svc.record_pt_voltage_measurement(pt_name, phase_pair)

    def finalize_pt_voltage_check(self):
        self.pt_voltage_svc.finalize_pt_voltage_check()

    def reset_pt_voltage_check(self):
        self.pt_voltage_svc.reset_pt_voltage_check()

    def start_pt_voltage_check(self):
        self.pt_voltage_svc.start_pt_voltage_check()

    def stop_pt_voltage_check(self):
        self.pt_voltage_svc.stop_pt_voltage_check()

    def get_pt_voltage_check_steps(self):
        return self.pt_voltage_svc.get_pt_voltage_check_steps()

    # ════════════════════════════════════════════════════════════════════════
    # 第三步：PT 相序检查 — 委托给 PtPhaseCheckService
    # ════════════════════════════════════════════════════════════════════════
    def record_pt_phase_check(self, pt_name, phase):
        self.pt_phase_svc.record_pt_phase_check(pt_name, phase)

    def finalize_pt_phase_check(self):
        self.pt_phase_svc.finalize_pt_phase_check()

    def start_pt_phase_check(self):
        self.pt_phase_svc.start_pt_phase_check()

    def stop_pt_phase_check(self):
        self.pt_phase_svc.stop_pt_phase_check()

    def reset_pt_phase_check(self):
        self.pt_phase_svc.reset_pt_phase_check()

    def get_pt_phase_check_steps(self):
        return self.pt_phase_svc.get_pt_phase_check_steps()

    # ════════════════════════════════════════════════════════════════════════
    # 第四步：PT 二次端子压差考核 — 委托给 PtExamService
    # ════════════════════════════════════════════════════════════════════════
    def reset_pt_exam(self, gen_id=None):
        self.pt_exam_svc.reset_pt_exam(gen_id)

    def record_pt_measurement(self, gen_phase, bus_phase, gen_id):
        self.pt_exam_svc.record_pt_measurement(gen_phase, bus_phase, gen_id)

    def record_current_pt_measurement(self, gen_id):
        """记录当前表笔位置对应的 PT 压差（由测试面板"记录当前"按钮调用）。"""
        matched = self.pt_exam_svc._get_current_pt_phase_match(gen_id)
        if matched is None:
            self.pt_exam_svc._set_pt_exam_feedback(
                gen_id, "表笔未放置在有效 PT 端子上，请在母排拓扑页放置表笔后再记录。", "red")
            return
        self.pt_exam_svc.record_pt_measurement(matched[0], matched[1], gen_id)

    def finalize_all_pt_exams(self):
        self.pt_exam_svc.finalize_all_pt_exams()

    def record_all_pt_measurements_quick(self):
        self.pt_exam_svc.record_all_pt_measurements_quick()

    def start_pt_exam(self, gen_id):
        self.pt_exam_svc.start_pt_exam(gen_id)

    def stop_pt_exam(self, gen_id):
        self.pt_exam_svc.stop_pt_exam(gen_id)

    # ════════════════════════════════════════════════════════════════════════
    # 第五步：同步功能测试 — 委托给 SyncTestService
    # ════════════════════════════════════════════════════════════════════════
    def record_sync_round(self, round_num):
        self.sync_svc.record_sync_round(round_num)

    def is_sync_test_active(self):
        """同步测试已开始但尚未最终完成——此期间屏蔽自动合闸。"""
        return self.sync_test_state.started and not self.sync_test_state.completed

    def finalize_sync_test(self):
        self.sync_svc.finalize_sync_test()

    def reset_sync_test(self):
        self.sync_svc.reset_sync_test()

    def start_sync_test(self):
        self.sync_svc.start_sync_test()

    def stop_sync_test(self):
        self.sync_svc.stop_sync_test()

    def queue_accident_dialog(self, scene_id: str):
        if self._pending_accident_scene_id is None:
            self._pending_accident_scene_id = scene_id

    def _consume_pending_accident_dialog(self):
        scene_id = self._pending_accident_scene_id
        self._pending_accident_scene_id = None
        if scene_id == 'E01':
            self.ui.show_e01_accident_dialog()
        elif scene_id == 'E02':
            self.ui.show_e02_accident_dialog()
        elif scene_id == 'E03':
            self.ui.show_e03_accident_dialog()

    def _handle_tick_failure(self, stage: str):
        self._consecutive_tick_failures += 1
        traceback.print_exc()
        if self._consecutive_tick_failures >= 3 and not self._tick_error_notified:
            self.ui.statusBar().showMessage(
                f"物理帧更新连续失败 {self._consecutive_tick_failures} 次（阶段: {stage}），请检查控制台错误日志。"
            )
            self._tick_error_notified = True

    def _clear_tick_failure_state(self):
        if self._consecutive_tick_failures > 0:
            self.ui.statusBar().clearMessage()
        self._consecutive_tick_failures = 0
        self._tick_error_notified = False

    def toggle_pause(self):
        self.sim_state.paused = not self.sim_state.paused
        self.ui.pause_btn.setText(
            "▶ 恢复物理时空" if self.sim_state.paused else "⏸ 暂停整个物理空间"
        )
        self.ui._apply_button_tone(
            self.ui.pause_btn,
            "success" if self.sim_state.paused else "warning",
            hero=True,
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

    def reset_blackbox_orders(self):
        self.g1_blackbox_order = ['A', 'B', 'C']
        self.g2_blackbox_order = ['A', 'B', 'C']
        self.pt1_pri_blackbox_order = ['A', 'B', 'C']
        self.pt1_sec_blackbox_order = ['A', 'B', 'C']

    def set_g2_terminal_fault(self, enabled: bool):
        self.sim_state.fault_reverse_bc = False
        self.g2_blackbox_order = ['A', 'C', 'B'] if enabled else ['A', 'B', 'C']
        self.blackbox_handler.sync_g2_blackbox_to_phase_orders()
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
    # 故障训练模式（FaultConfig 管理）
    # ════════════════════════════════════════════════════════════════════════
    def inject_fault(self, scenario_id: str):
        self.fault_mgr.inject_fault(scenario_id)

    def repair_fault(self, step: int = 4, source: str = 'repair_fault'):
        self.fault_mgr.repair_fault(step=step, source=source)

    def reset_for_scenario(self, scenario_id: str):
        """
        完整重置：停机 → 清空所有测试状态 → 注入新故障。
        管理员选定场景后调用，学员在全新状态下开始训练。
        """
        sim = self.sim_state
        # 1. 停止发电机，断路器复位
        sim.gen1.running = False
        sim.gen2.running = False
        sim.gen1.breaker_closed = False
        sim.gen2.breaker_closed = False
        sim.gen1.cmd_close = False
        sim.gen2.cmd_close = False
        sim.loop_test_mode = False

        # 2. 重置所有步骤状态
        self.loop_test_state        = self.loop_svc.create_loop_test_state()
        self.pt_voltage_check_state = self.pt_voltage_svc.create_pt_voltage_check_state()
        self.pt_phase_check_state   = self.pt_phase_svc.create_pt_phase_check_state()
        self.pt_exam_states = {
            1: self.pt_exam_svc.create_pt_exam_state(),
            2: self.pt_exam_svc.create_pt_exam_state(),
        }
        self.sync_test_state = self.sync_svc.create_sync_test_state()

        # 3. 恢复 PT 相序（inject_fault 会再按场景设置）
        self.pt_phase_orders = {
            'PT1': ['A', 'B', 'C'],
            'PT2': ['A', 'B', 'C'],
            'PT3': ['A', 'B', 'C'],
        }
        self.reset_blackbox_orders()
        self.sim_state.fault_reverse_bc = False

        # 4. 注入新故障
        self.inject_fault(scenario_id)
        self._last_fault_detected = False

        # 5. 刷新电路图
        try:
            self.rebuild_circuit_view()
        except Exception:
            traceback.print_exc()

    # ════════════════════════════════════════════════════════════════════════
    # 主循环（QTimer 每 33ms 触发）
    # ════════════════════════════════════════════════════════════════════════
    def _tick(self):
        now_perf = time.perf_counter()
        frame_dt = max(0.0, now_perf - self._last_tick_perf)
        self._last_tick_perf = now_perf
        try:
            self.physics.frame_dt = frame_dt
            self.physics.update_physics()
            fc = self.sim_state.fault_config
            self._last_fault_detected = bool(fc.detected)
            rs = self.physics.build_render_state()
        except Exception:
            self._handle_tick_failure("physics")
            return

        try:
            self.ui.render_visuals(rs)
            self._consume_pending_accident_dialog()
            self._clear_tick_failure_state()
        except Exception:
            self._handle_tick_failure("render")


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
