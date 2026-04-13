"""
services/pt_voltage_check_service.py
PT 单体线电压检查服务（第二步）

在进行 PT 相序检查之前，先用万用表逐一测量 PT1/PT2/PT3 各自的三相线电压（AB/BC/CA），
确认各 PT 输出电压量级一致（均约 100V AC），为后续相序比对提供基准验证。

测量方式：红表笔接同一 PT 的一相端子，黑表笔接同一 PT 的另一相端子。
"""

from domain.enums import BreakerPosition
from domain.test_states import PtVoltageCheckState, _PHASE_PAIR_LABEL

_ALL_KEYS = (
    'PT1_AB', 'PT1_BC', 'PT1_CA',
    'PT2_AB', 'PT2_BC', 'PT2_CA',
    'PT3_AB', 'PT3_BC', 'PT3_CA',
)

# 每个记录键对应的实际节点对
_KEY_TO_NODES = {
    'PT1_AB': ('PT1_A', 'PT1_B'), 'PT1_BC': ('PT1_B', 'PT1_C'), 'PT1_CA': ('PT1_C', 'PT1_A'),
    'PT2_AB': ('PT2_A', 'PT2_B'), 'PT2_BC': ('PT2_B', 'PT2_C'), 'PT2_CA': ('PT2_C', 'PT2_A'),
    'PT3_AB': ('PT3_A', 'PT3_B'), 'PT3_BC': ('PT3_B', 'PT3_C'), 'PT3_CA': ('PT3_C', 'PT3_A'),
}

# 反查：frozenset(节点对) → 记录键
_NODES_TO_KEY = {frozenset(v): k for k, v in _KEY_TO_NODES.items()}


class PtVoltageCheckService:
    """PT 单体线电压检查业务逻辑。"""

    def __init__(self, ctrl):
        self._ctrl = ctrl

    # ── 状态工厂 ──────────────────────────────────────────────────────────────
    def create_pt_voltage_check_state(self) -> PtVoltageCheckState:
        return PtVoltageCheckState()

    def start_pt_voltage_check(self):
        self._ctrl.pt_voltage_check_state.started = True

    def stop_pt_voltage_check(self):
        self._ctrl.pt_voltage_check_state.started = False

    def _set_feedback(self, message, color='#444444'):
        self._ctrl.pt_voltage_check_state.feedback = message
        self._ctrl.pt_voltage_check_state.feedback_color = color

    # ── 步骤列表 ──────────────────────────────────────────────────────────────
    def get_pt_voltage_check_steps(self):
        sim = self._ctrl.sim_state
        gen1, gen2 = sim.gen1, sim.gen2
        state = self._ctrl.pt_voltage_check_state
        loop_done = self._ctrl.loop_svc.is_loop_test_complete()
        gnd_ok = sim.grounding_mode == "小电阻接地"
        gen1_on_bus = (gen1.breaker_position == BreakerPosition.WORKING and gen1.breaker_closed)
        gen2_running_open = gen2.running and not gen2.breaker_closed
        rec = state.records

        pt1_done = all(rec[k] is not None for k in ('PT1_AB', 'PT1_BC', 'PT1_CA'))
        pt2_done = all(rec[k] is not None for k in ('PT2_AB', 'PT2_BC', 'PT2_CA'))
        pt3_done = all(rec[k] is not None for k in ('PT3_AB', 'PT3_BC', 'PT3_CA'))

        steps = [
            ("1. 前提：第一步回路连通性测试已完成", loop_done),
            ("2. 恢复中性点小电阻接地", gnd_ok),
            ("3. 参数核对：在停机状态下，确认控制器内已正确设置各 PT 变比（绝不可在运行中修改）",
             sim.pt_gen_ratio > 1.0 and sim.pt_bus_ratio > 1.0),
            ("4. 启动 Gen1，确认其建压并直接合闸并入无压母排（提供 PT1/PT2 参考电压）", gen1_on_bus),
            ("5. 启动 Gen2，控制器自动进入同期追赶模式，保持断路器断开（提供 PT3 参考电压）", gen2_running_open),
            ("6. 开启万用表，在母排拓扑页测量同一 PT 的两相端子", sim.multimeter_mode),
            ("7. 记录 PT1 三相线电压（AB/BC/CA）", pt1_done),
            ("8. 记录 PT2 三相线电压（AB/BC/CA）", pt2_done),
            ("9. 记录 PT3 三相线电压（AB/BC/CA）", pt3_done),
        ]
        if state.completed:
            return [(text, True) for text, _ in steps]
        return steps

    # ── 逐项记录 ──────────────────────────────────────────────────────────────
    def record_pt_voltage_measurement(self, pt_name, phase_pair):
        """
        记录 pt_name（'PT1'/'PT2'/'PT3'）的 phase_pair（'AB'/'BC'/'CA'）线电压。
        仅当 started=True 时对 records 进行写入。
        """
        sim = self._ctrl.sim_state
        gen1, gen2 = sim.gen1, sim.gen2
        state = self._ctrl.pt_voltage_check_state
        def _record_invalid(reason):
            self._ctrl.append_assessment_event(
                'measurement_invalid',
                step=2,
                target=pt_name,
                point=phase_pair,
                reason=reason,
            )

        if not state.started:
            _record_invalid("step_not_started")
            self._set_feedback("请先点击「开始第二步测试」，再进行测量记录。", "red")
            return

        pt_name = pt_name.upper()
        phase_pair = phase_pair.upper()
        key = f"{pt_name}_{phase_pair}"

        if not self._ctrl.loop_svc.is_loop_test_complete():
            _record_invalid("loop_test_incomplete")
            self._set_feedback("请先完成第一步【回路连通性测试】，再进行 PT 线电压检查。", "red")
            return
        if sim.grounding_mode != "小电阻接地":
            _record_invalid("grounding_not_ready")
            self._set_feedback("请先恢复中性点小电阻接地，再进行 PT 线电压检查。", "red")
            return
        if gen1.breaker_position != BreakerPosition.WORKING or not gen1.breaker_closed:
            _record_invalid("gen1_not_on_bus")
            self._set_feedback("请先确认 Gen1 已并入母排（工作位+合闸），作为 PT1/PT2 参考电压。", "red")
            return
        if pt_name == 'PT3':
            if not gen2.running:
                _record_invalid("gen2_not_running")
                self._set_feedback("测量 PT3 线电压时，请先启动 Gen2（保持断路器断开）。", "red")
                return
            if gen2.breaker_closed:
                _record_invalid("gen2_breaker_closed")
                self._set_feedback("测量 PT3 线电压时，Gen2 断路器应保持断开状态。", "red")
                return
        if not sim.multimeter_mode:
            _record_invalid("multimeter_disabled")
            self._set_feedback("请先开启万用表。", "red")
            return

        # 校验表笔是否放在正确的节点对上
        n1, n2 = sim.probe1_node, sim.probe2_node
        if not n1 or not n2:
            _record_invalid("probe_missing")
            self._set_feedback(
                f"请先在母排拓扑页将表笔放在 {pt_name} 的两相端子上，再点击记录。", "red")
            return

        expected_nodes = frozenset(_KEY_TO_NODES[key])
        actual_nodes = frozenset({n1, n2})
        if actual_nodes != expected_nodes:
            _record_invalid("probe_pair_mismatch")
            n1_expect, n2_expect = _KEY_TO_NODES[key]
            self._set_feedback(
                f"当前表笔不在 {n1_expect} 与 {n2_expect} 上，请重新放置后再记录。", "red")
            return

        meter_v_sec = getattr(self._ctrl.physics, 'meter_voltage', None)   # 二次侧 ≈100V
        meter_status = getattr(self._ctrl.physics, 'meter_status', 'idle')
        if meter_v_sec is None or meter_status not in ('ok', 'danger'):
            _record_invalid("invalid_meter_status")
            self._set_feedback("当前测量结果无效，请确认表笔接在同一 PT 的两相端子上。", "red")
            return

        # 换算回一次侧线电压（教学中关心的实际电压量）
        _pt_name = (sim.probe1_node or '').split('_')[0]
        _pt_ratio = (sim.pt_gen_ratio if _pt_name == 'PT1'
                     else sim.pt3_ratio if _pt_name == 'PT3'
                     else sim.pt_bus_ratio)
        # E04：一次侧换算使用额定变比，使学员能发现二次侧读数与额定不符
        _fc = sim.fault_config
        if (_pt_name == 'PT3' and _fc.active and not _fc.repaired
                and _fc.scenario_id == 'E04'):
            _pt_ratio = 11000.0 / 193.0
        primary_v = meter_v_sec * _pt_ratio          # ≈ 10500 V（无论哪侧PT均还原一次侧）

        state.records[key] = {
            'voltage': primary_v,       # 存一次侧值，单位 V
            'voltage_sec': meter_v_sec, # 保留二次侧，供历史对比
            'reading': self._ctrl.physics.meter_reading,
        }

        self._ctrl.append_assessment_event(
            'measurement_recorded',
            step=2,
            target=pt_name,
            point=phase_pair,
            value=round(primary_v, 2),
        )
        all_rec = all(state.records[k] is not None for k in _ALL_KEYS)
        # 额定二次侧线电压 = 一次侧额定（10500V）/ 变比
        _nominal_sec = 10500.0 / _pt_ratio
        # 一次侧额定线电压 10500V，±15% 容差由二次侧 status 已判定
        if meter_status != 'ok':
            rec_color = "#cc6600"
            rec_note = (f"（⚠️ 一次侧测量值 {primary_v:.0f} V，"
                        f"二次侧 {meter_v_sec:.1f} V，偏离额定 {_nominal_sec:.0f} V，请调整后重新测量）")
        else:
            rec_color = "#006600"
            rec_note = f"（一次侧 {primary_v:.0f} V ≈ 10500 V，正常）"

        if all_rec:
            msg = f"PT1/PT2/PT3 三组线电压已全部记录完成{rec_note}，请点击「完成第二步测试」确认。"
        else:
            msg = f"{key} 线电压已记录{rec_note}，请继续测量其余项目。"
        self._set_feedback(msg, rec_color)

    def _get_probe_key(self):
        """根据当前表笔位置返回对应记录键，未对准返回 None。"""
        sim = self._ctrl.sim_state
        n1, n2 = sim.probe1_node, sim.probe2_node
        if not n1 or not n2:
            return None
        return _NODES_TO_KEY.get(frozenset({n1, n2}))

    def reset_pt_voltage_check(self):
        self._ctrl.pt_voltage_check_state = self.create_pt_voltage_check_state()

    def is_pt_voltage_check_complete(self):
        """流程门禁：只有用户点击「完成第二步测试」后才返回 True。"""
        return self._ctrl.pt_voltage_check_state.completed

    def _are_records_complete(self):
        """内部辅助：九项是否已全部记录且均在合格范围内（用于 finalize 前置校验）。
        voltage 字段存一次侧值（V），额定 10500V，±15% → [8925, 12075V]。
        """
        records = self._ctrl.pt_voltage_check_state.records
        return all(
            records[k] is not None and 8925.0 <= records[k]['voltage'] <= 12075.0
            for k in _ALL_KEYS
        )

    def _are_all_records_filled(self):
        """九项是否已全部测量（无论是否在合格范围内）。"""
        records = self._ctrl.pt_voltage_check_state.records
        return all(records[k] is not None for k in _ALL_KEYS)

    def finalize_pt_voltage_check(self):
        state = self._ctrl.pt_voltage_check_state
        fc = self._ctrl.sim_state.fault_config
        fault_training = (
            fc.active and fc.detected and not fc.repaired
            and self._ctrl.can_advance_with_fault()
        )

        if fault_training:
            # 当前流程策略允许带异常完成，但仍要求本步测量项齐全
            if not self._are_all_records_filled():
                records = state.records
                missing = [k for k in _ALL_KEYS if records[k] is None]
                self._set_feedback(
                    f'以下项目尚未完成记录：{", ".join(missing)}。请补充测量后再点击「完成第二步测试」。',
                    "red")
                return
            state.completed = True
            records = state.records
            bad = [k for k in _ALL_KEYS
                   if not (8925.0 <= records[k]['voltage'] <= 12075.0)]
            if bad:
                bad_str = "、".join(
                    f"{k}={records[k]['voltage']/1000:.2f} kV" for k in bad)
                self._set_feedback(
                    f"第二步完成（发现异常）：{bad_str} 电压偏离额定范围，"
                    f"已记录故障证据，请继续后续步骤收集更多数据，将在第五步前统一检修。",
                    "#92400e")
            else:
                self._set_feedback(
                    "第二步【PT 单体线电压检查】已确认完成，后续操作将不再影响该步骤状态。",
                    "#006600")
        else:
            # 当前流程策略要求本步全部通过后才能完成
            if not self._are_records_complete():
                records = state.records
                missing = [k for k in _ALL_KEYS if records[k] is None]
                bad = [k for k in _ALL_KEYS
                       if records[k] is not None
                       and not (8925.0 <= records[k]['voltage'] <= 12075.0)]
                if missing:
                    self._set_feedback(
                        f'以下项目尚未完成记录：{", ".join(missing)}。请补充测量后再点击「完成第二步测试」。',
                        "red")
                else:
                    bad_str = "、".join(
                        f"{k}={records[k]['voltage']/1000:.2f} kV" for k in bad)
                    self._set_feedback(
                        f'以下线电压偏离目标 10.5 kV（需在 8.925～12.075 kV 内）：{bad_str}。'
                        '请调整发电机输出电压，使各 PT 一次侧线电压均约为 10.5 kV，再点击「完成第二步测试」。',
                        "red")
                return
            state.completed = True
            self._set_feedback(
                "第二步【PT 单体线电压检查】已确认完成，后续操作将不再影响该步骤状态。",
                "#006600")

    def get_pt_voltage_check_blockers(self):
        return [text for text, done in self.get_pt_voltage_check_steps() if not done]
