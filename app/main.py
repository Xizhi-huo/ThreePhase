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
import traceback
import time
from typing import Any, Dict, Optional

# 将项目根目录加入 sys.path，确保 domain/services/ui 包可以被找到
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5 import QtWidgets, QtCore

from domain.constants import GRID_FREQ, GRID_AMP
from domain.enums import BreakerPosition, SystemMode
from domain.models import GeneratorState, SimulationState, FaultConfig
from services.assessment_service import AssessmentService
from services.assessment_coordinator import AssessmentCoordinator, StepProgressSnapshot
from services.blackbox_repair_handler import BlackboxRepairHandler, BlackboxRepairOutcome
from services.fault_manager import FaultManager
from services.physics_engine import PhysicsEngine
from services.loop_test_service import LoopTestService
from services.pt_voltage_check_service import PtVoltageCheckService
from services.pt_phase_check_service import PtPhaseCheckService
from services.pt_exam_service import PtExamService
from services.sync_test_service import SyncTestService
from services.flow_mode_manager import FlowModeManager, FlowModePolicy
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
        self._flow_mgr = FlowModeManager()
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
        self._assessment_svc      = AssessmentService(self)
        self._assessment_coord    = AssessmentCoordinator(self)
        self._blackbox_handler    = BlackboxRepairHandler(self)
        self._fault_mgr           = FaultManager(self)
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
        return self._pt_blackbox_mode_proxy

    @property
    def test_flow_mode(self):
        return self._flow_mgr.test_flow_mode

    @test_flow_mode.setter
    def test_flow_mode(self, value: str):
        self._flow_mgr.test_flow_mode = value

    def flow_policy(self) -> FlowModePolicy:
        return self._flow_mgr.flow_policy()

    def flow_policy_flag(self, name: str):
        return self._flow_mgr.flow_policy_flag(name)

    def is_teaching_mode(self):
        return self._flow_mgr.is_teaching_mode()

    def is_engineering_mode(self):
        return self._flow_mgr.is_engineering_mode()

    def is_assessment_mode(self):
        return self._flow_mgr.is_assessment_mode()

    def can_advance_with_fault(self):
        return self._flow_mgr.can_advance_with_fault()

    def require_all_measurements_before_finalize(self):
        return self._flow_mgr.require_all_measurements_before_finalize()

    def require_step_pass_to_finalize(self):
        return self._flow_mgr.require_step_pass_to_finalize()

    def should_show_fault_detected_banner(self):
        return self._flow_mgr.should_show_fault_detected_banner()

    def should_show_diagnostic_hints(self):
        return self._flow_mgr.should_show_diagnostic_hints()

    def should_block_step5_until_blackbox_fixed(self):
        return self._flow_mgr.should_block_step5_until_blackbox_fixed()

    def should_hold_at_step4_when_wiring_fault_unrepaired(self):
        return self._flow_mgr.should_hold_at_step4_when_wiring_fault_unrepaired()

    def should_show_blackbox_required_dialog_before_step5(self):
        return self._flow_mgr.should_show_blackbox_required_dialog_before_step5()

    def can_inspect_blackbox(self):
        return self._flow_mgr.can_inspect_blackbox()

    def can_repair_in_blackbox(self):
        return self._flow_mgr.can_repair_in_blackbox()

    def should_auto_clear_fault_only_when_all_blackboxes_normal(self):
        return self._flow_mgr.should_auto_clear_fault_only_when_all_blackboxes_normal()

    def allow_admin_shortcuts(self):
        return self._flow_mgr.allow_admin_shortcuts()

    def can_use_pt_exam_quick_record(self):
        return self._flow_mgr.can_use_pt_exam_quick_record()

    def should_record_assessment_metrics(self):
        return self._flow_mgr.should_record_assessment_metrics()

    def should_auto_score_assessment(self):
        return self._flow_mgr.should_auto_score_assessment()

    def assessment_ends_after_step4_closed_loop(self):
        return self._flow_mgr.assessment_ends_after_step4_closed_loop()

    def start_assessment_session(self, scene_id: str, preset_mode: str = 'specified'):
        return self._assessment_coord.start_assessment_session(scene_id, preset_mode)

    def append_assessment_event(self, event_type: str, step: int = 0, **payload):
        return self._assessment_coord.append_assessment_event(event_type, step=step, **payload)

    def mark_fault_detected(self, step: int, source: str, **payload) -> bool:
        return self._assessment_coord.mark_fault_detected(step, source, **payload)

    def capture_assessment_state_snapshot(self) -> Dict[str, Any]:
        return self._assessment_coord.capture_assessment_state_snapshot()

    def finish_assessment_session(self):
        return self._assessment_coord.finish_assessment_session()

    def requires_random_fault_identification(self, current_step: int) -> bool:
        return self._assessment_coord.requires_random_fault_identification(current_step)

    def submit_random_fault_identification(self, guessed_scene_id: str) -> bool:
        return self._assessment_coord.submit_random_fault_identification(guessed_scene_id)

    def mark_assessment_result_shown(self):
        return self._assessment_coord.mark_assessment_result_shown()

    def is_assessment_closed_loop_ready(self) -> bool:
        return self._assessment_coord.is_assessment_closed_loop_ready()

    def get_test_progress_snapshot(self, current_step: int, pre_step5_repair_triggered: bool) -> StepProgressSnapshot:
        return self._assessment_coord.get_test_progress_snapshot(current_step, pre_step5_repair_triggered)

    def finish_assessment_session_if_ready(self, current_step: int) -> Optional[object]:
        return self._assessment_coord.finish_assessment_session_if_ready(current_step)

    def get_blackbox_runtime_state(self, target: str) -> dict:
        return self._blackbox_handler.get_blackbox_runtime_state(target)

    def apply_blackbox_repair_attempt(
            self,
            target: str,
            step: int,
            *,
            initial_order=None,
            new_order=None,
            initial_pri_order=None,
            new_pri_order=None,
            initial_sec_order=None,
            new_sec_order=None) -> BlackboxRepairOutcome:
        return self._blackbox_handler.apply_blackbox_repair_attempt(
            target,
            step,
            initial_order=initial_order,
            new_order=new_order,
            initial_pri_order=initial_pri_order,
            new_pri_order=new_pri_order,
            initial_sec_order=initial_sec_order,
            new_sec_order=new_sec_order,
        )

    def record_phase_sequence(self, pt_name: str, seq: str) -> bool:
        return self._pt_phase_svc.record_phase_sequence(pt_name, seq)

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
    def resolve_pt_node_plot_key(self, node_name):
        parts = node_name.split('_', 1)
        if len(parts) != 2:
            return None
        pt_name, terminal = parts
        if pt_name not in self.pt_phase_orders or terminal not in ('A', 'B', 'C'):
            return None
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

        Returns: 'ABC' | 'ACB' | 'FAULT'
        """
        fc = self.sim_state.fault_config
        # E03：PT3 A 相极性反接 → VAB≈VCA≈相电压，VBC≈线电压，三相严重不平衡
        # 相序仪无法判定正/逆序，返回 FAULT（Widget 显示静止暗淡 + "未知"）
        if (fc.active and not fc.repaired
                and fc.scenario_id == 'E03' and pt_name == 'PT3'):
            return 'FAULT'
        phase_map = {}
        _rbc = self.sim_state.fault_reverse_bc
        for ph in ('A', 'B', 'C'):
            node = f"{pt_name}_{ph}"
            key = self.resolve_pt_node_plot_key(node)
            if key is None or key[-1] not in ('a', 'b', 'c'):
                return 'FAULT'
            actual = key[-1]   # 'a', 'b', or 'c'（基于 pt_phase_orders 的 key 名）
            # fault_reverse_bc 物理上对调 Gen2 B/C 绕组：
            # key 'g2b' 实际承载 C 相波形，'g2c' 实际承载 B 相波形
            if _rbc and key == 'g2b':
                actual = 'c'
            elif _rbc and key == 'g2c':
                actual = 'b'
            phase_map[ph] = actual

        order = (phase_map['A'], phase_map['B'], phase_map['C'])
        # 合法性校验：三端子必须对应三个不同物理相，否则为缺相/短接故障
        if len(set(order)) < 3:
            return 'FAULT'
        # 返回实际三字母相序（如 ABC、BAC、ACB 等），保留原始端子读取顺序
        return order[0].upper() + order[1].upper() + order[2].upper()

    def resolve_loop_node_phase(self, node_name):
        _, gen_name, terminal = node_name.split('_', 2)
        # G1：以 pt_phase_orders['PT2'] 为单一数据源（inject_fault/repair_fault/手动修复均写此处）
        if gen_name == 'G1':
            idx = ('A', 'B', 'C').index(terminal)
            return self.pt_phase_orders['PT2'][idx]
        if gen_name == 'G2':
            idx = ('A', 'B', 'C').index(terminal)
            # G2 机端端子级错接由 g2_blackbox_order 表达；fault_reverse_bc 仅保留为旧内部反相陷阱兼容。
            phase = self.g2_blackbox_order[idx]
            if self.sim_state.fault_reverse_bc:
                if phase == 'B':
                    phase = 'C'
                elif phase == 'C':
                    phase = 'B'
            return phase
        return terminal

    # ════════════════════════════════════════════════════════════════════════
    # 小型辅助（被 UI 或多个服务直接调用）
    # ════════════════════════════════════════════════════════════════════════
    def _get_generator_state(self, gen_id):
        return self.sim_state.gen1 if gen_id == 1 else self.sim_state.gen2

    def _expected_pt_probe_pair(self, gen_id, gen_phase, bus_phase):
        return self._pt_exam_svc._expected_pt_probe_pair(gen_id, gen_phase, bus_phase)

    def _get_current_pt_phase_match(self, gen_id):
        return self._pt_exam_svc._get_current_pt_phase_match(gen_id)

    def _get_current_loop_phase_match(self):
        return self._loop_svc._get_current_loop_phase_match()

    def _is_gen_synced(self, follower, master, freq_tol=0.5, amp_tol=500.0):
        return self._sync_svc._is_gen_synced(follower, master, freq_tol, amp_tol)

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
    def reset_pt_exam(self, gen_id=None):
        self._pt_exam_svc.reset_pt_exam(gen_id)

    def record_pt_measurement(self, gen_phase, bus_phase, gen_id):
        self._pt_exam_svc.record_pt_measurement(gen_phase, bus_phase, gen_id)

    def record_current_pt_measurement(self, gen_id):
        """记录当前表笔位置对应的 PT 压差（由测试面板"记录当前"按钮调用）。"""
        matched = self._pt_exam_svc._get_current_pt_phase_match(gen_id)
        if matched is None:
            self._pt_exam_svc._set_pt_exam_feedback(
                gen_id, "表笔未放置在有效 PT 端子上，请在母排拓扑页放置表笔后再记录。", "red")
            return
        self._pt_exam_svc.record_pt_measurement(matched[0], matched[1], gen_id)

    def get_pt_exam_steps(self, gen_id):
        return self._pt_exam_svc.get_pt_exam_steps(gen_id)

    def is_pt_exam_recorded(self, gen_id):
        return self._pt_exam_svc.is_pt_exam_recorded(gen_id)

    def finalize_all_pt_exams(self):
        self._pt_exam_svc.finalize_all_pt_exams()

    def record_all_pt_measurements_quick(self):
        self._pt_exam_svc.record_all_pt_measurements_quick()

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
        if not gen.running and gen.mode != "manual":
            self._on_engine_blocked(
                gen_id,
                "起机条件不满足",
                f"Gen {gen_id} 只有在手动工作模式下才能起机。\n请先将工作模式切换为“手动”，再执行起机。"
            )
            return
        gen.running = not gen.running

    def _on_engine_blocked(self, gen_id: int, title: str, message: str):
        self.ui.show_warning(title, message)

    def _on_breaker_blocked(self, gen_id: int, title: str, message: str):
        """合闸被拦截时的 UI 响应钩子。由 UI 层覆写以控制弹窗和 Tab 跳转。
        控制器本身只负责状态，不直接操作视图。"""
        self.request_ui_tab(5)
        self.ui.show_warning(title, message)

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
        # ── 拦截：E01/E02/E03 故障未修复时 Gen2 工作位合闸（仅第五步同步测试中）→ 并网事故 ──
        fc = self.sim_state.fault_config
        if (gen_id == 2
                and generator.breaker_position == BreakerPosition.WORKING
                and fc.active and not fc.repaired
                and self.is_sync_test_active()):
            if fc.scenario_id == 'E01':
                self.append_assessment_event('hazard_action', step=5, action='close_gen2_breaker', reason='E01 accident')
                self.ui.show_e01_accident_dialog()
                return
            elif fc.scenario_id == 'E02':
                self.append_assessment_event('hazard_action', step=5, action='close_gen2_breaker', reason='E02 accident')
                self.ui.show_e02_accident_dialog()
                return
            elif fc.scenario_id == 'E03':
                self.append_assessment_event('hazard_action', step=5, action='close_gen2_breaker', reason='E03 accident')
                self.ui.show_e03_accident_dialog()
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

    def sync_pt1_blackbox_to_phase_orders(self):
        return self._blackbox_handler.sync_pt1_blackbox_to_phase_orders()

    def sync_g2_blackbox_to_phase_orders(self):
        return self._blackbox_handler.sync_g2_blackbox_to_phase_orders()

    def set_g2_terminal_fault(self, enabled: bool):
        self.sim_state.fault_reverse_bc = False
        self.g2_blackbox_order = ['A', 'C', 'B'] if enabled else ['A', 'B', 'C']
        self.sync_g2_blackbox_to_phase_orders()
        self.rebuild_circuit_view()

    def has_unrepaired_wiring_fault(self) -> bool:
        return self._fault_mgr.has_unrepaired_wiring_fault()

    def all_repairable_wiring_targets_normal(self) -> bool:
        return self._fault_mgr.all_repairable_wiring_targets_normal()

    def fault_has_repairable_wiring_targets(self) -> bool:
        return self._fault_mgr.fault_has_repairable_wiring_targets()

    def _get_repairable_wiring_orders(self):
        return self._fault_mgr._get_repairable_wiring_orders()

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
        self._fault_mgr.inject_fault(scenario_id)

    def repair_fault(self, step: int = 4, source: str = 'repair_fault'):
        self._fault_mgr.repair_fault(step=step, source=source)

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
        self.loop_test_state        = self._loop_svc.create_loop_test_state()
        self.pt_voltage_check_state = self._pt_voltage_svc.create_pt_voltage_check_state()
        self.pt_phase_check_state   = self._pt_phase_svc.create_pt_phase_check_state()
        self.pt_exam_states = {
            1: self._pt_exam_svc.create_pt_exam_state(),
            2: self._pt_exam_svc.create_pt_exam_state(),
        }
        self.sync_test_state = self._sync_svc.create_sync_test_state()

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
